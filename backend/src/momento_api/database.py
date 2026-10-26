"""Comprobación de disponibilidad de PostgreSQL para desarrollo local."""

import os

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

load_dotenv()


def database_is_ready() -> bool:
    """Devuelve si PostgreSQL acepta una consulta sencilla."""
    database_url = os.getenv("MOMENTO_DATABASE_URL")
    if not database_url:
        return False

    engine = None
    try:
        engine = create_engine(database_url, pool_pre_ping=True)
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return True
    except SQLAlchemyError:
        return False
    finally:
        if engine is not None:
            engine.dispose()
