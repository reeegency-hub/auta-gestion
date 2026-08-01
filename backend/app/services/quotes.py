from __future__ import annotations
from sqlalchemy.orm import Session

from app.models import (
    ExpertiseReport,
    ExtractionStatus,
    GarageSettings,
    OperationType,
    Quote,
    QuoteLine,
    QuoteStatus,
)
from app.services.numbering import next_number


def _rate_for(settings: GarageSettings, category: str) -> float:
    if category == "peinture":
        return settings.hourly_rate_peinture
    if category == "mecanique":
        return settings.hourly_rate_mecanique
    return settings.hourly_rate_carrosserie


def _recalc_quote_totals(quote: Quote, settings: GarageSettings) -> None:
    parts = labor = paint = consumables = 0.0
    for line in quote.lines:
        total = round(line.quantity * line.unit_price, 2)
        line.total = total
        if line.category in ("pieces", "annexe"):
            parts += total
        elif line.category == "peinture":
            paint += total
        elif line.category == "consommables":
            consumables += total
        else:
            labor += total
    total_ht = parts + labor + paint + consumables
    tva = total_ht * (settings.tva_rate / 100.0)
    quote.parts_total = round(parts, 2)
    quote.labor_total = round(labor, 2)
    quote.paint_total = round(paint, 2)
    quote.consumables_total = round(consumables, 2)
    quote.total_ht = round(total_ht, 2)
    quote.tva_amount = round(tva, 2)
    quote.total_ttc = round(total_ht + tva, 2)


def build_quote_from_report(
    db: Session,
    dossier_id: int,
    tenant_id: int,
    report: ExpertiseReport,
    settings: GarageSettings,
    *,
    new_version: bool = False,
) -> Quote:
    if report.status != ExtractionStatus.validated:
        raise ValueError("Les opérations doivent être validées avant génération du devis")

    existing = (
        db.query(Quote)
        .filter(Quote.dossier_id == dossier_id)
        .order_by(Quote.version.desc())
        .first()
    )

    # Régénérer le brouillon courant ; sinon créer une nouvelle version
    if existing and existing.status == QuoteStatus.brouillon and not existing.invoice and not new_version:
        for line in list(existing.lines):
            db.delete(line)
        quote = existing
        quote.status = QuoteStatus.brouillon
        db.flush()
    else:
        version = (existing.version + 1) if existing else 1
        quote = Quote(
            dossier_id=dossier_id,
            tenant_id=tenant_id,
            number=next_number(db, tenant_id, "quote"),
            version=version,
            status=QuoteStatus.brouillon,
        )
        db.add(quote)
        db.flush()

    lines: list[QuoteLine] = []
    parts_total = labor_total = paint_total = 0.0
    margin = 1 + (settings.parts_margin_percent / 100.0)

    for i, op in enumerate(sorted(report.operations, key=lambda o: o.sort_order)):
        if op.operation_type in (OperationType.piece_remplacer, OperationType.piece_reparer):
            unit = op.unit_cost * margin
            total = unit * op.quantity
            parts_total += total
            lines.append(
                QuoteLine(
                    quote_id=quote.id,
                    category="pieces",
                    description=op.description,
                    quantity=op.quantity,
                    unit_price=round(unit, 2),
                    total=round(total, 2),
                    sort_order=i,
                )
            )
            if op.hours > 0:
                rate = _rate_for(settings, op.labor_category)
                labor = rate * op.hours
                labor_total += labor
                lines.append(
                    QuoteLine(
                        quote_id=quote.id,
                        category="main_doeuvre",
                        description=f"MO – {op.description}",
                        quantity=op.hours,
                        unit_price=round(rate, 2),
                        total=round(labor, 2),
                        sort_order=i,
                    )
                )
        elif op.operation_type == OperationType.peinture:
            rate = _rate_for(settings, "peinture")
            hours = op.hours or 1.0
            labor = rate * hours
            paint_total += labor
            lines.append(
                QuoteLine(
                    quote_id=quote.id,
                    category="peinture",
                    description=op.description,
                    quantity=hours,
                    unit_price=round(rate, 2),
                    total=round(labor, 2),
                    sort_order=i,
                )
            )
        elif op.operation_type == OperationType.main_doeuvre:
            rate = _rate_for(settings, op.labor_category)
            hours = op.hours or 1.0
            labor = rate * hours
            labor_total += labor
            lines.append(
                QuoteLine(
                    quote_id=quote.id,
                    category="main_doeuvre",
                    description=op.description,
                    quantity=hours,
                    unit_price=round(rate, 2),
                    total=round(labor, 2),
                    sort_order=i,
                )
            )
        else:
            total = op.unit_cost * op.quantity
            parts_total += total
            lines.append(
                QuoteLine(
                    quote_id=quote.id,
                    category="annexe",
                    description=op.description,
                    quantity=op.quantity,
                    unit_price=round(op.unit_cost, 2),
                    total=round(total, 2),
                    sort_order=i,
                )
            )

    if settings.forfait_peinture > 0:
        paint_total += settings.forfait_peinture
        lines.append(
            QuoteLine(
                quote_id=quote.id,
                category="peinture",
                description="Forfait peinture",
                quantity=1,
                unit_price=settings.forfait_peinture,
                total=settings.forfait_peinture,
                sort_order=999,
            )
        )

    consumables = settings.consumables_flat
    if consumables > 0:
        lines.append(
            QuoteLine(
                quote_id=quote.id,
                category="consommables",
                description="Consommables atelier",
                quantity=1,
                unit_price=consumables,
                total=consumables,
                sort_order=1000,
            )
        )

    for line in lines:
        db.add(line)

    total_ht = parts_total + labor_total + paint_total + consumables
    tva = total_ht * (settings.tva_rate / 100.0)
    quote.parts_total = round(parts_total, 2)
    quote.labor_total = round(labor_total, 2)
    quote.paint_total = round(paint_total, 2)
    quote.consumables_total = round(consumables, 2)
    quote.total_ht = round(total_ht, 2)
    quote.tva_amount = round(tva, 2)
    quote.total_ttc = round(total_ht + tva, 2)
    db.flush()
    return quote


def update_quote_lines(
    db: Session,
    quote: Quote,
    settings: GarageSettings,
    lines_payload: list,
) -> Quote:
    for line in list(quote.lines):
        db.delete(line)
    db.flush()
    for i, item in enumerate(lines_payload):
        data = item.model_dump() if hasattr(item, "model_dump") else dict(item)
        qty = float(data.get("quantity") or 0)
        unit = float(data.get("unit_price") or 0)
        db.add(
            QuoteLine(
                quote_id=quote.id,
                category=data.get("category") or "annexe",
                description=data.get("description") or "",
                quantity=qty,
                unit_price=unit,
                total=round(qty * unit, 2),
                sort_order=int(data.get("sort_order") or i),
            )
        )
    db.flush()
    db.refresh(quote)
    _recalc_quote_totals(quote, settings)
    db.flush()
    return quote
