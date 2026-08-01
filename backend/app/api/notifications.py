from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.models import User
from app.schemas import SmsIn

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


@router.post("/sms")
def send_sms(payload: SmsIn, user: User = Depends(get_current_user)):
    """Stub d'envoi de SMS : renvoie 501 tant qu'aucun prestataire n'est configuré."""
    settings = get_settings()
    if not settings.sms_provider_url or not settings.sms_api_key:
        raise HTTPException(
            status_code=501,
            detail=(
                "Envoi de SMS non configuré : renseignez SMS_PROVIDER_URL et SMS_API_KEY "
                "dans la configuration serveur."
            ),
        )
    raise HTTPException(
        status_code=501,
        detail="Fournisseur SMS non implémenté pour le moment.",
    )
