"""Analise de Contexto (ISO 27001 4.1)."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum as SAEnum, ForeignKey, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from wtnapp.models.base import Base
from wtnapp.models.context_common import now_utc
from wtnapp.settings import DocStatus, IssueFramework, IssueNature, IssueOrigin, Level


class ContextAnalysis(Base):
    __tablename__ = "context_analyses"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("organizations.id"), unique=True, index=True, nullable=False
    )
    intended_outcomes: Mapped[str] = mapped_column(Text, default="", nullable=False)
    methodology: Mapped[str | None] = mapped_column(Text, nullable=True)
    draft_status: Mapped[DocStatus] = mapped_column(
        SAEnum(DocStatus, native_enum=False, length=20), default=DocStatus.draft, nullable=False
    )
    current_version_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, onupdate=now_utc)


class ContextIssue(Base):
    __tablename__ = "context_issues"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("organizations.id"), index=True, nullable=False
    )
    analysis_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("context_analyses.id", ondelete="CASCADE"), index=True, nullable=False
    )
    origin: Mapped[IssueOrigin] = mapped_column(SAEnum(IssueOrigin, native_enum=False, length=20), nullable=False)
    framework: Mapped[IssueFramework] = mapped_column(
        SAEnum(IssueFramework, native_enum=False, length=20), nullable=False
    )
    nature: Mapped[IssueNature] = mapped_column(
        SAEnum(IssueNature, native_enum=False, length=20), default=IssueNature.contextual, nullable=False
    )
    category: Mapped[str] = mapped_column(String(80), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    impact: Mapped[Level] = mapped_column(SAEnum(Level, native_enum=False, length=20), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, onupdate=now_utc)
