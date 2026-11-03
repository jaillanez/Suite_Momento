"""Conservación del registro de control: 10 años, depuración manual."""

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from momento_api.audit_retention import cutoff, purge_expired, retention_years
from momento_api.models import AuditEvent, Base
from tests.access_helpers import client, scenario  # noqa: F401

NOW = datetime(2026, 11, 3, 12, tzinfo=timezone.utc)


def test_default_is_ten_years_and_configurable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MOMENTO_AUDIT_RETENTION_YEARS", raising=False)
    assert retention_years() == 10
    monkeypatch.setenv("MOMENTO_AUDIT_RETENTION_YEARS", "5")
    assert retention_years() == 5
    monkeypatch.setenv("MOMENTO_AUDIT_RETENTION_YEARS", "0")
    with pytest.raises(ValueError):
        retention_years()


def test_leap_day_cutoff() -> None:
    assert cutoff(datetime(2028, 2, 29, tzinfo=timezone.utc), 10) == datetime(2018, 2, 28, tzinfo=timezone.utc)


def test_only_expired_events_are_deleted_and_only_with_apply(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MOMENTO_AUDIT_RETENTION_YEARS", raising=False)
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        old = NOW.replace(year=2016) - timedelta(days=1)
        recent = NOW.replace(year=2016) + timedelta(days=1)
        for moment, action in ((old, "viejo"), (recent, "reciente")):
            session.add(AuditEvent(action=action, outcome="success", occurred_at=moment))
        session.commit()

        assert purge_expired(session, apply=False, now=NOW) == 1
        session.commit()
        assert len(session.scalars(select(AuditEvent)).all()) == 2

        assert purge_expired(session, apply=True, now=NOW, operator="jorge") == 1
        session.commit()
        actions = sorted(e.action for e in session.scalars(select(AuditEvent)).all())
        assert actions == ["audit.purged", "reciente"]
        purged = session.scalar(select(AuditEvent).where(AuditEvent.action == "audit.purged"))
        assert purged.details["run_by"] == "jorge"


def test_purge_is_recorded_in_each_affected_organization(monkeypatch: pytest.MonkeyPatch) -> None:
    from momento_api.models import Organization
    monkeypatch.delenv("MOMENTO_AUDIT_RETENTION_YEARS", raising=False)
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        orgs = [Organization(name="A"), Organization(name="B")]
        session.add_all(orgs)
        session.flush()
        old = NOW.replace(year=2010)
        for org, count in ((orgs[0], 2), (orgs[1], 1)):
            for _ in range(count):
                session.add(AuditEvent(action="viejo", outcome="success", occurred_at=old, organization_id=org.id))
        session.commit()
        assert purge_expired(session, apply=True, now=NOW, operator="jorge") == 3
        session.commit()
        records = {e.organization_id: e.details["deleted"] for e in session.scalars(select(AuditEvent)).all()}
        assert records == {orgs[0].id: 2, orgs[1].id: 1}
    engine.dispose()
    engine.dispose()


def test_manager_sees_retention(client, scenario) -> None:  # noqa: F811
    from tests.access_helpers import as_user
    path = f"/api/organizations/{scenario.organization_id}/audit-events/retention"
    assert as_user(client, "jefa@test.example").get(path).json() == {"years": 10}
    assert as_user(client, "medica@test.example").get(path).status_code == 403
