from __future__ import annotations
import io

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.models import Client, Dossier, GarageSettings, Invoice, Quote
from app.services.storage import save_bytes


def _money(v: float) -> str:
    return f"{v:,.2f} €".replace(",", " ").replace(".", ",")


def generate_quote_pdf(
    quote: Quote,
    dossier: Dossier,
    client: Client,
    settings: GarageSettings,
) -> str:
    filename = f"{quote.number}.pdf"
    data = _render_document(
        title=f"Devis {quote.number}",
        quote_or_invoice_lines=quote.lines,
        dossier=dossier,
        client=client,
        settings=settings,
        totals={
            "parts": quote.parts_total,
            "labor": quote.labor_total,
            "paint": quote.paint_total,
            "consumables": quote.consumables_total,
            "ht": quote.total_ht,
            "tva": quote.tva_amount,
            "ttc": quote.total_ttc,
            "tva_rate": settings.tva_rate,
        },
    )
    return save_bytes(data, "quotes", filename)


def generate_invoice_pdf(
    invoice: Invoice,
    quote: Quote,
    dossier: Dossier,
    client: Client,
    settings: GarageSettings,
) -> str:
    filename = f"{invoice.number}.pdf"
    data = _render_document(
        title=f"Facture {invoice.number}",
        quote_or_invoice_lines=quote.lines,
        dossier=dossier,
        client=client,
        settings=settings,
        totals={
            "parts": quote.parts_total,
            "labor": quote.labor_total,
            "paint": quote.paint_total,
            "consumables": quote.consumables_total,
            "ht": invoice.total_ht,
            "tva": invoice.tva_amount,
            "ttc": invoice.total_ttc,
            "tva_rate": settings.tva_rate,
        },
    )
    return save_bytes(data, "invoices", filename)


def _render_document(*, title, quote_or_invoice_lines, dossier, client, settings, totals) -> bytes:
    styles = getSampleStyleSheet()
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=2 * cm, rightMargin=2 * cm)
    story = []
    company = settings.company_name or "AUTA Gestion"
    story.append(Paragraph(f"<b>{company}</b>", styles["Title"]))
    if settings.address:
        story.append(Paragraph(settings.address, styles["Normal"]))
    if settings.siret:
        story.append(Paragraph(f"SIRET : {settings.siret}", styles["Normal"]))
    story.append(Spacer(1, 0.5 * cm))
    story.append(Paragraph(f"<b>{title}</b>", styles["Heading1"]))
    story.append(
        Paragraph(
            f"Client : {client.first_name} {client.last_name}<br/>"
            f"Véhicule : {dossier.vehicle_make} {dossier.vehicle_model} — {dossier.license_plate}<br/>"
            f"Dossier : {dossier.reference}",
            styles["Normal"],
        )
    )
    story.append(Spacer(1, 0.4 * cm))

    data = [["Description", "Qté", "P.U. HT", "Total HT"]]
    for line in sorted(quote_or_invoice_lines, key=lambda l: l.sort_order):
        data.append(
            [
                line.description[:60],
                f"{line.quantity:g}",
                _money(line.unit_price),
                _money(line.total),
            ]
        )
    table = Table(data, colWidths=[9 * cm, 2 * cm, 3 * cm, 3 * cm])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e3a2f")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.whitesmoke, colors.Color(0.95, 0.97, 0.95)]),
            ]
        )
    )
    story.append(table)
    story.append(Spacer(1, 0.5 * cm))
    totals_data = [
        ["Pièces", _money(totals["parts"])],
        ["Main d'œuvre", _money(totals["labor"])],
        ["Peinture", _money(totals["paint"])],
        ["Consommables", _money(totals["consumables"])],
        ["Total HT", _money(totals["ht"])],
        [f"TVA ({totals['tva_rate']:g} %)", _money(totals["tva"])],
        ["Total TTC", _money(totals["ttc"])],
    ]
    t2 = Table(totals_data, colWidths=[12 * cm, 5 * cm])
    t2.setStyle(
        TableStyle(
            [
                ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
                ("LINEABOVE", (0, -1), (-1, -1), 1, colors.black),
            ]
        )
    )
    story.append(t2)
    doc.build(story)
    return buffer.getvalue()
