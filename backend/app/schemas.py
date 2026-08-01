from __future__ import annotations
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field

from app.models import (
    ExtractionStatus,
    InvoiceStatus,
    OperationType,
    QuoteStatus,
    UserRole,
    WorkshopStatus,
)


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    id: int
    email: EmailStr
    full_name: str
    role: UserRole
    tenant_id: int

    model_config = {"from_attributes": True}


class RegisterIn(BaseModel):
    garage_name: str = Field(min_length=2)
    full_name: str = Field(min_length=2)
    email: EmailStr
    password: str = Field(min_length=6)


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class ChangePasswordIn(BaseModel):
    current_password: str
    new_password: str = Field(min_length=6)


class GarageSettingsIn(BaseModel):
    hourly_rate_carrosserie: float = 65.0
    hourly_rate_peinture: float = 75.0
    hourly_rate_mecanique: float = 70.0
    tva_rate: float = 20.0
    consumables_flat: float = 45.0
    parts_margin_percent: float = 30.0
    forfait_peinture: float = 0.0
    company_name: str = ""
    address: str = ""
    siret: str = ""


class GarageSettingsOut(GarageSettingsIn):
    id: int
    tenant_id: int

    model_config = {"from_attributes": True}


class ClientIn(BaseModel):
    first_name: str
    last_name: str
    email: str = ""
    phone: str = ""
    address: str = ""


class ClientOut(ClientIn):
    id: int
    tenant_id: int
    created_at: datetime

    model_config = {"from_attributes": True}


class DossierCreate(BaseModel):
    client: ClientIn
    vehicle_make: str = ""
    vehicle_model: str = ""
    vehicle_year: str = ""
    license_plate: str = ""
    vin: str = ""
    insurance_name: str = ""
    insurance_claim_number: str = ""
    comments: str = ""


class DossierUpdate(BaseModel):
    vehicle_make: Optional[str] = None
    vehicle_model: Optional[str] = None
    vehicle_year: Optional[str] = None
    license_plate: Optional[str] = None
    vin: Optional[str] = None
    insurance_name: Optional[str] = None
    insurance_claim_number: Optional[str] = None
    comments: Optional[str] = None
    assigned_user_id: Optional[int] = None
    workshop_status: Optional[WorkshopStatus] = None
    is_closed: Optional[bool] = None


class PhotoOut(BaseModel):
    id: int
    filename: str
    original_name: str
    caption: str
    created_at: datetime

    model_config = {"from_attributes": True}


class OperationIn(BaseModel):
    id: Optional[int] = None
    operation_type: OperationType
    description: str
    quantity: float = 1.0
    hours: float = 0.0
    unit_cost: float = 0.0
    labor_category: str = "carrosserie"
    sort_order: int = 0


class OperationOut(OperationIn):
    id: int

    model_config = {"from_attributes": True}


class ExpertiseReportOut(BaseModel):
    id: int
    filename: str
    original_name: str
    status: ExtractionStatus
    raw_text: str
    error_message: str
    operations: list[OperationOut] = []
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class QuoteLineOut(BaseModel):
    id: int
    category: str
    description: str
    quantity: float
    unit_price: float
    total: float
    sort_order: int

    model_config = {"from_attributes": True}


class QuoteOut(BaseModel):
    id: int
    dossier_id: int
    number: str
    version: int = 1
    status: QuoteStatus
    parts_total: float
    labor_total: float
    paint_total: float
    consumables_total: float
    total_ht: float
    tva_amount: float
    total_ttc: float
    pdf_filename: str
    lines: list[QuoteLineOut] = []
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class QuoteStatusUpdate(BaseModel):
    status: QuoteStatus


class QuoteLineUpdate(BaseModel):
    id: Optional[int] = None
    category: str = "annexe"
    description: str
    quantity: float = 1.0
    unit_price: float = 0.0
    sort_order: int = 0


class QuoteLinesUpdate(BaseModel):
    lines: list[QuoteLineUpdate]


class EmailSendIn(BaseModel):
    to: EmailStr
    message: str = ""


class SmsIn(BaseModel):
    to: str
    message: str


class PartsCatalogItemIn(BaseModel):
    sku: str = ""
    label: str
    unit_price: float = 0.0
    stock_qty: float = 0.0
    active: bool = True


class PartsCatalogItemUpdate(BaseModel):
    sku: Optional[str] = None
    label: Optional[str] = None
    unit_price: Optional[float] = None
    stock_qty: Optional[float] = None
    active: Optional[bool] = None


class PartsCatalogItemOut(PartsCatalogItemIn):
    id: int
    tenant_id: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class InvoiceTemplateOut(BaseModel):
    id: int
    tenant_id: int
    name: str
    kind: str
    filename: str
    original_name: str
    variables_schema: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class InvoiceOut(BaseModel):
    id: int
    quote_id: int
    dossier_id: int
    number: str
    status: InvoiceStatus
    total_ht: float
    tva_amount: float
    total_ttc: float
    pdf_filename: str
    created_at: datetime

    model_config = {"from_attributes": True}


class StatusHistoryOut(BaseModel):
    id: int
    from_status: str
    to_status: str
    note: str
    created_at: datetime

    model_config = {"from_attributes": True}


class AuditLogOut(BaseModel):
    id: int
    action: str
    details: str
    created_at: datetime

    model_config = {"from_attributes": True}


class DossierOut(BaseModel):
    id: int
    reference: str
    vehicle_make: str
    vehicle_model: str
    vehicle_year: str
    license_plate: str
    vin: str
    insurance_name: str
    insurance_claim_number: str
    comments: str
    workshop_status: WorkshopStatus
    assigned_user_id: Optional[int]
    is_closed: bool
    created_at: datetime
    updated_at: datetime
    client: ClientOut
    photos: list[PhotoOut] = []
    expertise_report: Optional[ExpertiseReportOut] = None
    quote: Optional[QuoteOut] = None
    quotes: list[QuoteOut] = []
    status_history: list[StatusHistoryOut] = []
    audit_logs: list[AuditLogOut] = []

    model_config = {"from_attributes": True}


class DossierListItem(BaseModel):
    id: int
    reference: str
    vehicle_make: str
    vehicle_model: str
    license_plate: str
    workshop_status: WorkshopStatus
    assigned_user_id: Optional[int]
    is_closed: bool
    created_at: datetime
    client_name: str
    has_quote: bool = False
    quote_status: Optional[QuoteStatus] = None
    has_invoice: bool = False

    model_config = {"from_attributes": True}


class WorkshopUpdate(BaseModel):
    workshop_status: WorkshopStatus
    assigned_user_id: Optional[int] = None
    note: str = ""


class DashboardOut(BaseModel):
    dossiers_en_cours: int
    devis_en_attente: int
    vehicules_en_atelier: int
    pret_a_livrer: int
    factures_en_attente: int
