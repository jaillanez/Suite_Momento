"""Modelos iniciales de organización y servicios de cuidado."""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    ForeignKeyConstraint,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base común para las tablas de Momento."""


class CareUnitType(str, Enum):
    """Contextos de cuidado acordados para la plataforma."""

    RESIDENCE = "residence"
    HOME_CARE = "home_care"


class UserGroup(str, Enum):
    """Grupos generales de usuarios confirmados para el piloto."""

    STAFF = "staff"
    FAMILY = "family"
    OLDER_ADULT = "older_adult"


class StaffRole(str, Enum):
    """Puestos del personal confirmados para el piloto (02/11/2026)."""

    MANAGER = "manager"
    ADMINISTRATIVE = "administrative"
    PHYSICIAN = "physician"
    CAREGIVER = "caregiver"


# Puestos que pueden otorgar y revocar acceso familiar.
FAMILY_AUTHORIZER_ROLES = frozenset(
    {StaffRole.MANAGER, StaffRole.ADMINISTRATIVE, StaffRole.PHYSICIAN}
)


class SharedCareCategory(str, Enum):
    """Categorías que pueden habilitarse para el acceso familiar."""

    MEDICATION = "medication"
    ACTIVITIES = "activities"
    DIET = "diet"


class Organization(Base):
    """Entidad prestadora que puede administrar varios servicios."""

    __tablename__ = "organizations"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    care_units: Mapped[list[CareUnit]] = relationship(back_populates="organization")
    memberships: Mapped[list[OrganizationMembership]] = relationship(
        back_populates="organization",
        overlaps="care_unit,memberships",
    )


class CareUnit(Base):
    """Residencia o servicio de cuidado domiciliario de una organización."""

    __tablename__ = "care_units"
    __table_args__ = (
        CheckConstraint(
            "service_type IN ('residence', 'home_care')",
            name="ck_care_units_service_type",
        ),
        UniqueConstraint(
            "organization_id",
            "id",
            name="uq_care_units_org_id",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("organizations.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    service_type: Mapped[CareUnitType] = mapped_column(
        SAEnum(
            CareUnitType,
            name="care_unit_type",
            native_enum=False,
            create_constraint=False,
            values_callable=lambda enum_type: [item.value for item in enum_type],
        ),
        nullable=False,
    )
    country_code: Mapped[str] = mapped_column(String(2), nullable=False)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    organization: Mapped[Organization] = relationship(back_populates="care_units")
    workflow_statuses: Mapped[list[CareUnitWorkflowStatus]] = relationship(
        back_populates="care_unit",
        cascade="all, delete-orphan",
        order_by="CareUnitWorkflowStatus.display_order",
    )
    memberships: Mapped[list[OrganizationMembership]] = relationship(
        back_populates="care_unit",
        overlaps="organization,memberships",
    )


class CareUnitWorkflowStatus(Base):
    """Estado editable del seguimiento familiar de un servicio."""

    __tablename__ = "care_unit_workflow_statuses"
    __table_args__ = (
        UniqueConstraint(
            "care_unit_id",
            "code",
            name="uq_care_unit_workflow_statuses_service_code",
        ),
        CheckConstraint(
            "display_order > 0",
            name="ck_care_unit_workflow_statuses_order",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    care_unit_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("care_units.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    code: Mapped[str] = mapped_column(String(40), nullable=False)
    label: Mapped[str] = mapped_column(String(80), nullable=False)
    display_order: Mapped[int] = mapped_column(Integer, nullable=False)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )
    family_visible: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    care_unit: Mapped[CareUnit] = relationship(back_populates="workflow_statuses")


class UserAccount(Base):
    """Identidad de usuario; no contiene credenciales ni inicia sesión."""

    __tablename__ = "user_accounts"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    display_name: Mapped[str] = mapped_column(String(160), nullable=False)
    email: Mapped[str | None] = mapped_column(String(254), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    memberships: Mapped[list[OrganizationMembership]] = relationship(
        back_populates="user"
    )
    credential: Mapped[UserCredential | None] = relationship(lazy="selectin", viewonly=True)

    @property
    def can_sign_in(self) -> bool:
        """Indica si la cuenta tiene contraseña; nunca expone la clave."""
        return self.credential is not None


class OrganizationMembership(Base):
    """Vínculo de una cuenta con una organización y, opcionalmente, un servicio."""

    __tablename__ = "organization_memberships"
    __table_args__ = (
        CheckConstraint(
            "user_group IN ('staff', 'family', 'older_adult')",
            name="ck_membership_user_group",
        ),
        CheckConstraint(
            "(user_group = 'staff' AND staff_role IS NOT NULL) "
            "OR (user_group <> 'staff' AND staff_role IS NULL)",
            name="ck_membership_staff_role",
        ),
        CheckConstraint(
            "staff_role IS NULL OR staff_role IN "
            "('manager', 'administrative', 'physician', 'caregiver')",
            name="ck_membership_staff_role_value",
        ),
        CheckConstraint(
            "handles_inbox = false OR user_group = 'staff'",
            name="ck_membership_inbox_staff",
        ),
        ForeignKeyConstraint(
            ["organization_id", "care_unit_id"],
            ["care_units.organization_id", "care_units.id"],
            name="fk_membership_care_unit_same_organization",
            ondelete="RESTRICT",
        ),
        UniqueConstraint(
            "user_account_id",
            "organization_id",
            "care_unit_id",
            "user_group",
            name="uq_membership_user_scope_group",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    user_account_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("user_accounts.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    organization_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("organizations.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    care_unit_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        nullable=True,
        index=True,
    )
    user_group: Mapped[UserGroup] = mapped_column(
        SAEnum(
            UserGroup,
            name="user_group",
            native_enum=False,
            create_constraint=False,
            values_callable=lambda enum_type: [item.value for item in enum_type],
        ),
        nullable=False,
    )
    role_label: Mapped[str | None] = mapped_column(String(80), nullable=True)
    staff_role: Mapped[StaffRole | None] = mapped_column(
        SAEnum(
            StaffRole,
            name="staff_role",
            native_enum=False,
            create_constraint=False,
            length=20,
            values_callable=lambda enum_type: [item.value for item in enum_type],
        ),
        nullable=True,
    )
    handles_inbox: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    user: Mapped[UserAccount] = relationship(back_populates="memberships")
    organization: Mapped[Organization] = relationship(
        back_populates="memberships",
        overlaps="care_unit,memberships",
    )
    care_unit: Mapped[CareUnit | None] = relationship(
        back_populates="memberships",
        overlaps="organization,memberships",
    )


class CareRecipient(Base):
    """Ficha mínima de una persona cuidada, sin datos clínicos."""

    __tablename__ = "care_recipients"
    __table_args__ = (
        UniqueConstraint(
            "care_unit_id",
            "id",
            name="uq_care_recipients_service_id",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    care_unit_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("care_units.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    display_name: Mapped[str] = mapped_column(String(160), nullable=False)

    # Identificación (Fase 3). Todo opcional hasta que el piloto defina obligatorios.
    first_name: Mapped[str | None] = mapped_column(String(80))
    last_name: Mapped[str | None] = mapped_column(String(80))
    preferred_name: Mapped[str | None] = mapped_column(String(80))
    birth_date: Mapped[date | None] = mapped_column(Date)
    document_type: Mapped[str | None] = mapped_column(String(20))
    document_number: Mapped[str | None] = mapped_column(String(30))
    sex: Mapped[str | None] = mapped_column(String(10))
    nationality: Mapped[str | None] = mapped_column(String(60))
    birth_country: Mapped[str | None] = mapped_column(String(60))
    birth_province: Mapped[str | None] = mapped_column(String(60))
    birth_locality: Mapped[str | None] = mapped_column(String(100))
    education_level: Mapped[str | None] = mapped_column(String(40))
    education_title: Mapped[str | None] = mapped_column(String(120))
    occupation: Mapped[str | None] = mapped_column(String(40))
    occupation_detail: Mapped[str | None] = mapped_column(String(200))
    marital_status: Mapped[str | None] = mapped_column(String(30))
    has_children: Mapped[bool | None] = mapped_column(Boolean)
    children_details: Mapped[str | None] = mapped_column(Text)
    languages: Mapped[str | None] = mapped_column(String(120))
    admission_date: Mapped[date | None] = mapped_column(Date)
    room: Mapped[str | None] = mapped_column(String(40))
    address: Mapped[str | None] = mapped_column(String(200))

    # Cobertura y profesional de referencia.
    health_coverage: Mapped[str | None] = mapped_column(String(120))
    coverage_member_number: Mapped[str | None] = mapped_column(String(60))
    primary_physician: Mapped[str | None] = mapped_column(String(120))
    primary_physician_phone: Mapped[str | None] = mapped_column(String(40))

    # Salud: información de referencia registrada por profesionales. No son
    # indicaciones ni reemplazan la historia clínica.
    allergies: Mapped[str | None] = mapped_column(Text)
    relevant_conditions: Mapped[str | None] = mapped_column(Text)
    diet_notes: Mapped[str | None] = mapped_column(Text)
    mobility_support: Mapped[str | None] = mapped_column(Text)
    sensory_communication: Mapped[str | None] = mapped_column(Text)
    support_needs: Mapped[str | None] = mapped_column(Text)

    # Antecedentes y datos de ingreso según la planilla del equipo; se valida
    # contra la definición de momento_api.forms.
    background: Mapped[dict[str, object] | None] = mapped_column(JSON)

    # Historia de vida y preferencias.
    life_history: Mapped[str | None] = mapped_column(Text)
    preferences: Mapped[str | None] = mapped_column(Text)
    routines: Mapped[str | None] = mapped_column(Text)
    beliefs: Mapped[str | None] = mapped_column(Text)

    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    contacts: Mapped[list[CareRecipientContact]] = relationship(
        back_populates="care_recipient",
        order_by="CareRecipientContact.created_at",
        cascade="all, delete-orphan",
    )
    documents: Mapped[list[CareRecipientDocument]] = relationship(
        order_by="CareRecipientDocument.created_at.desc()",
        viewonly=True,
    )
    care_unit: Mapped[CareUnit] = relationship(viewonly=True)


class CareRecipientContact(Base):
    """Contacto de la persona cuidada; no es una cuenta ni da acceso."""

    __tablename__ = "care_recipient_contacts"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    care_recipient_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("care_recipients.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    full_name: Mapped[str] = mapped_column(String(160), nullable=False)
    relationship_label: Mapped[str | None] = mapped_column(String(60))
    phone: Mapped[str | None] = mapped_column(String(40))
    email: Mapped[str | None] = mapped_column(String(254))
    is_emergency: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    is_legal_representative: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    notes: Mapped[str | None] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    care_recipient: Mapped[CareRecipient] = relationship(back_populates="contacts")


class CareRecipientDocument(Base):
    """Archivo adjunto a la ficha; el contenido se guarda fuera de la base."""

    __tablename__ = "care_recipient_documents"
    __table_args__ = (
        CheckConstraint(
            "category IN ('identity', 'consent', 'study', 'photo', 'other')",
            name="ck_recipient_documents_category",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    care_recipient_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("care_recipients.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    category: Mapped[str] = mapped_column(String(20), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(200), nullable=False)
    content_type: Mapped[str] = mapped_column(String(60), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    # Nombre interno generado por el sistema; nunca deriva del nombre original.
    storage_key: Mapped[str] = mapped_column(String(80), nullable=False, unique=True)
    uploaded_by_membership_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("organization_memberships.id", ondelete="RESTRICT"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    uploaded_by: Mapped[OrganizationMembership] = relationship()


class Assessment(Base):
    """Escala aplicada a una persona; el puntaje lo calcula el sistema."""

    __tablename__ = "assessments"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    care_recipient_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("care_recipients.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    scale_code: Mapped[str] = mapped_column(String(20), nullable=False)
    performed_on: Mapped[date] = mapped_column(Date, nullable=False)
    answers: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    total_score: Mapped[int] = mapped_column(Integer, nullable=False)
    max_score: Mapped[int] = mapped_column(Integer, nullable=False)
    subscores: Mapped[dict[str, object] | None] = mapped_column(JSON)
    interpretation: Mapped[str | None] = mapped_column(String(80))
    notes: Mapped[str | None] = mapped_column(Text)
    performed_by_membership_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("organization_memberships.id", ondelete="RESTRICT"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    performed_by: Mapped[OrganizationMembership] = relationship()


class FamilyAuthorization(Base):
    """Permisos familiares explícitos por persona y categoría."""

    __tablename__ = "family_authorizations"
    __table_args__ = (
        CheckConstraint(
            "category IN ('medication', 'activities', 'diet')",
            name="ck_family_authorizations_category",
        ),
        UniqueConstraint(
            "family_membership_id",
            "care_recipient_id",
            "category",
            name="uq_family_authorizations_person_family_category",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    care_recipient_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("care_recipients.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    family_membership_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("organization_memberships.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    authorized_by_membership_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("organization_memberships.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    category: Mapped[SharedCareCategory] = mapped_column(
        SAEnum(
            SharedCareCategory,
            name="shared_care_category",
            native_enum=False,
            create_constraint=False,
            values_callable=lambda enum_type: [item.value for item in enum_type],
        ),
        nullable=False,
    )
    can_view: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )
    can_respond: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )
    can_request: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )
    granted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    revoked_by_membership_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("organization_memberships.id", ondelete="RESTRICT"),
        nullable=True,
    )


class FamilyRequest(Base):
    """Solicitud iniciada por una familia; no modifica indicaciones ni planes."""

    __tablename__ = "family_requests"
    __table_args__ = (
        CheckConstraint(
            "category IN ('medication', 'activities', 'diet')",
            name="ck_family_requests_category",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    care_unit_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("care_units.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    care_recipient_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("care_recipients.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    family_membership_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("organization_memberships.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    category: Mapped[SharedCareCategory] = mapped_column(
        SAEnum(
            SharedCareCategory,
            name="shared_care_category",
            native_enum=False,
            create_constraint=False,
            values_callable=lambda enum_type: [item.value for item in enum_type],
        ),
        nullable=False,
    )
    subject: Mapped[str] = mapped_column(String(160), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    status_code: Mapped[str] = mapped_column(String(40), nullable=False)
    assigned_to_membership_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("organization_memberships.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    shared_response: Mapped[str | None] = mapped_column(Text, nullable=True)
    responded_by_membership_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("organization_memberships.id", ondelete="RESTRICT"),
        nullable=True,
    )
    responded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    care_recipient: Mapped[CareRecipient] = relationship()
    family_membership: Mapped[OrganizationMembership] = relationship(
        foreign_keys=[family_membership_id]
    )
    assigned_to: Mapped[OrganizationMembership | None] = relationship(
        foreign_keys=[assigned_to_membership_id]
    )


class AuditEvent(Base):
    """Registro de acciones sensibles; no guarda contraseñas ni textos libres."""

    __tablename__ = "audit_events"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True
    )
    actor_account_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("user_accounts.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    organization_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("organizations.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    action: Mapped[str] = mapped_column(String(60), nullable=False)
    target_type: Mapped[str | None] = mapped_column(String(40), nullable=True)
    target_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    outcome: Mapped[str] = mapped_column(String(20), nullable=False)
    details: Mapped[dict[str, object] | None] = mapped_column(JSON, nullable=True)


class UserCredential(Base):
    """Clave protegida asociada a una cuenta Momento."""

    __tablename__ = "user_credentials"

    user_account_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("user_accounts.id", ondelete="CASCADE"),
        primary_key=True,
    )
    password_hash: Mapped[str] = mapped_column(String(256), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class AuthSession(Base):
    """Sesión opaca de corta duración, almacenada por huella y revocable."""

    __tablename__ = "auth_sessions"
    __table_args__ = (
        UniqueConstraint("token_hash", name="uq_auth_sessions_token_hash"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    user_account_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("user_accounts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class PasswordToken(Base):
    """Enlace de un solo uso, enviado por correo, para crear o recuperar la contraseña.

    Solo se guarda la huella del token; el token viaja únicamente en el correo.
    """

    __tablename__ = "password_tokens"
    __table_args__ = (
        UniqueConstraint("token_hash", name="uq_password_tokens_token_hash"),
        CheckConstraint("purpose IN ('reset', 'invite')", name="ck_password_tokens_purpose"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    user_account_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("user_accounts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    purpose: Mapped[str] = mapped_column(String(10), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
