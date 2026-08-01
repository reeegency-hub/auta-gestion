from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models import (
    Dossier,
    GarageSettings,
    Invoice,
    InvoiceStatus,
    Quote,
    QuoteStatus,
    User,
)
from app.services.audit import log_action
from app.services.emailing import send_document_email
from app.services.numbering import next_number
from app.services.pdfs import generate_invoice_pdf
from app.services.storage import file_response_or_404, resolve_path
from app.schemas import EmailSendIn, InvoiceOut

router = APIRouter(prefix="/api", tags=["invoices"])


class InvoiceStatusUpdate(BaseModel):
    status: InvoiceStatus


@router.get("/invoices", response_model=list[InvoiceOut])
def list_invoices(
    status: Optional[InvoiceStatus] = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    q = db.query(Invoice).filter(Invoice.tenant_id == user.tenant_id)
    if status:
        q = q.filter(Invoice.status == status)
    return q.order_by(Invoice.created_at.desc()).all()


@router.post("/quotes/{quote_id}/invoice", response_model=InvoiceOut)
def convert_to_invoice(
    quote_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    quote = (
        db.query(Quote)
        .options(joinedload(Quote.lines), joinedload(Quote.invoice))
        .filter(Quote.id == quote_id, Quote.tenant_id == user.tenant_id)
        .first()
    )
    if not quote:
        raise HTTPException(status_code=404, detail="Devis introuvable")
    if quote.status != QuoteStatus.accepte:
        raise HTTPException(status_code=400, detail="Le devis doit être accepté")
    if quote.invoice:
        raise HTTPException(status_code=400, detail="Facture déjà créée")

    dossier = (
        db.query(Dossier)
        .options(joinedload(Dossier.client))
        .filter(Dossier.id == quote.dossier_id)
        .first()
    )
    if not dossier:
        raise HTTPException(status_code=404, detail="Dossier introuvable")
    settings = db.query(GarageSettings).filter(GarageSettings.tenant_id == user.tenant_id).first()
    if not settings:
        raise HTTPException(status_code=400, detail="Paramètres garage manquants")

    invoice = Invoice(
        quote_id=quote.id,
        dossier_id=quote.dossier_id,
        tenant_id=user.tenant_id,
        number=next_number(db, user.tenant_id, "invoice"),
        status=InvoiceStatus.en_attente,
        total_ht=quote.total_ht,
        tva_amount=quote.tva_amount,
        total_ttc=quote.total_ttc,
    )
    db.add(invoice)
    db.flush()
    pdf_name = generate_invoice_pdf(invoice, quote, dossier, dossier.client, settings)
    invoice.pdf_filename = pdf_name
    # Facture ≠ clôture atelier : le véhicule reste suivi jusqu'à livraison
    log_action(db, dossier.id, user, "invoice_created", invoice.number)
    db.commit()
    db.refresh(invoice)
    return invoice


@router.patch("/invoices/{invoice_id}/status", response_model=InvoiceOut)
def update_invoice_status(
    invoice_id: int,
    payload: InvoiceStatusUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    invoice = (
        db.query(Invoice)
        .filter(Invoice.id == invoice_id, Invoice.tenant_id == user.tenant_id)
        .first()
    )
    if not invoice:
        raise HTTPException(status_code=404, detail="Facture introuvable")
    invoice.status = payload.status
    log_action(db, invoice.dossier_id, user, "invoice_status", payload.status.value)
    db.commit()
    db.refresh(invoice)
    return invoice


@router.get("/invoices/{invoice_id}", response_model=InvoiceOut)
def get_invoice(
    invoice_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    invoice = (
        db.query(Invoice)
        .filter(Invoice.id == invoice_id, Invoice.tenant_id == user.tenant_id)
        .first()
    )
    if not invoice:
        raise HTTPException(status_code=404, detail="Facture introuvable")
    return invoice


@router.get("/invoices/{invoice_id}/pdf")
def download_invoice_pdf(
    invoice_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    invoice = (
        db.query(Invoice)
        .filter(Invoice.id == invoice_id, Invoice.tenant_id == user.tenant_id)
        .first()
    )
    if not invoice or not invoice.pdf_filename:
        raise HTTPException(status_code=404, detail="PDF introuvable")
    return file_response_or_404("invoices", invoice.pdf_filename, invoice.pdf_filename)


@router.get("/dossiers/{dossier_id}/invoice", response_model=InvoiceOut)
def get_dossier_invoice(
    dossier_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    invoice = (
        db.query(Invoice)
        .filter(Invoice.dossier_id == dossier_id, Invoice.tenant_id == user.tenant_id)
        .order_by(Invoice.created_at.desc())
        .first()
    )
    if not invoice:
        raise HTTPException(status_code=404, detail="Facture introuvable")
    return invoice


@router.post("/invoices/{invoice_id}/email")
def email_invoice(
    invoice_id: int,
    payload: EmailSendIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    invoice = (
        db.query(Invoice)
        .filter(Invoice.id == invoice_id, Invoice.tenant_id == user.tenant_id)
        .first()
    )
    if not invoice or not invoice.pdf_filename:
        raise HTTPException(status_code=404, detail="Facture introuvable")
    path = resolve_path("invoices", invoice.pdf_filename)
    try:
        send_document_email(
            payload.to,
            f"Facture {invoice.number}",
            payload.message or f"Veuillez trouver ci-joint la facture {invoice.number}.",
            path if path.is_file() else None,
        )
    except ValueError as exc:
        raise HTTPException(status_code=501, detail=str(exc)) from exc
    log_action(db, invoice.dossier_id, user, "invoice_emailed", payload.to)
    db.commit()
    return {"ok": True}
