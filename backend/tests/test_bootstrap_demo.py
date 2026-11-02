from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from momento_api.bootstrap_demo import add_membership
from momento_api.models import (
    Base,
    CareUnit,
    CareUnitType,
    Organization,
    StaffRole,
    UserAccount,
    UserGroup,
)


def test_demo_manager_membership_persists_organization_id() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        organization = Organization(name="Residencia de prueba")
        session.add(organization)
        session.flush()

        unit = CareUnit(
            organization_id=organization.id,
            name="Sede de prueba",
            service_type=CareUnitType.RESIDENCE,
            country_code="AR",
        )
        manager = UserAccount(display_name="Encargado de prueba")
        session.add_all([unit, manager])
        session.flush()

        membership = add_membership(
            session,
            user_account_id=manager.id,
            organization_id=organization.id,
            care_unit_id=None,
            user_group=UserGroup.STAFF,
            role_label="Encargado de residencia",
            staff_role=StaffRole.MANAGER,
        )
        session.commit()

        stored = session.get(type(membership), membership.id)
        assert stored is not None
        assert stored.user_account_id == manager.id
        assert stored.organization_id == organization.id
        assert stored.care_unit_id is None

    engine.dispose()


def test_demo_scenario_is_complete_and_completion_is_idempotent() -> None:
    from sqlalchemy import func, select

    from momento_api.auth import verify_password
    from momento_api.bootstrap_demo import DEMO_USERS, complete_demo, create_base_scenario
    from momento_api.models import (
        FamilyAuthorization,
        FamilyRequest,
        OrganizationMembership,
        UserCredential,
    )

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        organization = create_base_scenario(session)
        first = complete_demo(session, organization)
        session.commit()
        second = complete_demo(session, organization)
        session.commit()

        assert first and second == []
        assert session.scalar(select(func.count(FamilyRequest.id))) == 4
        assert session.scalar(select(func.count(FamilyAuthorization.id))) == 32 * 3
        designated = session.scalars(
            select(OrganizationMembership).where(OrganizationMembership.handles_inbox.is_(True))
        ).all()
        assert len(designated) == 5
        from momento_api.models import CareRecipient, CareRecipientContact
        assert session.scalar(select(func.count(CareRecipient.id)).where(CareRecipient.birth_date.is_not(None))) == 42
        assert session.scalar(select(func.count(CareRecipientContact.id))) == 31
        for user in DEMO_USERS:
            account = session.scalar(select(UserAccount).where(UserAccount.email == user.email))
            credential = session.get(UserCredential, account.id)
            assert verify_password(user.password, credential.password_hash)

    engine.dispose()
