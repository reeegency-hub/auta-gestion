from __future__ import annotations
from typing import Optional

from sqlalchemy.orm import Session

from app.models import AuditLog, User


def log_action(db: Session, dossier_id: int, user: Optional[User], action: str, details: str = "") -> None:
    db.add(
        AuditLog(
            dossier_id=dossier_id,
            user_id=user.id if user else None,
            action=action,
            details=details,
        )
    )
