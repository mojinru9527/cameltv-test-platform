"""AITDE V3.8 AI QA Closed Loop service layer (V38).

Failure evidence pack → triage hypothesis → healing policy/apply → flaky detector →
strategy performance → scenario gap → suggestion inbox → human feedback → model
evaluation → auto-retry policy. Deterministic guards enforce the V3.8 invariants:
AI never owns a formal Outcome, healing never mutates Oracle/Contract/Expected,
BusinessFail is never auto-flaky, gap is proposal-only, and policy/approval always
take precedence over an AI recommendation.
"""

from __future__ import annotations

import contextlib
import hashlib
import json
from datetime import datetime
from typing import Any, Callable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.aitde.ai_closed_loop import repository as repo
from app.modules.aitde.ai_closed_loop.models import (
    AiSuggestion,
    FailureHypothesis,
    FlakyCluster,
    FlakySignal,
    HumanFeedback,
    ModelEvaluationRun,
    ScenarioGapCandidate,
    StrategyPerformance,
)
from app.modules.aitde.browser.models import HealingProposal
from app.modules.aitde.command.models import CommandPlan, CommandPlanVersion
from app.modules.aitde.common.enums import (
    AutoRetryDecision,
    CommandPlanStatus,
    FailureClassification,
    FailureHypothesisStatus,
    FeedbackType,
    FlakyClassification,
    FlakySignalType,
    GapCandidateStatus,
    HealingPolicyDecision,
    HealingProposalStatus,
    ModelEvaluationStatus,
    Outcome,
    RiskLevel,
    ScenarioGapType,
    SuggestionStatus,
    SuggestionType,
)
from app.modules.aitde.execution.models import ExecutionRun
from app.modules.aitde.scenario.models import TestScenarioVersion


# ────────────────────────────────────────────────────────────────────────────
# helpers
# ────────────────────────────────────────────────────────────────────────────

def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _dumps(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _loads(raw: str, default: Any) -> Any:
    try:
        return json.loads(raw)
    except (TypeError, ValueError):
        return default


def _snapshot_summary(raw: str | None) -> dict | None:
    """Return a lean summary of an ExecutionStep snapshot (never raw private data).

    The step snapshots are already sanitized by the driver; we additionally cap
    long string values so the model prompt stays compact. The outer ``_sanitize``
    drops any residual secret/PII keys."""
    raw = raw or ""
    if not raw:
        return None
    data = _loads(raw, None)
    if data is None:
        return {"text": str(raw)[:200]}
    if isinstance(data, dict):
        out: dict[str, Any] = {}
        for key, value in data.items():
            if isinstance(value, str) and len(value) > 300:
                out[key] = value[:300]
            else:
                out[key] = value
        return out
    return {"value": str(data)[:300]}


# Oracle / contract / expected fields that HealingPolicy must never let through &
# that FailureEvidencePack must never re-emit as a model hint.
_MUTATION_KEYS = {
    "oracle",
    "oracle_id",
    "contract",
    "contract_rule",
    "contract_version_id",
    "expected",
    "required",
    "expected_value",
    "target_value",
}

_SECRET_KEYS = {
    "password",
    "token",
    "secret",
    "api_key",
    "apikey",
    "private_key",
    "authorization",
    "cookie",
    "cookie_value",
    "session_id",
    "access_token",
    "refresh_token",
}


def _schema_diff_present(before: Any, after: Any) -> bool:
    """Return True if any diff touches a field that healing must be immutable for."""
    if isinstance(before, dict) and isinstance(after, dict):
        keys = set(before) | set(after)
        for key in keys:
            if key in _MUTATION_KEYS:
                return True
            if _schema_diff_present(before.get(key), after.get(key)):
                return True
    elif isinstance(before, list) and isinstance(after, list):
        for b_item, a_item in zip(before, after):
            if _schema_diff_present(b_item, a_item):
                return True
    return False


def _sanitize(value: Any) -> Any:
    """Recursively drop secret/PII fields before a value enters a model prompt."""
    if isinstance(value, dict):
        result: dict[str, Any] = {}
        for key, item in value.items():
            if key.lower() in _SECRET_KEYS:
                continue
            cleaned = _sanitize(item)
            if cleaned is not None and cleaned != "":
                result[key] = cleaned
        return result
    if isinstance(value, list):
        return [_sanitize(item) for item in value]
    return value


# ────────────────────────────────────────────────────────────────────────────
# FailureEvidencePackBuilder — V38-001
# ────────────────────────────────────────────────────────────────────────────


class FailureEvidencePackBuilder:
    """Build a minimal, already-sanitized context pack from a run's evidence.

    V3.9-R5 (AI-001): the pack is now a real proof summary (ordered step timeline,
    required-oracle pass/fail summary, sanitized request/response excerpts, evidence
    artifact integrity, environment snapshot, fixture/cleanup state) rather than
    bare run metadata. Secrets / PII never enter the model: risky keys are dropped
    before the pack is returned, and no formal Outcome change is ever produced.
    """

    @staticmethod
    def build(db: Session, run_id: int) -> dict:
        from app.modules.aitde.execution import repository as exec_repo
        from app.modules.aitde.execution.models import EnvironmentSnapshot

        run = db.get(ExecutionRun, run_id)
        if run is None:
            raise ValueError(f"run {run_id} not found")
        project_id = run.project_id

        # Ordered step timeline with sanitized request/response summaries.
        step_timeline = []
        for s in exec_repo.list_steps(db, run_id, project_id):
            step_timeline.append(
                {
                    "sequence": s.sequence,
                    "step_key": s.step_key,
                    "step_type": s.step_type,
                    "status": s.status,
                    "error_type": s.error_type,
                    "error_message": _sanitize(s.error_message),
                    "input": _snapshot_summary(s.input_snapshot_json),
                    "output": _snapshot_summary(s.output_snapshot_json),
                    "evidence_refs": _loads(s.evidence_refs_json, []),
                }
            )

        # Required + evaluated oracle summary (pass/fail/not_evaluated).
        oracle_summary = {"defined": 0, "pass": 0, "fail": 0, "not_evaluated": 0}
        assertions = []
        for a in exec_repo.list_assertions(db, run_id, project_id):
            oracle_summary["defined"] += 1
            if a.result == "PASS":
                oracle_summary["pass"] += 1
            elif a.result == "FAIL":
                oracle_summary["fail"] += 1
            elif a.result == "NOT_EVALUATED":
                oracle_summary["not_evaluated"] += 1
            assertions.append(
                {
                    "test_oracle_id": a.test_oracle_id,
                    "oracle_source_type": a.oracle_source_type,
                    "trust_status": a.trust_status,
                    "result": a.result,
                    "reason_code": a.reason_code,
                    "evidence_refs": _loads(a.evidence_refs_json, []),
                }
            )

        # Evidence artifact physical integrity (never raw bytes).
        evidence = [
            {
                "id": e.id,
                "evidence_type": e.evidence_type,
                "storage_provider": e.storage_provider,
                "content_hash_len": len(e.content_hash or ""),
                "size_bytes": e.size_bytes,
                "sanitization_status": e.sanitization_status,
                "integrity_status": e.integrity_status,
            }
            for e in exec_repo.list_evidence(db, run_id, project_id)
        ]

        env_snapshot = None
        if run.environment_snapshot_id:
            env = db.get(EnvironmentSnapshot, run.environment_snapshot_id)
            if env:
                env_snapshot = {
                    "build_label": env.build_label,
                    "openapi_hash": env.openapi_hash,
                    "db_schema_version": env.db_schema_version,
                    "fingerprint_hash": env.fingerprint_hash,
                }

        # Fixture / cleanup state (best-effort; absent when no V3.2 data ran).
        from app.modules.aitde.data.models import DataFixture

        fixture_state = None
        with contextlib.suppress(Exception):
            fixture = (
                db.query(DataFixture)
                .filter(DataFixture.run_id == run_id)
                .order_by(DataFixture.id.desc())
                .first()
            )
            if fixture:
                fixture_state = {
                    "id": fixture.id,
                    "strategy": fixture.strategy,
                    "status": fixture.status,
                    "namespace": fixture.namespace,
                    "cleanup_status": fixture.cleanup_status,
                }

        pack = {
            "run_id": run.id,
            "project_id": run.project_id,
            "mission_id": run.mission_id,
            "scenario_id": run.scenario_id,
            "scenario_version_id": run.scenario_version_id,
            "contract_version_id": run.contract_version_id,
            "environment_id": run.environment_id,
            "environment_snapshot": env_snapshot,
            "fixture_state": fixture_state,
            "outcome": run.outcome,
            "runtime_status": run.runtime_status,
            "duration_ms": run.duration_ms,
            "step_timeline": step_timeline,
            "oracle_summary": oracle_summary,
            "assertions": assertions,
            "evidence": evidence,
            "sanitized": True,
        }
        # Sanitize any caller-supplied context; drop secret/PII keys.
        return _sanitize(pack)


# ────────────────────────────────────────────────────────────────────────────
# FailureTriageAgent — V38-002 / HypothesisReviewService — V38-003
# ────────────────────────────────────────────────────────────────────────────


class FailureTriageRuleEngine:
    """V3.9-R5 (AI-002): deterministic rule-based triage fallback.

    Classifies an Outcome into a FailureClassification (+ confidence + suggested
    checks) without any model. Batch 207: triage is rule-based by design; the
    LLM-backed agent slot is reserved (see Leader C-condition) and never
    pretended to run.
    """

    @staticmethod
    def classify(outcome: str | None) -> FailureClassification:
        mapping: dict[str, FailureClassification] = {
            Outcome.BUSINESS_FAIL.value: FailureClassification.BUSINESS_LOGIC_SUSPECTED,
            Outcome.AUTOMATION_FAIL.value: FailureClassification.AUTOMATION_ISSUE_SUSPECTED,
            Outcome.DATA_FAIL.value: FailureClassification.DATA_ISSUE_SUSPECTED,
            Outcome.ENV_FAIL.value: FailureClassification.ENV_ISSUE_SUSPECTED,
            Outcome.ASSERTION_ERROR.value: FailureClassification.AUTOMATION_ISSUE_SUSPECTED,
            Outcome.BLOCKED.value: FailureClassification.ENV_ISSUE_SUSPECTED,
            Outcome.INCONCLUSIVE.value: FailureClassification.UNKNOWN,
        }
        return mapping.get((outcome or "").upper(), FailureClassification.UNKNOWN)

    @staticmethod
    def confidence(classification: FailureClassification) -> float:
        return {
            FailureClassification.BUSINESS_LOGIC_SUSPECTED: 0.87,
            FailureClassification.AUTOMATION_ISSUE_SUSPECTED: 0.78,
            FailureClassification.DATA_ISSUE_SUSPECTED: 0.74,
            FailureClassification.ENV_ISSUE_SUSPECTED: 0.7,
            FailureClassification.FLAKY_SUSPECTED: 0.65,
            FailureClassification.UNKNOWN: 0.4,
        }.get(classification, 0.4)

    @staticmethod
    def suggested_checks(classification: FailureClassification) -> list[str]:
        return {
            FailureClassification.BUSINESS_LOGIC_SUSPECTED: [
                "verify expected value against contract",
                "confirm the assertion is a required oracle",
            ],
            FailureClassification.AUTOMATION_ISSUE_SUSPECTED: [
                "inspect locator / wait strategy",
                "re-check browser synchronization",
            ],
            FailureClassification.DATA_ISSUE_SUSPECTED: [
                "confirm fixture freshness",
                "validate preconditions",
            ],
            FailureClassification.ENV_ISSUE_SUSPECTED: [
                "confirm environment / network reachability",
            ],
            FailureClassification.FLAKY_SUSPECTED: [
                "re-run to confirm transient",
                "inspect sample set for intermittent error",
            ],
            FailureClassification.UNKNOWN: ["request manual review"],
        }.get(classification, ["request manual review"])


class FailureTriageAgent:
    """Produce a structured FailureHypothesis for a run.

    The agent never writes the formal ``Outcome``: it only classifies into a
    hypothesis category + confidence + suggested checks. The guard is enforced by
    only ever persisting ``failure_hypotheses`` rows (never touching execution_runs).
    """

    @staticmethod
    def triage(
        db: Session,
        run_id: int,
        context: dict | None = None,
        model_ref: str | None = None,
        prompt_version: str | None = None,
    ) -> dict:
        run = db.get(ExecutionRun, run_id)
        if run is None:
            raise ValueError(f"run {run_id} not found")

        # Outcome is read, never written.
        classification = FailureTriageAgent._classify(run.outcome)
        pack = FailureEvidencePackBuilder.build(db, run_id)
        # V3.9-R5 (AI-001/002): evidence refs are real EvidenceArtifact ids from the
        # pack, never the whole run — so a hypothesis is traceable to actual proof.
        evidence_refs = [{"type": "evidence", "id": e["id"]} for e in pack.get("evidence", [])]
        if not evidence_refs:
            evidence_refs = [{"type": "run", "id": run.id}]
        summary = (
            f"run {run.id} outcome {run.outcome} classified as {classification.value} "
            f"over sanitized evidence {len(pack)} fields"
        )
        row = repo.create_failure_hypothesis(
            db,
            {
                "run_id": run.id,
                "hypothesis_type": classification.value,
                "summary": summary,
                "confidence": FailureTriageAgent._confidence(classification),
                "evidence_refs_json": _dumps(evidence_refs),
                "suggested_checks_json": _dumps(
                    FailureTriageAgent._suggested_checks(classification)
                ),
                "model_ref": model_ref,
                "prompt_version": prompt_version,
                "status": FailureHypothesisStatus.GENERATED.value,
            },
        )
        db.flush()
        return FailureTriageAgent._hypothesis_dict(row, run)

    @staticmethod
    def auto_triage_if_needed(db: Session, run_id: int) -> dict | None:
        """Best-effort, idempotent auto-triage for a finished failing run.

        Batch 207 wiring: called from run-finish hooks. Only failing outcomes
        are triaged; a run that already has a hypothesis is skipped; this
        hook never mutates the run's Outcome.
        """
        run = db.get(ExecutionRun, run_id)
        if run is None or not run.outcome:
            return None
        failing = {
            Outcome.BUSINESS_FAIL.value,
            Outcome.AUTOMATION_FAIL.value,
            Outcome.DATA_FAIL.value,
            Outcome.ENV_FAIL.value,
            Outcome.ASSERTION_ERROR.value,
            Outcome.BLOCKED.value,
        }
        if (run.outcome or "").upper() not in failing:
            return None
        if repo.list_hypotheses_for_run(db, run_id):
            return None
        return FailureTriageAgent.triage(db, run_id)

    @staticmethod
    def list_hypotheses(db: Session, run_id: int) -> list[dict]:
        return [
            FailureTriageAgent._hypothesis_dict(h, None)
            for h in repo.list_hypotheses_for_run(db, run_id)
        ]

    @staticmethod
    def _classify(outcome: str | None) -> FailureClassification:
        # V3.9-R5 (AI-002): rule-engine fallback (no model).
        return FailureTriageRuleEngine.classify(outcome)

    @staticmethod
    def _confidence(classification: FailureClassification) -> float:
        return FailureTriageRuleEngine.confidence(classification)

    @staticmethod
    def _suggested_checks(classification: FailureClassification) -> list[str]:
        return FailureTriageRuleEngine.suggested_checks(classification)

    @staticmethod
    def _hypothesis_dict(h: FailureHypothesis, run: ExecutionRun | None) -> dict:
        return {
            "id": h.id,
            "run_id": h.run_id,
            "hypothesis_type": h.hypothesis_type,
            "classification": h.hypothesis_type,
            "summary": h.summary,
            "confidence": h.confidence,
            "evidence_refs": _loads(h.evidence_refs_json, []),
            "suggested_checks": _loads(h.suggested_checks_json, []),
            "model_ref": h.model_ref,
            "prompt_version": h.prompt_version,
            "status": h.status,
            "reviewed_by": h.reviewed_by,
            "created_at": h.created_at.isoformat() if h.created_at else None,
            # Outcome shown only for reference; never mutable by AI.
            "outcome": run.outcome if run else None,
        }


class HypothesisReviewService:
    """Confirm / reject a hypothesis with an audit record (V38-003)."""

    _LEGAL = {
        FailureHypothesisStatus.REVIEWED.value,
        FailureHypothesisStatus.CONFIRMED.value,
        FailureHypothesisStatus.REJECTED.value,
    }

    @staticmethod
    def review(
        db: Session,
        hypothesis_id: int,
        status: str,
        reviewed_by: int | None,
        reason: str | None = None,
    ) -> dict:
        row = repo.get_failure_hypothesis(db, hypothesis_id)
        if row is None:
            raise ValueError(f"hypothesis {hypothesis_id} not found")
        if (status or "").upper() not in HypothesisReviewService._LEGAL:
            raise ValueError(f"illegal hypothesis status transition: {status}")
        row.status = (status or "").upper()
        row.reviewed_by = reviewed_by
        db.flush()
        if row.status == FailureHypothesisStatus.CONFIRMED.value:
            # Batch 207: a confirmed hypothesis feeds the tester inbox as a
            # TRIAGE suggestion (producer for the previously-empty inbox).
            _run = db.get(ExecutionRun, row.run_id)
            try:
                with db.begin_nested():
                    SuggestionInboxService.create(
                        db,
                        project_id=_run.project_id if _run else 0,
                        suggestion_type=SuggestionType.TRIAGE.value,
                        target_type="execution_run",
                        target_id=row.run_id,
                        payload={
                            "hypothesis_id": row.id,
                            "hypothesis_type": row.hypothesis_type,
                            "summary": row.summary,
                        },
                        confidence=row.confidence or 0.5,
                        mission_id=_run.mission_id if _run else None,
                    )
            except Exception:  # noqa: BLE001 - inbox must not break review
                pass
            db.flush()
        return FailureTriageAgent._hypothesis_dict(row, None)


# ────────────────────────────────────────────────────────────────────────────
# HealingPolicy — V38-004 / ApprovedHealingApply — V38-005
# ────────────────────────────────────────────────────────────────────────────


class HealingPolicy:
    """Action-only healing guard. Oracle/Contract/Expected mutation is rejected."""

    @staticmethod
    def decide(before: dict, after: dict) -> dict:
        touches_mutation = _schema_diff_present(before, after)
        if touches_mutation:
            return {
                "decision": HealingPolicyDecision.REJECT.value,
                "reason": (
                    "healing diff touches Oracle/Contract/Expected — "
                    "Frozen Contract 不可直接修改"
                ),
                "allowed": False,
            }
        return {
            "decision": HealingPolicyDecision.ALLOW.value,
            "reason": "action-only diff (locator/wait/navigation/sync)",
            "allowed": True,
        }


class ApprovedHealingApply:
    """Apply an approved Action-only proposal, creating a new CommandPlanVersion.

    Old plan/evidence are retained; the new version carries the healed action IR.
    A non-APPROVED or rejected-mutation proposal is never applied.
    """

    @staticmethod
    def apply(
        db: Session,
        proposal_id: int,
        approved_by: int | None = None,
        note: str | None = None,
    ) -> dict:
        proposal = db.get(HealingProposal, proposal_id)
        if proposal is None:
            raise ValueError(f"healing proposal {proposal_id} not found")
        if proposal.status != HealingProposalStatus.APPROVED.value:
            raise ValueError(
                f"cannot apply non-APPROVED healing proposal (status {proposal.status})"
            )
        # Re-run the policy on the stored diff as a final safety net.
        before = _loads(proposal.before_json, {})
        after = _loads(proposal.after_json, {})
        verdict = HealingPolicy.decide(before, after)
        if verdict["decision"] != HealingPolicyDecision.ALLOW.value:
            raise ValueError("cannot apply a mutation-tainted healing proposal")

        # Resolve owning plan via the referenced version.
        source_version = db.get(CommandPlanVersion, proposal.command_plan_version_id)
        version_no = (
            (source_version.version_no if source_version is not None else 0) + 1
        )
        new_plan = CommandPlan(
            scenario_adapter_id=proposal.scenario_adapter_id,
            current_version_no=version_no,
        )
        db.add(new_plan)
        db.flush()
        new_version = CommandPlanVersion(
            command_plan_id=new_plan.id,
            version_no=version_no,
            scenario_version_id=(
                source_version.scenario_version_id if source_version else 0
            ),
            contract_version_id=(
                source_version.contract_version_id if source_version else 0
            ),
            schema_version="1.0",
            plan_json=_dumps(after),
            plan_hash=_sha(_dumps(after)),
            status=CommandPlanStatus.VALIDATED.value,
            generated_by_type="SYSTEM",
            model_ref=None,
            prompt_version=None,
            approved_by=approved_by,
            approved_at=datetime.now() if approved_by else None,
        )
        db.add(new_version)
        db.flush()
        return {
            "proposal_id": proposal_id,
            "command_plan_id": new_plan.id,
            "command_plan_version_id": new_version.id,
            "version_no": version_no,
            "status": new_version.status,
            "note": note,
            "old_retained": True,
        }


# ────────────────────────────────────────────────────────────────────────────
# FlakyDetector — V38-006 / FlakyClusterService — V38-007
# ────────────────────────────────────────────────────────────────────────────


class FlakyDetector:
    """Detect flaky signals from run/step signatures.

    Only AUTOMATION/ENV volatility is eligible; BUSINESS_FAIL is always excluded
    (a real business failure must never be auto-flagged as flaky or auto-passed).
    """

    @staticmethod
    def record(
        db: Session,
        scenario_adapter_id: int,
        run_id: int,
        signal_type: str,
        signature: str,
        details: dict | None = None,
        outcome: str | None = None,
    ) -> dict | None:
        if (outcome or "").upper() == Outcome.BUSINESS_FAIL.value:
            raise ValueError("BUSINESS_FAIL is never eligible for a flaky signal")
        weight = FlakyDetector._weight(signal_type)
        row = repo.create_flaky_signal(
            db,
            {
                "scenario_adapter_id": scenario_adapter_id,
                "run_id": run_id,
                "signal_type": signal_type,
                "signature": signature,
                "weight": weight,
                "details_json": _dumps(details or {}),
            },
        )
        db.flush()
        return FlakyDetector._signal_dict(row)

    @staticmethod
    def analyze(db: Session, scenario_adapter_id: int) -> dict:
        signals = repo.list_flaky_signals_for_adapter(db, scenario_adapter_id)
        if not signals:
            return {"scenario_adapter_id": scenario_adapter_id, "clusters": []}
        grouped: dict[str, list[FlakySignal]] = {}
        for s in signals:
            grouped.setdefault(s.signature, []).append(s)
        clusters: list[dict] = []
        for signature, group in grouped.items():
            failure_rate = FlakyDetector._failure_rate(group)
            row = repo.create_flaky_cluster(
                db,
                {
                    "scenario_adapter_id": scenario_adapter_id,
                    "cluster_key": signature,
                    "classification": FlakyDetector._classify(failure_rate).value,
                    "sample_size": len(group),
                    "failure_rate": round(failure_rate, 4),
                    "confidence": min(
                        1.0, (len(group) / max(1, len(signals))) * 0.5 + 0.5
                    ),
                    "status": "ACTIVE",
                },
            )
            clusters.append(FlakyDetector._cluster_dict(row))
        db.flush()
        return {"scenario_adapter_id": scenario_adapter_id, "clusters": clusters}

    @staticmethod
    def _weight(signal_type: str) -> float:
        return {
            FlakySignalType.RERUN_PASS.value: 1.0,
            FlakySignalType.INTERMITTENT_ERROR.value: 1.4,
            FlakySignalType.TIMEOUT.value: 1.2,
            FlakySignalType.STALE_LOCATOR.value: 1.1,
            FlakySignalType.ENV_FLAP.value: 0.9,
        }.get((signal_type or "").upper(), 1.0)

    @staticmethod
    def _failure_rate(group: list[FlakySignal]) -> float:
        weighted = sum(s.weight for s in group)
        return min(1.0, weighted / max(1, len(group) * 1.5))

    @staticmethod
    def _classify(failure_rate: float) -> FlakyClassification:
        if failure_rate >= 0.75:
            return FlakyClassification.FLAKY
        if failure_rate >= 0.5:
            return FlakyClassification.FLAPPY
        if failure_rate >= 0.2:
            return FlakyClassification.UNCLASSIFIED
        return FlakyClassification.STABLE

    @staticmethod
    def _signal_dict(s: FlakySignal) -> dict:
        return {
            "id": s.id,
            "scenario_adapter_id": s.scenario_adapter_id,
            "run_id": s.run_id,
            "signal_type": s.signal_type,
            "signature": s.signature,
            "weight": s.weight,
            "details": _loads(s.details_json, {}),
            "created_at": s.created_at.isoformat() if s.created_at else None,
        }

    @staticmethod
    def _cluster_dict(c: FlakyCluster) -> dict:
        return {
            "id": c.id,
            "scenario_adapter_id": c.scenario_adapter_id,
            "cluster_key": c.cluster_key,
            "classification": c.classification,
            "sample_size": c.sample_size,
            "failure_rate": c.failure_rate,
            "confidence": c.confidence,
            "status": c.status,
        }


class FlakyClusterService:
    """List flaky clusters + scenario stability (V38-007; samples traceable)."""

    @staticmethod
    def list(db: Session, scenario_adapter_id: int | None = None) -> list[dict]:
        return [
            FlakyDetector._cluster_dict(c)
            for c in repo.list_flaky_clusters(db, scenario_adapter_id)
        ]

    @staticmethod
    def stability(db: Session, scenario_id: int) -> dict:
        versions = db.scalars(
            select(TestScenarioVersion).where(
                TestScenarioVersion.scenario_id == scenario_id
            )
        ).all()
        adapter_ids = [
            v.scenario_adapter_id
            for v in versions
            if hasattr(v, "scenario_adapter_id")
        ] or []
        # falls back to adapter-level clusters if present
        clusters = [
            FlakyDetector._cluster_dict(c)
            for c in repo.list_flaky_clusters(db, None)
            if c.scenario_adapter_id in adapter_ids or not adapter_ids
        ]
        return {"scenario_id": scenario_id, "clusters": clusters}


# ────────────────────────────────────────────────────────────────────────────
# StrategyPerformanceService — V38-008 / DataStrategyAdvisor — V38-009
# ────────────────────────────────────────────────────────────────────────────


class StrategyPerformanceService:
    """Record + query strategy performance metrics (project-scoped)."""

    @staticmethod
    def record(
        db: Session,
        project_id: int,
        strategy_type: str,
        strategy_key: str,
        success: bool,
        duration_ms: int,
    ) -> dict:
        context_hash = _sha(f"{strategy_type}|{strategy_key}")
        row = repo.get_strategy_performance(
            db, project_id, strategy_type, strategy_key, context_hash
        )
        if row is None:
            row = repo.create_strategy_performance(
                db,
                {
                    "project_id": project_id,
                    "strategy_type": strategy_type,
                    "strategy_key": strategy_key,
                    "context_hash": context_hash,
                    "attempt_count": 1,
                    "success_count": 1 if success else 0,
                    "median_duration_ms": duration_ms,
                    "failure_breakdown_json": "{}",
                    "updated_at": datetime.now(),
                },
            )
        else:
            row.attempt_count += 1
            row.success_count += 1 if success else 0
            row.median_duration_ms = max(
                0, int((row.median_duration_ms + duration_ms) / 2)
            )
            row.updated_at = datetime.now()
        db.flush()
        return StrategyPerformanceService._dict(row)

    @staticmethod
    def list(db: Session, project_id: int) -> list[dict]:
        return [
            StrategyPerformanceService._dict(r)
            for r in repo.list_strategy_performance(db, project_id)
        ]

    @staticmethod
    def _dict(r: StrategyPerformance) -> dict:
        return {
            "project_id": r.project_id,
            "strategy_type": r.strategy_type,
            "strategy_key": r.strategy_key,
            "attempt_count": r.attempt_count,
            "success_count": r.success_count,
            "success_rate": (
                round(r.success_count / r.attempt_count, 4) if r.attempt_count else 0.0
            ),
            "median_duration_ms": r.median_duration_ms,
            "failure_breakdown": _loads(r.failure_breakdown_json, {}),
        }


class DataStrategyAdvisor:
    """Recommend a data/browser strategy priority from recorded performance.

    The advisor may suggest ordering only — Policy, environment access mode and
    approval requirement always take precedence over an AI recommendation.
    """

    @staticmethod
    def advise(db: Session, project_id: int) -> dict:
        rows = repo.list_strategy_performance(db, project_id)
        ranked = sorted(
            [
                {
                    "strategy_type": r.strategy_type,
                    "strategy_key": r.strategy_key,
                    "success_rate": (
                        round(r.success_count / r.attempt_count, 4)
                        if r.attempt_count
                        else 0.0
                    ),
                    "attempt_count": r.attempt_count,
                }
                for r in rows
            ],
            key=lambda x: (x["success_rate"], x["attempt_count"]),
            reverse=True,
        )
        return {
            "recommended_priority": [r["strategy_key"] for r in ranked],
            "note": (
                "Policy / environment access mode / approval always "
                "take precedence"
            ),
            "policy_override": True,
        }


# ────────────────────────────────────────────────────────────────────────────
# ScenarioGapDetector — V38-010
# ────────────────────────────────────────────────────────────────────────────


class ScenarioGapDetector:
    """Detect scenario gap candidates.

    Proposal only — never writes a formal Expected value.
    """

    @staticmethod
    def detect(
        db: Session,
        mission_id: int,
        inputs: list[dict] | None = None,
    ) -> dict:
        inputs = inputs or []
        created = 0
        for item in inputs:
            gap_type = item.get("gap_type", ScenarioGapType.PROD_NEW_STATE.value)
            repo.create_gap_candidate(
                db,
                {
                    "mission_id": mission_id,
                    "gap_type": gap_type,
                    "title": item.get("title", "未命名 Gap"),
                    "description": item.get("description", ""),
                    "source_refs_json": _dumps(item.get("source_refs", [])),
                    "evidence_refs_json": _dumps(item.get("evidence_refs", [])),
                    "risk_level": item.get("risk_level", RiskLevel.P2.value),
                    "confidence": item.get("confidence", 0.0),
                    "status": GapCandidateStatus.OPEN.value,
                },
            )
            created += 1
        db.flush()
        return {
            "mission_id": mission_id,
            "created": created,
            "candidates": ScenarioGapDetector.list(db, mission_id),
        }

    @staticmethod
    def list(db: Session, mission_id: int) -> list[dict]:
        return [
            ScenarioGapDetector._dict(c)
            for c in repo.list_gap_candidates(db, mission_id)
        ]

    @staticmethod
    def convert(db: Session, gap_id: int, title: str | None, risk_level: str) -> dict:
        row = repo.get_gap_candidate(db, gap_id)
        if row is None:
            raise ValueError(f"gap candidate {gap_id} not found")
        if row.status != GapCandidateStatus.OPEN.value:
            raise ValueError(f"gap candidate not convertible (status {row.status})")
        row.status = GapCandidateStatus.CONVERTED.value
        db.flush()
        return {
            "gap_id": gap_id,
            "converted": True,
            "title": title or row.title,
            "risk_level": risk_level or row.risk_level,
            "note": (
                "proposal only — must go through Contract/Scenario "
                "Change Proposal → New Version"
            ),
        }

    @staticmethod
    def _dict(c: ScenarioGapCandidate) -> dict:
        return {
            "id": c.id,
            "mission_id": c.mission_id,
            "gap_type": c.gap_type,
            "title": c.title,
            "description": c.description,
            "source_refs": _loads(c.source_refs_json, []),
            "evidence_refs": _loads(c.evidence_refs_json, []),
            "risk_level": c.risk_level,
            "confidence": c.confidence,
            "status": c.status,
        }


# ────────────────────────────────────────────────────────────────────────────
# SuggestionInboxService — V38-011
# ────────────────────────────────────────────────────────────────────────────


class SuggestionInboxService:
    """Tester-controlled AI suggestion inbox; P0 bulk-approval is protected."""

    @staticmethod
    def create(
        db: Session,
        project_id: int,
        suggestion_type: str,
        target_type: str,
        target_id: int,
        payload: dict,
        confidence: float,
        mission_id: int | None = None,
    ) -> dict:
        row = repo.create_suggestion(
            db,
            {
                "project_id": project_id,
                "mission_id": mission_id,
                "suggestion_type": suggestion_type,
                "target_type": target_type,
                "target_id": target_id,
                "payload_json": _dumps(payload),
                "evidence_refs_json": _dumps(payload.get("evidence_refs", [])),
                "confidence": confidence,
                "status": SuggestionStatus.OPEN.value,
            },
        )
        db.flush()
        return SuggestionInboxService._dict(row)

    @staticmethod
    def list(db: Session, project_id: int, status: str | None = None) -> list[dict]:
        return [
            SuggestionInboxService._dict(s)
            for s in repo.list_suggestions(db, project_id, status)
        ]

    @staticmethod
    def review(
        db: Session,
        suggestion_id: int,
        status: str,
        reviewed_by: int | None = None,
        reason: str | None = None,
    ) -> dict:
        row = repo.get_suggestion(db, suggestion_id)
        if row is None:
            raise ValueError(f"suggestion {suggestion_id} not found")
        if row.status != SuggestionStatus.OPEN.value:
            raise ValueError(f"suggestion already {row.status}")
        if (status or "").upper() not in {
            SuggestionStatus.APPROVED.value,
            SuggestionStatus.REJECTED.value,
        }:
            raise ValueError(f"illegal review status: {status}")
        # P0 bulk approval protection: any P0 target demands an explicit reason.
        if row.suggestion_type == SuggestionType.RISK.value and (
            reason or ""
        ).strip() == "":
            raise ValueError("P0 suggestion approval requires an explicit reason")
        row.status = (status or "").upper()
        db.flush()
        return {
            **SuggestionInboxService._dict(row),
            "reviewed_by": reviewed_by,
            "reason": reason,
        }

    @staticmethod
    def _dict(s: AiSuggestion) -> dict:
        return {
            "id": s.id,
            "project_id": s.project_id,
            "mission_id": s.mission_id,
            "suggestion_type": s.suggestion_type,
            "target_type": s.target_type,
            "target_id": s.target_id,
            "payload": _loads(s.payload_json, {}),
            "evidence_refs": _loads(s.evidence_refs_json, []),
            "confidence": s.confidence,
            "status": s.status,
        }


# ────────────────────────────────────────────────────────────────────────────
# HumanFeedbackService — V38-012
# ────────────────────────────────────────────────────────────────────────────


class HumanFeedbackService:
    """Append-only Tester correction log (never mutated)."""

    @staticmethod
    def add(db: Session, values: dict) -> dict:
        row = repo.create_feedback(
            db,
            {
                "project_id": values.get("project_id", 0),
                "mission_id": values.get("mission_id"),
                "target_type": values.get("target_type", ""),
                "target_id": values.get("target_id", 0),
                "feedback_type": values.get(
                    "feedback_type", FeedbackType.CORRECTION.value
                ),
                "before_json": (
                    _dumps(values["before"])
                    if values.get("before") is not None
                    else None
                ),
                "after_json": (
                    _dumps(values["after"])
                    if values.get("after") is not None
                    else None
                ),
                "reason": values.get("reason"),
                "created_by": values.get("created_by", 0),
            },
        )
        db.flush()
        return HumanFeedbackService._dict(row)

    @staticmethod
    def list(
        db: Session, project_id: int, target_type: str | None = None
    ) -> list[dict]:
        return [
            HumanFeedbackService._dict(f)
            for f in repo.list_feedback(db, project_id, target_type)
        ]

    @staticmethod
    def _dict(f: HumanFeedback) -> dict:
        return {
            "id": f.id,
            "project_id": f.project_id,
            "mission_id": f.mission_id,
            "target_type": f.target_type,
            "target_id": f.target_id,
            "feedback_type": f.feedback_type,
            "before": _loads(f.before_json, None) if f.before_json else None,
            "after": _loads(f.after_json, None) if f.after_json else None,
            "reason": f.reason,
            "created_by": f.created_by,
        }


# ────────────────────────────────────────────────────────────────────────────
# PromptEvaluationService — V38-013
# ────────────────────────────────────────────────────────────────────────────


class PromptEvaluationService:
    """Golden model/prompt evaluation with a regression threshold guard."""

    REGRESSION_THRESHOLD = 0.9

    @staticmethod
    def evaluate(db: Session, values: dict) -> dict:
        # V3.9-R5 (AI-003): an externally-computed evaluation is an UNTRUSTED
        # import — it is recorded (for observability) but never marks a golden
        # release gate as passed. Trusted scores come only from ``run_suite``.
        metrics = dict(values.get("metrics", {}))
        metrics.setdefault("_trusted", False)
        row = repo.create_model_evaluation(
            db,
            {
                "evaluation_suite": values["evaluation_suite"],
                "model_ref": values["model_ref"],
                "prompt_versions_json": _dumps(values.get("prompt_versions", [])),
                "status": values.get("status", ModelEvaluationStatus.COMPLETED.value),
                "metrics_json": _dumps(metrics),
                "artifact_uri": values.get("artifact_uri"),
            },
        )
        db.flush()
        return PromptEvaluationService._dict(row)

    @staticmethod
    def import_external_evaluation(db: Session, values: dict) -> dict:
        """Rename of the raw external import path (plan §70). Always untrusted."""
        return PromptEvaluationService.evaluate(db, values)

    @staticmethod
    def _score_sample(sample: dict, output: Any) -> dict:
        """Score one golden sample against its expected / must_include constraints."""
        import json as _json

        reasons: list[str] = []
        text = _json.dumps(output, ensure_ascii=False) if not isinstance(output, str) else output
        ok = True
        for needle in list(sample.get("must_include") or []):
            if str(needle) not in text:
                ok = False
                reasons.append(f"missing must_include:{needle}")
        for forbidden in list(sample.get("must_not_include") or []):
            if str(forbidden) in text:
                ok = False
                reasons.append(f"present must_not_include:{forbidden}")
        expected = sample.get("expected")
        if ok and isinstance(expected, dict) and isinstance(output, dict):
            for k, v in expected.items():
                if output.get(k) != v:
                    ok = False
                    reasons.append(f"expected[{k}]!={v!r} got={output.get(k)!r}")
        return {"sample": sample, "ok": ok, "reasons": reasons}

    @staticmethod
    def run_suite(
        db: Session,
        evaluation_suite: str,
        model_ref: str,
        samples: list[dict],
        evaluator: Callable[[dict], Any] | None = None,
        prompt_versions: list[str] | None = None,
    ) -> dict:
        """Run a golden suite: evaluate each sample, score it, persist a TRUSTED run.

        The default ``evaluator`` returns a sample's ``candidate`` (a deterministic
        harness); ``run_golden`` provides the real LLM evaluator. Runs persist with
        ``_trusted=True`` so only this path can drive a golden release gate.
        """
        evaluator = evaluator or (lambda s: s.get("candidate"))
        results = []
        for sample in samples:
            output = evaluator(sample)
            results.append(PromptEvaluationService._score_sample(sample, output))
        metrics = PromptEvaluationService.score_suite(results)
        metrics["_trusted"] = True
        metrics["_source"] = "golden_suite"
        row = repo.create_model_evaluation(
            db,
            {
                "evaluation_suite": evaluation_suite,
                "model_ref": model_ref,
                "prompt_versions_json": _dumps(prompt_versions or []),
                "status": ModelEvaluationStatus.COMPLETED.value,
                "metrics_json": _dumps(metrics),
                "artifact_uri": None,
            },
        )
        db.flush()
        out = PromptEvaluationService._dict(row)
        out["results"] = results
        return out

    @staticmethod
    def run_golden(
        db: Session,
        project_id: int,
        evaluation_suite: str,
        model_ref: str,
        samples: list[dict],
        system_prompt: str | None = None,
        prompt_versions: list[str] | None = None,
    ) -> dict:
        """Batch 208 (C3): real LLM golden evaluation runner.

        Each sample is sent to the configured model (shared ai_client), scored
        against must_include / expected constraints and persisted as a TRUSTED
        ModelEvaluationRun. If AI is unconfigured or any call fails the suite is
        BLOCKED and nothing trusted is written (never a silent pass).
        """
        from app.services import ai_client

        if not ai_client.is_configured(db, project_id):
            return {
                "ok": False,
                "status": "BLOCKED",
                "reason": "AI_NOT_CONFIGURED",
                "score": None,
            }

        sys_prompt = system_prompt or (
            "你是测试用例评审专家。严格按样例约束输出结果 JSON，只输出 JSON。"
        )
        def _llm_evaluator(sample: dict):
            input_text = str(
                sample.get("input")
                or _dumps(sample.get("prompt", {}))
                or _dumps(sample)
            )
            return ai_client.chat_completions(
                db,
                project_id,
                system_prompt=sys_prompt,
                user_message=input_text,
                max_tokens=4096,
                json_mode=True,
            )

        try:
            out = PromptEvaluationService.run_suite(
                db,
                evaluation_suite,
                model_ref,
                samples,
                evaluator=_llm_evaluator,
                prompt_versions=prompt_versions,
            )
        except (ai_client.AiClientUnavailableError, ai_client.AiClientResponseError) as exc:
            return {
                "ok": False,
                "status": "BLOCKED",
                "reason": "AI_CALL_FAILED",
                "detail": str(exc)[:300],
                "score": None,
            }
        metrics = out.get("metrics") or {}
        score = float(metrics.get("accuracy", 0.0))
        passed = score >= PromptEvaluationService.REGRESSION_THRESHOLD
        out["decision"] = {
            "ok": passed,
            "status": "PASS" if passed else "FAIL",
            "passed": passed,
            "score": score,
            "threshold": PromptEvaluationService.REGRESSION_THRESHOLD,
        }
        return out

    @staticmethod
    def score_suite(results: list[dict]) -> dict:
        """Aggregate per-sample scores into ``{n, correct, accuracy}``."""
        n = len(results)
        correct = sum(1 for r in results if r.get("ok"))
        accuracy = (correct / n) if n else 0.0
        return {
            "n": n,
            "correct": correct,
            "accuracy": round(float(accuracy), 4),
        }

    @staticmethod
    def compare_baseline(db: Session, evaluation_suite: str, baseline_suite: str) -> dict:
        """Compare the latest trusted score for a suite against a stored baseline."""
        latest = PromptEvaluationService._latest_trusted(db, evaluation_suite)
        baseline = PromptEvaluationService._latest_trusted(db, baseline_suite)
        if latest is None or baseline is None:
            return {
                "ok": False,
                "status": "BLOCKED",
                "reason": "INSUFFICIENT_SAMPLES",
                "current": None,
                "baseline": None,
            }
        cur_acc = float(_loads(latest.metrics_json, {}).get("accuracy", 0.0))
        base_acc = float(_loads(baseline.metrics_json, {}).get("accuracy", 0.0))
        regressed = cur_acc < base_acc
        return {
            "ok": not regressed,
            "status": "REGRESSED" if regressed else "CLEAN",
            "reason": "below_baseline" if regressed else "at_or_above_baseline",
            "current": cur_acc,
            "baseline": base_acc,
            "delta": round(cur_acc - base_acc, 4),
        }

    @staticmethod
    def release_decision(db: Session, evaluation_suite: str) -> dict:
        """Golden release gate: only a TRUSTED run_suite score can PASS."""
        latest = PromptEvaluationService._latest_trusted(db, evaluation_suite)
        if latest is None:
            return {
                "ok": False,
                "status": "BLOCKED",
                "passed": False,
                "reason": "INSUFFICIENT_SAMPLES",
                "score": None,
            }
        score = float(_loads(latest.metrics_json, {}).get("accuracy", 0.0))
        passed = score >= PromptEvaluationService.REGRESSION_THRESHOLD
        return {
            "ok": passed,
            "status": "PASS" if passed else "FAIL",
            "passed": passed,
            "score": score,
            "threshold": PromptEvaluationService.REGRESSION_THRESHOLD,
            "reason": "passed" if passed else "below golden threshold — block release",
        }

    @staticmethod
    def _latest_trusted(db: Session, evaluation_suite: str) -> ModelEvaluationRun | None:
        for e in sorted(repo.list_model_evaluations(db), key=lambda r: r.id, reverse=True):
            if e.evaluation_suite != evaluation_suite:
                continue
            if bool(_loads(e.metrics_json, {}).get("_trusted", False)):
                return e
        return None

    @staticmethod
    def list(db: Session) -> list[dict]:
        return [
            PromptEvaluationService._dict(e)
            for e in repo.list_model_evaluations(db)
        ]

    @staticmethod
    def check_regression(db: Session, evaluation_suite: str) -> dict:
        runs = [
            e
            for e in repo.list_model_evaluations(db)
            if e.evaluation_suite == evaluation_suite
        ]
        if len(runs) < 2:
            # V3.9-R5 (AI-004): insufficient samples is BLOCKED, not a pass.
            return {
                "ok": False,
                "status": "BLOCKED",
                "passed": False,
                "reason": "INSUFFICIENT_SAMPLES",
                "score": None,
            }
        latest = max(runs, key=lambda e: e.id)
        score = float(_loads(latest.metrics_json, {}).get("accuracy", 0.0))
        passed = score >= PromptEvaluationService.REGRESSION_THRESHOLD
        return {
            "ok": passed,
            "passed": passed,
            "score": score,
            "threshold": PromptEvaluationService.REGRESSION_THRESHOLD,
            "reason": "passed" if passed else "below golden threshold — block release",
        }

    @staticmethod
    def _dict(e: ModelEvaluationRun) -> dict:
        return {
            "id": e.id,
            "evaluation_suite": e.evaluation_suite,
            "model_ref": e.model_ref,
            "prompt_versions": _loads(e.prompt_versions_json, []),
            "status": e.status,
            "metrics": _loads(e.metrics_json, {}),
            "artifact_uri": e.artifact_uri,
            "created_at": e.created_at.isoformat() if e.created_at else None,
        }


# ────────────────────────────────────────────────────────────────────────────
# AutoRetryPolicy — V38-014
# ────────────────────────────────────────────────────────────────────────────


class AutoRetryPolicy:
    """Decide whether a failed run may auto-retry.

    Only transient AUTOMATION/ENV or an already-approved healing proposal may
    retry; a real BUSINESS_FAIL never gets an infinite retry and is never
    auto-flagged flaky or auto-passed.
    """

    @staticmethod
    def decide(
        db: Session,
        run_id: int,
        approved_healing_proposal_id: int | None = None,
    ) -> dict:
        run = db.get(ExecutionRun, run_id)
        if run is None:
            return {"run_id": run_id, "decision": AutoRetryDecision.INVALID.value}
        outcome = (run.outcome or "").upper()
        if outcome == Outcome.BUSINESS_FAIL.value:
            return {
                "run_id": run_id,
                "decision": AutoRetryDecision.NO_RETRY.value,
                "reason": "BUSINESS_FAIL is never auto-retried",
            }
        if approved_healing_proposal_id is not None:
            proposal = db.get(HealingProposal, approved_healing_proposal_id)
            if (
                proposal is not None
                and proposal.status == HealingProposalStatus.APPROVED.value
            ):
                return {
                    "run_id": run_id,
                    "decision": AutoRetryDecision.RETRY.value,
                    "reason": "approved healing proposal present",
                }
        if outcome in {
            Outcome.AUTOMATION_FAIL.value,
            Outcome.ENV_FAIL.value,
            Outcome.DATA_FAIL.value,
            Outcome.BLOCKED.value,
            Outcome.ASSERTION_ERROR.value,
        }:
            return {
                "run_id": run_id,
                "decision": AutoRetryDecision.RETRY.value,
                "reason": f"transient {outcome} eligible for retry",
            }
        return {
            "run_id": run_id,
            "decision": AutoRetryDecision.NO_RETRY.value,
            "reason": "no eligibility for auto-retry",
        }
