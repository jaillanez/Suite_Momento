"""Registro diario del cuidado, pendientes y entrega de turno (Fase 4, primera entrega).

Todo el personal del servicio puede registrar y ver. Los registros no se editan: si hay
un error, quien lo cargó (o el encargado) lo anula con un motivo y queda visible tachado.
La familia no ve estos registros; compartir información es parte de la Fase 5.
La medicación queda fuera hasta que el equipo valide el circuito.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Literal
from uuid import UUID
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from momento_api.access import find_staff_membership
from momento_api.audit import record_event
from momento_api.auth import get_authenticated_account
from momento_api.models import (
    CARE_ENTRY_CATEGORIES,
    CareEntry,
    CareRecipient,
    CareTask,
    CareUnit,
    OrganizationMembership,
    StaffRole,
    UserAccount,
)
from momento_api.session import get_session

router = APIRouter(prefix="/api/care-units", tags=["Registro del cuidado"])

# --- Parámetros (a validar con el piloto) -------------------------------------
# Turnos: nombre y hora de inicio; cada uno termina cuando empieza el siguiente.
SHIFTS = [("Mañana", 6), ("Tarde", 14), ("Noche", 22)]
TIMEZONES = {"AR": "America/Argentina/Buenos_Aires", "UY": "America/Montevideo"}
# Hasta cuántos días hacia atrás se puede cargar un registro olvidado.
MAX_BACKDATE_DAYS = 7

Category = Literal["food", "hygiene", "sleep", "mood", "activity", "health", "incident", "other"]
assert set(Category.__args__) == set(CARE_ENTRY_CATEGORIES)  # type: ignore[attr-defined]


# --- Turnos ------------------------------------------------------------------


def _zone(care_unit: CareUnit) -> ZoneInfo:
    return ZoneInfo(TIMEZONES.get(care_unit.country_code, "America/Argentina/Buenos_Aires"))


def shift_at(moment: datetime, zone: ZoneInfo) -> dict[str, object]:
    """Turno que contiene el momento dado, con inicio y fin en hora local."""
    local = moment.astimezone(zone)
    starts = []
    for day_offset in (-1, 0, 1):
        day = local.date() + timedelta(days=day_offset)
        for label, hour in SHIFTS:
            starts.append((datetime(day.year, day.month, day.day, hour, tzinfo=zone), label))
    starts.sort()
    for (start, label), (end, _) in zip(starts, starts[1:]):
        if start <= local < end:
            return {"label": label, "start": start, "end": end}
    raise AssertionError("turno no encontrado")  # pragma: no cover


# --- Esquemas ----------------------------------------------------------------


class EntryCreate(BaseModel):
    category: Category
    text: str = Field(min_length=1, max_length=2000)
    important: bool = False
    occurred_at: datetime | None = None

    @field_validator("text")
    @classmethod
    def clean_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Escribí qué pasó.")
        return value


class VoidInput(BaseModel):
    reason: str = Field(min_length=3, max_length=300)


class TaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    details: str | None = Field(default=None, max_length=2000)
    due_on: date | None = None
    care_recipient_id: UUID | None = None

    @field_validator("title")
    @classmethod
    def clean_title(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Escribí el pendiente.")
        return value


class TaskClose(BaseModel):
    note: str | None = Field(default=None, max_length=500)


# --- Ayudas ------------------------------------------------------------------


def _unit_and_member(session: Session, account: UserAccount, care_unit_id: UUID) -> tuple[CareUnit, OrganizationMembership]:
    care_unit = session.get(CareUnit, care_unit_id)
    member = (
        find_staff_membership(
            session, account_id=account.id, organization_id=care_unit.organization_id, care_unit_id=care_unit.id
        )
        if care_unit is not None and care_unit.is_active
        else None
    )
    if care_unit is None or member is None:
        raise HTTPException(status_code=404, detail="Servicio no encontrado.")
    return care_unit, member


def _is_manager(session: Session, account: UserAccount, care_unit: CareUnit) -> bool:
    return find_staff_membership(
        session, account_id=account.id, organization_id=care_unit.organization_id,
        care_unit_id=care_unit.id, roles=(StaffRole.MANAGER,),
    ) is not None


def _active_recipient(session: Session, care_unit: CareUnit, recipient_id: UUID) -> CareRecipient:
    recipient = session.scalar(
        select(CareRecipient).where(CareRecipient.id == recipient_id, CareRecipient.care_unit_id == care_unit.id)
    )
    if recipient is None or not recipient.is_active:
        raise HTTPException(status_code=404, detail="Persona cuidada no encontrada.")
    return recipient


def _utc(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value


def _may_void(entry: CareEntry, account: UserAccount, manager: bool) -> bool:
    """Quien lo cargó puede anular sus registros comunes; un incidente solo lo anula el encargado."""
    if entry.category == "incident":
        return manager
    return manager or entry.recorded_by.user_account_id == account.id


def _entry_read(entry: CareEntry, account: UserAccount, manager: bool) -> dict[str, object]:
    return {
        "id": str(entry.id),
        "care_recipient_id": str(entry.care_recipient_id),
        "recipient_name": entry.recipient.preferred_name or entry.recipient.display_name,
        "category": entry.category,
        "text": entry.text,
        "important": entry.important,
        "occurred_at": _utc(entry.occurred_at).isoformat(),
        "recorded_by_name": entry.recorded_by.user.display_name,
        "voided": entry.voided_at is not None,
        "void_reason": entry.void_reason,
        "voided_by_name": entry.voided_by.user.display_name if entry.voided_by else None,
        "can_void": entry.voided_at is None and _may_void(entry, account, manager),
    }


def _task_read(task: CareTask, account: UserAccount, manager: bool) -> dict[str, object]:
    return {
        "id": str(task.id),
        "title": task.title,
        "details": task.details,
        "due_on": task.due_on.isoformat() if task.due_on else None,
        "status": task.status,
        "care_recipient_id": str(task.care_recipient_id) if task.care_recipient_id else None,
        "recipient_name": (task.recipient.preferred_name or task.recipient.display_name) if task.recipient else None,
        "created_by_name": task.created_by.user.display_name,
        "created_at": _utc(task.created_at).isoformat(),
        "closed_by_name": task.closed_by.user.display_name if task.closed_by else None,
        "closing_note": task.closing_note,
        "can_cancel": task.status == "open" and (manager or task.created_by.user_account_id == account.id),
    }


_ENTRY_LOAD = (
    selectinload(CareEntry.recipient),
    selectinload(CareEntry.recorded_by).selectinload(OrganizationMembership.user),
    selectinload(CareEntry.voided_by).selectinload(OrganizationMembership.user),
)
_TASK_LOAD = (
    selectinload(CareTask.recipient),
    selectinload(CareTask.created_by).selectinload(OrganizationMembership.user),
    selectinload(CareTask.closed_by).selectinload(OrganizationMembership.user),
)


def _open_tasks(session: Session, care_unit: CareUnit, recipient_id: UUID | None = None) -> list[CareTask]:
    query = select(CareTask).options(*_TASK_LOAD).where(CareTask.care_unit_id == care_unit.id, CareTask.status == "open")
    if recipient_id is not None:
        query = query.where(CareTask.care_recipient_id == recipient_id)
    tasks = session.scalars(query).all()
    return sorted(tasks, key=lambda t: (t.due_on is None, t.due_on or date.max, _utc(t.created_at)))


# --- Registros ---------------------------------------------------------------


@router.get("/{care_unit_id}/care-recipients/{recipient_id}/care-entries")
def list_entries(
    care_unit_id: UUID,
    recipient_id: UUID,
    days: int = Query(default=7, ge=1, le=31),
    session: Session = Depends(get_session),
    account: UserAccount = Depends(get_authenticated_account),
) -> dict[str, object]:
    care_unit, member = _unit_and_member(session, account, care_unit_id)
    recipient = _active_recipient(session, care_unit, recipient_id)
    since = datetime.now(timezone.utc) - timedelta(days=days)
    entries = session.scalars(
        select(CareEntry).options(*_ENTRY_LOAD)
        .where(CareEntry.care_recipient_id == recipient.id, CareEntry.occurred_at >= since)
        .order_by(CareEntry.occurred_at.desc())
    ).all()
    manager = _is_manager(session, account, care_unit)
    record_event(
        session, action="care_log.viewed", actor_account_id=account.id,
        organization_id=care_unit.organization_id, target_type="care_recipient", target_id=recipient.id,
    )
    session.commit()
    return {
        "entries": [_entry_read(entry, account, manager) for entry in entries],
        "open_tasks": [_task_read(task, account, manager) for task in _open_tasks(session, care_unit, recipient.id)],
    }


@router.post("/{care_unit_id}/care-recipients/{recipient_id}/care-entries", status_code=status.HTTP_201_CREATED)
def create_entry(
    care_unit_id: UUID,
    recipient_id: UUID,
    payload: EntryCreate,
    session: Session = Depends(get_session),
    account: UserAccount = Depends(get_authenticated_account),
) -> dict[str, object]:
    care_unit, member = _unit_and_member(session, account, care_unit_id)
    recipient = _active_recipient(session, care_unit, recipient_id)
    now = datetime.now(timezone.utc)
    occurred_at = _utc(payload.occurred_at) if payload.occurred_at else now
    if occurred_at > now + timedelta(minutes=5):
        raise HTTPException(status_code=422, detail="La hora del registro no puede ser futura.")
    if occurred_at < now - timedelta(days=MAX_BACKDATE_DAYS):
        raise HTTPException(status_code=422, detail=f"Solo se pueden cargar registros de los últimos {MAX_BACKDATE_DAYS} días.")
    entry = CareEntry(
        care_unit_id=care_unit.id, care_recipient_id=recipient.id, category=payload.category,
        # Los incidentes siempre se destacan en la entrega de turno.
        text=payload.text, important=payload.important or payload.category == "incident", occurred_at=occurred_at,
        recorded_by_membership_id=member.id,
    )
    session.add(entry)
    session.flush()
    record_event(
        session, action="care_entry.created", actor_account_id=account.id,
        organization_id=care_unit.organization_id, target_type="care_entry", target_id=entry.id,
        details={"category": payload.category, "important": entry.important},
    )
    session.commit()
    entry = session.scalar(select(CareEntry).options(*_ENTRY_LOAD).where(CareEntry.id == entry.id))
    return _entry_read(entry, account, _is_manager(session, account, care_unit))


@router.post("/{care_unit_id}/care-entries/{entry_id}/void")
def void_entry(
    care_unit_id: UUID,
    entry_id: UUID,
    payload: VoidInput,
    session: Session = Depends(get_session),
    account: UserAccount = Depends(get_authenticated_account),
) -> dict[str, object]:
    care_unit, member = _unit_and_member(session, account, care_unit_id)
    entry = session.scalar(
        select(CareEntry).options(*_ENTRY_LOAD).where(CareEntry.id == entry_id, CareEntry.care_unit_id == care_unit.id)
    )
    if entry is None:
        raise HTTPException(status_code=404, detail="Registro no encontrado.")
    manager = _is_manager(session, account, care_unit)
    if not _may_void(entry, account, manager):
        detail = ("Un incidente solo lo puede anular el encargado." if entry.category == "incident"
                  else "Solo quien cargó el registro o el encargado pueden anularlo.")
        raise HTTPException(status_code=403, detail=detail)
    if entry.voided_at is not None:
        raise HTTPException(status_code=409, detail="El registro ya estaba anulado.")
    entry.voided_at = datetime.now(timezone.utc)
    entry.voided_by_membership_id = member.id
    entry.void_reason = payload.reason.strip()
    record_event(
        session, action="care_entry.voided", actor_account_id=account.id,
        organization_id=care_unit.organization_id, target_type="care_entry", target_id=entry.id,
        details={"category": entry.category, "important": entry.important},
    )
    session.commit()
    session.refresh(entry)
    return _entry_read(entry, account, manager)


# --- Pendientes --------------------------------------------------------------


@router.get("/{care_unit_id}/care-tasks")
def list_tasks(
    care_unit_id: UUID,
    status_filter: Literal["open", "closed"] = Query(default="open", alias="status"),
    session: Session = Depends(get_session),
    account: UserAccount = Depends(get_authenticated_account),
) -> list[dict[str, object]]:
    care_unit, _ = _unit_and_member(session, account, care_unit_id)
    manager = _is_manager(session, account, care_unit)
    if status_filter == "open":
        tasks = _open_tasks(session, care_unit)
    else:
        tasks = session.scalars(
            select(CareTask).options(*_TASK_LOAD)
            .where(CareTask.care_unit_id == care_unit.id, CareTask.status != "open")
            .order_by(CareTask.closed_at.desc()).limit(100)
        ).all()
    return [_task_read(task, account, manager) for task in tasks]


@router.post("/{care_unit_id}/care-tasks", status_code=status.HTTP_201_CREATED)
def create_task(
    care_unit_id: UUID,
    payload: TaskCreate,
    session: Session = Depends(get_session),
    account: UserAccount = Depends(get_authenticated_account),
) -> dict[str, object]:
    care_unit, member = _unit_and_member(session, account, care_unit_id)
    if payload.care_recipient_id is not None:
        _active_recipient(session, care_unit, payload.care_recipient_id)
    task = CareTask(
        care_unit_id=care_unit.id, care_recipient_id=payload.care_recipient_id, title=payload.title,
        details=(payload.details or "").strip() or None, due_on=payload.due_on,
        created_by_membership_id=member.id,
    )
    session.add(task)
    session.flush()
    record_event(
        session, action="care_task.created", actor_account_id=account.id,
        organization_id=care_unit.organization_id, target_type="care_task", target_id=task.id,
    )
    session.commit()
    task = session.scalar(select(CareTask).options(*_TASK_LOAD).where(CareTask.id == task.id))
    return _task_read(task, account, _is_manager(session, account, care_unit))


def _close_task(
    session: Session, account: UserAccount, care_unit_id: UUID, task_id: UUID, payload: TaskClose, new_status: str
) -> dict[str, object]:
    care_unit, member = _unit_and_member(session, account, care_unit_id)
    task = session.scalar(
        select(CareTask).options(*_TASK_LOAD).where(CareTask.id == task_id, CareTask.care_unit_id == care_unit.id)
    )
    if task is None:
        raise HTTPException(status_code=404, detail="Pendiente no encontrado.")
    if task.status != "open":
        raise HTTPException(status_code=409, detail="El pendiente ya estaba cerrado.")
    manager = _is_manager(session, account, care_unit)
    # Resolver un pendiente lo puede hacer cualquiera del turno (es la idea de la continuidad);
    # queda quién lo cerró y la nota. Cancelarlo sin resolver es solo de quien lo creó o del encargado.
    if new_status == "cancelled" and not manager and task.created_by.user_account_id != account.id:
        raise HTTPException(status_code=403, detail="Solo quien lo creó o el encargado pueden cancelarlo.")
    task.status = new_status
    task.closed_at = datetime.now(timezone.utc)
    task.closed_by_membership_id = member.id
    task.closing_note = (payload.note or "").strip() or None
    record_event(
        session, action=f"care_task.{'completed' if new_status == 'done' else 'cancelled'}",
        actor_account_id=account.id, organization_id=care_unit.organization_id,
        target_type="care_task", target_id=task.id,
    )
    session.commit()
    task = session.scalar(select(CareTask).options(*_TASK_LOAD).where(CareTask.id == task.id))
    return _task_read(task, account, manager)


@router.post("/{care_unit_id}/care-tasks/{task_id}/complete")
def complete_task(
    care_unit_id: UUID, task_id: UUID, payload: TaskClose,
    session: Session = Depends(get_session), account: UserAccount = Depends(get_authenticated_account),
) -> dict[str, object]:
    return _close_task(session, account, care_unit_id, task_id, payload, "done")


@router.post("/{care_unit_id}/care-tasks/{task_id}/cancel")
def cancel_task(
    care_unit_id: UUID, task_id: UUID, payload: TaskClose,
    session: Session = Depends(get_session), account: UserAccount = Depends(get_authenticated_account),
) -> dict[str, object]:
    return _close_task(session, account, care_unit_id, task_id, payload, "cancelled")


# --- Entrega de turno --------------------------------------------------------


@router.get("/{care_unit_id}/handover")
def handover(
    care_unit_id: UUID,
    session: Session = Depends(get_session),
    account: UserAccount = Depends(get_authenticated_account),
) -> dict[str, object]:
    """Lo ocurrido en el turno anterior y en el actual, y los pendientes abiertos."""
    care_unit, _ = _unit_and_member(session, account, care_unit_id)
    zone = _zone(care_unit)
    now = datetime.now(timezone.utc)
    current = shift_at(now, zone)
    previous = shift_at(current["start"] - timedelta(minutes=1), zone)  # type: ignore[operator]
    entries = session.scalars(
        select(CareEntry).options(*_ENTRY_LOAD)
        .where(
            CareEntry.care_unit_id == care_unit.id,
            CareEntry.occurred_at >= previous["start"].astimezone(timezone.utc),  # type: ignore[union-attr]
            CareEntry.voided_at.is_(None),
        )
        .order_by(CareEntry.occurred_at.desc())
    ).all()
    manager = _is_manager(session, account, care_unit)
    record_event(
        session, action="handover.viewed", actor_account_id=account.id,
        organization_id=care_unit.organization_id, target_type="care_unit", target_id=care_unit.id,
    )
    session.commit()

    def window(shift: dict[str, object]) -> dict[str, object]:
        return {"label": shift["label"], "start": shift["start"].isoformat(), "end": shift["end"].isoformat()}  # type: ignore[union-attr]

    return {
        "current_shift": window(current),
        "previous_shift": window(previous),
        "entries": [_entry_read(entry, account, manager) for entry in entries],
        "open_tasks": [_task_read(task, account, manager) for task in _open_tasks(session, care_unit)],
    }
