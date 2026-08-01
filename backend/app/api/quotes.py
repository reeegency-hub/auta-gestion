from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_current_user, require_open_dossier
from app.core.database import get_db
from app.models import Dossier, ExtractionStatus, GarageSettings, Quote, QuoteStatus, User
from app.schemas import EmailSendIn, QuoteLinesUpdate, QuoteOut, QuoteStatusUpdate
from app.services.audit import log_action
from app.services.emailing import send_document_email
from app.services.pdfs import generate_quote_pdf
from app.services.quotes import build_quote_from_report, update_quote_lines
from app.services.storage import file_response_or_404, read_bytes

router = APIRouter(prefix="/api", tags=["quotes"])


def _load_quote(db: Session, quote_id: int, tenant_id: int) -> Quote | None:
    return (
        db.query(Quote)
        .options(joinedload(Quote.lines), joinedload(Quote.invoice))
        .filter(Quote.id == quote_id, Quote.tenant_id == tenant_id)
        .first()
    )


@router.get("/quotes", response_model=list[QuoteOut])
def list_quotes(
    status: Optional[QuoteStatus] = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    q = (
        db.query(Quote)
        .options(joinedload(Quote.lines))
        .filter(Quote.tenant_id == user.tenant_id)
    )
    if status:
        q = q.filter(Quote.status == status)
    return q.order_by(Quote.created_at.desc()).all()


@router.get("/dossiers/{dossier_id}/quotes", response_model=list[QuoteOut])
def list_dossier_quotes(
    dossier_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    dossier = (
        db.query(Dossier)
        .filter(Dossier.id == dossier_id, Dossier.tenant_id == user.tenant_id)
        .first()
    )
    if not dossier:
        raise HTTPException(status_code=404, detail="Dossier introuvable")
    return (
        db.query(Quote)
        .options(joinedload(Quote.lines))
        .filter(Quote.dossier_id == dossier_id, Quote.tenant_id == user.tenant_id)
        .order_by(Quote.version.desc())
        .all()
    )


@router.post("/dossiers/{dossier_id}/quote", response_model=QuoteOut)
def generate_quote(
    dossier_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    dossier = (
        db.query(Dossier)
        .options(
            joinedload(Dossier.client),
            joinedload(Dossier.expertise_report),
            joinedload(Dossier.quotes).joinedload(Quote.invoice),
        )
        .filter(Dossier.id == dossier_id, Dossier.tenant_id == user.tenant_id)
        .first()
    )
    require_open_dossier(dossier)
    current = dossier.quote
    if current and current.invoice:
        raise HTTPException(
            status_code=400,
            detail="Impossible de régénérer : une facture existe sur la dernière version. Créez une nouvelle version après correction.",
        )

    report = dossier.expertise_report
    if not report or report.status != ExtractionStatus.validated:
        raise HTTPException(status_code=400, detail="Validez d'abord le rapport d'expertise")
    settings = db.query(GarageSettings).filter(GarageSettings.tenant_id == user.tenant_id).first()
    if not settings:
        raise HTTPException(status_code=400, detail="Paramètres garage manquants")

    # Si devis déjà envoyé/accepté/refusé → nouvelle version
    new_version = bool(current and current.status != QuoteStatus.brouillon)
    try:
        quote = build_quote_from_report(
            db, dossier_id, user.tenant_id, report, settings, new_version=new_version
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    pdf_name = generate_quote_pdf(quote, dossier, dossier.client, settings)
    quote.pdf_filename = pdf_name
    log_action(db, dossier_id, user, "quote_generated", f"{quote.number} v{quote.version}")
    db.commit()
    return _load_quote(db, quote.id, user.tenant_id)


@router.get("/dossiers/{dossier_id}/quote", response_model=QuoteOut)
def get_quote(
    dossier_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    quote = (
        db.query(Quote)
        .options(joinedload(Quote.lines))
        .filter(Quote.dossier_id == dossier_id, Quote.tenant_id == user.tenant_id)
        .order_by(Quote.version.desc())
        .first()
    )
    if not quote:
        raise HTTPException(status_code=404, detail="Devis introuvable")
    return quote


@router.put("/quotes/{quote_id}/lines", response_model=QuoteOut)
def edit_quote_lines(
    quote_id: int,
    payload: QuoteLinesUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    quote = _load_quote(db, quote_id, user.tenant_id)
    if not quote:
        raise HTTPException(status_code=404, detail="Devis introuvable")
    if quote.invoice:
        raise HTTPException(status_code=400, detail="Devis figé (facture émise)")
    if quote.status == QuoteStatus.accepte:
        raise HTTPException(status_code=400, detail="Devis accepté : créez une nouvelle version")
    settings = db.query(GarageSettings).filter(GarageSettings.tenant_id == user.tenant_id).first()
    if not settings:
        raise HTTPException(status_code=400, detail="Paramètres garage manquants")
    dossier = (
        db.query(Dossier)
        .options(joinedload(Dossier.client))
        .filter(Dossier.id == quote.dossier_id)
        .first()
    )
    update_quote_lines(db, quote, settings, payload.lines)
    pdf_name = generate_quote_pdf(quote, dossier, dossier.client, settings)
    quote.pdf_filename = pdf_name
    log_action(db, quote.dossier_id, user, "quote_lines_edited", quote.number)
    db.commit()
    return _load_quote(db, quote.id, user.tenant_id)


@router.patch("/quotes/{quote_id}/status", response_model=QuoteOut)
def update_quote_status(
    quote_id: int,
    payload: QuoteStatusUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    quote = _load_quote(db, quote_id, user.tenant_id)
    if not quote:
        raise HTTPException(status_code=404, detail="Devis introuvable")
    if quote.invoice:
        raise HTTPException(
            status_code=400,
            detail="Le devis est figé car une facture a déjà été émise",
        )
    quote.status = payload.status
    log_action(db, quote.dossier_id, user, "quote_status", payload.status.value)
    db.commit()
    db.refresh(quote)
    return quote


@router.post("/quotes/{quote_id}/email")
def email_quote(
    quote_id: int,
    payload: EmailSendIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    quote = _load_quote(db, quote_id, user.tenant_id)
    if not quote or not quote.pdf_filename:
        raise HTTPException(status_code=404, detail="Devis introuvable")
    try:
        pdf_data = read_bytes("quotes", quote.pdf_filename)
        send_document_email(
            payload.to,
            f"Devis {quote.number}",
            payload.message or f"Veuillez trouver ci-joint le devis {quote.number}.",
            attachment_bytes=pdf_data,
            attachment_filename=quote.pdf_filename,
        )
    except ValueError as exc:
        raise HTTPException(status_code=501, detail=str(exc)) from exc
    log_action(db, quote.dossier_id, user, "quote_emailed", payload.to)
    db.commit()
    return {"ok": True}


@router.get("/quotes/{quote_id}/pdf")
def download_quote_pdf(
    quote_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    quote = db.query(Quote).filter(Quote.id == quote_id, Quote.tenant_id == user.tenant_id).first()
    if not quote or not quote.pdf_filename:
        raise HTTPException(status_code=404, detail="PDF introuvable")
    return file_response_or_404("quotes", quote.pdf_filename, quote.pdf_filename)
