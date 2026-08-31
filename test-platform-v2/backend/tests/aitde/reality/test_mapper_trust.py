"""V3.9-R1 TRUST-007/TRUST-004 — mapper exposes trust + integrity to the frontend."""
from __future__ import annotations

from app.modules.aitde.execution.mapper import assertion_to_dict, evidence_to_dict
from app.modules.aitde.execution.models import AssertionResult, EvidenceArtifact


def test_assertion_to_dict_exposes_trust_fields():
    a = assertion_to_dict(
        AssertionResult(oracle_source_type="TEST_ORACLE", trust_status="TRUSTED", test_oracle_id=7)
    )
    assert a["trust_status"] == "TRUSTED"
    assert a["oracle_source_type"] == "TEST_ORACLE"
    assert a["test_oracle_id"] == 7


def test_evidence_to_dict_exposes_integrity():
    e = evidence_to_dict(EvidenceArtifact(integrity_status="VERIFIED", size_bytes=10, storage_uri="/x", content_hash="a" * 64))
    assert e["integrity_status"] == "VERIFIED"
    assert e["object_exists"] is True
    assert e["stored_verified"] is True
    assert e["hash_verified"] is True


def test_evidence_to_dict_no_verified_when_missing():
    e = evidence_to_dict(EvidenceArtifact(integrity_status="MISSING", size_bytes=0, storage_uri="", content_hash=""))
    assert e["object_exists"] is False
    assert e["stored_verified"] is False
    assert e["hash_verified"] is False
