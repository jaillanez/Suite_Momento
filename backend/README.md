# Backend de Momento

API con FastAPI, PostgreSQL y migraciones Alembic. Incluye autenticación local con clave derivada por scrypt y sesión de servidor en cookie HttpOnly. El escenario ficticio se crea a pedido con el asistente de demostración.

## Preparar el entorno local

Desde esta carpeta, crea un entorno con el Python 3.13.5 que ya está instalado:

    python3 -m venv .venv
    source .venv/bin/activate
    python -m pip install --upgrade pip
    python -m pip install -e ".[dev]"

Copia .env.example a .env y configura MOMENTO_DATABASE_URL con una base local. El archivo .env es privado y no se sube a GitHub. La API puede iniciarse aunque PostgreSQL todavía no esté configurado; la comprobación de base de datos informará que no está disponible.

## Iniciar y comprobar

Con el entorno virtual activo:

    uvicorn momento_api.main:app --reload --host 127.0.0.1 --port 8020

API: http://127.0.0.1:8020/api/health  
PostgreSQL: http://127.0.0.1:8020/api/health/database  
Documentación interactiva: http://127.0.0.1:8020/docs

## Esquema inicial de organizaciones y servicios

Las migraciones versionan organizaciones, servicios, membresías, personas cuidadas, autorizaciones familiares, credenciales protegidas y sesiones. Las credenciales existentes no se convierten automáticamente; la cuenta local se configura con el asistente.

Después de actualizar dependencias y configurar `backend/.env`, desde esta carpeta ejecuta:

    .venv/bin/alembic upgrade head

Para preparar una cuenta y un escenario local de ejemplo, seguí [la guía del entorno de demostración](../docs/entorno-demostracion-local.md). Para consultar la revisión aplicada:

    .venv/bin/alembic current

La migración no se ejecuta automáticamente al iniciar la aplicación.

## Pruebas

    pytest
