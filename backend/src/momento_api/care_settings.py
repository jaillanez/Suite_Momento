"""Configuración del registro del cuidado por servicio.

Cada residencia o servicio domiciliario decide cómo trabaja: turnos, tipos de
novedades, cuánto se puede cargar hacia atrás y qué pasa con los incidentes. La
configura el encargado de la organización desde "Organizaciones". Si un servicio no
guardó nada, se usan los valores de DEFAULTS.
"""

from __future__ import annotations

import copy
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from momento_api.access import find_staff_membership
from momento_api.audit import record_event
from momento_api.auth import get_authenticated_account, get_organization_admin_account
from momento_api.models import CARE_ENTRY_CATEGORIES, CareUnit, StaffRole, UserAccount
from momento_api.session import get_session

CATEGORY_LABELS = {
    "food": "Alimentación",
    "hygiene": "Higiene",
    "sleep": "Descanso",
    "mood": "Ánimo",
    "activity": "Actividad",
    "health": "Salud",
    "incident": "Incidente",
    "other": "Otro",
}

DEFAULTS: dict[str, Any] = {
    # Nombre y hora de inicio; cada turno termina cuando empieza el siguiente.
    "shifts": [{"label": "Mañana", "start_hour": 6}, {"label": "Tarde", "start_hour": 14}, {"label": "Noche", "start_hour": 22}],
    # Tipos de novedad habilitados, con el nombre que usa el servicio.
    "categories": [{"code": code, "label": CATEGORY_LABELS[code], "enabled": True} for code in CARE_ENTRY_CATEGORIES],
    "max_backdate_days": 7,
    "incident_always_important": True,
    # "manager": solo el encargado anula incidentes; "author": también quien lo cargó.
    "incident_void": "manager",
    # Puestos que reciben un aviso en Momento cuando se registra un incidente (vacío: nadie).
    "incident_notify_roles": ["manager"],
    # Además del aviso en Momento, mandar un correo (sin nombre ni detalle).
    "incident_notify_email": False,
}

SHIFT_PRESETS = {
    "3x8": DEFAULTS["shifts"],
    "2x12": [{"label": "Día", "start_hour": 8}, {"label": "Noche", "start_hour": 20}],
}

router = APIRouter(tags=["Configuración del cuidado"])


def settings_for(care_unit: CareUnit) -> dict[str, Any]:
    """Configuración vigente: lo guardado por el servicio sobre los valores por defecto."""
    merged = copy.deepcopy(DEFAULTS)
    merged.update(care_unit.care_settings or {})
    return merged


def category_label(settings: dict[str, Any], code: str) -> str:
    return next((c["label"] for c in settings["categories"] if c["code"] == code), CATEGORY_LABELS.get(code, code))


def clean_settings(raw: Any) -> dict[str, Any]:
    """Valida lo que envía el encargado. Lanza ValueError con un mensaje en español."""
    if not isinstance(raw, dict) or set(raw) - set(DEFAULTS):
        raise ValueError("Hay opciones que no corresponden a la configuración.")
    result = copy.deepcopy(DEFAULTS)

    shifts = raw.get("shifts", result["shifts"])
    if not isinstance(shifts, list) or not 1 <= len(shifts) <= 6:
        raise ValueError("Configurá entre 1 y 6 turnos.")
    clean_shifts = []
    for shift in shifts:
        if not isinstance(shift, dict) or set(shift) != {"label", "start_hour"}:
            raise ValueError("Cada turno necesita nombre y hora de inicio.")
        label, hour = shift["label"], shift["start_hour"]
        if not isinstance(label, str) or not label.strip() or len(label.strip()) > 30:
            raise ValueError("El nombre del turno debe tener entre 1 y 30 caracteres.")
        if isinstance(hour, bool) or not isinstance(hour, int) or not 0 <= hour <= 23:
            raise ValueError("La hora de inicio del turno va de 0 a 23.")
        clean_shifts.append({"label": label.strip(), "start_hour": hour})
    if len({s["start_hour"] for s in clean_shifts}) != len(clean_shifts):
        raise ValueError("Dos turnos no pueden empezar a la misma hora.")
    result["shifts"] = sorted(clean_shifts, key=lambda s: s["start_hour"])

    categories = raw.get("categories", result["categories"])
    if not isinstance(categories, list) or len(categories) != len(CARE_ENTRY_CATEGORIES):
        raise ValueError("Enviá todos los tipos de novedad, habilitados o no.")
    clean_categories = []
    for item in categories:
        if not isinstance(item, dict) or set(item) != {"code", "label", "enabled"} or item["code"] not in CARE_ENTRY_CATEGORIES:
            raise ValueError("Tipo de novedad inválido.")
        label = item["label"]
        if not isinstance(label, str) or not label.strip() or len(label.strip()) > 40 or not isinstance(item["enabled"], bool):
            raise ValueError("Cada tipo de novedad necesita un nombre de hasta 40 caracteres.")
        clean_categories.append({"code": item["code"], "label": label.strip(), "enabled": item["enabled"]})
    # "Incidente" está protegido: siempre habilitado y con su nombre, porque de él dependen
    # los avisos y las reglas de anulación. Ningún otro tipo puede llamarse igual.
    reserved = CATEGORY_LABELS["incident"].casefold()
    for c in clean_categories:
        if c["code"] == "incident":
            c["enabled"], c["label"] = True, CATEGORY_LABELS["incident"]
        elif c["label"].casefold() == reserved:
            raise ValueError("«Incidente» está reservado para el tipo de novedad incidente.")
    if len({c["code"] for c in clean_categories}) != len(CARE_ENTRY_CATEGORIES):
        raise ValueError("Hay tipos de novedad repetidos.")
    if not any(c["enabled"] for c in clean_categories):
        raise ValueError("Dejá al menos un tipo de novedad habilitado.")
    order = {code: index for index, code in enumerate(CARE_ENTRY_CATEGORIES)}
    result["categories"] = sorted(clean_categories, key=lambda c: order[c["code"]])

    days = raw.get("max_backdate_days", result["max_backdate_days"])
    if isinstance(days, bool) or not isinstance(days, int) or not 0 <= days <= 31:
        raise ValueError("Los días para cargar hacia atrás van de 0 a 31.")
    result["max_backdate_days"] = days

    important = raw.get("incident_always_important", result["incident_always_important"])
    if not isinstance(important, bool):
        raise ValueError("Opción inválida para incidentes importantes.")
    result["incident_always_important"] = important

    void = raw.get("incident_void", result["incident_void"])
    if void not in ("manager", "author"):
        raise ValueError("Opción inválida para anular incidentes.")
    result["incident_void"] = void

    roles = raw.get("incident_notify_roles", result["incident_notify_roles"])
    valid_roles = {role.value for role in StaffRole}
    if not isinstance(roles, list) or not all(isinstance(r, str) and r in valid_roles for r in roles):
        raise ValueError("Puesto inválido en los avisos de incidentes.")
    result["incident_notify_roles"] = [role.value for role in StaffRole if role.value in roles]

    email = raw.get("incident_notify_email", result["incident_notify_email"])
    if not isinstance(email, bool):
        raise ValueError("Opción inválida para el aviso por correo.")
    result["incident_notify_email"] = email
    return result


def _public(settings: dict[str, Any]) -> dict[str, Any]:
    return {**settings, "presets": SHIFT_PRESETS}


@router.get("/api/care-units/{care_unit_id}/care-settings")
def read_settings(
    care_unit_id: UUID,
    session: Session = Depends(get_session),
    account: UserAccount = Depends(get_authenticated_account),
) -> dict[str, Any]:
    """Cualquier persona del equipo del servicio ve cómo está configurado."""
    care_unit = session.get(CareUnit, care_unit_id)
    if care_unit is None or not care_unit.is_active or find_staff_membership(
        session, account_id=account.id, organization_id=care_unit.organization_id, care_unit_id=care_unit.id
    ) is None:
        raise HTTPException(status_code=404, detail="Servicio no encontrado.")
    return _public(settings_for(care_unit))


@router.put("/api/organizations/{organization_id}/care-units/{care_unit_id}/care-settings")
def update_settings(
    organization_id: UUID,
    care_unit_id: UUID,
    payload: dict[str, Any],
    session: Session = Depends(get_session),
    account: UserAccount = Depends(get_organization_admin_account),
) -> dict[str, Any]:
    """Solo el encargado de la organización cambia la configuración."""
    care_unit = session.scalar(
        select(CareUnit).where(
            CareUnit.id == care_unit_id, CareUnit.organization_id == organization_id, CareUnit.is_active.is_(True)
        )
    )
    if care_unit is None:
        raise HTTPException(status_code=404, detail="Servicio no encontrado.")
    try:
        settings = clean_settings(payload)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    previous = settings_for(care_unit)
    care_unit.care_settings = settings
    record_event(
        session, action="care_settings.updated", actor_account_id=account.id,
        organization_id=organization_id, target_type="care_unit", target_id=care_unit.id,
        details={"changed": sorted(key for key in settings if settings[key] != previous.get(key))},
    )
    session.commit()
    return _public(settings)
