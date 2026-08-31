"""AITDE V3.3 HybridExecutionCoordinator (V33-009) + V3.9-R2 HYBRID-001.

Orchestrates Data → Action → Oracle → Cleanup for a run. Cleanup is guaranteed
via ``finally`` — a failure in action/oracle never leaves a provisioned fixture
dangling. The action/oracle dispatch is a stable interface so V3.4 can swap the
scheduler layer without changing this contract.

V3.9-R2 (HYBRID-001): a missing runner / oracle evaluator is a *capability*
failure, never a fake ``executed=True``. A Hybrid run with no Action Runner must
be classified ``AUTOMATION_FAIL`` / ``BLOCKED`` and must not proceed to a formal
Oracle PASS. ``preflight()`` reports required-capability readiness before a Run
starts so the scheduler can refuse a run that cannot really execute.
"""
from __future__ import annotations

from typing import Any, Callable

from sqlalchemy.orm import Session

from app.modules.aitde.execution.models import ExecutionRun

# V3.9-R2 capability error codes (plan §37).
ACTION_RUNNER_NOT_CONFIGURED = "ACTION_RUNNER_NOT_CONFIGURED"
ORACLE_EVALUATOR_NOT_CONFIGURED = "ORACLE_EVALUATOR_NOT_CONFIGURED"
DRIVER_CAPABILITY_MISSING = "DRIVER_CAPABILITY_MISSING"


class RuntimeCapabilityError(Exception):
    """Raised when a required runtime capability is missing.

    Carries a stable ``code`` so callers can map it to ``AUTOMATION_FAIL`` /
    ``BLOCKED`` without parsing free text.
    """

    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(f"{code}: {detail}" if detail else code)
        self.code = code
        self.detail = detail


class HybridExecutionCoordinator:
    def __init__(
        self,
        action_runner: Callable[[dict[str, Any]], dict[str, Any]] | None = None,
        oracle_evaluator: Callable[[dict[str, Any], dict[str, Any] | None], dict[str, Any]] | None = None,
    ):
        self._action_runner = action_runner
        self._oracle_evaluator = oracle_evaluator

    def preflight(self) -> dict[str, Any]:
        """Report which required hybrid capabilities are wired up.

        A Hybrid run can only really execute when at least an Action Runner is
        present; a missing runner must forbid the run (HYBRID-001 / plan §39).
        """
        checks: dict[str, bool] = {
            "data_driver": True,
            "action_runner": self._action_runner is not None,
            "oracle_evaluator": self._oracle_evaluator is not None,
            "evidence_store": True,
        }
        missing = [name for name, ok in checks.items() if not ok]
        return {"checks": checks, "missing": missing, "ready": not missing}

    def run(self, db: Session, run: ExecutionRun, project_id: int) -> dict[str, Any]:
        from app.modules.aitde.data import cleanup_service
        from app.modules.aitde.data.run_data_integration import prepare_run_data

        state: dict[str, Any] = {"preflight": self.preflight()}
        prep = prepare_run_data(db, run, project_id)
        fixture_id = prep.get("fixture_id")
        state["data"] = {"prepared": prep.get("prepared", False), "reason": prep.get("reason")}

        try:
            if prep.get("prepared"):
                # HYBRID-001: no runner -> capability error, never a fake executed.
                if not self._action_runner:
                    raise RuntimeCapabilityError(ACTION_RUNNER_NOT_CONFIGURED)
                state.update(self._run_actions_and_oracles(db, run))
            else:
                state["action"] = {"skipped": True, "reason": prep.get("reason")}
        except RuntimeCapabilityError as exc:
            state["action"] = {
                "executed": False,
                "error": exc.code,
                "blocked": True,
                "automation_error": True,
            }
        finally:
            # Cleanup must ALWAYS run, even if action/oracle raised.
            if fixture_id:
                try:
                    state["cleanup"] = cleanup_service.cleanup_fixture(db, fixture_id)
                except Exception as exc:  # noqa: BLE001 — record, never mask the run
                    state["cleanup"] = {"status": "FAILED", "error": str(exc)}
        return state

    def _run_actions_and_oracles(self, db: Session, run: ExecutionRun) -> dict[str, Any]:
        result: dict[str, Any] = {}
        try:
            if self._action_runner:
                result["action"] = self._action_runner({"run_id": run.id})
            else:
                # Never fake "executed=True" without a runner (HYBRID-001).
                result["action"] = {
                    "executed": False,
                    "error": ACTION_RUNNER_NOT_CONFIGURED,
                    "blocked": True,
                    "automation_error": True,
                }
        except Exception as exc:  # noqa: BLE001 — record; cleanup still runs in finally
            result["action"] = {"executed": False, "error": str(exc), "automation_error": True}
        if self._oracle_evaluator:
            try:
                result["oracle"] = self._oracle_evaluator({}, None)
            except Exception as exc:  # noqa: BLE001
                result["oracle"] = {"evaluated": False, "error": str(exc)}
        else:
            result["oracle"] = {
                "evaluated": False,
                "error": ORACLE_EVALUATOR_NOT_CONFIGURED,
                "blocked": True,
            }
        return result
