"""Printable document templates, previews, signatures and custody timeline."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    event,
)
from sqlalchemy.orm import Mapped, mapped_column

from wtnapp.models.base import Base
from wtnapp.settings import (
    Classification,
    DocumentPreviewStatus,
    PrintTemplateScope,
    PrintTemplateStatus,
    PrintableDocumentType,
    SignatureCoordinateSystem,
    SignatureMethod,
    SignaturePlacementOrigin,
    SignedDocumentStatus,
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


class PrintTemplate(Base):
    """Logical print template. System templates have ``tenant_id`` set to NULL."""

    __tablename__ = "print_templates"
    __table_args__ = (
        UniqueConstraint("tenant_id", "document_type", "name", name="uq_print_template_tenant_type_name"),
        Index("ix_print_templates_tenant_id", "tenant_id"),
        Index("ix_print_templates_document_type", "document_type"),
        Index("ix_print_templates_scope", "scope"),
        Index("ix_print_templates_status", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("organizations.id"), nullable=True
    )
    scope: Mapped[PrintTemplateScope] = mapped_column(
        SAEnum(PrintTemplateScope, native_enum=False, length=20), nullable=False
    )
    document_type: Mapped[PrintableDocumentType] = mapped_column(
        SAEnum(PrintableDocumentType, native_enum=False, length=40), nullable=False
    )
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    status: Mapped[PrintTemplateStatus] = mapped_column(
        SAEnum(PrintTemplateStatus, native_enum=False, length=20),
        default=PrintTemplateStatus.draft,
        nullable=False,
    )
    default_classification: Mapped[Classification] = mapped_column(
        SAEnum(Classification, native_enum=False, length=30),
        default=Classification.uso_interno,
        nullable=False,
    )
    current_version_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now, nullable=False
    )


class PrintTemplateVersion(Base):
    """Immutable renderable version for a print template."""

    __tablename__ = "print_template_versions"
    __table_args__ = (
        UniqueConstraint("template_id", "version_number", name="uq_print_template_version_number"),
        Index("ix_print_template_versions_tenant_id", "tenant_id"),
        Index("ix_print_template_versions_template_id", "template_id"),
        Index("ix_print_template_versions_hash", "content_hash"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("organizations.id"), nullable=True
    )
    template_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("print_templates.id"), nullable=False
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    renderer: Mapped[str] = mapped_column(String(40), default="reportlab_v1", nullable=False)
    layout_schema: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    allowed_variables: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    required_sections: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_by: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)


class PrintTemplateVariable(Base):
    """Variable available for building printable template versions."""

    __tablename__ = "print_template_variables"
    __table_args__ = (
        UniqueConstraint("tenant_id", "document_type", "variable_key", name="uq_print_template_variable_key"),
        Index("ix_print_template_variables_tenant_id", "tenant_id"),
        Index("ix_print_template_variables_document_type", "document_type"),
        Index("ix_print_template_variables_scope", "scope"),
        Index("ix_print_template_variables_status", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("organizations.id"), nullable=True
    )
    scope: Mapped[str] = mapped_column(String(20), nullable=False, default="tenant")
    document_type: Mapped[PrintableDocumentType] = mapped_column(
        SAEnum(PrintableDocumentType, native_enum=False, length=40), nullable=False
    )
    variable_key: Mapped[str] = mapped_column(String(80), nullable=False)
    label: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    value_type: Mapped[str] = mapped_column(String(30), default="string", nullable=False)
    required_by_default: Mapped[bool] = mapped_column(default=False, nullable=False)
    optional_by_default: Mapped[bool] = mapped_column(default=True, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=100, nullable=False)
    created_by: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now, nullable=False
    )


class DocumentPreview(Base):
    """Temporary snapshot/PDF reviewed before an electronic signature."""

    __tablename__ = "document_previews"
    __table_args__ = (
        Index("ix_document_previews_tenant_id", "tenant_id"),
        Index("ix_document_previews_document_type", "document_type"),
        Index("ix_document_previews_source", "source_artifact_type", "source_artifact_id"),
        Index("ix_document_previews_status", "status"),
        Index("ix_document_previews_created_by", "created_by"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    document_type: Mapped[PrintableDocumentType] = mapped_column(
        SAEnum(PrintableDocumentType, native_enum=False, length=40), nullable=False
    )
    source_artifact_type: Mapped[str] = mapped_column(String(40), nullable=False)
    source_artifact_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    source_document_version_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("document_versions.id"), nullable=True
    )
    template_version_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("print_template_versions.id"), nullable=False
    )
    classification: Mapped[Classification] = mapped_column(
        SAEnum(Classification, native_enum=False, length=30), nullable=False
    )
    status: Mapped[DocumentPreviewStatus] = mapped_column(
        SAEnum(DocumentPreviewStatus, native_enum=False, length=20),
        default=DocumentPreviewStatus.active,
        nullable=False,
    )
    artifact_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    template_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    snapshot_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    preview_pdf_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    preview_storage_key: Mapped[str] = mapped_column(String(500), nullable=False)
    snapshot_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    rendered_variables: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    pdf_page_metrics: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    signature_policy_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    default_signature_placement: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    warnings: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_by: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)


class DocumentSignaturePlacement(Base):
    """Append-only confirmed visual seal placement for a preview."""

    __tablename__ = "document_signature_placements"
    __table_args__ = (
        UniqueConstraint("tenant_id", "preview_id", "placement_revision", name="uq_document_signature_placement_revision"),
        Index("ix_document_signature_placements_tenant_id", "tenant_id"),
        Index("ix_document_signature_placements_preview_id", "preview_id"),
        Index("ix_document_signature_placements_document_type", "document_type"),
        Index("ix_document_signature_placements_created_by", "created_by"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    preview_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("document_previews.id"), nullable=False
    )
    document_type: Mapped[PrintableDocumentType] = mapped_column(
        SAEnum(PrintableDocumentType, native_enum=False, length=40), nullable=False
    )
    source_artifact_type: Mapped[str] = mapped_column(String(40), nullable=False)
    source_artifact_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    placement_revision: Mapped[int] = mapped_column(Integer, nullable=False)
    page_number: Mapped[int] = mapped_column(Integer, nullable=False)
    x_points: Mapped[float] = mapped_column(nullable=False)
    y_points: Mapped[float] = mapped_column(nullable=False)
    width_points: Mapped[float] = mapped_column(nullable=False)
    height_points: Mapped[float] = mapped_column(nullable=False)
    page_width_points: Mapped[float] = mapped_column(nullable=False)
    page_height_points: Mapped[float] = mapped_column(nullable=False)
    coordinate_system: Mapped[SignatureCoordinateSystem] = mapped_column(
        SAEnum(SignatureCoordinateSystem, native_enum=False, length=40),
        default=SignatureCoordinateSystem.pdf_points_bottom_left,
        nullable=False,
    )
    origin: Mapped[SignaturePlacementOrigin] = mapped_column(
        SAEnum(SignaturePlacementOrigin, native_enum=False, length=20),
        default=SignaturePlacementOrigin.user,
        nullable=False,
    )
    template_version_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("print_template_versions.id"), nullable=False
    )
    snapshot_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    artifact_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    signature_policy_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    placement_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_by: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)


class SignedDocument(Base):
    """Immutable signed PDF metadata."""

    __tablename__ = "signed_documents"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "document_type",
            "source_artifact_type",
            "source_artifact_id",
            "version_number",
            name="uq_signed_document_version_number",
        ),
        UniqueConstraint("tenant_id", "identifier", name="uq_signed_document_identifier"),
        Index("ix_signed_documents_tenant_id", "tenant_id"),
        Index("ix_signed_documents_document_type", "document_type"),
        Index("ix_signed_documents_source", "source_artifact_type", "source_artifact_id"),
        Index("ix_signed_documents_signed_at", "signed_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    document_type: Mapped[PrintableDocumentType] = mapped_column(
        SAEnum(PrintableDocumentType, native_enum=False, length=40), nullable=False
    )
    source_artifact_type: Mapped[str] = mapped_column(String(40), nullable=False)
    source_artifact_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    source_document_version_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("document_versions.id"), nullable=True
    )
    preview_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("document_previews.id"), nullable=False)
    template_version_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("print_template_versions.id"), nullable=False
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[SignedDocumentStatus] = mapped_column(
        SAEnum(SignedDocumentStatus, native_enum=False, length=20),
        default=SignedDocumentStatus.signed,
        nullable=False,
    )
    classification: Mapped[Classification] = mapped_column(
        SAEnum(Classification, native_enum=False, length=30), nullable=False
    )
    identifier: Mapped[str] = mapped_column(String(80), nullable=False)
    pdf_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    snapshot_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    hash_algorithm: Mapped[str] = mapped_column(String(20), default="sha256", nullable=False)
    pdf_storage_key: Mapped[str] = mapped_column(String(500), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    signed_by: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id"), nullable=False)
    signed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)


class SignedDocumentSnapshot(Base):
    """Immutable canonical snapshot used to render a signed document."""

    __tablename__ = "signed_document_snapshots"
    __table_args__ = (
        UniqueConstraint("signed_document_id", name="uq_signed_document_snapshot_document"),
        Index("ix_signed_document_snapshots_tenant_id", "tenant_id"),
        Index("ix_signed_document_snapshots_document_id", "signed_document_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    signed_document_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("signed_documents.id"), nullable=False
    )
    artifact_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    template_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    snapshot_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    rendered_variables: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    snapshot_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)


class DocumentSignature(Base):
    """Internal advanced electronic signature for a printable document."""

    __tablename__ = "document_signatures"
    __table_args__ = (
        Index("ix_document_signatures_tenant_id", "tenant_id"),
        Index("ix_document_signatures_document_id", "signed_document_id"),
        Index("ix_document_signatures_signer_user_id", "signer_user_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    signed_document_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("signed_documents.id"), nullable=False
    )
    signer_user_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id"), nullable=False)
    signer_role: Mapped[str] = mapped_column(String(60), nullable=False)
    signer_name: Mapped[str] = mapped_column(String(200), nullable=False)
    signer_email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    signed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    pdf_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    algorithm: Mapped[str] = mapped_column(String(20), default="sha256", nullable=False)
    level: Mapped[str] = mapped_column(String(20), default="advanced", nullable=False)
    auth_context: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    ip: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(500), nullable=True)
    signature_method: Mapped[SignatureMethod] = mapped_column(
        SAEnum(SignatureMethod, native_enum=False, length=40),
        default=SignatureMethod.internal_electronic_signature,
        nullable=False,
    )
    signature_provider: Mapped[str | None] = mapped_column(String(80), nullable=True)
    visual_signature_present: Mapped[bool] = mapped_column(default=True, nullable=False)
    provider_reference: Mapped[str | None] = mapped_column(String(200), nullable=True)
    provider_payload_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)


class SignedDocumentSignaturePlacement(Base):
    """Immutable snapshot of the exact seal placement used in a signed document."""

    __tablename__ = "signed_document_signature_placements"
    __table_args__ = (
        UniqueConstraint("signed_document_id", name="uq_signed_document_signature_placement_document"),
        Index("ix_signed_document_signature_placements_tenant_id", "tenant_id"),
        Index("ix_signed_document_signature_placements_document_id", "signed_document_id"),
        Index("ix_signed_document_signature_placements_placement_id", "placement_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    signed_document_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("signed_documents.id"), nullable=False
    )
    placement_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("document_signature_placements.id"), nullable=False
    )
    page_number: Mapped[int] = mapped_column(Integer, nullable=False)
    x_points: Mapped[float] = mapped_column(nullable=False)
    y_points: Mapped[float] = mapped_column(nullable=False)
    width_points: Mapped[float] = mapped_column(nullable=False)
    height_points: Mapped[float] = mapped_column(nullable=False)
    page_width_points: Mapped[float] = mapped_column(nullable=False)
    page_height_points: Mapped[float] = mapped_column(nullable=False)
    coordinate_system: Mapped[SignatureCoordinateSystem] = mapped_column(
        SAEnum(SignatureCoordinateSystem, native_enum=False, length=40), nullable=False
    )
    origin: Mapped[SignaturePlacementOrigin] = mapped_column(
        SAEnum(SignaturePlacementOrigin, native_enum=False, length=20), nullable=False
    )
    placement_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)


class DocumentAccessEvent(Base):
    """Append-only local event stream for printable document custody."""

    __tablename__ = "document_access_events"
    __table_args__ = (
        Index("ix_document_access_events_tenant_id", "tenant_id"),
        Index("ix_document_access_events_entity", "entity_type", "entity_id"),
        Index("ix_document_access_events_event_type", "event_type"),
        Index("ix_document_access_events_actor_user_id", "actor_user_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    event_type: Mapped[str] = mapped_column(String(40), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(60), nullable=False)
    entity_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id"), nullable=True)
    actor_role: Mapped[str | None] = mapped_column(String(60), nullable=True)
    outcome: Mapped[str] = mapped_column(String(20), nullable=False)
    details: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)


_APPEND_ONLY_TABLES = (
    "print_template_versions",
    "signed_documents",
    "signed_document_snapshots",
    "document_signature_placements",
    "document_signatures",
    "signed_document_signature_placements",
    "document_access_events",
)


def _sqlite_triggers(table: str) -> tuple[str, str]:
    return (
        f"CREATE TRIGGER IF NOT EXISTS {table}_no_update BEFORE UPDATE ON {table} "
        f"BEGIN SELECT RAISE(ABORT, '{table} is append-only'); END;",
        f"CREATE TRIGGER IF NOT EXISTS {table}_no_delete BEFORE DELETE ON {table} "
        f"BEGIN SELECT RAISE(ABORT, '{table} is append-only'); END;",
    )


def _pg_statements(table: str) -> tuple[str, str, str]:
    fn = f"wtn_{table}_append_only"
    trigger = f"{table}_append_only"
    return (
        f"CREATE OR REPLACE FUNCTION {fn}() RETURNS trigger AS $$ "
        f"BEGIN RAISE EXCEPTION '{table} is append-only'; END; $$ LANGUAGE plpgsql;",
        f"DROP TRIGGER IF EXISTS {trigger} ON {table};",
        f"CREATE TRIGGER {trigger} BEFORE UPDATE OR DELETE ON {table} "
        f"FOR EACH ROW EXECUTE FUNCTION {fn}();",
    )


def _append_only_statements(dialect: str, table: str) -> tuple[str, ...]:
    if dialect == "sqlite":
        return _sqlite_triggers(table)
    if dialect == "postgresql":
        return _pg_statements(table)
    return ()


def _install_append_only(table_name: str, connection) -> None:
    for stmt in _append_only_statements(connection.dialect.name, table_name):
        connection.exec_driver_sql(stmt)


@event.listens_for(PrintTemplateVersion.__table__, "after_create")
def _template_version_append_only(target, connection, **kw):  # pragma: no cover - infra
    _install_append_only("print_template_versions", connection)


@event.listens_for(SignedDocument.__table__, "after_create")
def _signed_document_append_only(target, connection, **kw):  # pragma: no cover - infra
    _install_append_only("signed_documents", connection)


@event.listens_for(SignedDocumentSnapshot.__table__, "after_create")
def _signed_snapshot_append_only(target, connection, **kw):  # pragma: no cover - infra
    _install_append_only("signed_document_snapshots", connection)


@event.listens_for(DocumentSignature.__table__, "after_create")
def _document_signature_append_only(target, connection, **kw):  # pragma: no cover - infra
    _install_append_only("document_signatures", connection)


@event.listens_for(DocumentSignaturePlacement.__table__, "after_create")
def _document_signature_placement_append_only(target, connection, **kw):  # pragma: no cover - infra
    _install_append_only("document_signature_placements", connection)


@event.listens_for(SignedDocumentSignaturePlacement.__table__, "after_create")
def _signed_document_signature_placement_append_only(target, connection, **kw):  # pragma: no cover - infra
    _install_append_only("signed_document_signature_placements", connection)


@event.listens_for(DocumentAccessEvent.__table__, "after_create")
def _document_access_event_append_only(target, connection, **kw):  # pragma: no cover - infra
    _install_append_only("document_access_events", connection)
