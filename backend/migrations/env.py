"""Configuración de Alembic para la base local de Momento."""

import os
from logging.config import fileConfig

from alembic import context
from dotenv import load_dotenv
from sqlalchemy import engine_from_config, pool

from momento_api.models import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

load_dotenv()
database_url = os.getenv("MOMENTO_DATABASE_URL")
if not database_url:
    raise RuntimeError("Configura MOMENTO_DATABASE_URL en backend/.env antes de migrar.")

# Alembic usa ConfigParser; escapar '%' evita errores con contraseñas codificadas en URL.
config.set_main_option("sqlalchemy.url", database_url.replace("%", "%%"))
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Genera SQL sin abrir una conexión a la base."""
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Ejecuta migraciones usando la conexión configurada."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
