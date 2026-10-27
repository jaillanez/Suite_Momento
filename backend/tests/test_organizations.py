from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from momento_api.models import (
    Base,
    CareUnit,
    CareUnitType,
    CareRecipient,
    FamilyAuthorization,
    Organization,
    OrganizationMembership,
    SharedCareCategory,
    UserAccount,
    UserGroup,
)


def test_organization_can_hold_residential_and_home_care_services() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        organization = Organization(name="Organización de prueba")
        organization.care_units.extend(
            [
                CareUnit(
                    name="Residencia piloto",
                    service_type=CareUnitType.RESIDENCE,
                    country_code="AR",
                ),
                CareUnit(
                    name="Atención domiciliaria",
                    service_type=CareUnitType.HOME_CARE,
                    country_code="UY",
                ),
            ]
        )
        session.add(organization)
        session.commit()

        stored = session.get(Organization, organization.id)

        assert stored is not None
        assert {unit.service_type for unit in stored.care_units} == {
            CareUnitType.RESIDENCE,
            CareUnitType.HOME_CARE,
        }
        assert {unit.country_code for unit in stored.care_units} == {"AR", "UY"}

    engine.dispose()


def test_api_creates_and_lists_organization(api_client: TestClient) -> None:
    created = api_client.post("/api/organizations", json={"name": "  Residencia Momento  "})

    assert created.status_code == 201
    assert created.json()["name"] == "Residencia Momento"
    assert created.headers["location"].startswith("/api/organizations/")

    listed = api_client.get("/api/organizations")
    assert listed.status_code == 200
    assert created.json()["id"] in [item["id"] for item in listed.json()]


def test_api_creates_care_unit_and_rejects_unknown_country(api_client: TestClient) -> None:
    organization = api_client.post(
        "/api/organizations",
        json={"name": "Residencia Momento"},
    ).json()
    organization_id = organization["id"]

    created = api_client.post(
        f"/api/organizations/{organization_id}/care-units",
        json={
            "name": "Sede Centro",
            "service_type": "residence",
            "country_code": "AR",
        },
    )
    assert created.status_code == 201
    assert created.json()["organization_id"] == organization_id

    listed = api_client.get(f"/api/organizations/{organization_id}/care-units")
    assert listed.status_code == 200
    assert len(listed.json()) == 1

    invalid = api_client.post(
        f"/api/organizations/{organization_id}/care-units",
        json={
            "name": "Servicio fuera de alcance",
            "service_type": "home_care",
            "country_code": "BR",
        },
    )
    assert invalid.status_code == 422


def test_api_returns_not_found_for_unknown_organization(api_client: TestClient) -> None:
    response = api_client.get(
        "/api/organizations/aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa/care-units"
    )

    assert response.status_code == 404


def create_test_service(client: TestClient) -> tuple[str, str]:
    organization = client.post(
        "/api/organizations",
        json={"name": "Organización de prueba"},
    ).json()
    unit = client.post(
        f"/api/organizations/{organization['id']}/care-units",
        json={
            "name": "Residencia de prueba",
            "service_type": "residence",
            "country_code": "AR",
        },
    ).json()
    return organization["id"], unit["id"]


def test_care_unit_receives_configurable_default_workflow(api_client: TestClient) -> None:
    organization_id, care_unit_id = create_test_service(api_client)
    response = api_client.get(
        f"/api/organizations/{organization_id}/care-units/{care_unit_id}/workflow-statuses"
    )

    assert response.status_code == 200
    assert [item["code"] for item in response.json()] == [
        "received",
        "assigned",
        "in_progress",
        "responded",
        "closed",
    ]
    assert all(item["is_active"] and item["family_visible"] for item in response.json())


def test_workflow_status_labels_and_family_visibility_are_configurable(
    api_client: TestClient,
) -> None:
    organization_id, care_unit_id = create_test_service(api_client)
    path = (
        f"/api/organizations/{organization_id}/care-units/"
        f"{care_unit_id}/workflow-statuses"
    )
    current = api_client.get(path).json()
    payload = {
        "statuses": [
            {
                "code": item["code"],
                "label": (
                    "Recibida por el equipo"
                    if item["code"] == "received"
                    else item["label"]
                ),
                "display_order": item["display_order"],
                "is_active": item["is_active"],
                "family_visible": (
                    False if item["code"] == "assigned" else item["family_visible"]
                ),
            }
            for item in current
        ]
    }

    updated = api_client.put(path, json=payload)

    assert updated.status_code == 200
    first = next(item for item in updated.json() if item["code"] == "received")
    assigned = next(item for item in updated.json() if item["code"] == "assigned")
    assert first["label"] == "Recibida por el equipo"
    assert assigned["family_visible"] is False


def test_workflow_statuses_reject_duplicate_order_and_wrong_service(
    api_client: TestClient,
) -> None:
    organization_id, care_unit_id = create_test_service(api_client)
    path = (
        f"/api/organizations/{organization_id}/care-units/"
        f"{care_unit_id}/workflow-statuses"
    )
    payload = {
        "statuses": [
            {
                "code": "received",
                "label": "Recibida",
                "display_order": 1,
                "is_active": True,
                "family_visible": True,
            },
            {
                "code": "assigned",
                "label": "Asignada",
                "display_order": 1,
                "is_active": True,
                "family_visible": True,
            },
        ]
    }
    invalid = api_client.put(path, json=payload)
    assert invalid.status_code == 422

    wrong_owner = api_client.get(
        "/api/organizations/aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa/"
        f"care-units/{care_unit_id}/workflow-statuses"
    )
    assert wrong_owner.status_code == 404


def test_user_account_has_configurable_membership_scope() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        organization = Organization(name="Organización de prueba")
        unit = CareUnit(
            name="Residencia de prueba",
            service_type=CareUnitType.RESIDENCE,
            country_code="AR",
        )
        organization.care_units.append(unit)
        account = UserAccount(
            display_name="Cuenta ficticia",
            email=None,
            phone=None,
        )
        account.memberships.extend(
            [
                OrganizationMembership(
                    organization=organization,
                    care_unit=unit,
                    user_group=UserGroup.STAFF,
                    role_label="Personal designado",
                ),
                OrganizationMembership(
                    organization=organization,
                    care_unit=unit,
                    user_group=UserGroup.FAMILY,
                ),
            ]
        )
        session.add_all([organization, account])
        session.commit()

        stored = session.get(UserAccount, account.id)
        assert stored is not None
        assert {membership.user_group for membership in stored.memberships} == {
            UserGroup.STAFF,
            UserGroup.FAMILY,
        }
        assert all(membership.care_unit_id == unit.id for membership in stored.memberships)
        assert not hasattr(stored, "password_hash")

    engine.dispose()


def test_family_authorization_tracks_category_actions_and_grantor() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        organization = Organization(name="Organización de prueba")
        unit = CareUnit(
            name="Residencia de prueba",
            service_type=CareUnitType.RESIDENCE,
            country_code="AR",
        )
        organization.care_units.append(unit)
        family_account = UserAccount(display_name="Familiar ficticio")
        staff_account = UserAccount(display_name="Personal ficticio")
        family_membership = OrganizationMembership(
            organization=organization,
            care_unit=unit,
            user_group=UserGroup.FAMILY,
        )
        authorizer_membership = OrganizationMembership(
            organization=organization,
            care_unit=unit,
            user_group=UserGroup.STAFF,
            role_label="Encargado",
        )
        family_account.memberships.append(family_membership)
        staff_account.memberships.append(authorizer_membership)
        session.add_all([organization, family_account, staff_account])
        session.flush()
        recipient = CareRecipient(
            care_unit_id=unit.id,
            display_name="Persona ficticia",
        )
        session.add(recipient)
        session.flush()

        authorization = FamilyAuthorization(
            care_recipient_id=recipient.id,
            family_membership_id=family_membership.id,
            authorized_by_membership_id=authorizer_membership.id,
            category=SharedCareCategory.MEDICATION,
            can_view=True,
            can_respond=True,
            can_request=True,
        )
        session.add(authorization)
        session.commit()

        stored = session.get(FamilyAuthorization, authorization.id)
        assert stored is not None
        assert stored.category is SharedCareCategory.MEDICATION
        assert stored.can_view and stored.can_respond and stored.can_request
        assert stored.authorized_by_membership_id == authorizer_membership.id
        assert stored.revoked_at is None
        assert not hasattr(stored, "can_modify")

    engine.dispose()


def test_care_recipient_api_creates_and_lists_only_active_records(
    api_client: TestClient,
) -> None:
    _, care_unit_id = create_test_service(api_client)

    created = api_client.post(
        f"/api/care-units/{care_unit_id}/care-recipients",
        json={"display_name": "  Persona de prueba  "},
    )

    assert created.status_code == 201
    assert created.json()["display_name"] == "Persona de prueba"
    assert created.json()["care_unit_id"] == care_unit_id
    assert created.headers["location"].endswith(created.json()["id"])

    listed = api_client.get(f"/api/care-units/{care_unit_id}/care-recipients")
    assert listed.status_code == 200
    assert [item["id"] for item in listed.json()] == [created.json()["id"]]


def test_care_recipient_api_rejects_empty_name_and_unknown_service(
    api_client: TestClient,
) -> None:
    _, care_unit_id = create_test_service(api_client)

    empty_name = api_client.post(
        f"/api/care-units/{care_unit_id}/care-recipients",
        json={"display_name": "   "},
    )
    assert empty_name.status_code == 422

    unknown_service = api_client.get(
        "/api/care-units/aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa/care-recipients"
    )
    assert unknown_service.status_code == 404


def test_membership_api_creates_and_lists_user_by_organization(
    api_client: TestClient,
) -> None:
    organization_id, care_unit_id = create_test_service(api_client)

    created = api_client.post(
        f"/api/organizations/{organization_id}/memberships",
        json={
            "display_name": "  Familiar ficticio ",
            "email": " familiar@example.test ",
            "phone": "",
            "user_group": "family",
            "care_unit_id": care_unit_id,
        },
    )

    assert created.status_code == 201
    result = created.json()
    assert result["user"]["display_name"] == "Familiar ficticio"
    assert result["user"]["email"] == "familiar@example.test"
    assert result["user"]["phone"] is None
    assert result["user_group"] == "family"
    assert result["care_unit_id"] == care_unit_id

    listed = api_client.get(f"/api/organizations/{organization_id}/memberships")
    assert listed.status_code == 200
    listed_ids = [item["id"] for item in listed.json()]
    assert result["id"] in listed_ids
    assert len(listed_ids) == 2


def test_membership_api_rejects_service_from_another_organization(
    api_client: TestClient,
) -> None:
    first_organization_id, _ = create_test_service(api_client)
    second_organization_id, other_care_unit_id = create_test_service(api_client)

    response = api_client.post(
        f"/api/organizations/{first_organization_id}/memberships",
        json={
            "display_name": "Personal ficticio",
            "user_group": "staff",
            "care_unit_id": other_care_unit_id,
        },
    )

    assert second_organization_id != first_organization_id
    assert response.status_code == 422
