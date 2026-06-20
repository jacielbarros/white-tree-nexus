"""Assinatura eletronica avancada (Lei 14.063/2020, nivel avancada).

- Canonicaliza respostas (JSON ordenado) → SHA-256 = selo de integridade.
- Persiste FormSignature (append-only) + DocumentVersion imutavel.
- Externo: gate de OTP por email (fail-closed).
- Politica: unica (padrao) ou dupla (contra-assinatura do atribuidor).
"""

import hashlib
import json
import logging
import secrets
import uuid as _uuid_mod
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING

from fastapi import HTTPException, Request, status
from sqlalchemy.orm import Session

from wtnapp.models.document_version_model import DocumentVersion
from wtnapp.models.form_assignment_event_model import FormAssignmentEvent
from wtnapp.models.form_assignment_model import FormAssignment
from wtnapp.models.form_signature_model import FormSignature, FormSignatureOTP
from wtnapp.models.form_signature_policy_model import FormSignaturePolicy
from wtnapp.services import notification_service
from wtnapp.services.audit_service import AuditService
from wtnapp.services.form_workflow_service import AssignmentEventType, _record_event
from wtnapp.settings import (
    AssignmentStatus,
    AuditOutcome,
    Classification,
    DocStatus,
    DocType,
    OTP_EXPIRY_MINUTES,
    OTP_MAX_ATTEMPTS,
    SignerRole,
)

if TYPE_CHECKING:
    from wtnapp.helpers.tenant_scope import OrgContext

logger = logging.getLogger(__name__)


def _canonicalize(answers: dict) -> str:
    """JSON canonico com chaves ordenadas e encoding UTF-8."""
    return json.dumps(answers, sort_keys=True, ensure_ascii=False)


def _sha256(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _hash_otp(otp: str) -> str:
    return hashlib.sha256(otp.encode()).hexdigest()


def _get_or_create_policy(db: Session, tenant_id) -> FormSignaturePolicy:
    policy = db.query(FormSignaturePolicy).filter(
        FormSignaturePolicy.tenant_id == tenant_id
    ).first()
    if policy is None:
        policy = FormSignaturePolicy(
            tenant_id=tenant_id,
            require_assigner_countersignature=False,
        )
        db.add(policy)
        db.flush()
    return policy


def _create_immutable_snapshot(
    db: Session,
    assignment: FormAssignment,
    content_hash: str,
    signer_meta: dict,
) -> DocumentVersion:
    """Cria DocumentVersion imutavel do preenchimento assinado."""
    next_number = (
        db.query(DocumentVersion)
        .filter(
            DocumentVersion.tenant_id == assignment.tenant_id,
            DocumentVersion.document_type == DocType.form_response,
            DocumentVersion.document_id == assignment.id,
        )
        .count()
        + 1
    )
    raw_uid = signer_meta.get("user_id")
    signer_user_id = _uuid_mod.UUID(raw_uid) if raw_uid else None
    version = DocumentVersion(
        tenant_id=assignment.tenant_id,
        document_type=DocType.form_response,
        document_id=assignment.id,
        identifier=f"SGSI-FORM-{str(assignment.id)[:8].upper()}",
        version_number=next_number,
        status=DocStatus.in_force,
        classification=Classification.confidencial,
        elaborated_by=signer_user_id,
        reviewed_by=signer_user_id,
        approved_by=signer_user_id,
        change_nature="Assinatura eletronica avancada",
        content_snapshot={
            "assignment_id": str(assignment.id),
            "answers": assignment.answers,
            "content_hash": content_hash,
            "signed_by": signer_meta,
        },
    )
    db.add(version)
    db.flush()
    return version


def _apply_policy_and_conclude(
    db: Session,
    assignment: FormAssignment,
    policy: FormSignaturePolicy,
    new_sig: FormSignature,
    actor_user_id,
    request: Request | None,
) -> None:
    """Apos assinar, decide se vai a 'completed' ou aguarda contra-assinatura."""
    if not policy.require_assigner_countersignature:
        assignment.status = AssignmentStatus.completed
        assignment.completed_at = datetime.now(timezone.utc)
        _record_event(db, assignment, AssignmentEventType.completed,
                      actor_user_id=actor_user_id)
        if request:
            AuditService.log_from_request(
                request=request, operation="COMPLETED",
                outcome=AuditOutcome.success, actor_user_id=actor_user_id,
                tenant_id=assignment.tenant_id, entity_type="form_assignment",
                entity_id=str(assignment.id),
            )
    else:
        existing = db.query(FormSignature).filter(
            FormSignature.assignment_id == assignment.id
        ).count()
        if existing >= 2:
            assignment.status = AssignmentStatus.completed
            assignment.completed_at = datetime.now(timezone.utc)
            _record_event(db, assignment, AssignmentEventType.completed,
                          actor_user_id=actor_user_id)


def sign_as_member(
    db: Session,
    assignment: FormAssignment,
    ctx: "OrgContext",
    request: Request,
) -> FormSignature:
    """Assina como membro autenticado (preenchedor ou atribuidor)."""
    if assignment.status != AssignmentStatus.submitted:
        raise HTTPException(status.HTTP_409_CONFLICT,
                            "Apenas atribuicoes enviadas podem ser assinadas.")

    user = ctx.principal.user
    # Determina o papel: preenchedor ou contra-assinante (atribuidor)
    existing_sigs = db.query(FormSignature).filter(
        FormSignature.assignment_id == assignment.id
    ).all()

    # O preenchedor assina primeiro
    already_filler_signed = any(s.signer_role == SignerRole.filler for s in existing_sigs)
    if not already_filler_signed:
        # Apenas o respondent_user_id pode assinar como filler
        if assignment.respondent_user_id != user.id:
            raise HTTPException(status.HTTP_403_FORBIDDEN,
                                "Apenas o preenchedor designado pode assinar.")
        signer_role = SignerRole.filler
    else:
        # Contra-assinatura pelo atribuidor
        if assignment.assigned_by != user.id:
            raise HTTPException(status.HTTP_403_FORBIDDEN,
                                "Apenas o atribuidor pode contra-assinar.")
        signer_role = SignerRole.assigner

    content = _canonicalize(assignment.answers)
    content_hash = _sha256(content)
    now = datetime.now(timezone.utc)

    assignment.content_hash = content_hash
    assignment.signed_at = now

    sig = FormSignature(
        tenant_id=assignment.tenant_id,
        assignment_id=assignment.id,
        signer_user_id=user.id,
        signer_role=signer_role,
        signer_name=user.full_name or str(user.id),
        signer_email=user.email,
        content_hash=content_hash,
        otp_verified=False,
        ip=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    db.add(sig)
    db.flush()

    # Versao imutavel apenas na primeira assinatura (filler)
    if signer_role == SignerRole.filler:
        version = _create_immutable_snapshot(
            db, assignment, content_hash,
            {"user_id": str(user.id), "name": sig.signer_name, "role": "filler"},
        )
        assignment.current_version_id = version.id

    assignment.status = AssignmentStatus.signed
    _record_event(db, assignment, AssignmentEventType.signed,
                  actor_user_id=user.id)

    policy = _get_or_create_policy(db, assignment.tenant_id)
    _apply_policy_and_conclude(db, assignment, policy, sig, user.id, request)

    db.commit()
    db.refresh(sig)

    AuditService.log_from_request(
        request=request, operation="SIGN",
        outcome=AuditOutcome.success, actor_user_id=user.id,
        tenant_id=assignment.tenant_id, entity_type="form_signature",
        entity_id=str(sig.id),
    )
    return sig


def request_otp(
    db: Session,
    assignment: FormAssignment,
    request: Request | None = None,
) -> None:
    """Gera e envia OTP por email para assinatura externa (gate fail-closed)."""
    if not assignment.respondent_email:
        raise HTTPException(status.HTTP_400_BAD_REQUEST,
                            "Atribuicao sem email de respondente externo.")

    otp_code = f"{secrets.randbelow(1_000_000):06d}"
    code_hash = _hash_otp(otp_code)
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=OTP_EXPIRY_MINUTES)

    # Substitui OTP anterior (1 por atribuicao)
    existing = db.query(FormSignatureOTP).filter(
        FormSignatureOTP.assignment_id == assignment.id
    ).first()
    if existing:
        existing.code_hash = code_hash
        existing.expires_at = expires_at
        existing.attempts = 0
    else:
        otp_row = FormSignatureOTP(
            assignment_id=assignment.id,
            code_hash=code_hash,
            expires_at=expires_at,
            attempts=0,
        )
        db.add(otp_row)

    _record_event(db, assignment, AssignmentEventType.otp_requested)
    db.commit()

    # Envio fail-closed: se falhar, o OTP nao pode ser verificado
    sent = False
    try:
        sent = notification_service.send_signature_otp_email(
            to_email=assignment.respondent_email,
            otp_code=otp_code,
            assignment_title=assignment.title,
        )
    except Exception:
        logger.error("Falha ao enviar OTP de assinatura (fail-closed)", exc_info=True)

    if not sent:
        # Falha no envio — invalida o OTP e falha
        db.query(FormSignatureOTP).filter(
            FormSignatureOTP.assignment_id == assignment.id
        ).delete()
        db.commit()
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Nao foi possivel enviar o codigo OTP. Tente novamente."
        )


def sign_as_external(
    db: Session,
    assignment: FormAssignment,
    otp: str,
    signer_name: str,
    ip: str | None = None,
    user_agent: str | None = None,
    request: Request | None = None,
) -> FormSignature:
    """Assina como respondente externo (gate OTP fail-closed)."""
    if assignment.status != AssignmentStatus.submitted:
        raise HTTPException(status.HTTP_409_CONFLICT,
                            "Apenas atribuicoes enviadas podem ser assinadas.")

    otp_row = db.query(FormSignatureOTP).filter(
        FormSignatureOTP.assignment_id == assignment.id
    ).first()
    if otp_row is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED,
                            "Codigo OTP nao solicitado ou expirado.")

    # Verifica expiracaoo e numero de tentativas
    now = datetime.now(timezone.utc)
    exp = otp_row.expires_at
    if exp.tzinfo is None:
        exp = exp.replace(tzinfo=timezone.utc)

    if now > exp or otp_row.attempts >= OTP_MAX_ATTEMPTS:
        db.delete(otp_row)
        db.commit()
        raise HTTPException(status.HTTP_401_UNAUTHORIZED,
                            "Codigo OTP expirado ou invalido.")

    code_hash = _hash_otp(otp)
    if code_hash != otp_row.code_hash:
        otp_row.attempts += 1
        db.commit()
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Codigo OTP incorreto.")

    # OTP valido — remove e prossegue com a assinatura
    db.delete(otp_row)

    content = _canonicalize(assignment.answers)
    content_hash = _sha256(content)

    assignment.content_hash = content_hash
    assignment.signed_at = now

    sig = FormSignature(
        tenant_id=assignment.tenant_id,
        assignment_id=assignment.id,
        signer_user_id=None,
        signer_role=SignerRole.filler,
        signer_name=signer_name,
        signer_email=assignment.respondent_email,
        content_hash=content_hash,
        otp_verified=True,
        ip=ip,
        user_agent=user_agent,
    )
    db.add(sig)
    db.flush()

    version = _create_immutable_snapshot(
        db, assignment, content_hash,
        {"name": signer_name, "email": assignment.respondent_email, "role": "filler",
         "otp_verified": True},
    )
    assignment.current_version_id = version.id
    assignment.status = AssignmentStatus.signed
    _record_event(db, assignment, AssignmentEventType.signed, actor_label=signer_name)

    policy = _get_or_create_policy(db, assignment.tenant_id)
    _apply_policy_and_conclude(db, assignment, policy, sig, None, request)

    db.commit()
    db.refresh(sig)
    return sig


def verify_integrity(db: Session, assignment: FormAssignment) -> dict:
    """Recomputa o selo SHA-256 sobre o snapshot imutavel e compara com o registrado."""
    if assignment.current_version_id is None:
        return {"valid": False, "content_hash": None, "signed_at": None}

    version = db.get(DocumentVersion, assignment.current_version_id)
    if version is None:
        return {"valid": False, "content_hash": None, "signed_at": None}

    snapshot_answers = version.content_snapshot.get("answers", {})
    recomputed = _sha256(_canonicalize(snapshot_answers))
    stored_hash = version.content_snapshot.get("content_hash", assignment.content_hash)

    sig = db.query(FormSignature).filter(
        FormSignature.assignment_id == assignment.id,
        FormSignature.signer_role == SignerRole.filler,
    ).first()

    return {
        "valid": recomputed == stored_hash,
        "content_hash": stored_hash,
        "signed_at": sig.signed_at if sig else None,
    }


def get_policy(db: Session, tenant_id) -> FormSignaturePolicy:
    return _get_or_create_policy(db, tenant_id)


def update_policy(
    db: Session,
    tenant_id,
    require_countersignature: bool,
) -> FormSignaturePolicy:
    policy = _get_or_create_policy(db, tenant_id)
    policy.require_assigner_countersignature = require_countersignature
    db.commit()
    db.refresh(policy)
    return policy
