"""Ajoute les colonnes manquantes sans Alembic (Postgres / SQLite)."""
from __future__ import annotations
import logging

from sqlalchemy import inspect, text

from app.core.database import engine

logger = logging.getLogger("auta")

_GARAGE_EXTRA = {
    "phone": "VARCHAR(50) DEFAULT ''",
    "email": "VARCHAR(255) DEFAULT ''",
    "vat_number": "VARCHAR(50) DEFAULT ''",
    "rcs": "VARCHAR(100) DEFAULT ''",
    "payment_method": "VARCHAR(80) DEFAULT 'Chèque'",
}


def ensure_extra_columns() -> None:
    try:
        insp = inspect(engine)
        if "garage_settings" not in insp.get_table_names():
            return
        existing = {c["name"] for c in insp.get_columns("garage_settings")}
        with engine.begin() as conn:
            for name, ddl in _GARAGE_EXTRA.items():
                if name in existing:
                    continue
                conn.execute(text(f"ALTER TABLE garage_settings ADD COLUMN {name} {ddl}"))
                logger.info("Colonne garage_settings.%s ajoutée", name)
    except Exception as exc:  # noqa: BLE001
        logger.warning("ensure_extra_columns: %s", exc)
