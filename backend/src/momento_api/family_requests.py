"""Bandeja compartida de solicitudes familiares y acceso familiar separado."""

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_, select
from sqlalchemy.orm import Session, joinedload

from momento_api.access import find_staff_membership
from momento_api.audit import record_denied, record_event
from momento_api.auth import get_authenticated_account
from momento_api.models import (
    CareRecipient,
    CareUnit,
    CareUnitWorkflowStatus,
    FamilyAuthorization,
    FamilyRequest,
    OrganizationMembership,
    StaffRole,
    UserAccount,
    UserGroup,
)
from momento_api.schemas import (
    AssigneeRead,
    FamilyCategoryAccess,
    FamilyLinkedPerson,
    FamilyRequestCreate,
    FamilyRequestRead,
    RequestAssign,
    RequestResponse,
    RequestStatusChange,
    StaffRequestRead,
)
from momento_api.session import get_session

staff_router = APIRouter(
    prefix="/api/organizations/{organization_id}/care-units/{care_unit_id}/requests",
    tags=["Bandeja de solicitudes"],
)
family_router = APIRouter(prefix="/api/family", tags=["Acceso familiar"])

INITIAL_STATUS = "received"


# --- Utilidades compartidas -------------------------------------------------


def _statuses(session: Session, care_unit_id: UUID) -> list[CareUnitWorkflowStatus]:
    return list(
        session.scalars(
            select(CareUnitWorkflowStatus)
            .where(CareUnitWorkflowStatus.care_unit_id == care_unit_id)
            .order_by(CareUnitWorkflowStatus.display_order, CareUnitWorkflowStatus.code)
        ).all()
    )


def _active_code(statuses: list[CareUnitWorkflowStatus], code: str) -> str | None:
    """Devuelve el código si el servicio lo tiene activo."""
    return code if any(s.code == code and s.is_active for s in statuses) else None


def _family_status_label(statuses: list[CareUnitWorkflowStatus], code: str) -> str:
    """Muestra el último estado visible para la familia alcanzado por la solicitud."""
    current = next((s for s in statuses if s.code == code), None)
    if current is None:
        return "En proceso"
    if current.family_visible:
        return current.label
    visible = [
        s for s in statuses
        if s.family_visible and s.display_order <= current.display_order
    ]
    return visible[-1].label if visible else "En proceso"


def _set_status(request: FamilyRequest, statuses: list[CareUnitWorkflowStatus], code: str) -> None:
    if _active_code(statuses, code):
        request.status_code = code


# --- Bandeja del personal ---------------------------------------------------


def _care_unit(session: Session, organization_id: UUID, care_unit_id: UUID) -> CareUnit:
    unit = session.scalar(
        select(CareUnit).where(
            CareUnit.id == care_unit_id,
            CareUnit.organization_id == organization_id,
            CareUnit.is_active.is_(True),
        )
    )
    if unit is None:
        raise HTTPException(status_code=404, detail="Servicio no encontrado.")
    return unit


def _require_inbox_member(
    session: Session,
    account: UserAccount,
    organization_id: UUID,
    care_unit_id: UUID,
    *,
    action: str,
    manager_only: bool = False,
) -> OrganizationMembership:
    membership = find_staff_membership(
        session,
        account_id=account.id,
        organization_id=organization_id,
        care_unit_id=care_unit_id,
        roles=[StaffRole.MANAGER] if manager_only else None,
        inbox=not manager_only,
    )
    if membership is None:
        record_denied(
            session,
            action=action,
            actor_account_id=account.id,
            organization_id=organization_id,
            target_type="care_unit",
            target_id=care_unit_id,
        )
        detail = (
            "Solo el encargado puede asignar solicitudes."
            if manager_only
            else "La bandeja solo está disponible para el encargado y el personal designado."
        )
        raise HTTPException(status_code=403, detail=detail)
    return membership


def _load_request(session: Session, care_unit_id: UUID, request_id: UUID) -> FamilyRequest:
    request = session.scalar(
        select(FamilyRequest)
        .options(
            joinedload(FamilyRequest.care_recipient),
            joinedload(FamilyRequest.family_membership).joinedload(OrganizationMembership.user),
            joinedload(FamilyRequest.assigned_to).joinedload(OrganizationMembership.user),
        )
        .where(FamilyRequest.id == request_id, FamilyRequest.care_unit_id == care_unit_id)
    )
    if request is None:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada.")
    return request


def _staff_read(request: FamilyRequest, statuses: list[CareUnitWorkflowStatus]) -> StaffRequestRead:
    status_label = next((s.label for s in statuses if s.code == request.status_code), request.status_code)
    return StaffRequestRead(
        id=request.id,
        care_unit_id=request.care_unit_id,
        care_recipient_id=request.care_recipient_id,
        care_recipient_name=request.care_recipient.display_name,
        family_name=request.family_membership.user.display_name,
        category=request.category,
        subject=request.subject,
        message=request.message,
        status_code=request.status_code,
        status_label=status_label,
        assigned_to_membership_id=request.assigned_to_membership_id,
        assigned_to_name=request.assigned_to.user.display_name if request.assigned_to else None,
        shared_response=request.shared_response,
        responded_at=request.responded_at,
        created_at=request.created_at,
    )


def _require_handler(
    session: Session,
    account: UserAccount,
    organization_id: UUID,
    request: FamilyRequest,
    *,
    action: str,
) -> OrganizationMembership:
    """El encargado o la persona asignada pueden avanzar y responder."""
    membership = _require_inbox_member(
        session, account, organization_id, request.care_unit_id, action=action
    )
    is_assignee = (
        request.assigned_to is not None
        and request.assigned_to.user_account_id == account.id
    )
    if membership.staff_role is not StaffRole.MANAGER and not is_assignee:
        record_denied(
            session,
            action=action,
            actor_account_id=account.id,
            organization_id=organization_id,
            target_type="family_request",
            target_id=request.id,
        )
        raise HTTPException(
            status_code=403,
            detail="Solo el encargado o la persona asignada pueden gestionar esta solicitud.",
        )
    return membership


@staff_router.get("", response_model=list[StaffRequestRead])
def list_requests(
    organization_id: UUID,
    care_unit_id: UUID,
    session: Session = Depends(get_session),
    account: UserAccount = Depends(get_authenticated_account),
) -> list[StaffRequestRead]:
    """Bandeja compartida del servicio, de la más reciente a la más antigua."""
    _care_unit(session, organization_id, care_unit_id)
    _require_inbox_member(session, account, organization_id, care_unit_id, action="request.inbox_viewed")
    statuses = _statuses(session, care_unit_id)
    requests = session.scalars(
        select(FamilyRequest)
        .options(
            joinedload(FamilyRequest.care_recipient),
            joinedload(FamilyRequest.family_membership).joinedload(OrganizationMembership.user),
            joinedload(FamilyRequest.assigned_to).joinedload(OrganizationMembership.user),
        )
        .where(FamilyRequest.care_unit_id == care_unit_id)
        .order_by(FamilyRequest.created_at.desc(), FamilyRequest.id)
        .limit(200)
    ).all()
    return [_staff_read(item, statuses) for item in requests]


@staff_router.get("/assignees", response_model=list[AssigneeRead])
def list_assignees(
    organization_id: UUID,
    care_unit_id: UUID,
    session: Session = Depends(get_session),
    account: UserAccount = Depends(get_authenticated_account),
) -> list[AssigneeRead]:
    """Personal al que el encargado puede asignar: designado para la bandeja o encargado."""
    _care_unit(session, organization_id, care_unit_id)
    _require_inbox_member(
        session, account, organization_id, care_unit_id,
        action="request.assignees_viewed", manager_only=True,
    )
    memberships = session.scalars(
        select(OrganizationMembership)
        .options(joinedload(OrganizationMembership.user))
        .where(
            OrganizationMembership.organization_id == organization_id,
            OrganizationMembership.user_group == UserGroup.STAFF,
            OrganizationMembership.is_active.is_(True),
            or_(
                OrganizationMembership.care_unit_id.is_(None),
                OrganizationMembership.care_unit_id == care_unit_id,
            ),
            or_(
                OrganizationMembership.staff_role == StaffRole.MANAGER,
                OrganizationMembership.handles_inbox.is_(True),
            ),
        )
    ).all()
    result = [
        AssigneeRead(
            membership_id=item.id,
            display_name=item.user.display_name,
            staff_role=item.staff_role,
        )
        for item in memberships
        if item.staff_role is not None
    ]
    return sorted(result, key=lambda item: item.display_name)


@staff_router.post("/{request_id}/assign", response_model=StaffRequestRead)
def assign_request(
    organization_id: UUID,
    care_unit_id: UUID,
    request_id: UUID,
    payload: RequestAssign,
    session: Session = Depends(get_session),
    account: UserAccount = Depends(get_authenticated_account),
) -> StaffRequestRead:
    """El encargado asigna la solicitud a personal designado."""
    _care_unit(session, organization_id, care_unit_id)
    _require_inbox_member(
        session, account, organization_id, care_unit_id,
        action="request.assigned", manager_only=True,
    )
    request = _load_request(session, care_unit_id, request_id)
    assignee = session.get(OrganizationMembership, payload.membership_id)
    if (
        assignee is None
        or assignee.organization_id != organization_id
        or assignee.user_group is not UserGroup.STAFF
        or not assignee.is_active
        or assignee.care_unit_id not in (None, care_unit_id)
        or not (assignee.staff_role is StaffRole.MANAGER or assignee.handles_inbox)
    ):
        raise HTTPException(
            status_code=422,
            detail="Solo se puede asignar a personal designado para la bandeja de este servicio.",
        )
    statuses = _statuses(session, care_unit_id)
    request.assigned_to_membership_id = assignee.id
    if request.status_code == INITIAL_STATUS:
        _set_status(request, statuses, "assigned")
    record_event(
        session,
        action="request.assigned",
        actor_account_id=account.id,
        organization_id=organization_id,
        target_type="family_request",
        target_id=request.id,
        details={"assigned_to_membership_id": str(assignee.id)},
    )
    session.commit()
    return _staff_read(_load_request(session, care_unit_id, request_id), statuses)


@staff_router.post("/{request_id}/status", response_model=StaffRequestRead)
def change_request_status(
    organization_id: UUID,
    care_unit_id: UUID,
    request_id: UUID,
    payload: RequestStatusChange,
    session: Session = Depends(get_session),
    account: UserAccount = Depends(get_authenticated_account),
) -> StaffRequestRead:
    """Cambia el estado entre los configurados y activos del servicio."""
    _care_unit(session, organization_id, care_unit_id)
    request = _load_request(session, care_unit_id, request_id)
    _require_handler(session, account, organization_id, request, action="request.status_changed")
    statuses = _statuses(session, care_unit_id)
    if _active_code(statuses, payload.status_code) is None:
        raise HTTPException(status_code=422, detail="Ese estado no está activo en este servicio.")
    previous = request.status_code
    request.status_code = payload.status_code
    record_event(
        session,
        action="request.status_changed",
        actor_account_id=account.id,
        organization_id=organization_id,
        target_type="family_request",
        target_id=request.id,
        details={"from": previous, "to": payload.status_code},
    )
    session.commit()
    return _staff_read(_load_request(session, care_unit_id, request_id), statuses)


@staff_router.post("/{request_id}/respond", response_model=StaffRequestRead)
def respond_request(
    organization_id: UUID,
    care_unit_id: UUID,
    request_id: UUID,
    payload: RequestResponse,
    session: Session = Depends(get_session),
    account: UserAccount = Depends(get_authenticated_account),
) -> StaffRequestRead:
    """Registra la respuesta que verá la familia."""
    _care_unit(session, organization_id, care_unit_id)
    request = _load_request(session, care_unit_id, request_id)
    handler = _require_handler(session, account, organization_id, request, action="request.responded")
    statuses = _statuses(session, care_unit_id)
    request.shared_response = payload.shared_response
    request.responded_by_membership_id = handler.id
    request.responded_at = datetime.now(timezone.utc)
    _set_status(request, statuses, "responded")
    record_event(
        session,
        action="request.responded",
        actor_account_id=account.id,
        organization_id=organization_id,
        target_type="family_request",
        target_id=request.id,
    )
    session.commit()
    return _staff_read(_load_request(session, care_unit_id, request_id), statuses)


# --- Acceso familiar --------------------------------------------------------


def get_family_memberships(
    session: Session = Depends(get_session),
    account: UserAccount = Depends(get_authenticated_account),
) -> list[OrganizationMembership]:
    """Exige al menos un vínculo familiar activo; el personal no entra aquí."""
    memberships = list(
        session.scalars(
            select(OrganizationMembership).where(
                OrganizationMembership.user_account_id == account.id,
                OrganizationMembership.user_group == UserGroup.FAMILY,
                OrganizationMembership.is_active.is_(True),
            )
        ).all()
    )
    if not memberships:
        raise HTTPException(status_code=403, detail="Este acceso es solo para familias autorizadas.")
    return memberships


def _active_authorizations(
    session: Session, memberships: list[OrganizationMembership]
) -> list[FamilyAuthorization]:
    return list(
        session.scalars(
            select(FamilyAuthorization)
            .join(CareRecipient, CareRecipient.id == FamilyAuthorization.care_recipient_id)
            .where(
                FamilyAuthorization.family_membership_id.in_([m.id for m in memberships]),
                FamilyAuthorization.is_active.is_(True),
                CareRecipient.is_active.is_(True),
            )
            .order_by(FamilyAuthorization.category)
        ).all()
    )


@family_router.get("/people", response_model=list[FamilyLinkedPerson])
def list_linked_people(
    session: Session = Depends(get_session),
    memberships: list[OrganizationMembership] = Depends(get_family_memberships),
) -> list[FamilyLinkedPerson]:
    """Personas vinculadas y categorías autorizadas; nada más."""
    by_recipient: dict[UUID, list[FamilyAuthorization]] = {}
    for item in _active_authorizations(session, memberships):
        by_recipient.setdefault(item.care_recipient_id, []).append(item)
    if not by_recipient:
        return []
    rows = session.execute(
        select(CareRecipient, CareUnit.name)
        .join(CareUnit, CareUnit.id == CareRecipient.care_unit_id)
        .where(CareRecipient.id.in_(list(by_recipient)))
        .order_by(CareRecipient.display_name)
    ).all()
    return [
        FamilyLinkedPerson(
            care_recipient_id=recipient.id,
            display_name=recipient.display_name,
            care_unit_name=unit_name,
            categories=[
                FamilyCategoryAccess(
                    category=auth.category,
                    can_view=auth.can_view,
                    can_respond=auth.can_respond,
                    can_request=auth.can_request,
                )
                for auth in by_recipient[recipient.id]
            ],
        )
        for recipient, unit_name in rows
    ]


def _family_read(request: FamilyRequest, statuses: list[CareUnitWorkflowStatus]) -> FamilyRequestRead:
    return FamilyRequestRead(
        id=request.id,
        care_recipient_id=request.care_recipient_id,
        care_recipient_name=request.care_recipient.display_name,
        category=request.category,
        subject=request.subject,
        message=request.message,
        status_label=_family_status_label(statuses, request.status_code),
        shared_response=request.shared_response,
        responded_at=request.responded_at,
        created_at=request.created_at,
    )


@family_router.get("/requests", response_model=list[FamilyRequestRead])
def list_family_requests(
    session: Session = Depends(get_session),
    memberships: list[OrganizationMembership] = Depends(get_family_memberships),
) -> list[FamilyRequestRead]:
    """Solicitudes de esta cuenta sobre personas y temas que sigue teniendo autorizados.

    Si se revoca una autorización, la familia deja de ver también las
    solicitudes y respuestas anteriores de ese tema.
    """
    allowed = {
        (item.family_membership_id, item.care_recipient_id, item.category)
        for item in _active_authorizations(session, memberships)
        if item.can_view
    }
    if not allowed:
        return []
    candidates = session.scalars(
        select(FamilyRequest)
        .options(joinedload(FamilyRequest.care_recipient))
        .where(FamilyRequest.family_membership_id.in_([m.id for m in memberships]))
        .order_by(FamilyRequest.created_at.desc(), FamilyRequest.id)
        .limit(500)
    ).all()
    requests = [
        item for item in candidates
        if (item.family_membership_id, item.care_recipient_id, item.category) in allowed
    ][:100]
    status_cache: dict[UUID, list[CareUnitWorkflowStatus]] = {}
    result = []
    for item in requests:
        if item.care_unit_id not in status_cache:
            status_cache[item.care_unit_id] = _statuses(session, item.care_unit_id)
        result.append(_family_read(item, status_cache[item.care_unit_id]))
    return result


@family_router.post("/requests", response_model=FamilyRequestRead, status_code=201)
def create_family_request(
    payload: FamilyRequestCreate,
    session: Session = Depends(get_session),
    account: UserAccount = Depends(get_authenticated_account),
    memberships: list[OrganizationMembership] = Depends(get_family_memberships),
) -> FamilyRequestRead:
    """Envía una solicitud a la bandeja; no cambia indicaciones ni planes."""
    authorization = next(
        (
            item for item in _active_authorizations(session, memberships)
            if item.care_recipient_id == payload.care_recipient_id
            and item.category == payload.category
            and item.can_request
        ),
        None,
    )
    if authorization is None:
        # Solo se registra la persona si pertenece a una organización de la familia;
        # así un intento sobre otra organización no aparece en su registro.
        recipient_organization = session.scalar(
            select(CareUnit.organization_id)
            .join(CareRecipient, CareRecipient.care_unit_id == CareUnit.id)
            .where(CareRecipient.id == payload.care_recipient_id)
        )
        family_organizations = {m.organization_id for m in memberships}
        own = recipient_organization in family_organizations
        record_denied(
            session,
            action="request.created",
            actor_account_id=account.id,
            organization_id=recipient_organization if own else memberships[0].organization_id,
            target_type="care_recipient" if own else None,
            target_id=payload.care_recipient_id if own else None,
        )
        raise HTTPException(
            status_code=403,
            detail="No tenés autorización para enviar solicitudes sobre ese tema.",
        )
    recipient = session.get(CareRecipient, payload.care_recipient_id)
    assert recipient is not None
    statuses = _statuses(session, recipient.care_unit_id)
    initial = _active_code(statuses, INITIAL_STATUS) or next(
        (s.code for s in statuses if s.is_active), INITIAL_STATUS
    )
    request = FamilyRequest(
        care_unit_id=recipient.care_unit_id,
        care_recipient_id=recipient.id,
        family_membership_id=authorization.family_membership_id,
        category=payload.category,
        subject=payload.subject,
        message=payload.message,
        status_code=initial,
    )
    session.add(request)
    session.flush()
    organization_id = session.scalar(
        select(CareUnit.organization_id).where(CareUnit.id == recipient.care_unit_id)
    )
    record_event(
        session,
        action="request.created",
        actor_account_id=account.id,
        organization_id=organization_id,
        target_type="family_request",
        target_id=request.id,
        details={"category": payload.category.value},
    )
    session.commit()
    session.refresh(request)
    return _family_read(request, statuses)
