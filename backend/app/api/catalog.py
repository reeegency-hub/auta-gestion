from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models import PartsCatalogItem, User
from app.schemas import PartsCatalogItemIn, PartsCatalogItemOut, PartsCatalogItemUpdate

router = APIRouter(prefix="/api/catalog", tags=["catalog"])


@router.get("/parts", response_model=list[PartsCatalogItemOut])
def list_parts(
    active_only: bool = False,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    q = db.query(PartsCatalogItem).filter(PartsCatalogItem.tenant_id == user.tenant_id)
    if active_only:
        q = q.filter(PartsCatalogItem.active == True)  # noqa: E712
    return q.order_by(PartsCatalogItem.label).all()


@router.post("/parts", response_model=PartsCatalogItemOut)
def create_part(
    payload: PartsCatalogItemIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    item = PartsCatalogItem(tenant_id=user.tenant_id, **payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.patch("/parts/{part_id}", response_model=PartsCatalogItemOut)
def update_part(
    part_id: int,
    payload: PartsCatalogItemUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    item = (
        db.query(PartsCatalogItem)
        .filter(PartsCatalogItem.id == part_id, PartsCatalogItem.tenant_id == user.tenant_id)
        .first()
    )
    if not item:
        raise HTTPException(status_code=404, detail="Pièce introuvable")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(item, k, v)
    db.commit()
    db.refresh(item)
    return item
