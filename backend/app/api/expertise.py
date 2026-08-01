from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_current_user, require_open_dossier
from app.core.database import get_db
from app.models import (
    Dossier,
    ExpertiseReport,
    ExtractedOperation,
    ExtractionStatus,
    User,
)
from app.schemas import ExpertiseReportOut, OperationIn
from app.services.audit import log_action
from app.services.queue import enqueue_extraction
from app.services.storage import PDF_SUFFIXES, file_response_or_404, save_upload

router = APIRouter(prefix="/api/dossiers", tags=["expertise"])


@router.post("/{dossier_id}/expertise", response_model=ExpertiseReportOut)
async def upload_expertise(
    dossier_id: int,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    dossier = (
        db.query(Dossier)
        .filter(Dossier.id == dossier_id, Dossier.tenant_id == user.tenant_id)
        .first()
    )
    require_open_dossier(dossier)

    report = db.query(ExpertiseReport).filter(ExpertiseReport.dossier_id == dossier_id).first()
    if report and report.status == ExtractionStatus.processing:
        raise HTTPException(
            status_code=400,
            detail="Extraction déjà en cours. Attendez la fin avant de réimporter.",
        )

    stored, original = save_upload(file, "reports", allowed_suffixes=PDF_SUFFIXES)
    if report:
        report.filename = stored
        report.original_name = original
        report.status = ExtractionStatus.pending
        report.raw_text = ""
        report.error_message = ""
        report.operations.clear()
    else:
        report = ExpertiseReport(
            dossier_id=dossier_id,
            filename=stored,
            original_name=original,
            status=ExtractionStatus.pending,
        )
        db.add(report)
    log_action(db, dossier_id, user, "expertise_uploaded", original)
    db.commit()
    db.refresh(report)
    enqueue_extraction(report.id, background_tasks)
    return (
        db.query(ExpertiseReport)
        .options(joinedload(ExpertiseReport.operations))
        .filter(ExpertiseReport.id == report.id)
        .first()
    )


@router.get("/{dossier_id}/expertise", response_model=ExpertiseReportOut)
def get_expertise(
    dossier_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    report = (
        db.query(ExpertiseReport)
        .join(Dossier)
        .options(joinedload(ExpertiseReport.operations))
        .filter(ExpertiseReport.dossier_id == dossier_id, Dossier.tenant_id == user.tenant_id)
        .first()
    )
    if not report:
        raise HTTPException(status_code=404, detail="Rapport introuvable")
    return report


@router.put("/{dossier_id}/expertise/operations", response_model=ExpertiseReportOut)
def update_operations(
    dossier_id: int,
    operations: list[OperationIn],
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    dossier = (
        db.query(Dossier)
        .filter(Dossier.id == dossier_id, Dossier.tenant_id == user.tenant_id)
        .first()
    )
    require_open_dossier(dossier)
    report = (
        db.query(ExpertiseReport)
        .options(joinedload(ExpertiseReport.operations))
        .filter(ExpertiseReport.dossier_id == dossier_id)
        .first()
    )
    if not report:
        report = ExpertiseReport(
            dossier_id=dossier_id,
            filename="",
            original_name="Saisie manuelle",
            status=ExtractionStatus.draft,
        )
        db.add(report)
        db.flush()
    else:
        report.operations.clear()
    for i, op in enumerate(operations):
        report.operations.append(
            ExtractedOperation(
                operation_type=op.operation_type,
                description=op.description,
                quantity=op.quantity,
                hours=op.hours,
                unit_cost=op.unit_cost,
                labor_category=op.labor_category,
                sort_order=op.sort_order if op.sort_order else i,
            )
        )
    report.status = ExtractionStatus.draft
    log_action(db, dossier_id, user, "operations_updated", f"{len(operations)} opérations")
    db.commit()
    db.refresh(report)
    return (
        db.query(ExpertiseReport)
        .options(joinedload(ExpertiseReport.operations))
        .filter(ExpertiseReport.id == report.id)
        .first()
    )


@router.post("/{dossier_id}/expertise/validate", response_model=ExpertiseReportOut)
def validate_expertise(
    dossier_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    report = (
        db.query(ExpertiseReport)
        .join(Dossier)
        .options(joinedload(ExpertiseReport.operations))
        .filter(ExpertiseReport.dossier_id == dossier_id, Dossier.tenant_id == user.tenant_id)
        .first()
    )
    if not report:
        raise HTTPException(status_code=404, detail="Rapport introuvable")
    if report.status not in (ExtractionStatus.draft, ExtractionStatus.validated):
        raise HTTPException(status_code=400, detail="Extraction non prête")
    if not report.operations:
        raise HTTPException(status_code=400, detail="Aucune opération à valider")
    report.status = ExtractionStatus.validated
    log_action(db, dossier_id, user, "expertise_validated", "")
    db.commit()
    db.refresh(report)
    return report


@router.delete("/{dossier_id}/expertise")
def delete_expertise(
    dossier_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Supprime le rapport d'expertise et ses opérations (fichiers côté storage à purger séparément)."""
    dossier = (
        db.query(Dossier)
        .filter(Dossier.id == dossier_id, Dossier.tenant_id == user.tenant_id)
        .first()
    )
    require_open_dossier(dossier)
    report = (
        db.query(ExpertiseReport)
        .options(joinedload(ExpertiseReport.operations))
        .filter(ExpertiseReport.dossier_id == dossier_id)
        .first()
    )
    if not report:
        return {"ok": True, "deleted": False}
    filename = report.filename
    db.delete(report)
    log_action(db, dossier_id, user, "expertise_deleted", filename or "")
    db.commit()
    return {"ok": True, "deleted": True, "filename": filename}

