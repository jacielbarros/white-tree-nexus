"""Controlled printable template selection, validation and versioning."""

from __future__ import annotations

import hashlib
import json
import re
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from wtnapp.data.print_template_seed import default_templates
from wtnapp.helpers.tenant_scope import OrgContext
from wtnapp.models.print_document_model import PrintTemplate, PrintTemplateVersion
from wtnapp.schemas.print_document_schema import PrintTemplateCreate, PrintTemplateVersionCreate
from wtnapp.settings import (
    Classification,
    PrintTemplateScope,
    PrintTemplateStatus,
    PrintableDocumentType,
)

_VARIABLE_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]{0,80}$")


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_canonical(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def signature_appearance_policy(version: PrintTemplateVersion) -> dict[str, Any]:
    """Resolve the visual signature policy embedded in the template version."""
    policy = dict((version.layout_schema or {}).get("signature_appearance") or {})
    return {
        "default_page": policy.get("default_page", "last"),
        "default_anchor": policy.get("default_anchor", "bottom_right"),
        "default_margin_points": float(policy.get("default_margin_points", 36)),
        "default_width_points": float(policy.get("default_width_points", 180)),
        "default_height_points": float(policy.get("default_height_points", 54)),
        "min_width_points": float(policy.get("min_width_points", 96)),
        "min_height_points": float(policy.get("min_height_points", 32)),
        "max_width_points": float(policy.get("max_width_points", 260)),
        "max_height_points": float(policy.get("max_height_points", 96)),
        "blocked_areas": list(policy.get("blocked_areas") or []),
    }


def signature_policy_hash(version: PrintTemplateVersion) -> str:
    return sha256_canonical(signature_appearance_policy(version))


def template_content_hash(
    *,
    layout_schema: dict[str, Any],
    allowed_variables: dict[str, Any],
    required_sections: list[str],
    renderer: str = "reportlab_v1",
) -> str:
    return sha256_canonical(
        {
            "renderer": renderer,
            "layout_schema": layout_schema,
            "allowed_variables": allowed_variables,
            "required_sections": required_sections,
        }
    )


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _next_version_number(db: Session, template_id: uuid.UUID) -> int:
    return (
        db.query(func.max(PrintTemplateVersion.version_number))
        .filter(PrintTemplateVersion.template_id == template_id)
        .scalar()
        or 0
    ) + 1


def _normalize_variable_names(allowed_variables: dict[str, Any]) -> tuple[list[str], list[str]]:
    if isinstance(allowed_variables, list):
        required = allowed_variables
        optional = []
    else:
        required = allowed_variables.get("required", [])
        optional = allowed_variables.get("optional", [])
    if not isinstance(required, list) or not isinstance(optional, list):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Variaveis do template invalidas.")
    required_names = [str(v) for v in required]
    optional_names = [str(v) for v in optional]
    for name in [*required_names, *optional_names]:
        if not _VARIABLE_RE.match(name):
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                {"detail": "Variavel de template invalida.", "missing_variables": [name]},
            )
    return required_names, optional_names


def _validate_layout(layout_schema: dict[str, Any], required_sections: list[str]) -> None:
    if not isinstance(layout_schema, dict):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Layout de template invalido.")
    sections = layout_schema.get("sections", [])
    if sections and not isinstance(sections, list):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Secoes do template invalidas.")
    section_keys = {str(s.get("key")) for s in sections if isinstance(s, dict) and s.get("key")}
    missing_sections = [s for s in required_sections if s not in section_keys]
    if missing_sections:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            {"detail": "Template sem secoes obrigatorias.", "missing_sections": missing_sections},
        )


def _new_version(
    *,
    db: Session,
    template: PrintTemplate,
    layout_schema: dict[str, Any],
    allowed_variables: dict[str, Any],
    required_sections: list[str],
    created_by: uuid.UUID | None,
) -> PrintTemplateVersion:
    _normalize_variable_names(allowed_variables)
    _validate_layout(layout_schema, required_sections)
    version = PrintTemplateVersion(
        tenant_id=template.tenant_id,
        template_id=template.id,
        version_number=_next_version_number(db, template.id),
        renderer="reportlab_v1",
        layout_schema=layout_schema,
        allowed_variables=allowed_variables,
        required_sections=required_sections,
        content_hash=template_content_hash(
            layout_schema=layout_schema,
            allowed_variables=allowed_variables,
            required_sections=required_sections,
        ),
        created_by=created_by,
    )
    db.add(version)
    db.flush()
    return version


def ensure_system_templates(db: Session) -> None:
    """Create/update default system templates idempotently."""
    changed = False
    for definition in default_templates():
        document_type = PrintableDocumentType(definition["document_type"])
        template = (
            db.query(PrintTemplate)
            .filter(
                PrintTemplate.tenant_id.is_(None),
                PrintTemplate.scope == PrintTemplateScope.system,
                PrintTemplate.document_type == document_type,
                PrintTemplate.name == definition["name"],
            )
            .first()
        )
        if template is None:
            template = PrintTemplate(
                tenant_id=None,
                scope=PrintTemplateScope.system,
                document_type=document_type,
                name=definition["name"],
                description=definition.get("description"),
                status=PrintTemplateStatus.active,
                default_classification=Classification(definition["default_classification"]),
                created_by=None,
            )
            db.add(template)
            db.flush()
            changed = True

        desired_hash = template_content_hash(
            layout_schema=definition["layout_schema"],
            allowed_variables=definition["allowed_variables"],
            required_sections=definition["required_sections"],
        )
        version = (
            db.query(PrintTemplateVersion)
            .filter(
                PrintTemplateVersion.template_id == template.id,
                PrintTemplateVersion.content_hash == desired_hash,
            )
            .first()
        )
        if version is None:
            version = _new_version(
                db=db,
                template=template,
                layout_schema=definition["layout_schema"],
                allowed_variables=definition["allowed_variables"],
                required_sections=definition["required_sections"],
                created_by=None,
            )
            changed = True
        if template.current_version_id != version.id or template.status != PrintTemplateStatus.active:
            template.current_version_id = version.id
            template.status = PrintTemplateStatus.active
            changed = True
    if changed:
        db.commit()


def list_templates(
    db: Session,
    ctx: OrgContext,
    document_type: PrintableDocumentType | None = None,
) -> list[PrintTemplate]:
    ensure_system_templates(db)
    query = db.query(PrintTemplate).filter(
        or_(PrintTemplate.tenant_id == ctx.tenant_id, PrintTemplate.tenant_id.is_(None))
    )
    if document_type is not None:
        query = query.filter(PrintTemplate.document_type == document_type)
    return query.order_by(PrintTemplate.document_type, PrintTemplate.scope.desc(), PrintTemplate.name).all()


def _visible_template_query(db: Session, ctx: OrgContext):
    return db.query(PrintTemplate).filter(
        or_(PrintTemplate.tenant_id == ctx.tenant_id, PrintTemplate.tenant_id.is_(None))
    )


def get_visible_template(db: Session, ctx: OrgContext, template_id: uuid.UUID) -> PrintTemplate:
    template = _visible_template_query(db, ctx).filter(PrintTemplate.id == template_id).first()
    if template is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Recurso nao encontrado.")
    return template


def get_visible_template_version(db: Session, ctx: OrgContext, version_id: uuid.UUID) -> PrintTemplateVersion:
    version = db.get(PrintTemplateVersion, version_id)
    if version is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Recurso nao encontrado.")
    template = get_visible_template(db, ctx, version.template_id)
    if template.scope == PrintTemplateScope.tenant and template.tenant_id != ctx.tenant_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Recurso nao encontrado.")
    return version


def resolve_active_template_version(
    db: Session,
    ctx: OrgContext,
    document_type: PrintableDocumentType,
    template_version_id: uuid.UUID | None = None,
) -> PrintTemplateVersion:
    ensure_system_templates(db)
    if template_version_id is not None:
        version = get_visible_template_version(db, ctx, template_version_id)
        template = get_visible_template(db, ctx, version.template_id)
        if template.document_type != document_type:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Template incompativel com o documento.")
        return version

    template = (
        db.query(PrintTemplate)
        .filter(
            PrintTemplate.tenant_id == ctx.tenant_id,
            PrintTemplate.document_type == document_type,
            PrintTemplate.status == PrintTemplateStatus.active,
            PrintTemplate.current_version_id.isnot(None),
        )
        .order_by(PrintTemplate.updated_at.desc())
        .first()
    )
    if template is None:
        template = (
            db.query(PrintTemplate)
            .filter(
                PrintTemplate.tenant_id.is_(None),
                PrintTemplate.document_type == document_type,
                PrintTemplate.status == PrintTemplateStatus.active,
                PrintTemplate.current_version_id.isnot(None),
            )
            .order_by(PrintTemplate.name)
            .first()
        )
    if template is None or template.current_version_id is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Template ativo nao encontrado.")
    version = db.get(PrintTemplateVersion, template.current_version_id)
    if version is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Versao ativa do template nao encontrada.")
    return version


def resolve_variables(
    version: PrintTemplateVersion,
    values: dict[str, Any],
) -> tuple[dict[str, Any], list[str]]:
    required, optional = _normalize_variable_names(version.allowed_variables or {})
    missing_required = [name for name in required if values.get(name) in (None, "")]
    if missing_required:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            {
                "detail": "Dados obrigatorios ausentes para gerar o documento.",
                "missing_variables": missing_required,
            },
        )
    rendered: dict[str, Any] = dict(values)
    warnings: list[str] = []
    for name in optional:
        if rendered.get(name) in (None, ""):
            rendered[name] = "Nao informado"
            warnings.append(f"Variavel opcional ausente: {name}")
    return rendered, warnings


def create_tenant_template(db: Session, ctx: OrgContext, payload: PrintTemplateCreate) -> PrintTemplate:
    ensure_system_templates(db)
    exists = (
        db.query(PrintTemplate)
        .filter(
            PrintTemplate.tenant_id == ctx.tenant_id,
            PrintTemplate.document_type == payload.document_type,
            PrintTemplate.name == payload.name,
        )
        .first()
    )
    if exists is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Template ja existe para esta organizacao.")
    template = PrintTemplate(
        tenant_id=ctx.tenant_id,
        scope=PrintTemplateScope.tenant,
        document_type=payload.document_type,
        name=payload.name.strip(),
        description=payload.description.strip() if payload.description else None,
        status=PrintTemplateStatus.draft,
        default_classification=payload.default_classification,
        created_by=ctx.principal.user.id,
    )
    db.add(template)
    db.commit()
    db.refresh(template)
    return template


def create_template_version(
    db: Session,
    ctx: OrgContext,
    template_id: uuid.UUID,
    payload: PrintTemplateVersionCreate,
) -> PrintTemplateVersion:
    template = get_visible_template(db, ctx, template_id)
    if template.scope != PrintTemplateScope.tenant or template.tenant_id != ctx.tenant_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Template do sistema nao pode ser alterado.")
    version = _new_version(
        db=db,
        template=template,
        layout_schema=payload.layout_schema,
        allowed_variables=payload.allowed_variables,
        required_sections=payload.required_sections,
        created_by=ctx.principal.user.id,
    )
    if template.current_version_id is None:
        template.current_version_id = version.id
        template.status = PrintTemplateStatus.active
    template.updated_at = _now()
    db.commit()
    db.refresh(version)
    return version


def activate_template_version(
    db: Session,
    ctx: OrgContext,
    template_id: uuid.UUID,
    version_id: uuid.UUID,
) -> PrintTemplate:
    template = get_visible_template(db, ctx, template_id)
    if template.scope != PrintTemplateScope.tenant or template.tenant_id != ctx.tenant_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Template do sistema nao pode ser alterado.")
    version = db.get(PrintTemplateVersion, version_id)
    if version is None or version.template_id != template.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Recurso nao encontrado.")
    template.current_version_id = version.id
    template.status = PrintTemplateStatus.active
    template.updated_at = _now()
    db.commit()
    db.refresh(template)
    return template


def version_response(db: Session, version: PrintTemplateVersion) -> dict[str, Any]:
    template = db.get(PrintTemplate, version.template_id)
    return {
        "id": version.id,
        "template_id": version.template_id,
        "version_number": version.version_number,
        "renderer": version.renderer,
        "layout_schema": version.layout_schema,
        "allowed_variables": version.allowed_variables,
        "required_sections": version.required_sections,
        "content_hash": version.content_hash,
        "is_current": bool(template and template.current_version_id == version.id),
        "created_at": version.created_at,
    }
