"""Consulta del registro de acciones sensibles, solo para el encargado."""

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from momento_api.auth import get_organization_admin_account
from momento_api.models import AuditEvent, OrganizationMembership, UserAccount
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


@router.get("", response_model=list[AuditEventRead])
def list_audit_events(
    organization_id: UUID,
    outcome: str | None = Query(default=None, pattern="^(success|denied)$"),
    limit: int = Query(default=200, ge=1, le=500),
    session: Session = Depends(get_session),
    _: UserAccount = Depends(get_organization_admin_account),
) -> list[AuditEventRead]:
    """Eventos de la organización e inicios de sesión de sus integrantes."""
    members = select(OrganizationMembership.user_account_id).where(
        OrganizationMembership.organization_id == organization_id
    )
    statement = (
        select(AuditEvent, UserAccount.display_name)
        .outerjoin(UserAccount, UserAccount.id == AuditEvent.actor_account_id)
        .where(
            or_(
                AuditEvent.organization_id == organization_id,
                and_(
                    AuditEvent.organization_id.is_(None),
                    AuditEvent.actor_account_id.in_(members),
                ),
            )
        )
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
