from __future__ import annotations
import asyncio
from typing import Optional

from fastapi import BackgroundTasks

from app.core.config import get_settings
from app.core.database import SessionLocal


def run_extraction_job(report_id: int, expected_filename: Optional[str] = None) -> None:
    """Exécute l'extraction pour un rapport. Ignore les jobs obsolètes si un nouveau PDF
    a été importé entre-temps (expected_filename ne correspond plus)."""
    from app.models import ExpertiseReport
    from app.services.extraction import process_expertise_report
    from app.services.storage import materialize_path

    db = SessionLocal()
    tmp_path = None
    try:
        report = db.query(ExpertiseReport).filter(ExpertiseReport.id == report_id).first()
        if not report or not report.filename:
            return
        if expected_filename and report.filename != expected_filename:
            return
        pdf_path = materialize_path("reports", report.filename)
        tmp_path = pdf_path if get_settings().remote_storage_enabled else None
        asyncio.run(process_expertise_report(db, report_id, pdf_path))
    finally:
        if tmp_path is not None:
            try:
                tmp_path.unlink(missing_ok=True)
            except OSError:
                pass
        db.close()


def enqueue_extraction(report_id: int, background_tasks: Optional[BackgroundTasks] = None) -> None:
    """Planifie l'extraction d'un rapport : via une file Redis/RQ si REDIS_URL est configuré,
    sinon via les BackgroundTasks de FastAPI."""
    settings = get_settings()

    from app.models import ExpertiseReport

    db = SessionLocal()
    try:
        report = db.query(ExpertiseReport).filter(ExpertiseReport.id == report_id).first()
        expected_filename = report.filename if report else None
    finally:
        db.close()

    if settings.redis_url:
        try:
            import redis
            from rq import Queue

            connection = redis.from_url(settings.redis_url)
            queue = Queue("extraction", connection=connection)
            queue.enqueue(run_extraction_job, report_id, expected_filename)
            return
        except Exception:  # noqa: BLE001 - Redis/RQ indisponible : on retombe sur BackgroundTasks
            pass

    if background_tasks is not None:
        background_tasks.add_task(run_extraction_job, report_id, expected_filename)
    else:
        run_extraction_job(report_id, expected_filename)
