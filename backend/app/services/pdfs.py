from __future__ import annotations
import io
from datetime import datetime, timedelta
from typing import Literal, Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

from app.models import Client, Dossier, GarageSettings, Invoice, Quote
from app.services.storage import save_bytes

# Palette calquée sur le modèle AS AUTOS
RED = colors.HexColor("#E30613")
DARK = colors.HexColor("#3A3A3A")
MUTED = colors.HexColor("#6B6B6B")
LINE = colors.HexColor("#D0D0D0")
SIREN_BLUE = colors.HexColor("#4A6FA5")
PAGE_W, PAGE_H = A4


def _money(v: float) -> str:
    return f"{v:,.2f} €".replace(",", " ").replace(".", ",")


def _money_plain(v: float) -> str:
    return f"{v:,.2f}".replace(",", " ").replace(".", ",")


def _fr_date(dt: Optional[datetime]) -> str:
    if not dt:
        dt = datetime.utcnow()
    months = (
        "janv.", "févr.", "mars", "avr.", "mai", "juin",
        "juil.", "août", "sept.", "oct.", "nov.", "déc.",
    )
    return f"{dt.day} {months[dt.month - 1]} {dt.year}"


def generate_quote_pdf(
    quote: Quote,
    dossier: Dossier,
    client: Client,
    settings: GarageSettings,
) -> str:
    filename = f"{quote.number}.pdf"
    data = _render_as_autos_pdf(
        doc_kind="devis",
        number=quote.number,
        issued_at=quote.created_at,
        due_at=(quote.created_at or datetime.utcnow()) + timedelta(days=14),
        payment_method=getattr(settings, "payment_method", None) or "À définir",
        lines=quote.lines,
        dossier=dossier,
        client=client,
        settings=settings,
        total_ht=quote.total_ht,
        tva_amount=quote.tva_amount,
        total_ttc=quote.total_ttc,
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
    issued = invoice.created_at or datetime.utcnow()
    data = _render_as_autos_pdf(
        doc_kind="facture",
        number=invoice.number,
        issued_at=issued,
        due_at=issued + timedelta(days=14),
        payment_method=getattr(settings, "payment_method", None) or "Chèque",
        lines=quote.lines,
        dossier=dossier,
        client=client,
        settings=settings,
        total_ht=invoice.total_ht,
        tva_amount=invoice.tva_amount,
        total_ttc=invoice.total_ttc,
    )
    return save_bytes(data, "invoices", filename)


def _render_as_autos_pdf(
    *,
    doc_kind: Literal["facture", "devis"],
    number: str,
    issued_at: Optional[datetime],
    due_at: Optional[datetime],
    payment_method: str,
    lines,
    dossier: Dossier,
    client: Client,
    settings: GarageSettings,
    total_ht: float,
    tva_amount: float,
    total_ttc: float,
) -> bytes:
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    tva_rate = float(settings.tva_rate or 20.0)
    company = (settings.company_name or "AS AUTOS").strip() or "AS AUTOS"
    phone = (getattr(settings, "phone", None) or "").strip()
    email = (getattr(settings, "email", None) or "").strip()
    address = (settings.address or "").strip()
    siret = (settings.siret or "").strip()
    vat = (getattr(settings, "vat_number", None) or "").strip()
    rcs = (getattr(settings, "rcs", None) or "").strip()
    # Dérive n° TVA FR si SIRET/SIREN connu et TVA vide
    if not vat and siret:
        digits = "".join(ch for ch in siret if ch.isdigit())
        if len(digits) >= 9:
            siren = digits[:9]
            key = (12 + 3 * (int(siren) % 97)) % 97
            vat = f"FR{key:02d}{siren}"

    title = "Facture" if doc_kind == "facture" else "Devis"
    meta_label = "FACTURE N°:" if doc_kind == "facture" else "DEVIS N°:"

    # --- Bandeau rouge ---
    header_h = 28 * mm
    c.setFillColor(RED)
    c.rect(0, PAGE_H - header_h, PAGE_W, header_h, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 22)
    c.drawString(14 * mm, PAGE_H - 18 * mm, company.upper())
    c.setFont("Helvetica-Bold", 16)
    c.drawRightString(PAGE_W - 14 * mm, PAGE_H - 12 * mm, title)
    c.setFont("Helvetica", 8)
    contact_bits = [x for x in (phone, email) if x]
    if contact_bits:
        c.drawRightString(PAGE_W - 14 * mm, PAGE_H - 18 * mm, "  ".join(contact_bits))

    # --- Bandeau gris méta ---
    bar_y = PAGE_H - header_h - 16 * mm
    c.setFillColor(DARK)
    c.rect(0, bar_y, PAGE_W, 16 * mm, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.setFont("Helvetica", 7.5)
    y1 = bar_y + 9.5 * mm
    y2 = bar_y + 4 * mm
    c.drawString(10 * mm, y1, meta_label)
    c.setFont("Helvetica-Bold", 9)
    # Affiche le numéro court si FAC-2026-00021 → 21
    short_no = number.split("-")[-1].lstrip("0") or number
    c.drawString(10 * mm + 28 * mm, y1 - 0.5 * mm, short_no)
    c.setFont("Helvetica", 7.5)
    c.drawString(10 * mm, y2, "MODE DE PAIEMENT:")
    c.setFont("Helvetica-Bold", 8)
    c.drawString(10 * mm + 32 * mm, y2, payment_method)

    c.setFont("Helvetica", 7.5)
    c.drawString(75 * mm, y1, "DATE D'ÉMISSION:")
    c.setFont("Helvetica-Bold", 8)
    c.drawString(75 * mm + 30 * mm, y1, _fr_date(issued_at))

    c.setFont("Helvetica", 7.5)
    c.drawString(140 * mm, y1, "DATE D'ÉCHÉANCE:")
    c.setFont("Helvetica-Bold", 8)
    c.drawString(140 * mm + 30 * mm, y1, _fr_date(due_at))

    # --- Bloc DE / À / Montant ---
    block_top = bar_y - 4 * mm
    col1_x, col2_x, col3_x = 10 * mm, 75 * mm, 130 * mm
    c.setStrokeColor(LINE)
    c.setLineWidth(0.4)
    c.line(col2_x - 3 * mm, block_top - 28 * mm, col2_x - 3 * mm, block_top)
    c.line(col3_x - 3 * mm, block_top - 28 * mm, col3_x - 3 * mm, block_top)

    c.setFillColor(MUTED)
    c.setFont("Helvetica", 7)
    c.drawString(col1_x, block_top - 4 * mm, "DE")
    c.drawString(col2_x, block_top - 4 * mm, "À")
    c.drawString(col3_x, block_top - 4 * mm, "Montant à payer:")

    c.setFillColor(colors.black)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(col1_x, block_top - 9 * mm, company)
    c.setFont("Helvetica", 7.5)
    addr_y = block_top - 13 * mm
    for part in _wrap(address, 42)[:3]:
        c.drawString(col1_x, addr_y, part)
        addr_y -= 3.2 * mm
    c.setFont("Helvetica", 6.5)
    if siret:
        c.setFillColor(SIREN_BLUE)
        c.drawString(col1_x, addr_y - 1 * mm, f"n° SIREN: {_format_siren(siret)}")
        addr_y -= 3 * mm
    c.setFillColor(MUTED)
    if rcs:
        c.drawString(col1_x, addr_y, f"n° RCS: {rcs}")
        addr_y -= 3 * mm
    if vat:
        c.drawString(col1_x, addr_y, f"n° TVA: {vat}")

    c.setFillColor(colors.black)
    c.setFont("Helvetica-Bold", 11)
    client_name = f"{client.last_name} {client.first_name}".strip()
    c.drawString(col2_x, block_top - 10 * mm, client_name)
    c.setFont("Helvetica", 7.5)
    if client.address:
        cy = block_top - 14 * mm
        for part in _wrap(client.address, 30)[:3]:
            c.drawString(col2_x, cy, part)
            cy -= 3.2 * mm

    c.setFillColor(RED)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(col3_x, block_top - 12 * mm, _money(total_ttc))

    # --- Véhicule ---
    veh_y = block_top - 34 * mm
    c.setStrokeColor(LINE)
    c.line(10 * mm, veh_y + 4 * mm, PAGE_W - 10 * mm, veh_y + 4 * mm)
    c.setFillColor(colors.black)
    c.setFont("Helvetica-Oblique", 8)
    make_model = f"{dossier.vehicle_make} {dossier.vehicle_model}".strip() or "—"
    c.drawString(10 * mm, veh_y, f"Marque / Modèle: {make_model}")
    c.drawString(10 * mm, veh_y - 4 * mm, f"Immatriculation: {dossier.license_plate or '—'}")
    year = dossier.vehicle_year or "—"
    c.drawString(10 * mm, veh_y - 8 * mm, f"Année: {year}")
    c.drawString(10 * mm, veh_y - 12 * mm, f"Numéro de série: {dossier.vin or '—'}")

    # --- Table ---
    table_top = veh_y - 20 * mm
    headers = ["DESCRIPTION", "QUANTITÉ", "PRIX (€)", "TVA (€)", "MONTANT (€)"]
    col_w = [78 * mm, 22 * mm, 28 * mm, 28 * mm, 30 * mm]
    x0 = 10 * mm
    c.setStrokeColor(LINE)
    c.setLineWidth(0.6)
    c.line(x0, table_top + 5 * mm, PAGE_W - 10 * mm, table_top + 5 * mm)
    c.setFillColor(MUTED)
    c.setFont("Helvetica-Bold", 7)
    x = x0
    for i, h in enumerate(headers):
        if i == 0:
            c.drawString(x, table_top, h)
        else:
            c.drawRightString(x + col_w[i], table_top, h)
        x += col_w[i]
    c.setStrokeColor(LINE)
    c.line(x0, table_top - 2 * mm, PAGE_W - 10 * mm, table_top - 2 * mm)

    row_y = table_top - 7 * mm
    c.setFillColor(colors.black)
    c.setFont("Helvetica", 8)
    sorted_lines = sorted(lines, key=lambda l: l.sort_order)
    for line in sorted_lines:
        if row_y < 35 * mm:
            c.showPage()
            row_y = PAGE_H - 20 * mm
            c.setFont("Helvetica", 8)
        qty = float(line.quantity or 0)
        unit = float(line.unit_price or 0)
        ht = round(qty * unit, 2)
        line_tva = round(ht * (tva_rate / 100.0), 2)
        line_ttc = round(ht + line_tva, 2)
        desc = (line.description or "")[:55]
        vals = [
            desc,
            f"{qty:g}".replace(".", ","),
            _money_plain(unit),
            _money_plain(line_tva),
            _money_plain(line_ttc),
        ]
        x = x0
        for i, val in enumerate(vals):
            if i == 0:
                c.drawString(x, row_y, val)
            else:
                c.drawRightString(x + col_w[i], row_y, val)
            x += col_w[i]
        row_y -= 5.2 * mm

    # --- Totaux ---
    tot_x_label = 120 * mm
    tot_x_val = PAGE_W - 14 * mm
    tot_y = max(row_y - 8 * mm, 28 * mm)
    c.setFont("Helvetica", 9)
    c.setFillColor(colors.black)
    c.drawString(tot_x_label, tot_y, "Total H.T.")
    c.drawRightString(tot_x_val, tot_y, _money(total_ht))
    tot_y -= 5 * mm
    c.drawString(tot_x_label, tot_y, f"TVA {_money_plain(tva_rate)} % de {_money_plain(total_ht)}")
    c.drawRightString(tot_x_val, tot_y, _money(tva_amount))
    tot_y -= 7 * mm
    c.setFont("Helvetica-Bold", 11)
    c.drawString(tot_x_label, tot_y, "Montant total (EUR):")
    c.drawRightString(tot_x_val, tot_y, _money(total_ttc))

    c.save()
    return buffer.getvalue()


def _wrap(text: str, width: int) -> list[str]:
    if not text:
        return []
    words = text.replace("\n", " ").split()
    lines: list[str] = []
    cur = ""
    for w in words:
        trial = f"{cur} {w}".strip()
        if len(trial) <= width:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def _format_siren(siret: str) -> str:
    digits = "".join(ch for ch in siret if ch.isdigit())
    siren = digits[:9]
    if len(siren) < 9:
        return siret
    return f"{siren[:3]} {siren[3:6]} {siren[6:9]}"
