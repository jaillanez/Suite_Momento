"""Esquemas de entrada y salida para organizaciones y servicios."""

from datetime import date, datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from momento_api.models import CareUnitType, SharedCareCategory, StaffRole, UserGroup


class OrganizationCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)

    @field_validator("name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("El nombre no puede estar vacío.")
        return value


class OrganizationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


class CareUnitCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    service_type: CareUnitType
    country_code: Literal["AR", "UY"]

    @field_validator("name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("El nombre no puede estar vacío.")
        return value


class CareUnitRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    name: str
    service_type: CareUnitType
    country_code: str
    is_active: bool
    created_at: datetime
    updated_at: datetime



class MembershipCreate(BaseModel):
    display_name: str = Field(min_length=1, max_length=160)
    email: str | None = Field(default=None, max_length=254)
    phone: str | None = Field(default=None, max_length=32)
    user_group: UserGroup
    care_unit_id: UUID | None = None
    role_label: str | None = Field(default=None, max_length=80)
    staff_role: StaffRole | None = None
    handles_inbox: bool = False
    password: str | None = Field(default=None, min_length=8, max_length=128)
    send_invitation: bool = False

    @field_validator("display_name")
    @classmethod
    def clean_display_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("El nombre no puede estar vacío.")
        return value

    @model_validator(mode="after")
    def validate_staff_fields(self) -> "MembershipCreate":
        if self.user_group is UserGroup.STAFF and self.staff_role is None:
            raise ValueError("Elegí el puesto del personal.")
        if self.user_group is not UserGroup.STAFF and (
            self.staff_role is not None or self.handles_inbox
        ):
            raise ValueError("El puesto y la bandeja solo aplican al personal.")
        if self.password and not self.email:
            raise ValueError("Para entrar con contraseña, la cuenta necesita un correo.")
        return self

    @field_validator("email", "phone", "role_label")
    @classmethod
    def clean_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None


class UserAccountSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    display_name: str
    email: str | None
    phone: str | None
    can_sign_in: bool


class OrganizationMembershipRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_account_id: UUID
    organization_id: UUID
    care_unit_id: UUID | None
    user_group: UserGroup
    role_label: str | None
    staff_role: StaffRole | None
    handles_inbox: bool
    is_active: bool
    user: UserAccountSummary


class PasswordSet(BaseModel):
    password: str = Field(min_length=8, max_length=128)


class MembershipUpdate(BaseModel):
    """Cambios que solo el encargado puede hacer sobre un vínculo."""

    staff_role: StaffRole | None = None
    handles_inbox: bool | None = None
    is_active: bool | None = None


class CareRecipientCreate(BaseModel):
    display_name: str = Field(min_length=1, max_length=160)

    @field_validator("display_name")
    @classmethod
    def clean_display_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("El nombre visible no puede estar vacío.")
        return value


class CareRecipientRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    care_unit_id: UUID
    display_name: str
    room: str | None = None
    birth_date: date | None = None
    missing_count: int = 0
    is_active: bool
    created_at: datetime
    updated_at: datetime


class WorkflowStatusInput(BaseModel):
    code: str = Field(min_length=2, max_length=40, pattern=r"^[a-z][a-z0-9_]*$")
    label: str = Field(min_length=1, max_length=80)
    display_order: int = Field(ge=1, le=100)
    is_active: bool
    family_visible: bool

    @field_validator("label")
    @classmethod
    def clean_label(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("La etiqueta no puede estar vacía.")
        return value


class WorkflowStatusListUpdate(BaseModel):
    statuses: list[WorkflowStatusInput] = Field(min_length=1, max_length=20)

    @model_validator(mode="after")
    def validate_statuses(self) -> "WorkflowStatusListUpdate":
        codes = [item.code for item in self.statuses]
        orders = [item.display_order for item in self.statuses]
        if len(codes) != len(set(codes)):
            raise ValueError("No se pueden repetir los códigos de estado.")
        if len(orders) != len(set(orders)):
            raise ValueError("No se pueden repetir las posiciones.")
        if not any(item.is_active for item in self.statuses):
            raise ValueError("Debe quedar al menos un estado activo.")
        return self


class WorkflowStatusRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    care_unit_id: UUID
    code: str
    label: str
    display_order: int
    is_active: bool
    family_visible: bool
    created_at: datetime
    updated_at: datetime


class FamilyAuthorizationGrant(BaseModel):
    family_membership_id: UUID
    care_recipient_id: UUID
    categories: list[SharedCareCategory] = Field(min_length=1, max_length=3)

    @field_validator("categories")
    @classmethod
    def unique_categories(cls, value: list[SharedCareCategory]) -> list[SharedCareCategory]:
        return list(dict.fromkeys(value))


class FamilyAuthorizationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    care_recipient_id: UUID
    family_membership_id: UUID
    authorized_by_membership_id: UUID
    category: SharedCareCategory
    can_view: bool
    can_respond: bool
    can_request: bool
    is_active: bool
    granted_at: datetime
    revoked_at: datetime | None


def _clean_required_text(value: str) -> str:
    value = value.strip()
    if not value:
        raise ValueError("El texto no puede estar vacío.")
    return value


class FamilyRequestCreate(BaseModel):
    care_recipient_id: UUID
    category: SharedCareCategory
    subject: str = Field(min_length=1, max_length=160)
    message: str = Field(min_length=1, max_length=2000)

    @field_validator("subject", "message")
    @classmethod
    def clean_text(cls, value: str) -> str:
        return _clean_required_text(value)


class RequestAssign(BaseModel):
    membership_id: UUID


class RequestStatusChange(BaseModel):
    status_code: str = Field(min_length=2, max_length=40, pattern=r"^[a-z][a-z0-9_]*$")


class RequestResponse(BaseModel):
    shared_response: str = Field(min_length=1, max_length=2000)

    @field_validator("shared_response")
    @classmethod
    def clean_text(cls, value: str) -> str:
        return _clean_required_text(value)


class StaffRequestRead(BaseModel):
    """Vista del personal: incluye responsable asignado."""

    id: UUID
    care_unit_id: UUID
    care_recipient_id: UUID
    care_recipient_name: str
    family_name: str
    category: SharedCareCategory
    subject: str
    message: str
    status_code: str
    status_label: str
    assigned_to_membership_id: UUID | None
    assigned_to_name: str | None
    shared_response: str | None
    responded_at: datetime | None
    created_at: datetime


class FamilyRequestRead(BaseModel):
    """Vista familiar: sin notas internas ni datos del trabajador asignado."""

    id: UUID
    care_recipient_id: UUID
    care_recipient_name: str
    category: SharedCareCategory
    subject: str
    message: str
    status_label: str
    shared_response: str | None
    responded_at: datetime | None
    created_at: datetime


class AssigneeRead(BaseModel):
    membership_id: UUID
    display_name: str
    staff_role: StaffRole


class FamilyCategoryAccess(BaseModel):
    category: SharedCareCategory
    can_view: bool
    can_respond: bool
    can_request: bool


class FamilyLinkedPerson(BaseModel):
    care_recipient_id: UUID
    display_name: str
    care_unit_name: str
    categories: list[FamilyCategoryAccess]


# --- Ficha de la persona cuidada (Fase 3) ------------------------------------

IDENTITY_FIELDS = (
    "display_name", "first_name", "last_name", "preferred_name", "birth_date",
    "document_type", "document_number", "sex", "nationality", "languages",
    "admission_date", "room", "address", "birth_country", "birth_province", "birth_locality",
    "education_level", "education_title", "occupation", "occupation_detail", "marital_status",
    "has_children", "children_details",
)
SEX_OPTIONS = ("mujer", "hombre", "otro")
EDUCATION_LEVELS = (
    "primario_incompleto", "primario_completo", "complementaria", "secundario_incompleto",
    "secundario_completo", "terciario", "universitario",
)
OCCUPATIONS = (
    "ama_de_casa", "oficios", "comerciante", "administrativo", "profesional_no_docente",
    "docente", "desocupado",
)
MARITAL_STATUSES = ("soltero", "casado_en_pareja", "divorciado_separado", "viudo")
COVERAGE_FIELDS = (
    "health_coverage", "coverage_member_number", "primary_physician", "primary_physician_phone",
)
HEALTH_FIELDS = (
    "allergies", "relevant_conditions", "diet_notes", "mobility_support",
    "sensory_communication", "support_needs",
)
STORY_FIELDS = ("life_history", "preferences", "routines", "beliefs")
DOCUMENT_TYPES = ("DNI", "CI", "Pasaporte", "Otro")


class CareRecipientProfileUpdate(BaseModel):
    """Campos editables; solo se aplican los enviados."""

    display_name: str | None = Field(default=None, min_length=1, max_length=160)
    first_name: str | None = Field(default=None, max_length=80)
    last_name: str | None = Field(default=None, max_length=80)
    preferred_name: str | None = Field(default=None, max_length=80)
    birth_date: date | None = None
    document_type: Literal["DNI", "CI", "Pasaporte", "Otro"] | None = None
    document_number: str | None = Field(default=None, max_length=30)
    sex: Literal["mujer", "hombre", "otro"] | None = None
    nationality: str | None = Field(default=None, max_length=60)
    birth_country: str | None = Field(default=None, max_length=60)
    birth_province: str | None = Field(default=None, max_length=60)
    birth_locality: str | None = Field(default=None, max_length=100)
    education_level: Literal[
        "primario_incompleto", "primario_completo", "complementaria", "secundario_incompleto",
        "secundario_completo", "terciario", "universitario",
    ] | None = None
    education_title: str | None = Field(default=None, max_length=120)
    occupation: Literal[
        "ama_de_casa", "oficios", "comerciante", "administrativo", "profesional_no_docente",
        "docente", "desocupado",
    ] | None = None
    occupation_detail: str | None = Field(default=None, max_length=200)
    marital_status: Literal["soltero", "casado_en_pareja", "divorciado_separado", "viudo"] | None = None
    has_children: bool | None = None
    children_details: str | None = Field(default=None, max_length=4000)
    languages: str | None = Field(default=None, max_length=120)
    admission_date: date | None = None
    room: str | None = Field(default=None, max_length=40)
    address: str | None = Field(default=None, max_length=200)
    health_coverage: str | None = Field(default=None, max_length=120)
    coverage_member_number: str | None = Field(default=None, max_length=60)
    primary_physician: str | None = Field(default=None, max_length=120)
    primary_physician_phone: str | None = Field(default=None, max_length=40)
    allergies: str | None = Field(default=None, max_length=4000)
    relevant_conditions: str | None = Field(default=None, max_length=4000)
    diet_notes: str | None = Field(default=None, max_length=4000)
    mobility_support: str | None = Field(default=None, max_length=4000)
    sensory_communication: str | None = Field(default=None, max_length=4000)
    support_needs: str | None = Field(default=None, max_length=4000)
    life_history: str | None = Field(default=None, max_length=8000)
    preferences: str | None = Field(default=None, max_length=4000)
    routines: str | None = Field(default=None, max_length=4000)
    beliefs: str | None = Field(default=None, max_length=2000)
    is_active: bool | None = None

    @field_validator("*", mode="before")
    @classmethod
    def blank_to_none(cls, value: object) -> object:
        if isinstance(value, str):
            value = value.strip()
            return value or None
        return value

    @model_validator(mode="after")
    def validate_dates(self) -> "CareRecipientProfileUpdate":
        today = date.today()
        if self.birth_date and (self.birth_date > today or self.birth_date.year < 1900):
            raise ValueError("Revisá la fecha de nacimiento.")
        if self.admission_date and self.admission_date > today:
            raise ValueError("La fecha de ingreso no puede ser futura.")
        if "display_name" in self.model_fields_set and self.display_name is None:
            raise ValueError("El nombre visible no puede estar vacío.")
        return self


class CareRecipientContactInput(BaseModel):
    full_name: str = Field(min_length=1, max_length=160)
    relationship_label: str | None = Field(default=None, max_length=60)
    phone: str | None = Field(default=None, max_length=40)
    email: str | None = Field(default=None, max_length=254)
    is_emergency: bool = False
    is_legal_representative: bool = False
    notes: str | None = Field(default=None, max_length=200)

    @field_validator("full_name", "relationship_label", "phone", "email", "notes", mode="before")
    @classmethod
    def clean(cls, value: object) -> object:
        if isinstance(value, str):
            value = value.strip()
            return value or None
        return value

    @model_validator(mode="after")
    def needs_way_to_reach(self) -> "CareRecipientContactInput":
        if not self.full_name:
            raise ValueError("El nombre del contacto no puede estar vacío.")
        if self.is_emergency and not self.phone:
            raise ValueError("Un contacto de emergencia necesita teléfono.")
        return self


class CareRecipientContactRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    full_name: str
    relationship_label: str | None
    phone: str | None
    email: str | None
    is_emergency: bool
    is_legal_representative: bool
    notes: str | None


class CareRecipientProfileRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    care_unit_id: UUID
    display_name: str
    first_name: str | None
    last_name: str | None
    preferred_name: str | None
    birth_date: date | None
    document_type: str | None
    document_number: str | None
    sex: str | None
    nationality: str | None
    birth_country: str | None
    birth_province: str | None
    birth_locality: str | None
    education_level: str | None
    education_title: str | None
    occupation: str | None
    occupation_detail: str | None
    marital_status: str | None
    has_children: bool | None
    children_details: str | None
    background: dict[str, Any] | None
    languages: str | None
    admission_date: date | None
    room: str | None
    address: str | None
    health_coverage: str | None
    coverage_member_number: str | None
    primary_physician: str | None
    primary_physician_phone: str | None
    allergies: str | None
    relevant_conditions: str | None
    diet_notes: str | None
    mobility_support: str | None
    sensory_communication: str | None
    support_needs: str | None
    life_history: str | None
    preferences: str | None
    routines: str | None
    beliefs: str | None
    is_active: bool
    updated_at: datetime
    contacts: list[CareRecipientContactRead]
    documents: list["CareRecipientDocumentRead"] = []
    missing_fields: list[str] = []
    photo_document_id: UUID | None = None
    can_edit: bool = False
    can_edit_health: bool = False
    can_edit_story: bool = False
    can_manage_documents: bool = False
    can_deactivate: bool = False


DOCUMENT_CATEGORIES = ("identity", "consent", "study", "other")


class CareRecipientDocumentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    category: Literal["identity", "consent", "study", "photo", "other"]
    original_filename: str
    content_type: str
    size_bytes: int
    created_at: datetime


CareRecipientProfileRead.model_rebuild()


class BackgroundUpdate(BaseModel):
    answers: dict[str, Any]


class ScorePreview(BaseModel):
    answers: dict[str, Any]


class AssessmentCreate(BaseModel):
    scale_code: Literal["barthel", "gds15", "cqc", "ace3"]
    performed_on: date
    answers: dict[str, Any]
    notes: str | None = Field(default=None, max_length=4000)

    @model_validator(mode="after")
    def not_future(self) -> "AssessmentCreate":
        if self.performed_on > date.today():
            raise ValueError("La fecha de la evaluación no puede ser futura.")
        return self


class AssessmentSummary(BaseModel):
    id: UUID
    scale_code: str
    scale_name: str
    performed_on: date
    total_score: int
    max_score: int
    subscores: dict[str, Any] | None
    interpretation: str | None
    performed_by_name: str
    created_at: datetime


class AssessmentDetail(AssessmentSummary):
    answers: dict[str, Any]
    notes: str | None
    credited_by_recall: list[str] = []
