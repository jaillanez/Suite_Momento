# Backend de Momento

API inicial con FastAPI. Incluye una comprobación de salud de la API y otra de conexión a PostgreSQL. Todavía no contiene procesos de cuidado ni datos de residentes.

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

La primera migración crea solamente `organizations` y `care_units` (residencia o cuidado domiciliario). No crea usuarios, roles ni datos de personas mayores; esos accesos siguen en definición. La migración agrega tablas y no modifica datos existentes.

Después de actualizar dependencias y configurar `backend/.env`, desde esta carpeta ejecuta:

    .venv/bin/alembic upgrade head

Para consultar la revisión aplicada:

    .venv/bin/alembic current

La migración no se ejecuta automáticamente al iniciar la aplicación.

## Pruebas

    pytest
