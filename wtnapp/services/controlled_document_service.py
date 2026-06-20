"""Ciclo de vida dos documentos controlados da Clausula 4."""

from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from wtnapp.models.document_version_model import DocumentVersion
from wtnapp.settings import Classification, DocStatus, DocType


def review_overdue(version: DocumentVersion | None) -> bool:
    if version is None or version.next_review_at is None:
        return False
    due = version.next_review_at
    if due.tzinfo is None:
        due = due.replace(tzinfo=timezone.utc)
    return due < datetime.now(timezone.utc)


def submit_review(db: Session, artifact: Any) -> Any:
    if artifact.draft_status == DocStatus.in_review:
        raise HTTPException(status.HTTP_409_CONFLICT, "Artefato ja esta em revisao.")
    artifact.draft_status = DocStatus.in_review
    db.commit()
    db.refresh(artifact)
    return artifact


def approve_document(
    *,
    db: Session,
    artifact: Any,
    doc_type: DocType,
    actor_id,
    classification: Classification,
    next_review_at,
    change_nature: str,
    snapshot_factory: Callable[[], dict],
) -> DocumentVersion:
    if artifact.draft_status != DocStatus.in_review:
        raise HTTPException(status.HTTP_409_CONFLICT, "Envie o artefato para revisao antes de aprovar.")

    next_number = (
        db.query(DocumentVersion)
        .filter(
            DocumentVersion.tenant_id == artifact.tenant_id,
            DocumentVersion.document_type == doc_type,
            DocumentVersion.document_id == artifact.id,
        )
        .count()
        + 1
    )
    identifier = f"SGSI-DOC-{doc_type.value.replace('_', '-').upper()}"
    version = DocumentVersion(
        tenant_id=artifact.tenant_id,
        document_type=doc_type,
        document_id=artifact.id,
        identifier=identifier,
        version_number=next_number,
        status=DocStatus.in_force,
        classification=classification,
        next_review_at=next_review_at,
        elaborated_by=actor_id,
        reviewed_by=actor_id,
        approved_by=actor_id,
        change_nature=change_nature,
        content_snapshot=snapshot_factory(),
    )
    db.add(version)
    db.flush()

    # Append-only: a versão antiga NÃO é alterada (gatilho bloqueia UPDATE). A versão "em vigor" é
    # determinada pelo ponteiro `current_version_id` do artefato (exatamente uma) e a obsolescência
    # de uma versão referenciada é derivada por recência (ver `is_superseded`).
    artifact.current_version_id = version.id
    artifact.draft_status = DocStatus.draft
    db.commit()
    db.refresh(version)
    return version


def is_superseded(db: Session, version_id) -> bool:
    """Uma versão está obsoleta se existe uma versão mais recente do mesmo documento.

    Não depende de mutação de status (impossível sob append-only); deriva por `version_number`.
    """
    if version_id is None:
        return False
    version = db.get(DocumentVersion, version_id)
    if version is None:
        return True  # referência quebrada ⇒ tratar como desatualizada
    newer = (
        db.query(DocumentVersion)
        .filter(
            DocumentVersion.tenant_id == version.tenant_id,
            DocumentVersion.document_type == version.document_type,
            DocumentVersion.document_id == version.document_id,
            DocumentVersion.version_number > version.version_number,
        )
        .first()
    )
    return newer is not None


def list_versions(db: Session, tenant_id, doc_type: DocType, document_id) -> list[DocumentVersion]:
    return (
        db.query(DocumentVersion)
        .filter(
            DocumentVersion.tenant_id == tenant_id,
            DocumentVersion.document_type == doc_type,
            DocumentVersion.document_id == document_id,
        )
        .order_by(DocumentVersion.version_number.desc())
        .all()
    )
