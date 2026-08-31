"""OracleEngine — V3.9-R1 (TRUST-001 / TRUST-002).

Loads the *real* required ``TestOracle`` + ``ScenarioOracleBinding`` for a run and
hands each ``(oracle, observation)`` pair to the deterministic ``AssertionEngine``.
This is the single source of Expected: Expected always comes from
``TestOracle.expected_value_json``; a CommandPlan may declare *observations* only and
must never carry ``expected`` / ``asserts``.

CommandPlan versions
    v2  (schema_version == "2.0"): ``commands[].observations`` -> real Oracle + Binding.
    v1  (has ``steps[].asserts``): decoded but flagged ``LEGACY_COMMAND_ASSERT`` and
        ``LEGACY_UNVERIFIED`` so it never blocks a Trusted Release Gate.

The engine requires no ``temporalio`` and is unit-testable with an in-memory DB.
"""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.aitde.assertion.engine import evaluate_and_persist
from app.modules.aitde.common.enums import (
    AssertionTrustStatus,
    OracleBindingType,
    OracleSourceType,
)
from app.modules.aitde.execution.models import AssertionResult, ExecutionRun, ExecutionStep
from app.modules.aitde.scenario.models import ScenarioOracleBinding, TestOracle


class OracleEngineError(Exception):
    """Raised when the Oracle chain cannot be evaluated deterministically."""


def parse_command_plan(plan: dict[str, Any] | None) -> dict[str, Any]:
    """Return a normalized CommandPlan descriptor.

    ``is_v2`` True when ``schema_version == "2.0"`` or the plan uses ``commands``.
    ``legacy_steps`` carries the v1.x ``steps[].asserts`` (decoded but untrusted).
    """
    plan = plan or {}
    schema_version = str(plan.get("schema_version") or plan.get("version") or "1.0")
    commands = plan.get("commands") or []
    steps = plan.get("steps") or []

    is_v2 = schema_version.startswith("2.") or bool(commands)
    observations: list[dict[str, Any]] = []
    for cmd in commands:
        for obs in cmd.get("observations") or []:
            observations.append(
                {
                    "command_id": cmd.get("id", ""),
                    "key": obs.get("key", ""),
                    "type": obs.get("type", ""),
                }
            )
    return {
        "schema_version": schema_version if is_v2 else "1.x",
        "is_v2": is_v2,
        "commands": commands,
        "observations": observations,
        "legacy_steps": [] if is_v2 else steps,
    }


def load_required_oracles(
    db: Session, scenario_version_id: int | None
) -> list[TestOracle]:
    """Return the required TestOracle rows for a scenario version."""
    if not scenario_version_id:
        return []
    return list(
        db.scalars(
            select(TestOracle)
            .where(TestOracle.scenario_version_id == scenario_version_id)
            .order_by(TestOracle.id.asc())
        ).all()
    )


def load_bindings(
    db: Session, adapter_id: int | None, scenario_version_id: int | None
) -> list[ScenarioOracleBinding]:
    """Return ACTIVE bindings for an adapter + scenario version."""
    if not adapter_id or not scenario_version_id:
        return []
    return list(
        db.scalars(
            select(ScenarioOracleBinding)
            .where(
                ScenarioOracleBinding.scenario_adapter_id == adapter_id,
                ScenarioOracleBinding.scenario_version_id == scenario_version_id,
                ScenarioOracleBinding.status == "ACTIVE",
            )
        ).all()
    )


def _json_path(data: Any, path: str) -> Any:
    """Minimal JSONPath: ``$.data.membership.status`` / ``data.result[0].name``."""
    import re

    normalized = path
    if normalized.startswith("$."):
        normalized = normalized[2:]
    cur = data
    for seg in normalized.split("."):
        if not seg:
            continue
        m = re.match(r"^([^\[\]]+)(?:\[(\d+)\])?$", seg)
        key = m.group(1) if m else seg
        idx = int(m.group(2)) if m and m.group(2) else None
        if isinstance(cur, dict):
            if key not in cur:
                return None
            cur = cur[key]
        elif isinstance(cur, list) and idx is not None:
            cur = cur[idx] if idx < len(cur) else None
        else:
            return None
        if idx is not None and isinstance(cur, list):
            cur = cur[idx] if idx < len(cur) else None
    return cur


def _step_output(steps: list[ExecutionStep], step_key: str) -> dict[str, Any]:
    for step in steps:
        if step.step_key == step_key:
            try:
                return json.loads(step.output_snapshot_json or "{}")
            except (ValueError, TypeError):
                return {}
    return {}


def resolve_observation(
    binding: ScenarioOracleBinding, steps: list[ExecutionStep]
) -> Any:
    """Resolve the Actual for a binding from the persisted step observations.

    ``binding.binding_type`` decides how to extract from the selected step output:
      API_STATUS     -> output["status"]
      API_JSONPATH   -> jsonpath over output["body"]
      UI_TEXT/VISIBLE/ATTRIBUTE -> jsonpath over output["body"] (UI snapshot)
      DB_COLUMN      -> output["columns"][selector["column"]] (DB observation)
    Returns None when the observation cannot be resolved (-> NOT_EVALUATED).
    """
    selector = {}
    try:
        selector = json.loads(binding.observation_selector_json or "{}")
    except (ValueError, TypeError):
        selector = {}

    output = _step_output(steps, binding.source_step_key)
    if not output:
        return None

    binding_type = str(binding.binding_type or "").upper()
    if binding_type == OracleBindingType.API_STATUS.value:
        return output.get("status")

    if binding_type == OracleBindingType.DB_COLUMN.value:
        columns = output.get("columns") or {}
        col = selector.get("column")
        return columns.get(col) if col else None

    # JSONPath / UI / event / log all read from the body/payload region.
    path = selector.get("jsonpath") or selector.get("path")
    if path:
        return _json_path(output.get("body") or {}, str(path))
    if binding_type == OracleBindingType.UI_VISIBLE.value:
        return output.get("visible")
    if binding_type == OracleBindingType.UI_TEXT.value:
        return output.get("text")
    return None


def _mark_trusted(row: AssertionResult, oracle_id: int, binding_id: int | None) -> None:
    row.test_oracle_id = oracle_id
    row.oracle_source_type = OracleSourceType.TEST_ORACLE.value
    row.trust_status = AssertionTrustStatus.TRUSTED.value
    row.binding_id = binding_id


def evaluate_oracles(db: Session, run: ExecutionRun, project_id: int) -> dict[str, Any]:
    """Evaluate all real required oracles for a run and persist trusted assertions.

    Returns a summary dict with ``assertions``, ``pass``, ``fail`` and
    ``trust_level``. Raises ``OracleEngineError`` when an Oracle cannot be read.
    """
    from app.modules.aitde.execution import repository

    plan, _plan_version_id = _load_plan_for_run(db, run)
    descriptor = parse_command_plan(plan)
    steps = repository.list_steps(db, run.id, project_id)

    if descriptor["is_v2"]:
        oracles = load_required_oracles(db, run.scenario_version_id)
        bindings = load_bindings(db, run.adapter_id, run.scenario_version_id)
        binding_by_oracle = {b.oracle_id: b for b in bindings}
        return _evaluate_v2(
            db, run, project_id, oracles, binding_by_oracle, steps
        )

    return _evaluate_v1_legacy(db, run, project_id, descriptor["legacy_steps"])


def _evaluate_v2(
    db: Session,
    run: ExecutionRun,
    project_id: int,
    oracles: list[TestOracle],
    binding_by_oracle: dict[int, ScenarioOracleBinding],
    steps: list[ExecutionStep],
) -> dict[str, Any]:
    assertions: list[dict[str, Any]] = []
    for oracle in oracles:
        binding = binding_by_oracle.get(oracle.id)
        actual = None
        reason = ""
        if binding:
            actual = resolve_observation(binding, steps)
            if actual is None:
                reason = "observation_missing"
        else:
            reason = "no_oracle_binding"

        oracle_snapshot = {
            "operator": oracle.operator or "eq",
            "expected_value_json": oracle.expected_value_json or "{}",
        }
        outcome = evaluate_and_persist(
            db,
            run_id=run.id,
            oracle_id=oracle.id,
            oracle_snapshot=oracle_snapshot,
            actual=actual,
            step_id=None,
            evidence_refs=[],
        )
        # Set trust fields on the row we just persisted.
        row = db.get(AssertionResult, outcome["id"])
        if row:
            _mark_trusted(row, oracle.id, binding.id if binding else None)
            if reason:
                row.reason_code = reason or row.reason_code
            db.commit()

        assertions.append(
            {
                "oracle_id": oracle.id,
                "test_oracle_id": oracle.id,
                "trust_status": AssertionTrustStatus.TRUSTED.value,
                "result": outcome["result"],
                "reason_code": outcome["reason_code"] or reason,
                "binding_type": binding.binding_type if binding else None,
            }
        )

    return {
        "assertions": assertions,
        "pass": sum(1 for a in assertions if a["result"] == "PASS"),
        "fail": sum(1 for a in assertions if a["result"] == "FAIL"),
        "not_evaluated": sum(1 for a in assertions if a["result"] == "NOT_EVALUATED"),
        "trust_level": AssertionTrustStatus.TRUSTED.value,
        "oracle_total": len(oracles),
    }


def _evaluate_v1_legacy(
    db: Session,
    run: ExecutionRun,
    project_id: int,
    legacy_steps: list[dict[str, Any]],
) -> dict[str, Any]:
    """Decode v1.x ``steps[].asserts`` as untrusted legacy assertions.

    They are materialized in AssertionResult (so existing consumers keep working)
    but flagged ``LEGACY_COMMAND_ASSERT`` / ``LEGACY_UNVERIFIED`` so they never
    count toward a Trusted Release Gate.
    """
    from app.modules.aitde.execution import repository

    assertions: list[dict[str, Any]] = []
    for step in legacy_steps:
        step_key = str(step.get("name") or step.get("id") or "api")
        for assert_def in step.get("asserts") or []:
            kind = assert_def.get("kind")
            expected = assert_def.get("expected")
            row = repository.add_assertion(
                db,
                {
                    "run_id": run.id,
                    "oracle_id": 0,  # legacy: no real TestOracle
                    "test_oracle_id": None,
                    "oracle_source_type": OracleSourceType.LEGACY_COMMAND_ASSERT.value,
                    "trust_status": AssertionTrustStatus.LEGACY_UNVERIFIED.value,
                    "oracle_snapshot_json": json.dumps(
                        {"kind": kind, "path": assert_def.get("path")},
                        ensure_ascii=False,
                    ),
                    "expected_json": json.dumps(expected, ensure_ascii=False),
                    "actual_json": json.dumps(assert_def.get("actual"), ensure_ascii=False),
                    "result": assert_def.get("result") or "NOT_EVALUATED",
                    "reason_code": assert_def.get("reason") or "",
                    "evidence_refs_json": "[]",
                    "evaluated_at": datetime.now(),
                },
            )
            assertions.append(
                {
                    "oracle_id": row.id,
                    "test_oracle_id": None,
                    "trust_status": AssertionTrustStatus.LEGACY_UNVERIFIED.value,
                    "result": row.result,
                    "reason_code": row.reason_code,
                }
            )
    return {
        "assertions": assertions,
        "pass": sum(1 for a in assertions if a["result"] == "PASS"),
        "fail": sum(1 for a in assertions if a["result"] == "FAIL"),
        "not_evaluated": sum(1 for a in assertions if a["result"] == "NOT_EVALUATED"),
        "trust_level": AssertionTrustStatus.LEGACY_UNVERIFIED.value,
        "oracle_total": len(assertions),
    }


def _load_plan_for_run(
    db: Session, run: ExecutionRun
) -> tuple[dict[str, Any], int | None]:
    """Load the CommandPlanVersion JSON for a run's scenario version."""
    from app.modules.aitde.command.models import CommandPlanVersion

    if not run.scenario_version_id:
        return {}, None
    version = (
        db.query(CommandPlanVersion)
        .filter(CommandPlanVersion.scenario_version_id == run.scenario_version_id)
        .order_by(CommandPlanVersion.id.desc())
        .first()
    )
    if version is None:
        return {}, None
    try:
        return json.loads(version.plan_json or "{}"), version.id
    except (ValueError, TypeError):
        return {}, version.id
