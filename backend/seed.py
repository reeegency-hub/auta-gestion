from __future__ import annotations
"""Seed demo data for AUTA Gestion."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))

from reportlab.pdfgen import canvas

from sqlalchemy.orm import joinedload

from app.core.database import Base, SessionLocal, engine
from app.core.security import hash_password
from app.models import (
    Client,
    Dossier,
    ExpertiseReport,
    ExtractedOperation,
    ExtractionStatus,
    GarageSettings,
    OperationType,
    Quote,
    QuoteLine,
    QuoteStatus,
    StatusHistory,
    Tenant,
    User,
    UserRole,
    WorkshopStatus,
)
from app.services.pdfs import generate_quote_pdf
from app.services.storage import ensure_upload_dirs


def make_sample_pdf(path: Path, title: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    c = canvas.Canvas(str(path))
    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, 800, title)
    c.setFont("Helvetica", 11)
    y = 770
    for line in [
        "Rapport d'expertise automobile",
        "Remplacement pare-chocs avant 250.00 €",
        "Réparation aile gauche 2.5 h",
        "Peinture aile gauche 3 h",
        "Main d'oeuvre démontage 1.5 h",
        "Opération annexe : géométrie 80 €",
    ]:
        c.drawString(50, y, line)
        y -= 20
    c.save()


def seed():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    ensure_upload_dirs()
    db = SessionLocal()

    tenant = Tenant(name="Carrosserie Auta Demo")
    db.add(tenant)
    db.flush()

    directeur = User(
        tenant_id=tenant.id,
        email="directeur@auta.demo",
        full_name="Marie Directeur",
        hashed_password=hash_password("auta123"),
        role=UserRole.directeur,
    )
    db.add(directeur)
    db.flush()

    db.add(
        GarageSettings(
            tenant_id=tenant.id,
            company_name="Carrosserie Auta Demo",
            address="12 rue de l'Atelier, 69003 Lyon",
            siret="123 456 789 00012",
            hourly_rate_carrosserie=68.0,
            hourly_rate_peinture=78.0,
            hourly_rate_mecanique=72.0,
            tva_rate=20.0,
            consumables_flat=49.0,
            parts_margin_percent=28.0,
            forfait_peinture=35.0,
        )
    )

    client = Client(
        tenant_id=tenant.id,
        first_name="Jean",
        last_name="Dupont",
        email="jean.dupont@email.fr",
        phone="06 12 34 56 78",
        address="5 avenue des Lilas, Lyon",
    )
    db.add(client)
    db.flush()

    dossier = Dossier(
        tenant_id=tenant.id,
        client_id=client.id,
        reference="DOS-00001",
        vehicle_make="Peugeot",
        vehicle_model="308",
        vehicle_year="2021",
        license_plate="AB-123-CD",
        vin="VF3XXXXXXXXXXXXXX",
        insurance_name="MAIF",
        insurance_claim_number="SIN-2026-0042",
        comments="Choc avant gauche parking",
        workshop_status=WorkshopStatus.carrosserie,
        assigned_user_id=directeur.id,
    )
    db.add(dossier)
    db.flush()
    db.add(
        StatusHistory(
            dossier_id=dossier.id,
            from_status="",
            to_status=WorkshopStatus.reception.value,
            changed_by_id=directeur.id,
            note="Création",
        )
    )
    db.add(
        StatusHistory(
            dossier_id=dossier.id,
            from_status=WorkshopStatus.reception.value,
            to_status=WorkshopStatus.carrosserie.value,
            changed_by_id=directeur.id,
            note="Entrée atelier",
        )
    )

    pdf_path = Path(ensure_upload_dirs()) / "reports" / "demo_expertise.pdf"
    make_sample_pdf(pdf_path, "Expertise Peugeot 308")
    report = ExpertiseReport(
        dossier_id=dossier.id,
        filename="demo_expertise.pdf",
        original_name="expertise_peugeot.pdf",
        status=ExtractionStatus.validated,
        raw_text="Remplacement pare-chocs avant\nRéparation aile\nPeinture",
    )
    db.add(report)
    db.flush()
    ops = [
        ExtractedOperation(
            report_id=report.id,
            operation_type=OperationType.piece_remplacer,
            description="Pare-chocs avant",
            quantity=1,
            unit_cost=250,
            sort_order=0,
        ),
        ExtractedOperation(
            report_id=report.id,
            operation_type=OperationType.piece_reparer,
            description="Aile avant gauche",
            hours=2.5,
            labor_category="carrosserie",
            sort_order=1,
        ),
        ExtractedOperation(
            report_id=report.id,
            operation_type=OperationType.peinture,
            description="Peinture aile avant gauche",
            hours=3,
            labor_category="peinture",
            sort_order=2,
        ),
        ExtractedOperation(
            report_id=report.id,
            operation_type=OperationType.main_doeuvre,
            description="Démontage / remontage",
            hours=1.5,
            labor_category="carrosserie",
            sort_order=3,
        ),
    ]
    db.add_all(ops)

    # Second dossier in reception without quote
    client2 = Client(
        tenant_id=tenant.id,
        first_name="Claire",
        last_name="Martin",
        phone="06 98 76 54 32",
    )
    db.add(client2)
    db.flush()
    d2 = Dossier(
        tenant_id=tenant.id,
        client_id=client2.id,
        reference="DOS-00002",
        vehicle_make="Renault",
        vehicle_model="Clio",
        vehicle_year="2019",
        license_plate="EF-456-GH",
        insurance_name="AXA",
        workshop_status=WorkshopStatus.reception,
    )
    db.add(d2)

    # Third ready to deliver with pending quote
    client3 = Client(
        tenant_id=tenant.id,
        first_name="Omar",
        last_name="Benali",
        phone="07 11 22 33 44",
    )
    db.add(client3)
    db.flush()
    d3 = Dossier(
        tenant_id=tenant.id,
        client_id=client3.id,
        reference="DOS-00003",
        vehicle_make="Volkswagen",
        vehicle_model="Golf",
        license_plate="IJ-789-KL",
        workshop_status=WorkshopStatus.pret_a_livrer,
    )
    db.add(d3)
    db.flush()
    q = Quote(
        dossier_id=d3.id,
        tenant_id=tenant.id,
        number="DEV-2026-00001",
        version=1,
        status=QuoteStatus.en_attente,
        parts_total=180,
        labor_total=200,
        paint_total=150,
        consumables_total=49,
        total_ht=579,
        tva_amount=115.8,
        total_ttc=694.8,
    )
    db.add(q)
    db.flush()
    db.add(
        QuoteLine(
            quote_id=q.id,
            category="pieces",
            description="Rétroviseur droit",
            quantity=1,
            unit_price=180,
            total=180,
        )
    )
    db.add(
        QuoteLine(
            quote_id=q.id,
            category="main_doeuvre",
            description="Remplacement rétroviseur",
            quantity=1.5,
            unit_price=68,
            total=102,
            sort_order=1,
        )
    )
    db.flush()
    db.refresh(q)
    q = (
        db.query(Quote)
        .options(joinedload(Quote.lines))
        .filter(Quote.id == q.id)
        .first()
    )
    settings = db.query(GarageSettings).filter(GarageSettings.tenant_id == tenant.id).first()
    q.pdf_filename = generate_quote_pdf(q, d3, client3, settings)

    # Extra atelier vehicles so board stays rich after testing invoicing
    client4 = Client(tenant_id=tenant.id, first_name="Léa", last_name="Petit", phone="06 55 44 33 22")
    db.add(client4)
    db.flush()
    db.add(
        Dossier(
            tenant_id=tenant.id,
            client_id=client4.id,
            reference="DOS-00004",
            vehicle_make="Citroën",
            vehicle_model="C3",
            license_plate="MN-012-OP",
            workshop_status=WorkshopStatus.peinture,
            assigned_user_id=directeur.id,
        )
    )
    client5 = Client(tenant_id=tenant.id, first_name="Hugo", last_name="Moreau", phone="06 11 00 99 88")
    db.add(client5)
    db.flush()
    db.add(
        Dossier(
            tenant_id=tenant.id,
            client_id=client5.id,
            reference="DOS-00005",
            vehicle_make="Toyota",
            vehicle_model="Yaris",
            license_plate="QR-345-ST",
            workshop_status=WorkshopStatus.preparation,
        )
    )

    db.commit()
    db.close()
    print("Seed OK — compte directeur :")
    print("  directeur@auta.demo / auta123")


if __name__ == "__main__":
    seed()
