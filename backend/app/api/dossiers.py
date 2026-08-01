from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_current_user, require_open_dossier
from app.core.database import get_db
from app.models import (
    Client,
    Dossier,
    ExpertiseReport,
    Quote,
    StatusHistory,
    User,
    VehiclePhoto,
    WorkshopStatus,
)
from app.schemas import (
    DossierCreate,
    DossierListItem,
    DossierOut,
    DossierUpdate,
    PhotoOut,
)
from app.services.audit import log_action
from app.services.storage import IMAGE_SUFFIXES, file_response_or_404, save_upload

router = APIRouter(prefix="/api/dossiers", tags=["dossiers"])


def _ref(db: Session, tenant_id: int) -> str:
    n = db.query(Dossier).filter(Dossier.tenant_id == tenant_id).count() + 1
    return f"DOS-{n:05d}"


@router.get("", response_model=list[DossierListItem])
def list_dossiers(
    q: Optional[str] = None,
    status: Optional[WorkshopStatus] = None,
    assigned_to_me: bool = False,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    query = (
        db.query(Dossier)
        .options(joinedload(Dossier.client), joinedload(Dossier.quotes).joinedload(Quote.invoice))
        .filter(Dossier.tenant_id == user.tenant_id)
    )
    if status:
        query = query.filter(Dossier.workshop_status == status)
    if assigned_to_me:
        query = query.filter(Dossier.assigned_user_id == user.id)
    if q:
        like = f"%{q}%"
        query = query.join(Client).filter(
            (Dossier.reference.ilike(like))
            | (Dossier.license_plate.ilike(like))
            | (Dossier.vehicle_make.ilike(like))
            | (Dossier.vehicle_model.ilike(like))
            | (Client.first_name.ilike(like))
            | (Client.last_name.ilike(like))
        )
    items = []
    for d in query.order_by(Dossier.created_at.desc()).all():
        current = d.quote
        has_invoice = any(q.invoice for q in d.quotes)
        items.append(
            DossierListItem(
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
                has_invoice=has_invoice,
            )
        )
    return items


@router.post("", response_model=DossierOut)
def create_dossier(
    payload: DossierCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    client = Client(tenant_id=user.tenant_id, **payload.client.model_dump())
    db.add(client)
    db.flush()
    dossier = Dossier(
        tenant_id=user.tenant_id,
        client_id=client.id,
        reference=_ref(db, user.tenant_id),
        vehicle_make=payload.vehicle_make,
        vehicle_model=payload.vehicle_model,
        vehicle_year=payload.vehicle_year,
        license_plate=payload.license_plate,
        vin=payload.vin,
        insurance_name=payload.insurance_name,
        insurance_claim_number=payload.insurance_claim_number,
        comments=payload.comments,
        workshop_status=WorkshopStatus.reception,
    )
    db.add(dossier)
    db.flush()
    db.add(
        StatusHistory(
            dossier_id=dossier.id,
            from_status="",
            to_status=WorkshopStatus.reception.value,
            changed_by_id=user.id,
            note="Création du dossier",
        )
    )
    log_action(db, dossier.id, user, "dossier_created", f"Réf {dossier.reference}")
    db.commit()
    return get_dossier(dossier.id, db, user)


@router.get("/{dossier_id}", response_model=DossierOut)
def get_dossier(
    dossier_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    dossier = (
        db.query(Dossier)
        .options(
            joinedload(Dossier.client),
            joinedload(Dossier.photos),
            joinedload(Dossier.expertise_report).joinedload(ExpertiseReport.operations),
            joinedload(Dossier.quotes).joinedload(Quote.lines),
            joinedload(Dossier.quotes).joinedload(Quote.invoice),
            joinedload(Dossier.status_history),
            joinedload(Dossier.audit_logs),
        )
        .filter(Dossier.id == dossier_id, Dossier.tenant_id == user.tenant_id)
        .first()
    )
    if not dossier:
        raise HTTPException(status_code=404, detail="Dossier introuvable")
    return dossier


@router.patch("/{dossier_id}", response_model=DossierOut)
def update_dossier(
    dossier_id: int,
    payload: DossierUpdate,
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
    data = payload.model_dump(exclude_unset=True)
    # Allow only explicit reopen via is_closed=False; block other edits when closed
    if dossier.is_closed and not (data.get("is_closed") is False):
        raise HTTPException(status_code=400, detail="Ce dossier est clôturé")
    if "workshop_status" in data and data["workshop_status"] != dossier.workshop_status:
        db.add(
            StatusHistory(
                dossier_id=dossier.id,
                from_status=dossier.workshop_status.value,
                to_status=data["workshop_status"].value,
                changed_by_id=user.id,
            )
        )
        if data["workshop_status"] == WorkshopStatus.livre:
            data["is_closed"] = True
    for k, v in data.items():
        setattr(dossier, k, v)
    log_action(db, dossier.id, user, "dossier_updated", str(data))
    db.commit()
    return get_dossier(dossier_id, db, user)


@router.post("/{dossier_id}/photos", response_model=PhotoOut)
async def upload_photo(
    dossier_id: int,
    file: UploadFile = File(...),
    caption: str = "",
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    dossier = (
        db.query(Dossier)
        .filter(Dossier.id == dossier_id, Dossier.tenant_id == user.tenant_id)
        .first()
    )
    require_open_dossier(dossier)
    stored, original = save_upload(file, "photos", allowed_suffixes=IMAGE_SUFFIXES)
    photo = VehiclePhoto(
        dossier_id=dossier.id,
        filename=stored,
        original_name=original,
        caption=caption,
    )
    db.add(photo)
    log_action(db, dossier.id, user, "photo_uploaded", original)
    db.commit()
    db.refresh(photo)
    return photo


@router.get("/{dossier_id}/photos/{photo_id}/file")
def get_photo_file(
    dossier_id: int,
    photo_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    photo = (
        db.query(VehiclePhoto)
        .join(Dossier)
        .filter(
            VehiclePhoto.id == photo_id,
            VehiclePhoto.dossier_id == dossier_id,
            Dossier.tenant_id == user.tenant_id,
        )
        .first()
    )
    if not photo:
        raise HTTPException(status_code=404, detail="Photo introuvable")
    return file_response_or_404("photos", photo.filename, photo.original_name)
