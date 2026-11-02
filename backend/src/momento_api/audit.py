"""Registro de acciones sensibles para trazabilidad."""

from uuid import UUID

from sqlalchemy.orm import Session

from momento_api.models import AuditEvent


def record_event(
    session: Session,
    *,
    action: str,
    actor_account_id: UUID | None,
    organization_id: UUID | None = None,
    target_type: str | None = None,
    target_id: UUID | None = None,
    outcome: str = "success",
    details: dict[str, object] | None = None,
) -> None:
    """Agrega un evento a la transacción en curso; quien llama confirma.

    Los detalles solo deben contener identificadores o códigos, nunca
    contraseñas, mensajes de familias ni datos personales en texto libre.
    """
    session.add(
        AuditEvent(
            action=action,
            actor_account_id=actor_account_id,
            organization_id=organization_id,
            target_type=target_type,
            target_id=target_id,
            outcome=outcome,
            details=details,
        )
    )


def record_denied(
    session: Session,
    *,
    action: str,
    actor_account_id: UUID | None,
    organization_id: UUID | None = None,
    target_type: str | None = None,
    target_id: UUID | None = None,
) -> None:
    """Guarda de inmediato un acceso rechazado, antes de responder con error."""
    session.rollback()
    record_event(
        session,
        action=action,
        actor_account_id=actor_account_id,
        organization_id=organization_id,
        target_type=target_type,
        target_id=target_id,
        outcome="denied",
    )
    session.commit()
