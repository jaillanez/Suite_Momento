"""Sesiones SQLAlchemy para las rutas que requieren PostgreSQL."""

import os
from functools import lru_cache
from collections.abc import Generator

from fastapi import HTTPException
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session

from momento_api.database import load_dotenv


@lru_cache(maxsize=4)
def _engine_for_url(database_url: str) -> Engine:
    return create_engine(database_url, pool_pre_ping=True)


def get_session() -> Generator[Session, None, None]:
    """Provee una sesión por solicitud, sin exponer detalles de conexión."""
    load_dotenv()
    database_url = os.getenv("MOMENTO_DATABASE_URL")
    if not database_url:
        raise HTTPException(
            status_code=503,
            detail="PostgreSQL no está configurado o no responde.",
        )

    session = Session(_engine_for_url(database_url))
    try:
        yield session
    finally:
        session.close()
