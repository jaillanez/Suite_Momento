"""Consulta del registro de acciones sensibles, solo para el encargado."""

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from momento_api.audit_retention import retention_years
from momento_api.auth import get_organization_admin_account
from momento_api.models import AuditEvent, UserAccount
from momento_api.session import get_session

router = APIRouter(prefix="/api/organizations/{organization_id}/audit-events", tags=["Auditoría"])


class AuditEventRead(BaseModel):
    id: UUID
    occurred_at: datetime
    actor_name: str | None
    action: str
    outcome: str
    target_type: str | None
    details: dict[str, object] | None


@router.get("/retention")
def read_retention(
    organization_id: UUID,
    _: UserAccount = Depends(get_organization_admin_account),
) -> dict[str, int]:
    """Cuántos años se conserva el registro de control."""
    return {"years": retention_years()}


@router.get("", response_model=list[AuditEventRead])
def list_audit_events(
    organization_id: UUID,
    outcome: str | None = Query(default=None, pattern="^(success|denied)$"),
    limit: int = Query(default=200, ge=1, le=500),
    session: Session = Depends(get_session),
    _: UserAccount = Depends(get_organization_admin_account),
) -> list[AuditEventRead]:
    """Solo eventos registrados para esta organización."""
    statement = (
        select(AuditEvent, UserAccount.display_name)
        .outerjoin(UserAccount, UserAccount.id == AuditEvent.actor_account_id)
        .where(AuditEvent.organization_id == organization_id)
        .order_by(AuditEvent.occurred_at.desc(), AuditEvent.id)
        .limit(limit)
    )
    if outcome is not None:
        statement = statement.where(AuditEvent.outcome == outcome)
    return [
        AuditEventRead(
            id=event.id,
            occurred_at=event.occurred_at,
            actor_name=actor_name,
            action=event.action,
            outcome=event.outcome,
            target_type=event.target_type,
            details=event.details,
        )
        for event, actor_name in session.execute(statement).all()
    ]
