from __future__ import annotations
from datetime import datetime, timezone

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import DocumentSequence

PREFIXES = {"quote": "DEV", "invoice": "FAC"}


def next_number(db: Session, tenant_id: int, doc_type: str) -> str:
    """Retourne le prochain numéro légal (ex. DEV-2026-00001 / FAC-2026-00001).

    Utilise un compteur annuel par tenant/type de document (DocumentSequence).
    """
    year = datetime.now(timezone.utc).year
    query = db.query(DocumentSequence).filter(
        DocumentSequence.tenant_id == tenant_id,
        DocumentSequence.doc_type == doc_type,
        DocumentSequence.year == year,
    )
    bind = db.get_bind()
    if bind is not None and bind.dialect.name != "sqlite":
        # Verrouille la ligne pour éviter les doublons de numéro en cas d'accès concurrent.
        query = query.with_for_update()
    seq = query.first()
    if not seq:
        seq = DocumentSequence(tenant_id=tenant_id, doc_type=doc_type, year=year, last_number=0)
        db.add(seq)
        try:
            db.flush()
        except IntegrityError:
            db.rollback()
            seq = query.first()
            if not seq:
                raise
    seq.last_number += 1
    db.flush()
    prefix = PREFIXES.get(doc_type, doc_type.upper())
    return f"{prefix}-{year}-{seq.last_number:05d}"
