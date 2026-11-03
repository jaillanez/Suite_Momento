"""Punto de entrada de la API de Momento."""

from fastapi import Depends, FastAPI, HTTPException

from momento_api.assessments import definitions_router as scales_definitions_router
from momento_api.assessments import router as assessments_router
from momento_api.audit_log import router as audit_log_router
from momento_api.auth import get_management_account, router as auth_router
from momento_api.care_log import router as care_log_router
from momento_api.care_recipients import router as care_recipients_router
from momento_api.care_settings import router as care_settings_router
from momento_api.database import database_is_ready
from momento_api.documents import router as documents_router
from momento_api.family_authorizations import router as family_authorizations_router
from momento_api.family_requests import family_router, staff_router as requests_router
from momento_api.memberships import router as memberships_router
from momento_api.organizations import router as organizations_router
from momento_api.password_links import router as password_links_router
from momento_api.workflow_config import router as workflow_config_router

app = FastAPI(
    title="Momento API",
    description="Base técnica inicial de Momento.",
    version="0.1.0",
)
app.include_router(auth_router)
app.include_router(password_links_router)
authenticated = [Depends(get_management_account)]
app.include_router(organizations_router, dependencies=authenticated)
app.include_router(memberships_router, dependencies=authenticated)
app.include_router(care_recipients_router, dependencies=authenticated)
app.include_router(care_log_router, dependencies=authenticated)
app.include_router(care_settings_router, dependencies=authenticated)
app.include_router(documents_router, dependencies=authenticated)
app.include_router(assessments_router, dependencies=authenticated)
app.include_router(scales_definitions_router, dependencies=authenticated)
app.include_router(workflow_config_router, dependencies=authenticated)
app.include_router(family_authorizations_router, dependencies=authenticated)
app.include_router(requests_router, dependencies=authenticated)
app.include_router(audit_log_router, dependencies=authenticated)
# El acceso familiar no pasa por la dependencia de personal: valida su propio vínculo.
app.include_router(family_router)


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
