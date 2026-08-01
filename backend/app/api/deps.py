from __future__ import annotations

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import decode_access_token
from app.models import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login-form")


def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> User:
    email = decode_access_token(token)
    if not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expirée ou token invalide",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user = db.query(User).filter(User.email == email).first()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Utilisateur invalide",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def require_open_dossier(dossier) -> None:
    if dossier is None:
        raise HTTPException(status_code=404, detail="Dossier introuvable")
    if dossier.is_closed:
        raise HTTPException(
            status_code=400,
            detail="Ce dossier est clôturé. Réouverture impossible depuis cette action.",
        )
