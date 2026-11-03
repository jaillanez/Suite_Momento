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


def purge_expired(session: Session, *, apply: bool, now: datetime | None = None) -> int:
    """Cuenta (y si apply, borra) los eventos anteriores al plazo. Quien llama confirma."""
    years = retention_years()
    limit = cutoff(now or datetime.now(timezone.utc), years)
    expired = session.scalar(select(func.count(AuditEvent.id)).where(AuditEvent.occurred_at < limit)) or 0
    if apply and expired:
        session.execute(delete(AuditEvent).where(AuditEvent.occurred_at < limit))
        record_event(
            session, action="audit.purged", actor_account_id=None,
            details={"deleted": expired, "retention_years": years, "before": limit.date().isoformat()},
        )
    return expired


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
            count = purge_expired(session, apply=args.apply)
        if args.apply:
            print(f"Plazo: {years} años. Se borraron {count} eventos vencidos.")
        else:
            print(f"Plazo: {years} años. Hay {count} eventos vencidos. Usá --apply para borrarlos.")
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
