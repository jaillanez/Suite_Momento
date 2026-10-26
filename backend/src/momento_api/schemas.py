"""Esquemas de entrada y salida para organizaciones y servicios."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

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
