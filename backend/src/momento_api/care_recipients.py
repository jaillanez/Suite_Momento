"""Operaciones locales de personas cuidadas, sin datos clínicos."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from momento_api.models import CareRecipient, CareUnit
from momento_api.schemas import CareRecipientCreate, CareRecipientRead
from momento_api.session import get_session

router = APIRouter(prefix="/api/care-units", tags=["Personas cuidadas"])


@router.post(
    "/{care_unit_id}/care-recipients",
    response_model=CareRecipientRead,
    status_code=status.HTTP_201_CREATED,
)
def create_care_recipient(
    care_unit_id: UUID,
    payload: CareRecipientCreate,
    response: Response,
    session: Session = Depends(get_session),
) -> CareRecipient:
    """Crea una ficha mínima para pruebas locales."""
    care_unit = session.get(CareUnit, care_unit_id)
    if care_unit is None or not care_unit.is_active:
        raise HTTPException(status_code=404, detail="Servicio no encontrado.")

    recipient = CareRecipient(
        care_unit_id=care_unit_id,
        display_name=payload.display_name,
    )
    session.add(recipient)
    session.commit()
    session.refresh(recipient)
    response.headers["Location"] = (
        f"/api/care-units/{care_unit_id}/care-recipients/{recipient.id}"
    )
    return recipient


@router.get(
    "/{care_unit_id}/care-recipients",
    response_model=list[CareRecipientRead],
)
def list_care_recipients(
    care_unit_id: UUID,
    session: Session = Depends(get_session),
) -> list[CareRecipient]:
    """Lista fichas activas del servicio para pruebas locales."""
    care_unit = session.get(CareUnit, care_unit_id)
    if care_unit is None or not care_unit.is_active:
        raise HTTPException(status_code=404, detail="Servicio no encontrado.")

    statement = (
        select(CareRecipient)
        .where(
            CareRecipient.care_unit_id == care_unit_id,
            CareRecipient.is_active.is_(True),
        )
        .order_by(CareRecipient.display_name, CareRecipient.id)
        .limit(100)
    )
    return list(session.scalars(statement).all())
