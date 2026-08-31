"""V3.9-R5 AI-002 — FailureTriageRuleEngine split + real evidence refs."""
from __future__ import annotations

from app.modules.aitde.ai_closed_loop.service import FailureEvidencePackBuilder, FailureTriageRuleEngine
from app.modules.aitde.ai_closed_loop import service
from app.modules.aitde.common.enums import FailureClassification, Outcome


def test_rule_engine_classifies_business_fail():
    assert FailureTriageRuleEngine.classify(Outcome.BUSINESS_FAIL.value) == FailureClassification.BUSINESS_LOGIC_SUSPECTED


def test_rule_engine_classifies_unknown():
    assert FailureTriageRuleEngine.classify("SOMETHING_ELSE") == FailureClassification.UNKNOWN


def test_rule_engine_confidence_and_checks_are_deterministic():
    cls = FailureTriageRuleEngine.classify(Outcome.ENV_FAIL.value)
    conf = FailureTriageRuleEngine.confidence(cls)
    checks = FailureTriageRuleEngine.suggested_checks(cls)
    assert 0 <= conf <= 1
    assert checks


def test_triage_uses_real_evidence_refs(db, run_graph):
    # Store a real evidence artifact for the run.
    from app.modules.aitde.data.run_data_integration import store_data_evidence

    run = run_graph["run"]
    artifact = store_data_evidence(
        db, run.id, "RESPONSE", project_id=run_graph["project_id"], data=b'{"status":200}'
    )
    run.outcome = Outcome.BUSINESS_FAIL.value
    db.commit()

    hypothesis = service.FailureTriageAgent.triage(db, run.id)
    refs = hypothesis["evidence_refs"]
    # Real evidence refs must include the stored artifact's id (not just run metadata).
    assert any(isinstance(r, dict) and r.get("id") == artifact.id for r in refs)


def test_evidence_pack_includes_evidence_ids(db, run_graph):
    run = run_graph["run"]
    from app.modules.aitde.data.run_data_integration import store_data_evidence

    artifact = store_data_evidence(
        db, run.id, "REQUEST", project_id=run_graph["project_id"], data=b'{"path":"/x"}'
    )
    pack = FailureEvidencePackBuilder.build(db, run.id)
    assert any(e["id"] == artifact.id for e in pack["evidence"])
