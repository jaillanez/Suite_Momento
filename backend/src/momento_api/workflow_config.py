"""Consulta y configuración local de estados del seguimiento familiar."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from momento_api.models import CareUnit, CareUnitWorkflowStatus
from momento_api.schemas import WorkflowStatusListUpdate, WorkflowStatusRead
from momento_api.session import get_session

router = APIRouter(
    prefix=(
        "/api/organizations/{organization_id}/care-units/"
        "{care_unit_id}/workflow-statuses"
    ),
    tags=["Configuración de seguimiento"],
)


def _get_care_unit(
    session: Session,
    organization_id: UUID,
    care_unit_id: UUID,
) -> CareUnit:
    care_unit = session.scalar(
        select(CareUnit).where(
            CareUnit.id == care_unit_id,
            CareUnit.organization_id == organization_id,
            CareUnit.is_active.is_(True),
        )
    )
    if care_unit is None:
        raise HTTPException(status_code=404, detail="Servicio no encontrado.")
    return care_unit


@router.get("", response_model=list[WorkflowStatusRead])
def list_workflow_statuses(
    organization_id: UUID,
    care_unit_id: UUID,
    session: Session = Depends(get_session),
) -> list[CareUnitWorkflowStatus]:
    """Devuelve los estados configurados para la familia y el equipo."""
    _get_care_unit(session, organization_id, care_unit_id)
    statement = (
        select(CareUnitWorkflowStatus)
        .where(CareUnitWorkflowStatus.care_unit_id == care_unit_id)
        .order_by(
            CareUnitWorkflowStatus.display_order,
            CareUnitWorkflowStatus.code,
        )
    )
    return list(session.scalars(statement).all())


@router.put("", response_model=list[WorkflowStatusRead])
def replace_workflow_statuses(
    organization_id: UUID,
    care_unit_id: UUID,
    payload: WorkflowStatusListUpdate,
    session: Session = Depends(get_session),
) -> list[CareUnitWorkflowStatus]:
    """Actualiza etiquetas, orden y visibilidad de estados del servicio.

    Los códigos no incluidos se desactivan en vez de borrarse, para preservar
    referencias cuando el flujo de solicitudes se conecte en otra entrega.
    """
    _get_care_unit(session, organization_id, care_unit_id)
    current = list(
        session.scalars(
            select(CareUnitWorkflowStatus).where(
                CareUnitWorkflowStatus.care_unit_id == care_unit_id
            )
        ).all()
    )
    by_code = {item.code: item for item in current}
    incoming_codes = {item.code for item in payload.statuses}

    for item in current:
        if item.code not in incoming_codes:
            item.is_active = False

    for item in payload.statuses:
        record = by_code.get(item.code)
        if record is None:
            record = CareUnitWorkflowStatus(
                care_unit_id=care_unit_id,
                code=item.code,
            )
            session.add(record)
        record.label = item.label
        record.display_order = item.display_order
        record.is_active = item.is_active
        record.family_visible = item.family_visible

    session.commit()
    statement = (
        select(CareUnitWorkflowStatus)
        .where(CareUnitWorkflowStatus.care_unit_id == care_unit_id)
        .order_by(
            CareUnitWorkflowStatus.display_order,
            CareUnitWorkflowStatus.code,
        )
    )
    return list(session.scalars(statement).all())

