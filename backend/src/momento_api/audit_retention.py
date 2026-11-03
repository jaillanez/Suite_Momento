"""Conservación del registro de control.

Los eventos se guardan AUDIT_RETENTION_YEARS años (10 por defecto, decidido por el equipo
el 03/11/2026). Se puede cambiar con MOMENTO_AUDIT_RETENTION_YEARS en backend/.env.

Nada se borra solo: la depuración se ejecuta a mano y primero muestra cuántos eventos
vencieron.

    python -m momento_api.audit_retention            # solo cuenta
    python -m momento_api.audit_retention --apply    # borra los vencidos
"""

from __future__ import annotations

import argparse
import os
import pwd
import re
from datetime import datetime, timezone

from dotenv import load_dotenv
from sqlalchemy import create_engine, delete, func, select
from sqlalchemy.orm import Session

from momento_api.audit import record_event
from momento_api.models import AuditEvent

AUDIT_RETENTION_YEARS = 10


def retention_years() -> int:
    raw = os.getenv("MOMENTO_AUDIT_RETENTION_YEARS", "").strip()
    if not raw:
        return AUDIT_RETENTION_YEARS
    if not raw.isdigit() or int(raw) < 1:
        raise ValueError("MOMENTO_AUDIT_RETENTION_YEARS debe ser un número entero de años, 1 o más.")
    return int(raw)


def cutoff(now: datetime, years: int) -> datetime:
    """Misma fecha y hora, `years` años antes (el 29 de febrero pasa al 28)."""
    try:
        return now.replace(year=now.year - years)
    except ValueError:
        return now.replace(year=now.year - years, day=28)


def purge_expired(session: Session, *, apply: bool, now: datetime | None = None, operator: str | None = None) -> int:
    """Cuenta (y si apply, borra) los eventos anteriores al plazo. Quien llama confirma."""
    years = retention_years()
    limit = cutoff(now or datetime.now(timezone.utc), years)
    per_organization = dict(session.execute(
        select(AuditEvent.organization_id, func.count(AuditEvent.id))
        .where(AuditEvent.occurred_at < limit)
        .group_by(AuditEvent.organization_id)
    ).all())
    expired = sum(per_organization.values())
    if apply and expired:
        session.execute(delete(AuditEvent).where(AuditEvent.occurred_at < limit))
        details = {"retention_years": years, "before": limit.date().isoformat()}
        # Una constancia por organización, para que cada encargado la vea en su registro.
        for organization_id, deleted in per_organization.items():
            if organization_id is not None:
                record_event(
                    session, action="audit.purged", actor_account_id=None, organization_id=organization_id,
                    details={"deleted": deleted, **details},
                )
        # Quién lo ejecutó queda solo en una constancia interna, sin organización: no la ve
        # ninguna residencia.
        record_event(
            session, action="audit.purged", actor_account_id=None, organization_id=None,
            details={"deleted": expired, **details, "run_by": _clean_operator(operator)},
        )
    return expired


def _clean_operator(value: str | None) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]", "", value or "")[:64]
    return cleaned or "desconocido"


def _system_user() -> str:
    """Usuario del sistema operativo según el proceso (no según variables de entorno)."""
    try:
        return pwd.getpwuid(os.getuid()).pw_name
    except KeyError:
        return str(os.getuid())


def main() -> None:
    parser = argparse.ArgumentParser(description="Depura el registro de control vencido.")
    parser.add_argument("--apply", action="store_true", help="borrar los eventos vencidos (sin esto, solo cuenta)")
    args = parser.parse_args()
    load_dotenv()
    database_url = os.getenv("MOMENTO_DATABASE_URL")
    if not database_url:
        raise SystemExit("Configurá MOMENTO_DATABASE_URL en backend/.env.")
    engine = create_engine(database_url, pool_pre_ping=True)
    try:
        with Session(engine) as session, session.begin():
            years = retention_years()
            count = purge_expired(session, apply=args.apply, operator=_system_user())
        if args.apply:
            print(f"Plazo: {years} años. Se borraron {count} eventos vencidos.")
        else:
            print(f"Plazo: {years} años. Hay {count} eventos vencidos. Usá --apply para borrarlos.")
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
