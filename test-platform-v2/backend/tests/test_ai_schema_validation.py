"""Golden AI Schema validation tests (v331-remediation-2 C2 / V30-124 + V30-123).

Manifest-driven corpus at ``tests/fixtures/aitde/v3/``:
- every ``valid`` golden file must validate against its output schema with
  ``Schema Valid Rate = 100%`` and satisfy the human-authored golden
  expectations (expected scope/ambiguity/intents, required contract rules,
  must-have scenarios);
- every ``invalid`` file must be rejected (schema guard or Oracle Guard).
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.modules.aitde.contract.schemas import ContractSnapshot
from app.modules.aitde.scenario.schemas import ScenarioDesignOutput
from app.modules.aitde.scope.ambiguity_schemas import (
    AmbiguityDetectionOutput,
    IntentDetectionOutput,
)
from app.modules.aitde.scope.schemas import ScopeAnalysisOutput

FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "aitde" / "v3"
MANIFEST = json.loads((FIXTURE_DIR / "manifest.json").read_text(encoding="utf-8"))

SCHEMA_MAP = {
    "ScopeAnalysisOutput": ScopeAnalysisOutput,
    "AmbiguityDetectionOutput": AmbiguityDetectionOutput,
    "IntentDetectionOutput": IntentDetectionOutput,
    "ContractSnapshot": ContractSnapshot,
    "ScenarioDesignOutput": ScenarioDesignOutput,
}

# V30-124 硬性要求：至少覆盖 5 类需求
def test_manifest_covers_five_requirement_classes():
    assert len(MANIFEST["requirement_classes"]) >= 5


def _golden(entry) -> dict:
    return json.loads((FIXTURE_DIR / entry["file"]).read_text(encoding="utf-8"))


@pytest.mark.parametrize("entry", MANIFEST["valid"], ids=lambda e: e["file"])
def test_golden_output_validates_and_matches_human_expectations(entry):
    """Schema Valid Rate = 100% + 人工 Golden 期望逐条成立。"""
    model = SCHEMA_MAP[entry["schema"]]
    parsed = model.model_validate(_golden(entry))

    golden = entry.get("golden", {})
    items = getattr(parsed, "items", [])
    if "expected_scope_keys" in golden:
        assert {i.scope_key for i in items} >= set(golden["expected_scope_keys"])
    if "expected_ambiguity_keys" in golden:
        assert {i.ambiguity_key for i in items} >= set(golden["expected_ambiguity_keys"])
    if "min_candidate_options" in golden:
        for i in items:
            assert len(i.candidate_options) >= golden["min_candidate_options"]
    if "expected_intent_keys" in golden:
        assert {i.intent_key for i in items} >= set(golden["expected_intent_keys"])
    if golden.get("required_outcomes_nonempty"):
        assert all(len(i.required_outcomes) > 0 for i in items)
    if "required_rule_keys" in golden:
        assert {r.rule_key for r in parsed.rules} >= set(golden["required_rule_keys"])
    if "must_have_scenarios" in golden:
        assert {s.scenario_key for s in items} >= set(golden["must_have_scenarios"])
    if golden.get("ai_inferred_oracles_must_not_be_required"):
        for s in items:
            for o in s.oracles:
                if o.source_type == "AI_INFERRED":
                    assert o.required is False  # AI Inferred Required Oracle = 0


@pytest.mark.parametrize(
    "entry",
    [e for e in MANIFEST["invalid"] if not e.get("guard")],
    ids=lambda e: e["file"],
)
def test_invalid_corpus_rejected(entry):
    payload = (FIXTURE_DIR / entry["file"]).read_text(encoding="utf-8")
    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        return  # malformed_json: json 层即拒绝，符合预期
    model = SCHEMA_MAP[entry["schema"]]
    with pytest.raises(ValidationError):
        model.model_validate(data)


def test_invalid_fake_fragment_rejected_by_source_ref_validator():
    """guard=source_ref：artifact 不存在由 validate_source_refs 拒绝（repo 层）。"""
    from tests.test_source_ref_validation import run_fake_fragment_scenario

    run_fake_fragment_scenario()


def test_invalid_oracle_required_rejected_by_oracle_guard():
    """guard=oracle_guard：AI_INFERRED + approve 必须保持 PROPOSED，不成为 required。"""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool

    from app.core.db import Base
    from app.modules.aitde import scenario as scenario_pkg  # noqa: F401
    from app.modules.aitde.common.enums import ReviewStatus
    from app.modules.aitde.scenario.models import TestOracle
    from app.modules.aitde.scenario.repository import review_oracle

    payload = json.loads(
        (FIXTURE_DIR / "invalid" / "oracle_required.json").read_text(encoding="utf-8")
    )
    oracle_spec = payload["items"][0]["oracles"][0]

    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    try:
        row = TestOracle(
            id=1, scenario_version_id=1, oracle_key=oracle_spec["oracle_key"],
            oracle_type=oracle_spec["oracle_type"], operator=oracle_spec["operator"],
            expected_value_json=json.dumps(oracle_spec["expected_value"]),
            source_type=oracle_spec["source_type"], required=True,
        )
        session.add(row)
        session.commit()
        reviewed = review_oracle(
            session, row, ReviewStatus.APPROVED.value, user_id=9, required=True
        )
        # Oracle Guard：AI_INFERRED 不能直接成为 approved REQUIRED oracle
        assert reviewed.review_status == ReviewStatus.PROPOSED.value
        assert reviewed.source_type == "AI_INFERRED"
    finally:
        session.close()
        engine.dispose()
