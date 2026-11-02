"""Escalas de evaluación aplicadas a cada persona."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from momento_api.audit import record_event
from momento_api.auth import get_authenticated_account
from momento_api.care_recipients import HEALTH_EDITORS, _care_unit, _deny, _recipient, _roles, _viewer
from momento_api.forms import BACKGROUND_SECTIONS
from momento_api.models import Assessment, OrganizationMembership, StaffRole, UserAccount
from momento_api.scales import SCALES, public_definitions, score
from momento_api.schemas import AssessmentCreate, AssessmentDetail, AssessmentSummary, ScorePreview
from momento_api.session import get_session

definitions_router = APIRouter(prefix="/api", tags=["Escalas"])
router = APIRouter(prefix="/api/care-units", tags=["Escalas"])


@definitions_router.get("/scales")
def list_scales() -> list[dict[str, object]]:
    """Definición de cada escala para dibujar el formulario."""
    return public_definitions()


@definitions_router.get("/forms/background")
def background_form() -> list[dict[str, object]]:
    """Definición de antecedentes y datos de ingreso."""
    return BACKGROUND_SECTIONS


@definitions_router.post("/scales/{code}/score")
def preview_score(code: str, payload: ScorePreview) -> dict[str, object]:
    """Calcula el puntaje parcial mientras se completa; no guarda nada."""
    try:
        return score(code, payload.answers, require_complete=False)
    except (ValueError, TypeError) as error:
        raise HTTPException(status_code=422, detail=str(error)) from None


def _summary(assessment: Assessment) -> dict[str, object]:
    return {
        "id": assessment.id,
        "scale_code": assessment.scale_code,
        "scale_name": SCALES[assessment.scale_code]["name"],
        "performed_on": assessment.performed_on,
        "total_score": assessment.total_score,
        "max_score": assessment.max_score,
        "subscores": assessment.subscores,
        "interpretation": assessment.interpretation,
        "performed_by_name": assessment.performed_by.user.display_name,
        "created_at": assessment.created_at,
    }


def _query(recipient_id: UUID):
    return (
        select(Assessment)
        .options(joinedload(Assessment.performed_by).joinedload(OrganizationMembership.user))
        .where(Assessment.care_recipient_id == recipient_id)
    )


@router.get("/{care_unit_id}/care-recipients/{recipient_id}/assessments", response_model=list[AssessmentSummary])
def list_assessments(
    care_unit_id: UUID,
    recipient_id: UUID,
    session: Session = Depends(get_session),
    account: UserAccount = Depends(get_authenticated_account),
) -> list[dict[str, object]]:
    care_unit = _care_unit(session, care_unit_id)
    _viewer(session, account, care_unit)
    recipient = _recipient(session, care_unit_id, recipient_id)
    rows = session.scalars(
        _query(recipient.id).order_by(Assessment.performed_on.desc(), Assessment.created_at.desc())
    ).all()
    return [_summary(item) for item in rows]


@router.get("/{care_unit_id}/care-recipients/{recipient_id}/assessments/{assessment_id}", response_model=AssessmentDetail)
def read_assessment(
    care_unit_id: UUID,
    recipient_id: UUID,
    assessment_id: UUID,
    session: Session = Depends(get_session),
    account: UserAccount = Depends(get_authenticated_account),
) -> dict[str, object]:
    care_unit = _care_unit(session, care_unit_id)
    _viewer(session, account, care_unit)
    recipient = _recipient(session, care_unit_id, recipient_id)
    assessment = session.scalar(_query(recipient.id).where(Assessment.id == assessment_id))
    if assessment is None:
        raise HTTPException(status_code=404, detail="Evaluación no encontrada.")
    record_event(
        session,
        action="assessment.viewed",
        actor_account_id=account.id,
        organization_id=care_unit.organization_id,
        target_type="care_recipient",
        target_id=recipient.id,
        details={"scale": assessment.scale_code},
    )
    session.commit()
    credited = score(assessment.scale_code, assessment.answers, require_complete=False)["credited_by_recall"]
    return {**_summary(assessment), "answers": assessment.answers, "notes": assessment.notes, "credited_by_recall": credited}


@router.post(
    "/{care_unit_id}/care-recipients/{recipient_id}/assessments",
    response_model=AssessmentSummary,
    status_code=status.HTTP_201_CREATED,
)
def create_assessment(
    care_unit_id: UUID,
    recipient_id: UUID,
    payload: AssessmentCreate,
    session: Session = Depends(get_session),
    account: UserAccount = Depends(get_authenticated_account),
) -> dict[str, object]:
    """Registra una evaluación; la aplican el encargado o el médico."""
    care_unit = _care_unit(session, care_unit_id)
    recipient = _recipient(session, care_unit_id, recipient_id)
    if not _roles(session, account, care_unit) & set(HEALTH_EDITORS):
        raise _deny(session, account, care_unit, "assessment.created", recipient.id,
                    "Las escalas las aplican el encargado o el médico.")
    try:
        result = score(payload.scale_code, payload.answers)
    except (ValueError, TypeError) as error:
        raise HTTPException(status_code=422, detail=str(error)) from None
    performer = _viewer(session, account, care_unit)
    assessment = Assessment(
        care_recipient_id=recipient.id,
        scale_code=payload.scale_code,
        performed_on=payload.performed_on,
        answers=result["answers"],  # normalizadas: sin repetidos
        total_score=result["total"],
        max_score=result["max"],
        subscores=result["subscores"],
        interpretation=result["interpretation"],
        notes=(payload.notes or "").strip() or None,
        performed_by_membership_id=performer.id,
    )
    session.add(assessment)
    session.flush()
    record_event(
        session,
        action="assessment.created",
        actor_account_id=account.id,
        organization_id=care_unit.organization_id,
        target_type="care_recipient",
        target_id=recipient.id,
        details={"scale": payload.scale_code},
    )
    session.commit()
    return _summary(session.scalar(_query(recipient.id).where(Assessment.id == assessment.id)))


@router.delete(
    "/{care_unit_id}/care-recipients/{recipient_id}/assessments/{assessment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_assessment(
    care_unit_id: UUID,
    recipient_id: UUID,
    assessment_id: UUID,
    session: Session = Depends(get_session),
    account: UserAccount = Depends(get_authenticated_account),
) -> Response:
    """Solo el encargado puede borrar una evaluación cargada por error."""
    care_unit = _care_unit(session, care_unit_id)
    recipient = _recipient(session, care_unit_id, recipient_id)
    if StaffRole.MANAGER not in _roles(session, account, care_unit):
        raise _deny(session, account, care_unit, "assessment.deleted", recipient.id,
                    "Solo el encargado puede borrar una evaluación.")
    assessment = session.scalar(_query(recipient.id).where(Assessment.id == assessment_id))
    if assessment is None:
        raise HTTPException(status_code=404, detail="Evaluación no encontrada.")
    record_event(
        session,
        action="assessment.deleted",
        actor_account_id=account.id,
        organization_id=care_unit.organization_id,
        target_type="care_recipient",
        target_id=recipient.id,
        details={"scale": assessment.scale_code},
    )
    session.delete(assessment)
    session.commit()
    return Response(status_code=204)
