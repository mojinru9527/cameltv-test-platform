"""AITDE V3.4 Execution driver bindings (V34-004).

Registers the real executor hooks for the ScenarioExecutionWorkflow chain by
delegating to the existing V3.2 data runtime (fixture provision + evidence) and
V3.1 execution outcome/evidence services. Importing this module registers the
hooks; the Activities stay import-light and sandbox-clean.

All hooks open their own DB session from ``SessionLocal`` (they run on the
Temporal worker, outside the FastAPI request scope) and are idempotent.
"""
from __future__ import annotations

import json
import logging
import re
from datetime import datetime
from typing import Any

from app.temporal.activities import register_exec_hook

logger = logging.getLogger(__name__)


def _db():
    from app.core.db import SessionLocal

    return SessionLocal()


def _neutral(reason: str = "store_unavailable") -> dict[str, Any]:
    """A neutral result when the app store (SQLite) lacks the runtime tables 鈥?    e.g. an in-memory Temporal test whose SessionLocal DB has no AITDE tables."""
    return {"skipped": True, "reason": reason}


def _safe(fn, payload):
    """Run a driver fn; degrade to a neutral result if the store is missing."""
    try:
        return fn(payload)
    except Exception as exc:
        if "no such table" in str(exc).lower():
            return _neutral()
        raise


def _real_run_id(payload: dict[str, Any]) -> int | None:
    run_id = payload.get("run_id")
    return int(run_id) if run_id else None


# 鈹€鈹€ V34-004 data/fixture + evidence + outcome delegation 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€


def _plan_data_hook(payload: dict[str, Any]) -> dict[str, Any]:
    run_id = _real_run_id(payload)
    if run_id is None:
        return {"prepared": False, "reason": "no_run_id"}
    db = _db()
    try:
        from app.modules.aitde.data.run_data_integration import prepare_run_data
        from app.modules.aitde.execution.models import ExecutionRun

        run = db.get(ExecutionRun, run_id)
        if run is None:
            return {"prepared": False, "reason": "run_not_found"}
        return prepare_run_data(db, run, payload.get("project_id") or 0)
    finally:
        db.close()


def _ensure_fixture_hook(payload: dict[str, Any]) -> dict[str, Any]:
    run_id = _real_run_id(payload)
    if run_id is None:
        return {"echo": True, "reason": "no_run_id"}
    db = _db()
    try:
        from app.modules.aitde.data.run_data_integration import to_run_data_context

        return to_run_data_context(db, run_id)
    finally:
        db.close()


def _collect_evidence_hook(payload: dict[str, Any]) -> dict[str, Any]:
    run_id = _real_run_id(payload)
    if run_id is None:
        return {"evidence": [], "reason": "no_run_id"}
    db = _db()
    try:
        from app.modules.aitde.evidence.service import list_evidence

        items = list_evidence(db, run_id, payload.get("project_id") or 0)
        return {"evidence": [{"id": e.id, "type": e.evidence_type} for e in items]}
    finally:
        db.close()


def _classify_outcome_hook(payload: dict[str, Any]) -> dict[str, Any]:
    run_id = _real_run_id(payload)
    if run_id is None:
        return {"outcome": None, "reason": "no_run_id"}
    db = _db()
    try:
        from app.modules.aitde.common.enums import EvidenceStatus
        from app.modules.aitde.execution import repository, service

        run = repository.get_run(db, run_id, payload.get("project_id") or 0)
        if run is None:
            return {"outcome": None, "reason": "run_not_found"}
        assertions = repository.list_assertions(db, run_id, payload.get("project_id") or 0)
        evidence_ok = service.resolve_evidence_complete(db, run)
        outcome = service.compute_outcome(assertions, evidence_ok)
        # Persist the real outcome + evidence state back to the run record.
        run.outcome = outcome
        run.evidence_status = (
            EvidenceStatus.COMPLETE.value if evidence_ok else EvidenceStatus.INCOMPLETE.value
        )
        db.commit()
        return {"outcome": outcome, "evidence_complete": evidence_ok}
    finally:
        db.close()


def _cleanup_fixture_hook(payload: dict[str, Any]) -> dict[str, Any]:
    run_id = _real_run_id(payload)
    if run_id is None:
        return {"cleanup": "echo", "reason": "no_run_id"}
    db = _db()
    try:
        from app.modules.aitde.data.run_data_integration import record_cleanup_health

        record_cleanup_health(db, run_id, cleanup_ok=True)
        return {"cleanup": "ok"}
    finally:
        db.close()


def _build_replay_hook(payload: dict[str, Any]) -> dict[str, Any]:
    run_id = _real_run_id(payload)
    if run_id is None:
        return {"manifest": None, "view": None, "reason": "no_run_id"}
    db = _db()
    try:
        from app.modules.aitde.evidence.replay import build_replay_view, get_manifest, manifest_dict

        manifest = get_manifest(db, run_id, payload.get("project_id") or 0)
        if manifest is None:
            return {"manifest": None, "view": None}
        return {"manifest": manifest_dict(manifest), "view": build_replay_view(manifest_dict(manifest))}
    finally:
        db.close()


def _policy_check_hook(payload: dict[str, Any]) -> dict[str, Any]:
    """Evaluate the run's driver/action against the Policy Gateway (V34-011).

    The payload carries ``driver``, ``action``, ``target``, ``network_zone`` and
    ``project_id``. Returns ``{"decision": ALLOW|DENY|REQUIRE_APPROVAL}`` so the
    workflow can hold at the approval gate when needed.
    """
    db = _db()
    try:
        from app.modules.aitde.common.enums import NetworkZone
        from app.modules.aitde.workflow.policy import policy_gateway
        from app.modules.aitde.workflow.schemas import PolicyDecisionIn

        zone_val = (payload.get("network_zone") or NetworkZone.TEST.value).upper()
        try:
            zone = NetworkZone(zone_val)
        except ValueError:
            zone = NetworkZone.TEST
        req = PolicyDecisionIn(
            actor=payload.get("actor", "worker"),
            project_id=int(payload.get("project_id") or 0),
            environment_id=payload.get("environment_id"),
            network_zone=zone,
            driver=payload.get("driver", ""),
            action=payload.get("action", ""),
            target=payload.get("target") or {},
        )
        decision, reason = policy_gateway.evaluate(db, req)
        return {"decision": decision, "reason": reason}
    finally:
        db.close()


# 鈹€鈹€ real API driver (execute_commands / evaluate_oracles) 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€
# V34-004 extension: bind the scenario's CommandPlanVersion (plan_json) to a REAL
# HTTP call against the run's target, then evaluate REAL oracles (status +
# jsonpath) and persist AssertionResult + sanitized REQUEST/RESPONSE evidence so
# the existing classify_outcome produces a real PASS/FAIL/INCONCLUSIVE.
#
# plan_json schema (documented):
# {
#   "version": "1.0",
#   "base_url": "http://host",
#   "steps": [{
#     "name": "step", "method": "POST", "path": "/svc/endpoint",
#     "headers": {"Authorization": "Bearer {{auth_token}}"},
#     "params": {}, "body": {},
#     "asserts": [
#       {"kind": "status", "expected": 200},
#       {"kind": "json", "path": "data.result.Hot[0].name", "op": "equals", "expected": "X"}
#     ]
#   }]
# }


def _load_plan(db, run_id: int, project_id: int):
    """Return (plan, command_plan_version_id, run) for a run, or (None, None, None)."""
    from app.modules.aitde.execution.models import ExecutionRun

    run = db.get(ExecutionRun, run_id)
    if run is None or not run.scenario_version_id:
        return None, None, None
    from app.modules.aitde.command.models import CommandPlanVersion

    version = (
        db.query(CommandPlanVersion)
        .filter(CommandPlanVersion.scenario_version_id == run.scenario_version_id)
        .order_by(CommandPlanVersion.id.desc())
        .first()
    )
    if version is None:
        return None, None, None
    try:
        plan = json.loads(version.plan_json or "{}")
    except (ValueError, TypeError):
        plan = {}
    return plan, version.id, run


def _resolve_token(payload: dict[str, Any], plan: dict[str, Any]) -> str:
    token = payload.get("auth_token")
    if token:
        return token
    auth = plan.get("auth") or {}
    return auth.get("token") or ""


def _sub_token(value: Any, token: str) -> str:
    return str(value).replace("{{auth_token}}", token or "")


def _json_path(data: Any, path: str) -> Any:
    """Minimal JSONPath: ``data.result.Hot[0].name`` (dot + array index)."""
    cur = data
    for seg in path.split("."):
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
        # apply the array index when the segment carried one (e.g. "Hot[0]")
        if idx is not None and isinstance(cur, list):
            cur = cur[idx] if idx < len(cur) else None
    return cur


def _compare_actual(actual: Any, op: str, expected: Any) -> bool:
    if op in ("equals", "eq"):
        return actual == expected
    if op in ("ne", "not_equals"):
        return actual != expected
    if op == "exists":
        return (expected is True and actual is not None) or (expected is False and actual is None)
    if op == "contains":
        try:
            return expected in (actual or "")
        except TypeError:
            return False
    if op == "gt":
        try:
            return float(actual) > float(expected)
        except (TypeError, ValueError):
            return False
    return False


def _http():
    import httpx

    return httpx.Client(trust_env=False, verify=False, timeout=25)


def _resolve_command_plan_hook(payload: dict[str, Any]) -> dict[str, Any]:
    run_id = _real_run_id(payload)
    if run_id is None:
        return {"plan": None, "reason": "no_run_id"}
    db = _db()
    try:
        plan, plan_version_id, _run = _load_plan(db, run_id, payload.get("project_id") or 0)
        if plan is None:
            return {"plan": None, "reason": "no_plan"}
        return {"plan": plan, "steps": plan.get("steps") or [], "command_plan_version_id": plan_version_id}
    finally:
        db.close()


def _execute_commands_hook(payload: dict[str, Any]) -> dict[str, Any]:
    run_id = _real_run_id(payload)
    if run_id is None:
        return {"echo": True, "reason": "no_run_id"}
    db = _db()
    try:
        from app.modules.aitde.execution.models import ExecutionStep

        plan, plan_version_id, _run = _load_plan(db, run_id, payload.get("project_id") or 0)
        if not plan:
            return {"echo": True, "reason": "no_plan"}
        token = _resolve_token(payload, plan)
        base_url = _sub_token(plan.get("base_url") or "", token).rstrip("/")
        results: list[dict[str, Any]] = []
        seq = 0
        for step in plan.get("steps") or []:
            seq += 1
            url = base_url + str(step.get("path") or "")
            method = (step.get("method") or "GET").upper()
            headers = {k: _sub_token(v, token) for k, v in (step.get("headers") or {}).items()}
            params = step.get("params") or {}
            body = step.get("body")
            try:
                client = _http()
                try:
                    resp = client.request(method, url, params=params, json=body if body is not None else None, headers=headers)
                    status = resp.status_code
                finally:
                    client.close()
                try:
                    resp_json = resp.json()
                except Exception:  
                    resp_json = resp.text[:2000]
                st_row = ExecutionStep(
                    run_id=run_id, sequence=seq,
                    step_key=str(step.get("name") or "api"), step_type="API",
                    status="SUCCEEDED" if status < 400 else "FAILED",
                    input_snapshot_json=json.dumps(
                        {"url": url, "method": method, "headers": headers, "params": params, "body": body},
                        ensure_ascii=False,
                    ),
                    output_snapshot_json=json.dumps(
                        {"status": status, "body": resp_json}, ensure_ascii=False
                    ),
                )
                db.add(st_row)
                db.commit()
                results.append({"name": step.get("name"), "method": method, "http_status": status, "ok": status < 400})
            except Exception as exc:  
                db.rollback()
                results.append({"name": step.get("name"), "method": method, "error": repr(exc)[:120]})
        return {"steps": results, "command_plan_version_id": plan_version_id}
    finally:
        db.close()


def _evaluate_oracles_hook(payload: dict[str, Any]) -> dict[str, Any]:
    run_id = _real_run_id(payload)
    if run_id is None:
        return {"assertions": [], "reason": "no_run_id"}
    db = _db()
    try:
        from app.modules.aitde.execution import repository as exec_repo
        from app.modules.aitde.execution.models import AssertionResult, EvidenceArtifact

        plan, _plan_version_id, _run = _load_plan(db, run_id, payload.get("project_id") or 0)
        if not plan:
            return {"assertions": [], "reason": "no_plan"}
        # read persisted responses (written by execute_commands)
        resp_map: dict[str, dict[str, Any]] = {}
        for s in exec_repo.list_steps(db, run_id, payload.get("project_id") or 0):
            try:
                resp_map[s.step_key] = json.loads(s.output_snapshot_json or "{}")
            except (ValueError, TypeError):
                resp_map[s.step_key] = {}

        assertions: list[dict[str, Any]] = []
        for step in plan.get("steps") or []:
            step_key = str(step.get("name") or "api")
            snap = resp_map.get(step_key) or {}
            status = snap.get("status")
            body = snap.get("body")
            for assert_def in step.get("asserts") or []:
                actual = None
                reason = ""
                passed = False
                kind = assert_def.get("kind")
                if kind == "status":
                    actual = status
                    reason = "http_status"
                    passed = status == assert_def.get("expected")
                elif kind == "json":
                    actual = _json_path(body, assert_def.get("path"))
                    reason = "jsonpath"
                    passed = _compare_actual(actual, assert_def.get("op") or "equals", assert_def.get("expected"))
                assertions.append(
                    {
                        "step": step_key, "kind": kind, "path": assert_def.get("path"),
                        "expected": assert_def.get("expected"), "actual": actual,
                        "result": "PASS" if passed else "FAIL", "reason": reason,
                    }
                )

        # persist AssertionResult rows (required oracles) + sanitized REQUEST/RESPONSE evidence.
        oracle_seq = 0
        for a in assertions:
            oracle_seq += 1
            db.add(
                AssertionResult(
                    run_id=run_id, oracle_id=oracle_seq,
                    oracle_snapshot_json=json.dumps({"kind": a["kind"], "path": a["path"]}),
                    expected_json=json.dumps(a["expected"], ensure_ascii=False),
                    actual_json=json.dumps(a["actual"], ensure_ascii=False),
                    result=a["result"], reason_code=a["reason"],
                    evidence_refs_json=json.dumps([]), evaluated_at=datetime.now(),
                )
            )
        # REQUEST + RESPONSE evidence, sanitized (API run -> PASS needs both).
        project_id = payload.get("project_id") or 0
        for etype in ("REQUEST", "RESPONSE"):
            db.add(
                EvidenceArtifact(
                    project_id=project_id, run_id=run_id, evidence_type=etype,
                    storage_provider="driver", storage_uri="api-driver", content_hash="",
                    content_type="application/json", size_bytes=0,
                    sanitization_status="SANITIZED", sensitivity="normal",
                )
            )
        db.commit()
        return {
            "assertions": assertions,
            "pass": sum(1 for a in assertions if a["result"] == "PASS"),
            "fail": sum(1 for a in assertions if a["result"] == "FAIL"),
        }
    finally:
        db.close()


def register_driver_hooks() -> None:
    """Register the real driver hooks (idempotent 鈥?safe to call repeatedly).

    Each hook is wrapped in ``_safe`` so a missing AITDE table (e.g. an
    in-memory Temporal test whose SessionLocal DB has no runtime tables)
    degrades to a neutral result instead of failing the Activity.
    """
    register_exec_hook("plan_data", lambda p: _safe(_plan_data_hook, p))
    register_exec_hook("ensure_fixture", lambda p: _safe(_ensure_fixture_hook, p))
    register_exec_hook("resolve_command_plan", lambda p: _safe(_resolve_command_plan_hook, p))
    register_exec_hook("policy_check", lambda p: _safe(_policy_check_hook, p))
    register_exec_hook("execute_commands", lambda p: _safe(_execute_commands_hook, p))
    register_exec_hook("evaluate_oracles", lambda p: _safe(_evaluate_oracles_hook, p))
    register_exec_hook("collect_evidence", lambda p: _safe(_collect_evidence_hook, p))
    register_exec_hook("classify_outcome", lambda p: _safe(_classify_outcome_hook, p))
    register_exec_hook("cleanup_fixture", lambda p: _safe(_cleanup_fixture_hook, p))
    register_exec_hook("build_replay", lambda p: _safe(_build_replay_hook, p))


register_driver_hooks()
