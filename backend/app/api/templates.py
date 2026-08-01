from __future__ import annotations

import json
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models import InvoiceTemplate, User
from app.schemas import InvoiceTemplateOut
from app.services.storage import ensure_upload_dirs, save_upload

router = APIRouter(prefix="/api/templates", tags=["templates"])

DEFAULT_VARIABLES = {
    "invoice_number": "Numéro de facture",
    "invoice_date": "Date d’émission",
    "garage_name": "Raison sociale garage",
    "garage_address": "Adresse garage",
    "garage_siret": "SIRET",
    "client_name": "Nom client",
    "client_address": "Adresse client",
    "client_email": "Email client",
    "vehicle_label": "Marque / modèle",
    "license_plate": "Immatriculation",
    "lines": "Lignes (description, qté, prix, total)",
    "total_ht": "Total HT",
    "tva_amount": "TVA",
    "total_ttc": "Total TTC",
}


@router.get("/invoice", response_model=Optional[InvoiceTemplateOut])
def get_active_invoice_template(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    tpl = (
        db.query(InvoiceTemplate)
        .filter(
            InvoiceTemplate.tenant_id == user.tenant_id,
            InvoiceTemplate.is_active == True,  # noqa: E712
        )
        .order_by(InvoiceTemplate.updated_at.desc())
        .first()
    )
    return tpl


@router.post("/invoice", response_model=InvoiceTemplateOut)
async def upload_invoice_template(
    file: UploadFile = File(...),
    name: str = Form("Facture standard"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Enregistre le fichier modèle (HTML, DOCX, PDF annoté…) pour ce garage.

    La génération PDF utilisera ce modèle dès qu’il est branché ; en attendant
    le rendu ReportLab reste le fallback.
    """
    ensure_upload_dirs()
    suffix = (file.filename or "").lower()
    allowed = {".html", ".htm", ".pdf", ".docx", ".json", ".txt"}
    from pathlib import Path

    ext = Path(file.filename or "template.html").suffix.lower()
    if ext not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"Format non supporté ({ext}). Envoyez HTML, PDF, DOCX ou JSON.",
        )

    stored, original = save_upload(file, "templates", allowed_suffixes=allowed)
    # Désactive les anciens modèles actifs
    for old in (
        db.query(InvoiceTemplate)
        .filter(InvoiceTemplate.tenant_id == user.tenant_id, InvoiceTemplate.is_active == True)  # noqa: E712
        .all()
    ):
        old.is_active = False

    kind = "html" if ext in {".html", ".htm"} else ext.lstrip(".")
    tpl = InvoiceTemplate(
        tenant_id=user.tenant_id,
        name=name or "Facture standard",
        kind=kind,
        filename=stored,
        original_name=original,
        variables_schema=json.dumps(DEFAULT_VARIABLES, ensure_ascii=False),
        is_active=True,
    )
    db.add(tpl)
    db.commit()
    db.refresh(tpl)
    return tpl
