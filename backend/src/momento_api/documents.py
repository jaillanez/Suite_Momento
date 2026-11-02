"""Documentos adjuntos a la ficha, guardados en disco local sin servicios externos."""

import os
import re
from pathlib import Path
from urllib.parse import quote
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy.orm import Session

from momento_api.audit import record_event
from momento_api.auth import get_authenticated_account
from momento_api.care_recipients import (
    DOCUMENT_MANAGERS,
    _care_unit,
    _deny,
    _recipient,
    _roles,
    _viewer,
)
from momento_api.models import CareRecipientDocument, UserAccount
from momento_api.schemas import CareRecipientDocumentRead
from momento_api.session import get_session

router = APIRouter(prefix="/api/care-units", tags=["Documentos de la ficha"])

MAX_BYTES = 10 * 1024 * 1024
# Tipo declarado → firma del archivo. Se exige que ambos coincidan.
ALLOWED_TYPES = {
    "application/pdf": (b"%PDF-",),
    "image/jpeg": (b"\xff\xd8\xff",),
    "image/png": (b"\x89PNG\r\n\x1a\n",),
}
DEFAULT_DIR = Path(__file__).resolve().parents[2] / "storage" / "documents"


def storage_dir() -> Path:
    directory = Path(os.getenv("MOMENTO_DOCUMENTS_DIR") or DEFAULT_DIR)
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    return directory


def _safe_filename(name: str) -> str:
    """Solo para mostrar y descargar; nunca se usa para guardar en disco."""
    name = Path(name.replace("\\", "/")).name
    name = re.sub(r"[\x00-\x1f\x7f\"]", "", name).strip()
    return (name or "documento")[:200]


def _file_path(document: CareRecipientDocument) -> Path:
    return storage_dir() / document.storage_key


@router.post(
    "/{care_unit_id}/care-recipients/{recipient_id}/documents",
    response_model=CareRecipientDocumentRead,
    status_code=status.HTTP_201_CREATED,
)
async def upload_document(
    care_unit_id: UUID,
    recipient_id: UUID,
    request: Request,
    title: str = Query(min_length=1, max_length=160),
    category: str = Query(pattern="^(identity|consent|study|other)$"),
    filename: str = Query(min_length=1, max_length=255),
    session: Session = Depends(get_session),
    account: UserAccount = Depends(get_authenticated_account),
) -> CareRecipientDocument:
    """Recibe el archivo en el cuerpo de la solicitud (sin formulario multipart)."""
    care_unit = _care_unit(session, care_unit_id)
    recipient = _recipient(session, care_unit_id, recipient_id)
    if not _roles(session, account, care_unit) & set(DOCUMENT_MANAGERS):
        raise _deny(session, account, care_unit, "care_recipient.document_uploaded", recipient.id,
                    "Solo el encargado o un administrativo pueden subir documentos.")

    content_type = (request.headers.get("content-type") or "").split(";")[0].strip().lower()
    if content_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=415, detail="Solo se aceptan archivos PDF, JPG o PNG.")
    declared = request.headers.get("content-length")
    if declared and declared.isdigit() and int(declared) > MAX_BYTES:
        raise HTTPException(status_code=413, detail="El archivo supera los 10 MB.")

    content = bytearray()
    async for chunk in request.stream():
        content.extend(chunk)
        if len(content) > MAX_BYTES:
            raise HTTPException(status_code=413, detail="El archivo supera los 10 MB.")
    if not content:
        raise HTTPException(status_code=422, detail="El archivo está vacío.")
    if not bytes(content).startswith(ALLOWED_TYPES[content_type]):
        raise HTTPException(status_code=415, detail="El contenido no coincide con el tipo de archivo.")

    uploader = _viewer(session, account, care_unit)
    storage_key = uuid4().hex
    path = storage_dir() / storage_key
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as handle:
        handle.write(content)

    clean_title = title.strip() or "Documento"
    document = CareRecipientDocument(
        care_recipient_id=recipient.id,
        title=clean_title,
        category=category,
        original_filename=_safe_filename(filename),
        content_type=content_type,
        size_bytes=len(content),
        storage_key=storage_key,
        uploaded_by_membership_id=uploader.id,
    )
    session.add(document)
    session.flush()
    record_event(
        session,
        action="care_recipient.document_uploaded",
        actor_account_id=account.id,
        organization_id=care_unit.organization_id,
        target_type="care_recipient",
        target_id=recipient.id,
        details={"category": category},
    )
    try:
        session.commit()
    except Exception:
        path.unlink(missing_ok=True)
        raise
    session.refresh(document)
    return document


def _document(session: Session, recipient_id: UUID, document_id: UUID) -> CareRecipientDocument:
    document = session.get(CareRecipientDocument, document_id)
    if document is None or document.care_recipient_id != recipient_id:
        raise HTTPException(status_code=404, detail="Documento no encontrado.")
    return document


@router.get("/{care_unit_id}/care-recipients/{recipient_id}/documents/{document_id}")
def download_document(
    care_unit_id: UUID,
    recipient_id: UUID,
    document_id: UUID,
    session: Session = Depends(get_session),
    account: UserAccount = Depends(get_authenticated_account),
) -> Response:
    """Todo el personal del servicio puede descargar; cada descarga queda registrada."""
    care_unit = _care_unit(session, care_unit_id)
    _viewer(session, account, care_unit)
    recipient = _recipient(session, care_unit_id, recipient_id)
    document = _document(session, recipient.id, document_id)
    path = _file_path(document)
    if not path.is_file():
        raise HTTPException(status_code=404, detail="El archivo no está disponible.")
    record_event(
        session,
        action="care_recipient.document_downloaded",
        actor_account_id=account.id,
        organization_id=care_unit.organization_id,
        target_type="care_recipient",
        target_id=recipient.id,
        details={"category": document.category},
    )
    session.commit()
    return Response(
        content=path.read_bytes(),
        media_type=document.content_type,
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{quote(document.original_filename)}",
            "X-Content-Type-Options": "nosniff",
            "Cache-Control": "no-store",
        },
    )


@router.delete(
    "/{care_unit_id}/care-recipients/{recipient_id}/documents/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_document(
    care_unit_id: UUID,
    recipient_id: UUID,
    document_id: UUID,
    session: Session = Depends(get_session),
    account: UserAccount = Depends(get_authenticated_account),
) -> Response:
    care_unit = _care_unit(session, care_unit_id)
    recipient = _recipient(session, care_unit_id, recipient_id)
    if not _roles(session, account, care_unit) & set(DOCUMENT_MANAGERS):
        raise _deny(session, account, care_unit, "care_recipient.document_deleted", recipient.id,
                    "Solo el encargado o un administrativo pueden borrar documentos.")
    document = _document(session, recipient.id, document_id)
    path = _file_path(document)
    record_event(
        session,
        action="care_recipient.document_deleted",
        actor_account_id=account.id,
        organization_id=care_unit.organization_id,
        target_type="care_recipient",
        target_id=recipient.id,
        details={"category": document.category},
    )
    session.delete(document)
    session.commit()
    path.unlink(missing_ok=True)
    return Response(status_code=204)
