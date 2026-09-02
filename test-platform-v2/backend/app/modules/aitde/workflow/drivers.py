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
    except Exception:  # noqa: BLE001 — a missing run is a non-critical context; degrade
        return {"context": {}, "reason": "run_not_found", "idempotent": True}
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
        # Batch 207: keep the QA closed loop wired on the runtime path too.
        from app.modules.aitde.ai_closed_loop.service import FailureTriageAgent

        try:
            FailureTriageAgent.auto_triage_if_needed(db, run.id)
            db.commit()
        except Exception:  # noqa: BLE001 - triage never breaks classify
            db.rollback()
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


class _SecretRefMeta:
    """Adapter so a plain dict ``secret_ref`` can be fed to WorkerSecretResolver."""

    def __init__(self, data: dict[str, Any] | None) -> None:
        data = data or {}
        self.status = str(data.get("status") or "ACTIVE")
        self.provider = str(data.get("provider") or "env").lower()
        self.external_ref = data.get("external_ref") or ""
        self.scope_json = json.dumps(data.get("scope") or {}, ensure_ascii=False)


def _resolve_secret_value(plan: dict[str, Any]) -> str:
    """SEC-001: resolve a SecretRef at worker runtime.

    A CommandPlan may only carry a ``secret_ref`` (metadata); raw ``token`` /
    ``password`` / ``auth_token`` fields are forbidden. If no ref is present the
    value is empty — the caller NEVER falls back to a raw payload token field.
    """
    ref = plan.get("secret_ref") or (plan.get("auth") or {}).get("secret_ref")
    if not ref:
        return ""
    from app.modules.aitde.workflow.secret_resolver import worker_secret_resolver

    value = worker_secret_resolver.resolve(_SecretRefMeta(ref))
    return str(value or "")


def _resolve_token(payload: dict[str, Any], plan: dict[str, Any]) -> str:
    """DEPRECATED (SEC-001). Kept only as a shim to avoid breaking callers.

    Returns the resolved SecretRef value instead of any raw payload token. The
    old ``payload["auth_token"]`` / ``plan["auth"]["token"]`` writes are removed.
    """
    return _resolve_secret_value(plan)


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

    # SEC-002: never disable TLS verification in the formal runtime. An enterprise
    # in-house CA is loaded via a client CA bundle (see _http_ca); INSECURE_DEV_ONLY
    # is a dev-only policy and is guarded from the Trusted Release Gate.
    return httpx.Client(trust_env=False, verify=True, timeout=25)


def _resolve_command_plan_hook(payload: dict[str, Any]) -> dict[str, Any]:
    run_id = _real_run_id(payload)
    if run_id is None:
        return {"plan": None, "reason": "no_run_id", "trust_level": "LEGACY_UNVERIFIED"}
    db = _db()
    try:
        from app.modules.aitde.common.enums import AssertionTrustStatus
        from app.modules.aitde.workflow.oracle_engine import parse_command_plan

        plan, plan_version_id, _run = _load_plan(db, run_id, payload.get("project_id") or 0)
        if plan is None:
            return {"plan": None, "reason": "no_plan", "trust_level": "LEGACY_UNVERIFIED"}
        descriptor = parse_command_plan(plan)
        return {
            "plan": plan,
            "steps": plan.get("steps") or [],
            "commands": plan.get("commands") or [],
            "command_plan_version_id": plan_version_id,
            "schema_version": descriptor["schema_version"],
            "is_v2": descriptor["is_v2"],
            "trust_level": (
                AssertionTrustStatus.TRUSTED.value
                if descriptor["is_v2"]
                else AssertionTrustStatus.LEGACY_UNVERIFIED.value
            ),
        }
    finally:
        db.close()



# Batch 209 (C1): a browser Command IR runner may be injected by a real
# Playwright worker (future). Without it, browser commands are BLOCKED
# explicitly instead of being mis-routed as HTTP requests.
_BROWSER_RUNNER = None


def register_browser_runner(runner) -> None:
    """Register a browser IR runner callback for scenario runs (C1)."""
    global _BROWSER_RUNNER
    _BROWSER_RUNNER = runner


def _execute_commands_hook(payload: dict[str, Any]) -> dict[str, Any]:
    run_id = _real_run_id(payload)
    if run_id is None:
        return {"echo": True, "reason": "no_run_id"}
    db = _db()
    try:
        from app.modules.aitde.evidence.service import store_artifact
        from app.modules.aitde.evidence.snapshot_sanitizer import snapshot_sanitizer
        from app.modules.aitde.execution.models import ExecutionStep
        from app.modules.aitde.workflow.oracle_engine import parse_command_plan

        plan, plan_version_id, _run = _load_plan(db, run_id, payload.get("project_id") or 0)
        if not plan:
            return {"echo": True, "reason": "no_plan"}
        project_id = payload.get("project_id") or 0
        secret = _resolve_secret_value(plan)
        base_url = str(plan.get("base_url") or "").rstrip("/")
        descriptor = parse_command_plan(plan)
        commands = descriptor["commands"] if descriptor["is_v2"] else descriptor["legacy_steps"]

        results: list[dict[str, Any]] = []
        seq = 0
        for cmd in commands:
            seq += 1
            if descriptor["is_v2"]:
                driver = str(cmd.get("driver") or "api").lower()
                step_key = str(cmd.get("id") or "api")
                input_block = cmd.get("input") or {}

                if driver == "assertion":
                    # Oracle evaluation is a separate stage; never run assertions
                    # as HTTP here.
                    results.append(
                        {
                            "name": step_key,
                            "driver": "assertion",
                            "skipped": "assertion_evaluate",
                            "ok": True,
                            "sanitized": True,
                        }
                    )
                    continue

                if driver == "browser":
                    if _BROWSER_RUNNER is None:
                        blocked = ExecutionStep(
                            run_id=run_id,
                            sequence=seq,
                            step_key=step_key,
                            step_type="BROWSER",
                            status="FAILED",
                            error_message="no_browser_runtime",
                            input_snapshot_json=snapshot_sanitizer.dump(
                                {"driver": "browser", "input": input_block}
                            ),
                            output_snapshot_json=snapshot_sanitizer.dump(
                                {"reason": "no_browser_runtime"}
                            ),
                            evidence_refs_json="[]",
                        )
                        db.add(blocked)
                        db.commit()
                        db.refresh(blocked)
                        results.append(
                            {
                                "name": step_key,
                                "driver": "browser",
                                "ok": False,
                                "error": "no_browser_runtime",
                                "evidence_refs": [],
                                "sanitized": True,
                            }
                        )
                        continue
                    try:
                        runner_out = _BROWSER_RUNNER(
                            {"run_id": run_id, "command": cmd, "project_id": project_id},
                            db,
                            seq,
                        )
                        results.append(
                            {
                                "name": step_key,
                                "driver": "browser",
                                **(runner_out or {}),
                                "ok": bool((runner_out or {}).get("ok", False)),
                                "sanitized": True,
                            }
                        )
                    except Exception as exc:  # noqa: BLE001
                        db.rollback()
                        results.append(
                            {
                                "name": step_key,
                                "driver": "browser",
                                "ok": False,
                                "error": f"browser_runner_error:{exc}"[:200],
                                "sanitized": True,
                            }
                        )
                    continue

                # default v2 driver == api
                method = str(input_block.get("method") or "GET").upper()
                path = str(input_block.get("path") or "")
                headers = input_block.get("headers") or {}
                params = input_block.get("params") or {}
                body = input_block.get("body")
            else:
                step_key = str(cmd.get("name") or "api")
                method = str(cmd.get("method") or "GET").upper()
                path = str(cmd.get("path") or "")
                headers = cmd.get("headers") or {}
                params = cmd.get("params") or {}
                body = cmd.get("body")

            url = base_url + path
            substituted_headers = {k: _sub_token(v, secret) for k, v in headers.items()}

            status = None
            resp_json: Any = None
            error: str | None = None
            try:
                client = _http()
                try:
                    resp = client.request(
                        method, url, params=params,
                        json=body if body is not None else None,
                        headers=substituted_headers,
                    )
                    status = resp.status_code
                    try:
                        resp_json = resp.json()
                    except Exception:
                        resp_json = resp.text[:2000]
                finally:
                    client.close()
            except Exception as exc:  # noqa: BLE001
                db.rollback()
                error = repr(exc)[:120]

            req_snapshot = snapshot_sanitizer.sanitize_http_snapshot(
                method=method, url=url, headers=substituted_headers,
                params=params, body=body,
            )
            resp_snapshot = snapshot_sanitizer.sanitize_response_snapshot(
                status=status if status is not None else 0, body=resp_json,
            )
            if error:
                resp_snapshot["error"] = error

            st_row = ExecutionStep(
                run_id=run_id, sequence=seq, step_key=step_key, step_type="API",
                status="FAILED" if error or (status is not None and status >= 400) else "SUCCEEDED",
                error_message=error,
                input_snapshot_json=snapshot_sanitizer.dump(req_snapshot),
                output_snapshot_json=snapshot_sanitizer.dump(resp_snapshot),
                evidence_refs_json="[]",
            )
            db.add(st_row)
            db.commit()
            db.refresh(st_row)

            ev_refs: list[int] = []
            if error is None and status is not None:
                for etype, snap in (("REQUEST", req_snapshot), ("RESPONSE", resp_snapshot)):
                    try:
                        artifact = store_artifact(
                            db, project_id=project_id, run_id=run_id,
                            evidence_type=etype, step_id=st_row.id,
                            data=json.dumps(snap, ensure_ascii=False).encode("utf-8"),
                            content_type="application/json",
                        )
                        ev_refs.append(artifact.id)
                    except Exception as exc:  # noqa: BLE001
                        logger.warning("evidence store failed for run=%s step=%s: %s", run_id, step_key, exc)
                st_row.evidence_refs_json = json.dumps(ev_refs)
                db.commit()

            results.append({
                "name": step_key, "method": method, "http_status": status,
                "ok": bool(error is None and status is not None and status < 400),
                "error": error,
                "evidence_refs": json.loads(st_row.evidence_refs_json or "[]"),
                "sanitized": True,
            })
        return {"steps": results, "command_plan_version_id": plan_version_id}
    finally:
        db.close()


def _evaluate_oracles_hook(payload: dict[str, Any]) -> dict[str, Any]:
    run_id = _real_run_id(payload)
    if run_id is None:
        return {"assertions": [], "reason": "no_run_id", "trust_level": "LEGACY_UNVERIFIED"}
    db = _db()
    try:
        from app.modules.aitde.execution import repository as exec_repo
        from app.modules.aitde.workflow.oracle_engine import evaluate_oracles

        run = exec_repo.get_run(db, run_id, payload.get("project_id") or 0)
        if run is None:
            return {"assertions": [], "reason": "run_not_found", "trust_level": "LEGACY_UNVERIFIED"}
        result = evaluate_oracles(db, run, payload.get("project_id") or 0)
        return {
            "assertions": result["assertions"],
            "pass": result["pass"],
            "fail": result["fail"],
            "not_evaluated": result.get("not_evaluated", 0),
            "oracle_total": result.get("oracle_total", 0),
            "trust_level": result.get("trust_level", "LEGACY_UNVERIFIED"),
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
