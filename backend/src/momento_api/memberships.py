"""Gestión local de cuentas y vínculos organizativos de prueba."""

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Response, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload

from momento_api.access import find_staff_membership
from momento_api.audit import record_event
from momento_api.auth import (
    get_authenticated_account,
    get_organization_admin_account,
    hash_password,
)
from momento_api.models import (
    FAMILY_AUTHORIZER_ROLES,
    AuthSession,
    CareUnit,
    Organization,
    OrganizationMembership,
    StaffRole,
    UserAccount,
    UserCredential,
    UserGroup,
)
from momento_api.schemas import (
    MembershipCreate,
    PasswordSet,
    MembershipUpdate,
    OrganizationMembershipRead,
)
from momento_api.password_links import cancel_pending_links, issue_link, queue_link_email
from momento_api.session import get_session

router = APIRouter(prefix="/api/organizations", tags=["Usuarios y membresías"])


@router.post(
    "/{organization_id}/memberships",
    response_model=OrganizationMembershipRead,
    status_code=status.HTTP_201_CREATED,
)
def create_membership(
    organization_id: UUID,
    payload: MembershipCreate,
    response: Response,
    background: BackgroundTasks,
    session: Session = Depends(get_session),
    current_user: UserAccount = Depends(get_organization_admin_account),
) -> OrganizationMembership:
    """Crea una cuenta de prueba y la vincula con la organización o servicio."""
    organization = session.get(Organization, organization_id)
    if organization is None or not organization.is_active:
        raise HTTPException(status_code=404, detail="Organización no encontrada.")

    care_unit = None
    if payload.care_unit_id is not None:
        care_unit = session.get(CareUnit, payload.care_unit_id)
        if (
            care_unit is None
            or not care_unit.is_active
            or care_unit.organization_id != organization_id
        ):
            raise HTTPException(
                status_code=422,
                detail="El servicio no pertenece a esta organización activa.",
            )

    if payload.email and session.scalar(
        select(UserAccount.id).where(func.lower(UserAccount.email) == payload.email.lower())
    ):
        raise HTTPException(status_code=422, detail="Ese correo ya está en uso.")

    account = UserAccount(
        display_name=payload.display_name,
        email=payload.email,
        phone=payload.phone,
    )
    membership = OrganizationMembership(
        user=account,
        organization=organization,
        care_unit=care_unit,
        user_group=payload.user_group,
        role_label=payload.role_label,
        staff_role=payload.staff_role,
        handles_inbox=payload.handles_inbox,
    )
    session.add(membership)
    session.flush()
    if payload.password:
        session.add(UserCredential(
            user_account_id=account.id,
            password_hash=hash_password(payload.password),
        ))
    record_event(
        session,
        action="membership.created",
        actor_account_id=current_user.id,
        organization_id=organization_id,
        target_type="membership",
        target_id=membership.id,
        details={
            "user_group": payload.user_group.value,
            "staff_role": payload.staff_role.value if payload.staff_role else None,
            "handles_inbox": payload.handles_inbox,
            "can_sign_in": bool(payload.password),
            "invitation_sent": bool(payload.send_invitation and account.email and not payload.password),
        },
    )
    token = None
    if payload.send_invitation and account.email and not payload.password:
        token = issue_link(session, account, "invite")
    session.commit()
    session.refresh(membership)
    if token:
        queue_link_email(background, account, token, "invite", organization.name)
    response.headers["Location"] = (
        f"/api/organizations/{organization_id}/memberships/{membership.id}"
    )
    return membership


@router.get(
    "/{organization_id}/memberships",
    response_model=list[OrganizationMembershipRead],
)
def list_memberships(
    organization_id: UUID,
    limit: int = Query(default=500, ge=1, le=500),
    include_inactive: bool = Query(default=False),
    session: Session = Depends(get_session),
    current_user: UserAccount = Depends(get_authenticated_account),
) -> list[OrganizationMembership]:
    """Encargado: todas las cuentas. Administrativo y médico: familias de su alcance."""
    organization = session.get(Organization, organization_id)
    if organization is None or not organization.is_active:
        raise HTTPException(status_code=404, detail="Organización no encontrada.")
    viewer = find_staff_membership(
        session,
        account_id=current_user.id,
        organization_id=organization_id,
        roles=FAMILY_AUTHORIZER_ROLES,
    )
    if viewer is None:
        raise HTTPException(
            status_code=403,
            detail="La lista de usuarios es para encargado, administrativo o médico.",
        )

    statement = (
        select(OrganizationMembership)
        .options(joinedload(OrganizationMembership.user))
        .join(UserAccount, UserAccount.id == OrganizationMembership.user_account_id)
        .where(OrganizationMembership.organization_id == organization_id)
        .order_by(
            OrganizationMembership.user_group.desc(),
            UserAccount.display_name,
            OrganizationMembership.id,
        )
        .limit(limit)
    )
    # Solo el encargado de toda la organización ve todas las cuentas y las
    # desactivadas; el resto queda limitado a su sede y, si no es encargado, a familias.
    is_org_manager = viewer.staff_role is StaffRole.MANAGER and viewer.care_unit_id is None
    if not (include_inactive and is_org_manager):
        statement = statement.where(OrganizationMembership.is_active.is_(True))
    if not is_org_manager:
        if viewer.staff_role is not StaffRole.MANAGER:
            statement = statement.where(OrganizationMembership.user_group == UserGroup.FAMILY)
        if viewer.care_unit_id is not None:
            statement = statement.where(
                or_(
                    OrganizationMembership.care_unit_id.is_(None),
                    OrganizationMembership.care_unit_id == viewer.care_unit_id,
                )
            )
    return list(session.scalars(statement).all())


@router.patch(
    "/{organization_id}/memberships/{membership_id}",
    response_model=OrganizationMembershipRead,
)
def update_membership(
    organization_id: UUID,
    membership_id: UUID,
    payload: MembershipUpdate,
    session: Session = Depends(get_session),
    current_user: UserAccount = Depends(get_organization_admin_account),
) -> OrganizationMembership:
    """Cambia puesto, designación para la bandeja o estado de un vínculo."""
    membership = session.scalar(
        select(OrganizationMembership)
        .options(joinedload(OrganizationMembership.user))
        .where(
            OrganizationMembership.id == membership_id,
            OrganizationMembership.organization_id == organization_id,
        )
    )
    if membership is None:
        raise HTTPException(status_code=404, detail="Usuario no encontrado.")

    is_staff = membership.user_group is UserGroup.STAFF
    if not is_staff and (payload.staff_role is not None or payload.handles_inbox):
        raise HTTPException(
            status_code=422,
            detail="El puesto y la bandeja solo aplican al personal.",
        )
    if membership.user_account_id == current_user.id and (
        (payload.staff_role is not None and payload.staff_role is not StaffRole.MANAGER)
        or payload.is_active is False
    ):
        raise HTTPException(
            status_code=422,
            detail="No podés quitarte tu propio puesto de encargado ni desactivar tu cuenta.",
        )

    changes: dict[str, object] = {}
    if payload.staff_role is not None and payload.staff_role != membership.staff_role:
        membership.staff_role = payload.staff_role
        changes["staff_role"] = payload.staff_role.value
    if payload.handles_inbox is not None and payload.handles_inbox != membership.handles_inbox:
        membership.handles_inbox = payload.handles_inbox
        changes["handles_inbox"] = payload.handles_inbox
    if payload.is_active is not None and payload.is_active != membership.is_active:
        membership.is_active = payload.is_active
        changes["is_active"] = payload.is_active
        if not payload.is_active:
            cancel_pending_links(session, membership.user_account_id)

    if changes:
        record_event(
            session,
            action="membership.updated",
            actor_account_id=current_user.id,
            organization_id=organization_id,
            target_type="membership",
            target_id=membership.id,
            details=changes,
        )
        session.commit()
        session.refresh(membership)
    return membership


@router.post(
    "/{organization_id}/memberships/{membership_id}/password",
    status_code=204,
)
def set_password(
    organization_id: UUID,
    membership_id: UUID,
    payload: PasswordSet,
    session: Session = Depends(get_session),
    current_user: UserAccount = Depends(get_organization_admin_account),
) -> Response:
    """El encargado asigna una contraseña nueva y cierra las sesiones abiertas.

    Solo se permite si la cuenta pertenece únicamente a esta organización, para
    que un encargado no cambie el acceso de una persona a otro prestador.
    """
    membership, account = _own_account(session, organization_id, membership_id)
    credential = session.get(UserCredential, account.id)
    if credential is None:
        session.add(UserCredential(user_account_id=account.id, password_hash=hash_password(payload.password)))
    else:
        credential.password_hash = hash_password(payload.password)
    cancel_pending_links(session, account.id)
    now = datetime.now(timezone.utc)
    for auth_session in session.scalars(
        select(AuthSession).where(
            AuthSession.user_account_id == account.id,
            AuthSession.revoked_at.is_(None),
        )
    ).all():
        auth_session.revoked_at = now
    record_event(
        session,
        action="account.password_set",
        actor_account_id=current_user.id,
        organization_id=organization_id,
        target_type="membership",
        target_id=membership.id,
    )
    session.commit()
    return Response(status_code=204)


def _own_account(session: Session, organization_id: UUID, membership_id: UUID) -> tuple[OrganizationMembership, UserAccount]:
    """Vínculo y cuenta, solo si la cuenta pertenece únicamente a esta organización.

    Así un encargado no cambia el acceso de una persona a otro prestador.
    """
    membership = session.scalar(
        select(OrganizationMembership).where(
            OrganizationMembership.id == membership_id,
            OrganizationMembership.organization_id == organization_id,
        )
    )
    if membership is None:
        raise HTTPException(status_code=404, detail="Usuario no encontrado.")
    account = session.get(UserAccount, membership.user_account_id)
    if account is None or not account.email:
        raise HTTPException(status_code=422, detail="La cuenta necesita un correo para ingresar.")
    other_organization = session.scalar(
        select(OrganizationMembership.id).where(
            OrganizationMembership.user_account_id == account.id,
            OrganizationMembership.organization_id != organization_id,
        ).limit(1)
    )
    if other_organization is not None:
        raise HTTPException(
            status_code=422,
            detail="Esta cuenta también pertenece a otra organización; no se puede cambiar desde acá.",
        )

    return membership, account


@router.post(
    "/{organization_id}/memberships/{membership_id}/invite",
    status_code=202,
)
def send_invitation(
    organization_id: UUID,
    membership_id: UUID,
    background: BackgroundTasks,
    session: Session = Depends(get_session),
    current_user: UserAccount = Depends(get_organization_admin_account),
) -> dict[str, str]:
    """Envía por correo un enlace para que la persona cree (o cambie) su contraseña."""
    membership, account = _own_account(session, organization_id, membership_id)
    if not membership.is_active or not account.is_active:
        raise HTTPException(status_code=422, detail="Reactivá el usuario antes de invitarlo.")
    organization = session.get(Organization, organization_id)
    token = issue_link(session, account, "invite")
    record_event(
        session,
        action="account.invitation_sent",
        actor_account_id=current_user.id,
        organization_id=organization_id,
        target_type="membership",
        target_id=membership.id,
    )
    session.commit()
    queue_link_email(background, account, token, "invite", organization.name if organization else None)
    return {"detail": f"Enviamos la invitación a {account.email}."}
