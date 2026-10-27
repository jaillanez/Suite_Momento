"""Esquemas de entrada y salida para organizaciones y servicios."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from momento_api.models import CareUnitType


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
