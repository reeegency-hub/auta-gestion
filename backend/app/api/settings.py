from __future__ import annotations
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models import GarageSettings, User
from app.schemas import GarageSettingsIn, GarageSettingsOut

router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("", response_model=GarageSettingsOut)
def get_settings(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    settings = db.query(GarageSettings).filter(GarageSettings.tenant_id == user.tenant_id).first()
    if not settings:
        settings = GarageSettings(tenant_id=user.tenant_id)
        db.add(settings)
        db.commit()
        db.refresh(settings)
    return settings


@router.put("", response_model=GarageSettingsOut)
def update_settings(
    payload: GarageSettingsIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    settings = db.query(GarageSettings).filter(GarageSettings.tenant_id == user.tenant_id).first()
    if not settings:
        settings = GarageSettings(tenant_id=user.tenant_id)
        db.add(settings)
    for k, v in payload.model_dump().items():
        setattr(settings, k, v)
    db.commit()
    db.refresh(settings)
    return settings
