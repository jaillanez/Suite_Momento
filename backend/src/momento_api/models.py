"""Modelos iniciales de organización y servicios de cuidado."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    ForeignKeyConstraint,
    Integer,
    String,
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


class OrganizationMembership(Base):
    """Vínculo de una cuenta con una organización y, opcionalmente, un servicio."""

    __tablename__ = "organization_memberships"
    __table_args__ = (
        CheckConstraint(
            "user_group IN ('staff', 'family', 'older_adult')",
            name="ck_membership_user_group",
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
