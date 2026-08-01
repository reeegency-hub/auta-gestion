from __future__ import annotations
import json
import re
from pathlib import Path

import httpx
from pypdf import PdfReader
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import (
    ExpertiseReport,
    ExtractedOperation,
    ExtractionStatus,
    OperationType,
)


def extract_pdf_text(path: Path) -> str:
    reader = PdfReader(str(path))
    parts = []
    for page in reader.pages:
        text = page.extract_text() or ""
        parts.append(text)
    return "\n".join(parts).strip()


def _heuristic_operations(text: str) -> list[dict]:
    """Fallback parser when no LLM key is configured."""
    ops: list[dict] = []
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    for i, line in enumerate(lines[:40]):
        lower = line.lower()
        hours_match = re.search(r"(\d+[.,]?\d*)\s*h", lower)
        hours = float(hours_match.group(1).replace(",", ".")) if hours_match else 0.0
        price_match = re.search(r"(\d+[.,]?\d*)\s*€", line)
        unit = float(price_match.group(1).replace(",", ".")) if price_match else 0.0

        if any(k in lower for k in ("peinture", "paint", "vernis")):
            ops.append(
                {
                    "operation_type": OperationType.peinture,
                    "description": line[:500],
                    "quantity": 1,
                    "hours": hours or 1.0,
                    "unit_cost": unit,
                    "labor_category": "peinture",
                    "sort_order": i,
                }
            )
        elif any(k in lower for k in ("remplac", "neuf", "piece", "pièce")):
            ops.append(
                {
                    "operation_type": OperationType.piece_remplacer,
                    "description": line[:500],
                    "quantity": 1,
                    "hours": 0,
                    "unit_cost": unit or 80.0,
                    "labor_category": "carrosserie",
                    "sort_order": i,
                }
            )
        elif any(k in lower for k in ("repar", "déboss", "deboss", "redress")):
            ops.append(
                {
                    "operation_type": OperationType.piece_reparer,
                    "description": line[:500],
                    "quantity": 1,
                    "hours": hours or 1.5,
                    "unit_cost": unit,
                    "labor_category": "carrosserie",
                    "sort_order": i,
                }
            )
        elif any(k in lower for k in ("main", "t.o", "mo ", "heure")):
            ops.append(
                {
                    "operation_type": OperationType.main_doeuvre,
                    "description": line[:500],
                    "quantity": 1,
                    "hours": hours or 1.0,
                    "unit_cost": unit,
                    "labor_category": "carrosserie",
                    "sort_order": i,
                }
            )
    if not ops:
        return []
    return ops


async def _llm_operations(text: str):
    """Extraction via Grok (xAI). Sans clé → None (fallback heuristique)."""
    settings = get_settings()
    api_key = settings.grok_api_key
    if not api_key:
        return None
    prompt = (
        "Extrais les opérations d'un rapport d'expertise auto. "
        "Réponds UNIQUEMENT en JSON: {\"operations\":[{\"operation_type\":"
        "\"piece_remplacer|piece_reparer|main_doeuvre|peinture|annexe\","
        "\"description\":str,\"quantity\":number,\"hours\":number,"
        "\"unit_cost\":number,\"labor_category\":\"carrosserie|peinture|mecanique\"}]}\n\n"
        f"Rapport:\n{text[:12000]}"
    )
    base = settings.grok_base_url.rstrip("/")
    payload = {
        "model": settings.grok_model,
        "messages": [
            {
                "role": "system",
                "content": (
                    "Tu es un expert carrosserie. Tu structures des rapports "
                    "d'expertise en JSON strict, sans texte hors JSON."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.1,
    }
    # Certains modèles Grok acceptent le mode JSON objet
    payload["response_format"] = {"type": "json_object"}

    async with httpx.AsyncClient(timeout=90) as client:
        resp = await client.post(
            f"{base}/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
        )
        if resp.status_code >= 400:
            # Retry sans response_format si le modèle le refuse
            payload.pop("response_format", None)
            resp = await client.post(
                f"{base}/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"]
        # Au cas où Grok entoure le JSON de markdown
        content = content.strip()
        if content.startswith("```"):
            content = re.sub(r"^```(?:json)?\s*", "", content)
            content = re.sub(r"\s*```$", "", content)
        data = json.loads(content)
        ops = []
        for i, raw in enumerate(data.get("operations", [])):
            try:
                op_type = OperationType(raw["operation_type"])
            except Exception:
                op_type = OperationType.annexe
            ops.append(
                {
                    "operation_type": op_type,
                    "description": str(raw.get("description", "Opération"))[:500],
                    "quantity": float(raw.get("quantity") or 1),
                    "hours": float(raw.get("hours") or 0),
                    "unit_cost": float(raw.get("unit_cost") or 0),
                    "labor_category": str(raw.get("labor_category") or "carrosserie"),
                    "sort_order": i,
                }
            )
        return ops or None


async def process_expertise_report(db: Session, report_id: int, pdf_path: Path) -> None:
    report = db.query(ExpertiseReport).filter(ExpertiseReport.id == report_id).first()
    if not report:
        return
    report.status = ExtractionStatus.processing
    db.commit()
    try:
        text = extract_pdf_text(pdf_path)
        report.raw_text = text
        ops_data = await _llm_operations(text) if text else None
        if not ops_data:
            ops_data = _heuristic_operations(text or "")
        report.operations.clear()
        if not ops_data:
            report.status = ExtractionStatus.failed
            report.error_message = (
                "Aucune opération détectée dans le PDF. "
                "Ajoutez les lignes manuellement ou réessayez avec un rapport plus lisible."
            )
        else:
            for op in ops_data:
                report.operations.append(ExtractedOperation(**op))
            report.status = ExtractionStatus.draft
            report.error_message = ""
    except Exception as exc:  # noqa: BLE001
        report.status = ExtractionStatus.failed
        report.error_message = str(exc)
    db.commit()
