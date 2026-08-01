# Seed automatique au démarrage si la base est vide (démo cloud)
from __future__ import annotations

import logging

from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models import GarageSettings, Tenant, User, UserRole

logger = logging.getLogger("auta")


def ensure_demo_user() -> None:
    db = SessionLocal()
    try:
        if db.query(User).first():
            return
        tenant = Tenant(name="Carrosserie Auta Demo")
        db.add(tenant)
        db.flush()
        db.add(
            User(
                tenant_id=tenant.id,
                email="directeur@auta.demo",
                full_name="Marie Directeur",
                hashed_password=hash_password("auta123"),
                role=UserRole.directeur,
            )
        )
        db.add(GarageSettings(tenant_id=tenant.id, company_name="Carrosserie Auta Demo"))
        db.commit()
        logger.info("Compte démo créé : directeur@auta.demo / auta123")
    except Exception as exc:  # noqa: BLE001
        logger.warning("Seed démo ignoré : %s", exc)
        db.rollback()
    finally:
        db.close()
