import uuid

import pytest

from wtnapp.models.gap_assessment_model import GapAssessment, GapAssessmentItem
from wtnapp.models.gap_evidence_model import GapEvidence, GapEvidenceEvent, GapEvidenceVersion
from wtnapp.services.gap_seed_service import adopt_seed
from wtnapp.settings import Classification, GapEvidenceStatus


def _seed_item(db, factory, gap_seed):
    org = factory.org("evidence-model", "Evidence Model")
    user = factory.user("model@evidence.com", full_name="Model User")
    adopt_seed(db, org.id, "2022.1")
    assessment = db.query(GapAssessment).filter_by(tenant_id=org.id).first()
    item = db.query(GapAssessmentItem).filter_by(assessment_id=assessment.id).first()
    return org, user, item


def _seed_evidence(db, org, user, item):
    evidence = GapEvidence(
        tenant_id=org.id,
        assessment_item_id=item.id,
        title="Policy",
        classification=Classification.uso_interno,
        status=GapEvidenceStatus.active,
        created_by=user.id,
    )
    db.add(evidence)
    db.flush()
    version = GapEvidenceVersion(
        tenant_id=org.id,
        evidence_id=evidence.id,
        version_number=1,
        classification=Classification.uso_interno,
        original_filename="policy.pdf",
        storage_key=f"{org.id}/{evidence.id}/{uuid.uuid4()}.fernet",
        content_hash="a" * 64,
        hash_algorithm="sha256",
        encrypted=True,
        encryption_scheme="fernet",
        size_bytes=12,
        mime_type="application/pdf",
        extension=".pdf",
        uploaded_by=user.id,
    )
    db.add(version)
    db.flush()
    evidence.current_version_id = version.id
    event = GapEvidenceEvent(
        tenant_id=org.id,
        evidence_id=evidence.id,
        version_id=version.id,
        assessment_item_id=item.id,
        event_type="uploaded",
        outcome="success",
        actor_id=user.id,
        details={"version_number": 1},
    )
    db.add(event)
    db.commit()
    return evidence, version, event


def test_gap_evidence_version_is_append_only(db, factory, gap_seed):
    org, user, item = _seed_item(db, factory, gap_seed)
    _, version, _ = _seed_evidence(db, org, user, item)

    version.original_filename = "changed.pdf"
    with pytest.raises(Exception, match="append-only"):
        db.commit()
    db.rollback()

    db.delete(version)
    with pytest.raises(Exception, match="append-only"):
        db.commit()


def test_gap_evidence_event_is_append_only(db, factory, gap_seed):
    org, user, item = _seed_item(db, factory, gap_seed)
    _, _, event = _seed_evidence(db, org, user, item)

    event.details = {"changed": True}
    with pytest.raises(Exception, match="append-only"):
        db.commit()
    db.rollback()

    db.delete(event)
    with pytest.raises(Exception, match="append-only"):
        db.commit()
