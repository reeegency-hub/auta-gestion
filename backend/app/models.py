from __future__ import annotations
from datetime import datetime, timezone
import enum
from typing import Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class UserRole(str, enum.Enum):
    """MVP : un seul rôle — le directeur du garage."""
    directeur = "directeur"


class WorkshopStatus(str, enum.Enum):
    reception = "reception"
    carrosserie = "carrosserie"
    preparation = "preparation"
    peinture = "peinture"
    remontage = "remontage"
    controle_qualite = "controle_qualite"
    pret_a_livrer = "pret_a_livrer"
    livre = "livre"


WORKSHOP_ORDER = [
    WorkshopStatus.reception,
    WorkshopStatus.carrosserie,
    WorkshopStatus.preparation,
    WorkshopStatus.peinture,
    WorkshopStatus.remontage,
    WorkshopStatus.controle_qualite,
    WorkshopStatus.pret_a_livrer,
    WorkshopStatus.livre,
]


class OperationType(str, enum.Enum):
    piece_remplacer = "piece_remplacer"
    piece_reparer = "piece_reparer"
    main_doeuvre = "main_doeuvre"
    peinture = "peinture"
    annexe = "annexe"


class ExtractionStatus(str, enum.Enum):
    pending = "pending"
    processing = "processing"
    draft = "draft"
    validated = "validated"
    failed = "failed"


class QuoteStatus(str, enum.Enum):
    brouillon = "brouillon"
    en_attente = "en_attente"
    accepte = "accepte"
    refuse = "refuse"


class InvoiceStatus(str, enum.Enum):
    emise = "emise"
    en_attente = "en_attente"
    payee = "payee"


class Tenant(Base):
    __tablename__ = "tenants"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    users = relationship("User", back_populates="tenant")
    settings = relationship("GarageSettings", back_populates="tenant", uselist=False)
    clients = relationship("Client", back_populates="tenant")
    dossiers = relationship("Dossier", back_populates="tenant")


class User(Base):
    __tablename__ = "users"
    __table_args__ = (UniqueConstraint("email", name="uq_users_email"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), default=UserRole.directeur)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    tenant = relationship("Tenant", back_populates="users")


class GarageSettings(Base):
    __tablename__ = "garage_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"), unique=True, nullable=False)
    hourly_rate_carrosserie: Mapped[float] = mapped_column(Float, default=65.0)
    hourly_rate_peinture: Mapped[float] = mapped_column(Float, default=75.0)
    hourly_rate_mecanique: Mapped[float] = mapped_column(Float, default=70.0)
    tva_rate: Mapped[float] = mapped_column(Float, default=20.0)
    consumables_flat: Mapped[float] = mapped_column(Float, default=45.0)
    parts_margin_percent: Mapped[float] = mapped_column(Float, default=30.0)
    forfait_peinture: Mapped[float] = mapped_column(Float, default=0.0)
    company_name: Mapped[str] = mapped_column(String(200), default="")
    address: Mapped[str] = mapped_column(String(300), default="")
    siret: Mapped[str] = mapped_column(String(50), default="")
    phone: Mapped[str] = mapped_column(String(50), default="")
    email: Mapped[str] = mapped_column(String(255), default="")
    vat_number: Mapped[str] = mapped_column(String(50), default="")
    rcs: Mapped[str] = mapped_column(String(100), default="")
    payment_method: Mapped[str] = mapped_column(String(80), default="Chèque")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    tenant = relationship("Tenant", back_populates="settings")


class Client(Base):
    __tablename__ = "clients"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"), nullable=False)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(255), default="")
    phone: Mapped[str] = mapped_column(String(50), default="")
    address: Mapped[str] = mapped_column(String(300), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    tenant = relationship("Tenant", back_populates="clients")
    dossiers = relationship("Dossier", back_populates="client")


class Dossier(Base):
    __tablename__ = "dossiers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"), nullable=False)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id"), nullable=False)
    reference: Mapped[str] = mapped_column(String(50), nullable=False)
    vehicle_make: Mapped[str] = mapped_column(String(100), default="")
    vehicle_model: Mapped[str] = mapped_column(String(100), default="")
    vehicle_year: Mapped[str] = mapped_column(String(10), default="")
    license_plate: Mapped[str] = mapped_column(String(30), default="")
    vin: Mapped[str] = mapped_column(String(50), default="")
    insurance_name: Mapped[str] = mapped_column(String(150), default="")
    insurance_claim_number: Mapped[str] = mapped_column(String(100), default="")
    comments: Mapped[str] = mapped_column(Text, default="")
    workshop_status: Mapped[WorkshopStatus] = mapped_column(
        Enum(WorkshopStatus), default=WorkshopStatus.reception
    )
    assigned_user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    is_closed: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    tenant = relationship("Tenant", back_populates="dossiers")
    client = relationship("Client", back_populates="dossiers")
    assigned_user = relationship("User", foreign_keys=[assigned_user_id])
    photos = relationship("VehiclePhoto", back_populates="dossier", cascade="all, delete-orphan")
    expertise_report = relationship(
        "ExpertiseReport", back_populates="dossier", uselist=False, cascade="all, delete-orphan"
    )
    quotes = relationship(
        "Quote",
        back_populates="dossier",
        cascade="all, delete-orphan",
        order_by="Quote.version.desc()",
    )
    status_history = relationship(
        "StatusHistory", back_populates="dossier", cascade="all, delete-orphan", order_by="StatusHistory.created_at"
    )
    audit_logs = relationship(
        "AuditLog", back_populates="dossier", cascade="all, delete-orphan", order_by="AuditLog.created_at.desc()"
    )

    @property
    def quote(self) -> Optional["Quote"]:
        """Dernière version de devis (compat API / UI)."""
        return self.quotes[0] if self.quotes else None


class VehiclePhoto(Base):
    __tablename__ = "vehicle_photos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    dossier_id: Mapped[int] = mapped_column(ForeignKey("dossiers.id"), nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    original_name: Mapped[str] = mapped_column(String(255), default="")
    caption: Mapped[str] = mapped_column(String(255), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    dossier = relationship("Dossier", back_populates="photos")


class ExpertiseReport(Base):
    __tablename__ = "expertise_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    dossier_id: Mapped[int] = mapped_column(ForeignKey("dossiers.id"), unique=True, nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    original_name: Mapped[str] = mapped_column(String(255), default="")
    status: Mapped[ExtractionStatus] = mapped_column(Enum(ExtractionStatus), default=ExtractionStatus.pending)
    raw_text: Mapped[str] = mapped_column(Text, default="")
    error_message: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    dossier = relationship("Dossier", back_populates="expertise_report")
    operations = relationship(
        "ExtractedOperation", back_populates="report", cascade="all, delete-orphan"
    )


class ExtractedOperation(Base):
    __tablename__ = "extracted_operations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    report_id: Mapped[int] = mapped_column(ForeignKey("expertise_reports.id"), nullable=False)
    operation_type: Mapped[OperationType] = mapped_column(Enum(OperationType), nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    quantity: Mapped[float] = mapped_column(Float, default=1.0)
    hours: Mapped[float] = mapped_column(Float, default=0.0)
    unit_cost: Mapped[float] = mapped_column(Float, default=0.0)
    labor_category: Mapped[str] = mapped_column(String(50), default="carrosserie")
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    report = relationship("ExpertiseReport", back_populates="operations")


class Quote(Base):
    __tablename__ = "quotes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    dossier_id: Mapped[int] = mapped_column(ForeignKey("dossiers.id"), nullable=False)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"), nullable=False)
    number: Mapped[str] = mapped_column(String(50), nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[QuoteStatus] = mapped_column(Enum(QuoteStatus), default=QuoteStatus.brouillon)
    parts_total: Mapped[float] = mapped_column(Float, default=0.0)
    labor_total: Mapped[float] = mapped_column(Float, default=0.0)
    paint_total: Mapped[float] = mapped_column(Float, default=0.0)
    consumables_total: Mapped[float] = mapped_column(Float, default=0.0)
    total_ht: Mapped[float] = mapped_column(Float, default=0.0)
    tva_amount: Mapped[float] = mapped_column(Float, default=0.0)
    total_ttc: Mapped[float] = mapped_column(Float, default=0.0)
    pdf_filename: Mapped[str] = mapped_column(String(255), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    dossier = relationship("Dossier", back_populates="quotes")
    lines = relationship("QuoteLine", back_populates="quote", cascade="all, delete-orphan")
    invoice = relationship("Invoice", back_populates="quote", uselist=False, cascade="all, delete-orphan")


class QuoteLine(Base):
    __tablename__ = "quote_lines"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    quote_id: Mapped[int] = mapped_column(ForeignKey("quotes.id"), nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    quantity: Mapped[float] = mapped_column(Float, default=1.0)
    unit_price: Mapped[float] = mapped_column(Float, default=0.0)
    total: Mapped[float] = mapped_column(Float, default=0.0)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    quote = relationship("Quote", back_populates="lines")


class Invoice(Base):
    __tablename__ = "invoices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    quote_id: Mapped[int] = mapped_column(ForeignKey("quotes.id"), unique=True, nullable=False)
    dossier_id: Mapped[int] = mapped_column(ForeignKey("dossiers.id"), nullable=False)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"), nullable=False)
    number: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[InvoiceStatus] = mapped_column(Enum(InvoiceStatus), default=InvoiceStatus.en_attente)
    total_ht: Mapped[float] = mapped_column(Float, default=0.0)
    tva_amount: Mapped[float] = mapped_column(Float, default=0.0)
    total_ttc: Mapped[float] = mapped_column(Float, default=0.0)
    pdf_filename: Mapped[str] = mapped_column(String(255), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    quote = relationship("Quote", back_populates="invoice")


class StatusHistory(Base):
    __tablename__ = "status_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    dossier_id: Mapped[int] = mapped_column(ForeignKey("dossiers.id"), nullable=False)
    from_status: Mapped[str] = mapped_column(String(50), default="")
    to_status: Mapped[str] = mapped_column(String(50), nullable=False)
    changed_by_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    note: Mapped[str] = mapped_column(String(300), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    dossier = relationship("Dossier", back_populates="status_history")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    dossier_id: Mapped[int] = mapped_column(ForeignKey("dossiers.id"), nullable=False)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    details: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    dossier = relationship("Dossier", back_populates="audit_logs")


class DocumentSequence(Base):
    __tablename__ = "document_sequences"
    __table_args__ = (
        UniqueConstraint("tenant_id", "doc_type", "year", name="uq_docseq_tenant_type_year"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"), nullable=False)
    doc_type: Mapped[str] = mapped_column(String(20), nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    last_number: Mapped[int] = mapped_column(Integer, default=0)


class PartsCatalogItem(Base):
    __tablename__ = "parts_catalog_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"), nullable=False)
    sku: Mapped[str] = mapped_column(String(100), default="")
    label: Mapped[str] = mapped_column(String(300), nullable=False)
    unit_price: Mapped[float] = mapped_column(Float, default=0.0)
    stock_qty: Mapped[float] = mapped_column(Float, default=0.0)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class InvoiceTemplate(Base):
    """Modèle de facture garage : fichier source + mapping des variables client."""

    __tablename__ = "invoice_templates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(200), default="Facture standard")
    # html | pdf_layout | reportlab — pour l’instant on stocke le fichier + JSON de mapping
    kind: Mapped[str] = mapped_column(String(50), default="html")
    filename: Mapped[str] = mapped_column(String(255), default="")
    original_name: Mapped[str] = mapped_column(String(255), default="")
    # JSON : {"client_name": "{{client.full_name}}", ...} ou structure libre
    variables_schema: Mapped[str] = mapped_column(Text, default="{}")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
