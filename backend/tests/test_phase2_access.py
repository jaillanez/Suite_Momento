"""Permisos de Fase 2: puestos, acceso familiar, bandeja y auditoría."""

from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from momento_api.models import AuditEvent, CareUnitWorkflowStatus
from tests.access_helpers import PASSWORD, Scenario, as_user, client, scenario  # noqa: F401

def grant(client: TestClient, s: Scenario, categories=("medication", "activities", "diet")):
    return client.post(
        f"/api/organizations/{s.organization_id}/family-authorizations",
        json={
            "family_membership_id": s.memberships["family"],
            "care_recipient_id": s.recipient_id,
            "categories": list(categories),
        },
    )


def audit_actions(db_sessions: sessionmaker[Session]) -> list[tuple[str, str]]:
    with db_sessions() as session:
        return [(e.action, e.outcome) for e in session.scalars(select(AuditEvent)).all()]


# --- Puestos y usuarios -------------------------------------------------------


def test_staff_membership_requires_role_and_manager_can_designate_inbox(
    client: TestClient, scenario: Scenario
) -> None:
    as_user(client, "jefa@test.example")
    base = f"/api/organizations/{scenario.organization_id}/memberships"

    missing_role = client.post(base, json={"display_name": "Sin puesto", "user_group": "staff"})
    assert missing_role.status_code == 422

    family_with_role = client.post(
        base,
        json={"display_name": "Familia", "user_group": "family", "staff_role": "caregiver"},
    )
    assert family_with_role.status_code == 422

    updated = client.patch(
        f"{base}/{scenario.memberships['caregiver']}",
        json={"handles_inbox": True, "staff_role": "administrative"},
    )
    assert updated.status_code == 200
    assert updated.json()["handles_inbox"] is True
    assert updated.json()["staff_role"] == "administrative"

    own = client.patch(f"{base}/{scenario.memberships['manager']}", json={"staff_role": "caregiver"})
    assert own.status_code == 422


def test_users_list_depends_on_role(client: TestClient, scenario: Scenario) -> None:
    path = f"/api/organizations/{scenario.organization_id}/memberships"

    as_user(client, "medica@test.example")
    families = client.get(path)
    assert families.status_code == 200
    assert {item["user_group"] for item in families.json()} == {"family"}
    assert client.post(path, json={"display_name": "X", "user_group": "family"}).status_code == 403

    as_user(client, "cuidador@test.example")
    assert client.get(path).status_code == 403


def test_service_staff_can_sign_in_and_only_sees_their_service(
    client: TestClient, scenario: Scenario
) -> None:
    as_user(client, "cuidador@test.example")
    units = client.get(f"/api/organizations/{scenario.organization_id}/care-units").json()
    assert [unit["id"] for unit in units] == [scenario.unit_id]


def test_manager_creates_user_with_password_that_can_sign_in(
    client: TestClient, scenario: Scenario
) -> None:
    as_user(client, "jefa@test.example")
    path = f"/api/organizations/{scenario.organization_id}/memberships"
    created = client.post(path, json={
        "display_name": "Médico Nuevo",
        "email": "medico1@momento.com.ar",
        "user_group": "staff",
        "staff_role": "physician",
        "password": "Medico123",
    })
    assert created.status_code == 201
    duplicated = client.post(path, json={
        "display_name": "Otro",
        "email": "MEDICO1@momento.com.ar",
        "user_group": "staff",
        "staff_role": "physician",
    })
    assert duplicated.status_code == 422
    short = client.post(path, json={
        "display_name": "Corta",
        "email": "corta@momento.com.ar",
        "user_group": "staff",
        "staff_role": "caregiver",
        "password": "abc",
    })
    assert short.status_code == 422

    client.cookies.clear()
    login = client.post("/api/auth/login", json={"email": "medico1@momento.com.ar", "password": "Medico123"})
    assert login.status_code == 200
    assert login.json()["memberships"][0]["staff_role"] == "physician"


# --- Autorización familiar ----------------------------------------------------


def test_manager_and_physician_grant_but_caregiver_is_denied_and_audited(
    client: TestClient, scenario: Scenario, db_sessions: sessionmaker[Session]
) -> None:
    as_user(client, "cuidador@test.example")
    assert grant(client, scenario).status_code == 403
    assert ("family_authorization.granted", "denied") in audit_actions(db_sessions)

    as_user(client, "medica@test.example")
    granted = grant(client, scenario, ["diet"])
    assert granted.status_code == 200
    assert [item["category"] for item in granted.json()] == ["diet"]

    as_user(client, "jefa@test.example")
    granted = grant(client, scenario, ["medication", "diet"])
    assert {item["category"] for item in granted.json()} == {"medication", "diet"}
    assert ("family_authorization.granted", "success") in audit_actions(db_sessions)


def test_physician_cannot_authorize_outside_their_service(
    client: TestClient, scenario: Scenario
) -> None:
    as_user(client, "medicosur@test.example")
    assert grant(client, scenario).status_code == 403


def test_authorization_is_isolated_between_organizations(
    client: TestClient, scenario: Scenario
) -> None:
    as_user(client, "jefa@test.example")
    other = client.post("/api/organizations", json={"name": "Otra organización"}).json()
    response = client.post(
        f"/api/organizations/{other['id']}/family-authorizations",
        json={
            "family_membership_id": scenario.memberships["family"],
            "care_recipient_id": scenario.recipient_id,
            "categories": ["diet"],
        },
    )
    assert response.status_code == 404


# --- Acceso familiar ----------------------------------------------------------


def test_family_and_management_logins_are_separate(client: TestClient, scenario: Scenario) -> None:
    client.cookies.clear()
    assert client.post(
        "/api/auth/login", json={"email": "familia@test.example", "password": PASSWORD}
    ).status_code == 401
    assert client.post(
        "/api/auth/family-login", json={"email": "jefa@test.example", "password": PASSWORD}
    ).status_code == 401

    as_user(client, "familia@test.example", family=True)
    assert client.get(f"/api/organizations/{scenario.organization_id}/memberships").status_code in (403, 404)
    assert client.get("/api/family/people").json() == []

    as_user(client, "jefa@test.example")
    assert client.get("/api/family/people").status_code == 403


def test_family_sees_only_authorized_categories_and_loses_access_on_revoke(
    client: TestClient, scenario: Scenario
) -> None:
    as_user(client, "jefa@test.example")
    authorizations = grant(client, scenario, ["diet"]).json()

    as_user(client, "familia@test.example", family=True)
    people = client.get("/api/family/people").json()
    assert [p["care_recipient_id"] for p in people] == [scenario.recipient_id]
    assert [c["category"] for c in people[0]["categories"]] == ["diet"]

    request = {
        "care_recipient_id": scenario.recipient_id,
        "category": "medication",
        "subject": "Consulta",
        "message": "Pregunta sobre medicación",
    }
    assert client.post("/api/family/requests", json=request).status_code == 403
    other_person = {**request, "category": "diet", "care_recipient_id": scenario.other_recipient_id}
    assert client.post("/api/family/requests", json=other_person).status_code == 403
    assert client.post("/api/family/requests", json={**request, "category": "diet"}).status_code == 201

    as_user(client, "jefa@test.example")
    revoked = client.post(
        f"/api/organizations/{scenario.organization_id}/family-authorizations/"
        f"{authorizations[0]['id']}/revoke"
    )
    assert revoked.status_code == 200
    assert revoked.json()["is_active"] is False

    as_user(client, "familia@test.example", family=True)
    assert client.get("/api/family/people").json() == []
    assert client.post("/api/family/requests", json={**request, "category": "diet"}).status_code == 403


# --- Bandeja ------------------------------------------------------------------


def _create_family_request(client: TestClient, scenario: Scenario) -> str:
    as_user(client, "jefa@test.example")
    grant(client, scenario, ["activities"])
    as_user(client, "familia@test.example", family=True)
    created = client.post(
        "/api/family/requests",
        json={
            "care_recipient_id": scenario.recipient_id,
            "category": "activities",
            "subject": "Taller de música",
            "message": "¿Puede participar el jueves?",
        },
    )
    assert created.status_code == 201
    assert created.json()["status_label"] == "Recibida"
    return created.json()["id"]


def test_inbox_flow_assign_respond_and_family_view(
    client: TestClient, scenario: Scenario, db_sessions: sessionmaker[Session]
) -> None:
    request_id = _create_family_request(client, scenario)
    inbox = f"/api/organizations/{scenario.organization_id}/care-units/{scenario.unit_id}/requests"

    as_user(client, "cuidador@test.example")
    assert client.get(inbox).status_code == 403

    as_user(client, "bandeja@test.example")
    listed = client.get(inbox)
    assert listed.status_code == 200
    assert [item["id"] for item in listed.json()] == [request_id]
    assert client.post(f"{inbox}/{request_id}/assign", json={"membership_id": scenario.memberships["designated"]}).status_code == 403

    as_user(client, "jefa@test.example")
    assignees = {a["membership_id"] for a in client.get(f"{inbox}/assignees").json()}
    assert scenario.memberships["designated"] in assignees
    assert scenario.memberships["caregiver"] not in assignees
    assert client.post(
        f"{inbox}/{request_id}/assign", json={"membership_id": scenario.memberships["caregiver"]}
    ).status_code == 422
    assigned = client.post(
        f"{inbox}/{request_id}/assign", json={"membership_id": scenario.memberships["designated"]}
    )
    assert assigned.status_code == 200
    assert assigned.json()["status_code"] == "assigned"

    as_user(client, "bandeja2@test.example")
    assert client.post(f"{inbox}/{request_id}/respond", json={"shared_response": "Sí"}).status_code == 403

    as_user(client, "bandeja@test.example")
    responded = client.post(
        f"{inbox}/{request_id}/respond", json={"shared_response": "  Sí, quedó anotada.  "}
    )
    assert responded.status_code == 200
    assert responded.json()["status_code"] == "responded"
    assert responded.json()["shared_response"] == "Sí, quedó anotada."
    assert client.post(f"{inbox}/{request_id}/status", json={"status_code": "inexistente"}).status_code == 422
    assert client.post(f"{inbox}/{request_id}/status", json={"status_code": "closed"}).status_code == 200

    as_user(client, "familia@test.example", family=True)
    family_view = client.get("/api/family/requests").json()[0]
    assert family_view["status_label"] == "Cerrada"
    assert family_view["shared_response"] == "Sí, quedó anotada."
    assert "assigned_to_name" not in family_view

    actions = audit_actions(db_sessions)
    for action in ("request.created", "request.assigned", "request.responded", "request.status_changed"):
        assert (action, "success") in actions
    assert ("request.inbox_viewed", "denied") in actions


def test_family_sees_last_visible_status_when_current_is_hidden(
    client: TestClient, scenario: Scenario, db_sessions: sessionmaker[Session]
) -> None:
    request_id = _create_family_request(client, scenario)
    with db_sessions() as session:
        assigned = session.scalar(
            select(CareUnitWorkflowStatus).where(
                CareUnitWorkflowStatus.care_unit_id == UUID(scenario.unit_id),
                CareUnitWorkflowStatus.code == "assigned",
            )
        )
        assigned.family_visible = False
        session.commit()

    as_user(client, "jefa@test.example")
    inbox = f"/api/organizations/{scenario.organization_id}/care-units/{scenario.unit_id}/requests"
    client.post(f"{inbox}/{request_id}/assign", json={"membership_id": scenario.memberships["designated"]})

    as_user(client, "familia@test.example", family=True)
    assert client.get("/api/family/requests").json()[0]["status_label"] == "Recibida"


# --- Cierre de Fase 2 -----------------------------------------------------------


def test_manager_deactivates_reactivates_and_resets_password(
    client: TestClient, scenario: Scenario
) -> None:
    as_user(client, "jefa@test.example")
    base = f"/api/organizations/{scenario.organization_id}/memberships"
    target = scenario.memberships["caregiver"]

    assert client.patch(f"{base}/{target}", json={"is_active": False}).status_code == 200
    active_ids = {item["id"] for item in client.get(base).json()}
    assert target not in active_ids
    all_items = {item["id"]: item for item in client.get(f"{base}?include_inactive=true").json()}
    assert all_items[target]["is_active"] is False
    assert all_items[target]["user"]["can_sign_in"] is True

    client.cookies.clear()
    assert client.post("/api/auth/login", json={"email": "cuidador@test.example", "password": PASSWORD}).status_code == 401

    as_user(client, "jefa@test.example")
    assert client.patch(f"{base}/{target}", json={"is_active": True}).status_code == 200
    assert client.post(f"{base}/{target}/password", json={"password": "corta"}).status_code == 422
    assert client.post(f"{base}/{target}/password", json={"password": "Cuidador123"}).status_code == 204

    client.cookies.clear()
    assert client.post("/api/auth/login", json={"email": "cuidador@test.example", "password": PASSWORD}).status_code == 401
    assert client.post("/api/auth/login", json={"email": "cuidador@test.example", "password": "Cuidador123"}).status_code == 200
    # Un cuidador no ve cuentas desactivadas ni asigna contraseñas.
    assert client.post(f"{base}/{target}/password", json={"password": "OtraClave1"}).status_code == 403


def test_password_reset_revokes_open_sessions(client: TestClient, scenario: Scenario) -> None:
    as_user(client, "medica@test.example")
    medic_cookie = client.cookies.get("momento_session")
    as_user(client, "jefa@test.example")
    path = f"/api/organizations/{scenario.organization_id}/memberships/{scenario.memberships['physician']}/password"
    assert client.post(path, json={"password": "Medico123"}).status_code == 204

    client.cookies.clear()
    client.cookies.set("momento_session", medic_cookie, path="/api")
    assert client.get("/api/auth/session").json()["authenticated"] is False


def test_audit_log_is_manager_only_and_scoped(client: TestClient, scenario: Scenario) -> None:
    as_user(client, "cuidador@test.example")
    path = f"/api/organizations/{scenario.organization_id}/audit-events"
    assert client.get(path).status_code == 403
    grant(client, scenario)  # rechazado y registrado

    as_user(client, "jefa@test.example")
    events = client.get(path).json()
    actions = {(item["action"], item["outcome"]) for item in events}
    assert ("auth.login", "success") in actions
    assert ("family_authorization.granted", "denied") in actions
    denied = client.get(f"{path}?outcome=denied").json()
    assert denied and all(item["outcome"] == "denied" for item in denied)

    other = client.post("/api/organizations", json={"name": "Otra"}).json()
    other_events = client.get(f"/api/organizations/{other['id']}/audit-events").json()
    assert all(item["action"] != "family_authorization.granted" for item in other_events)


def test_manager_renames_organization(client: TestClient, scenario: Scenario) -> None:
    as_user(client, "jefa@test.example")
    path = f"/api/organizations/{scenario.organization_id}"
    renamed = client.patch(path, json={"name": "  Residencia Renombrada "})
    assert renamed.status_code == 200
    assert renamed.json()["name"] == "Residencia Renombrada"
    as_user(client, "medica@test.example")
    assert client.patch(path, json={"name": "X"}).status_code == 403


# --- Correcciones de la revisión de seguridad --------------------------------


def test_revoked_family_no_longer_sees_past_requests_of_that_topic(
    client: TestClient, scenario: Scenario
) -> None:
    request_id = _create_family_request(client, scenario)  # tema: actividades
    as_user(client, "jefa@test.example")
    grant(client, scenario, ["diet"])
    base = f"/api/organizations/{scenario.organization_id}/family-authorizations"
    activities = next(
        item for item in client.get(f"{base}?family_membership_id={scenario.memberships['family']}").json()
        if item["category"] == "activities"
    )
    inbox = f"/api/organizations/{scenario.organization_id}/care-units/{scenario.unit_id}/requests"
    client.post(f"{inbox}/{request_id}/respond", json={"shared_response": "Respuesta posterior"})
    client.post(f"{base}/{activities['id']}/revoke")

    as_user(client, "familia@test.example", family=True)
    assert client.get("/api/family/requests").json() == []


def test_audit_log_excludes_activity_from_other_organizations(
    client: TestClient, scenario: Scenario, db_sessions: sessionmaker[Session]
) -> None:
    from momento_api.models import Organization, OrganizationMembership, StaffRole, UserAccount, UserGroup

    # La médica también pertenece a otra organización.
    with db_sessions() as session:
        other = Organization(name="Otra residencia")
        session.add(other)
        session.flush()
        medic = session.scalar(select(UserAccount).where(UserAccount.email == "medica@test.example"))
        session.add(OrganizationMembership(
            user_account_id=medic.id,
            organization_id=other.id,
            user_group=UserGroup.STAFF,
            staff_role=StaffRole.PHYSICIAN,
        ))
        session.commit()
        other_id = str(other.id)
        medic_id = medic.id

    as_user(client, "medica@test.example")
    client.post("/api/auth/logout")

    with db_sessions() as session:
        logins = session.scalars(select(AuditEvent).where(AuditEvent.action == "auth.login")).all()
        assert {str(e.organization_id) for e in logins if e.actor_account_id == medic_id} == {
            scenario.organization_id, other_id,
        }
        assert all(e.organization_id is not None for e in session.scalars(select(AuditEvent)).all())


def test_family_denied_request_on_foreign_recipient_is_not_linked(
    client: TestClient, scenario: Scenario, db_sessions: sessionmaker[Session]
) -> None:
    as_user(client, "familia@test.example", family=True)
    response = client.post("/api/family/requests", json={
        "care_recipient_id": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
        "category": "diet",
        "subject": "x",
        "message": "y",
    })
    assert response.status_code == 403
    with db_sessions() as session:
        event = session.scalar(select(AuditEvent).where(AuditEvent.action == "request.created"))
        assert event.outcome == "denied"
        assert event.target_id is None
        assert str(event.organization_id) == scenario.organization_id


def test_service_manager_only_sees_users_of_their_service(
    client: TestClient, scenario: Scenario, db_sessions: sessionmaker[Session]
) -> None:
    from momento_api.models import OrganizationMembership, StaffRole

    with db_sessions() as session:
        membership = session.get(OrganizationMembership, UUID(scenario.memberships["physician_south"]))
        membership.staff_role = StaffRole.MANAGER
        session.commit()

    as_user(client, "medicosur@test.example")
    path = f"/api/organizations/{scenario.organization_id}/memberships"
    visible = {item["id"] for item in client.get(f"{path}?include_inactive=true").json()}
    assert scenario.memberships["physician_south"] in visible
    assert scenario.memberships["caregiver"] not in visible  # Sede Norte
    assert scenario.memberships["family"] not in visible  # Sede Norte
