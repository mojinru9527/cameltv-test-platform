"""V3.9-R5 AI-003 — Golden Evaluation Runner + trusted release gate.

Verifies the golden dataset runner scores samples (must_include / must_not_include
/ expected) into a TRUSTED evaluation run, and that only a trusted ``run_suite``
score can PASS a release decision — external ``import_external_evaluation`` is
never trusted and insufficient samples are BLOCKED (plan §69/§70/§71).
"""
from __future__ import annotations

import json
from pathlib import Path

from app.modules.aitde.ai_closed_loop.service import PromptEvaluationService as PES

_GOLDEN = Path(__file__).resolve().parent.parent / "golden"


def _load_suite(name: str) -> list[dict]:
    with open(_GOLDEN / name / "golden.json", encoding="utf-8") as fh:
        data = json.load(fh)
    return data


def test_run_suite_scores_golden_and_trusted(db):
    samples = _load_suite("scope")
    out = PES.run_suite(db, "scope-golden", "deepseek-v4", samples)
    assert out["metrics"]["n"] == len(samples)
    assert out["metrics"]["correct"] == len(samples)
    assert out["metrics"]["accuracy"] == 1.0
    # A golden run is TRUSTED; only this path can drive a release gate.
    assert out["metrics"]["_trusted"] is True
    assert all(r["ok"] for r in out["results"])


def test_release_decision_blocked_without_trusted_run(db):
    decision = PES.release_decision(db, "never-run")
    assert decision["ok"] is False
    assert decision["status"] == "BLOCKED"
    assert decision["passed"] is False
    assert decision["reason"] == "INSUFFICIENT_SAMPLES"


def test_release_decision_passes_with_high_score(db):
    PES.run_suite(db, "triage-golden", "deepseek-v4", _load_suite("triage"))
    decision = PES.release_decision(db, "triage-golden")
    assert decision["ok"] is True
    assert decision["passed"] is True
    assert decision["status"] == "PASS"
    assert decision["score"] >= PES.REGRESSION_THRESHOLD


def test_import_external_evaluation_is_untrusted(db):
    # Even a perfect externally-reported score cannot PASS the golden gate.
    PES.import_external_evaluation(
        db,
        {
            "evaluation_suite": "scope-golden",
            "model_ref": "external",
            "metrics": {"accuracy": 1.0, "n": 99},
        },
    )
    decision = PES.release_decision(db, "scope-golden")
    assert decision["status"] == "BLOCKED"
    assert decision["passed"] is False


def test_compare_baseline_detects_regression(db):
    PES.run_suite(db, "scope-good", "deepseek-v4", _load_suite("scope"))
    bad = _load_suite("scope")
    for s in bad:
        s["candidate"] = {"decision": "PROPOSED", "risk_level": "P0"}
    PES.run_suite(db, "scope-bad", "deepseek-v4", bad)
    res = PES.compare_baseline(db, "scope-bad", "scope-good")
    assert res["ok"] is False
    assert res["status"] == "REGRESSED"
    assert res["current"] < res["baseline"]
