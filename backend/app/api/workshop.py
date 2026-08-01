from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models import Dossier, StatusHistory, User, WORKSHOP_ORDER, WorkshopStatus
from app.schemas import DossierListItem, WorkshopUpdate
from app.services.audit import log_action

router = APIRouter(prefix="/api/workshop", tags=["workshop"])


def _item(d: Dossier) -> DossierListItem:
    current = d.quote
    return DossierListItem(
        id=d.id,
        reference=d.reference,
        vehicle_make=d.vehicle_make,
        vehicle_model=d.vehicle_model,
        license_plate=d.license_plate,
        workshop_status=d.workshop_status,
        assigned_user_id=d.assigned_user_id,
        is_closed=d.is_closed,
        created_at=d.created_at,
        client_name=f"{d.client.first_name} {d.client.last_name}",
        has_quote=current is not None,
        quote_status=current.status if current else None,
        has_invoice=any(q.invoice for q in (d.quotes or [])),
    )


@router.get("/board")
def workshop_board(
    assigned_to_me: bool = False,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    query = (
        db.query(Dossier)
        .options(joinedload(Dossier.client), joinedload(Dossier.quotes))
        .filter(Dossier.tenant_id == user.tenant_id, Dossier.is_closed == False)  # noqa: E712
    )
    if assigned_to_me:
        query = query.filter(Dossier.assigned_user_id == user.id)
    dossiers = query.order_by(Dossier.updated_at.desc()).all()
    columns = {s.value: [] for s in WORKSHOP_ORDER}
    for d in dossiers:
        columns[d.workshop_status.value].append(_item(d))
    return {"columns": columns, "order": [s.value for s in WORKSHOP_ORDER]}


@router.patch("/dossiers/{dossier_id}", response_model=DossierListItem)
def move_dossier(
    dossier_id: int,
    payload: WorkshopUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    dossier = (
        db.query(Dossier)
        .options(joinedload(Dossier.client), joinedload(Dossier.quotes))
        .filter(Dossier.id == dossier_id, Dossier.tenant_id == user.tenant_id)
        .first()
    )
    if not dossier:
        raise HTTPException(status_code=404, detail="Dossier introuvable")
    if dossier.is_closed:
        raise HTTPException(status_code=400, detail="Ce dossier est clôturé")
    old = dossier.workshop_status
    if payload.workshop_status != old:
        db.add(
            StatusHistory(
                dossier_id=dossier.id,
                from_status=old.value,
                to_status=payload.workshop_status.value,
                changed_by_id=user.id,
                note=payload.note,
            )
        )
        dossier.workshop_status = payload.workshop_status
        if payload.workshop_status == WorkshopStatus.livre:
            dossier.is_closed = True
    if "assigned_user_id" in payload.model_fields_set:
        dossier.assigned_user_id = payload.assigned_user_id
    log_action(
        db,
        dossier.id,
        user,
        "workshop_moved",
        f"{old.value} → {payload.workshop_status.value}",
    )
    db.commit()
    db.refresh(dossier)
    return _item(dossier)
