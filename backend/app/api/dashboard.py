from __future__ import annotations
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models import (
    Dossier,
    Invoice,
    InvoiceStatus,
    Quote,
    QuoteStatus,
    User,
    WorkshopStatus,
)
from app.schemas import DashboardOut

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])

ATELIER_STATUSES = [
    WorkshopStatus.carrosserie,
    WorkshopStatus.preparation,
    WorkshopStatus.peinture,
    WorkshopStatus.remontage,
    WorkshopStatus.controle_qualite,
]


@router.get("", response_model=DashboardOut)
def dashboard(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    tid = user.tenant_id
    return DashboardOut(
        dossiers_en_cours=db.query(Dossier)
        .filter(Dossier.tenant_id == tid, Dossier.is_closed == False)  # noqa: E712
        .count(),
        devis_en_attente=db.query(Quote)
        .filter(Quote.tenant_id == tid, Quote.status == QuoteStatus.en_attente)
        .count(),
        vehicules_en_atelier=db.query(Dossier)
        .filter(
            Dossier.tenant_id == tid,
            Dossier.is_closed == False,  # noqa: E712
            Dossier.workshop_status.in_(ATELIER_STATUSES),
        )
        .count(),
        pret_a_livrer=db.query(Dossier)
        .filter(
            Dossier.tenant_id == tid,
            Dossier.is_closed == False,  # noqa: E712
            Dossier.workshop_status == WorkshopStatus.pret_a_livrer,
        )
        .count(),
        factures_en_attente=db.query(Invoice)
        .filter(Invoice.tenant_id == tid, Invoice.status == InvoiceStatus.en_attente)
        .count(),
    )
