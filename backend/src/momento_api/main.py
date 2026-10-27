"""Punto de entrada de la API de Momento."""

from fastapi import FastAPI, HTTPException

from momento_api.care_recipients import router as care_recipients_router
from momento_api.database import database_is_ready
from momento_api.memberships import router as memberships_router
from momento_api.organizations import router as organizations_router
from momento_api.workflow_config import router as workflow_config_router

app = FastAPI(
    title="Momento API",
    description="Base técnica inicial de Momento.",
    version="0.1.0",
)
app.include_router(organizations_router)
app.include_router(memberships_router)
app.include_router(care_recipients_router)
app.include_router(workflow_config_router)


@app.get("/api/health", tags=["Sistema"])
def health_check() -> dict[str, str]:
    """Confirma que la API está respondiendo."""
    return {"status": "ok", "service": "momento-api"}


@app.get("/api/health/database", tags=["Sistema"])
def database_health_check() -> dict[str, str]:
    """Comprueba PostgreSQL sin exponer credenciales ni detalles internos."""
    if not database_is_ready():
        raise HTTPException(
            status_code=503,
            detail="PostgreSQL no está configurado o no responde.",
        )
    return {"status": "ok", "dependency": "postgresql"}
