from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.core.database import get_db
from app.core.security import create_access_token, hash_password, verify_password
from app.models import GarageSettings, Tenant, User, UserRole
from app.schemas import LoginIn, RegisterIn, Token, UserOut

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=Token)
def register(payload: RegisterIn, db: Session = Depends(get_db)):
    if not get_settings().allow_open_registration:
        raise HTTPException(
            status_code=403,
            detail="Inscription fermée. Contactez l’administrateur pour créer un compte.",
        )
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(status_code=400, detail="Email déjà utilisé")
    tenant = Tenant(name=payload.garage_name)
    db.add(tenant)
    db.flush()
    user = User(
        tenant_id=tenant.id,
        email=payload.email,
        full_name=payload.full_name,
        hashed_password=hash_password(payload.password),
        role=UserRole.directeur,
    )
    db.add(user)
    db.add(
        GarageSettings(
            tenant_id=tenant.id,
            company_name=payload.garage_name,
        )
    )
    db.commit()
    token = create_access_token(payload.email)
    return Token(access_token=token)


@router.get("/users", response_model=list[UserOut])
def list_users(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return (
        db.query(User)
        .filter(User.tenant_id == user.tenant_id, User.is_active == True)  # noqa: E712
        .order_by(User.full_name)
        .all()
    )


@router.post("/login", response_model=Token)
def login_json(payload: LoginIn, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Identifiants invalides")
    return Token(access_token=create_access_token(user.email))


@router.post("/login-form", response_model=Token)
def login_form(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == form.username).first()
    if not user or not verify_password(form.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Identifiants invalides")
    return Token(access_token=create_access_token(user.email))


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user
