"""AITDE V3.3 HybridExecutionCoordinator (V33-009).

Orchestrates Data → Action → Oracle → Cleanup for a run. Cleanup is guaranteed
via ``finally`` — a failure in action/oracle never leaves a provisioned fixture
dangling. The action/oracle dispatch is a stable interface so V3.4 can swap the
scheduler layer without changing this contract.
"""
from __future__ import annotations

from typing import Any, Callable

from sqlalchemy.orm import Session

from app.modules.aitde.execution.models import ExecutionRun


class HybridExecutionCoordinator:
    def __init__(
        self,
        action_runner: Callable[[dict[str, Any]], dict[str, Any]] | None = None,
        oracle_evaluator: Callable[[dict[str, Any], dict[str, Any] | None], dict[str, Any]] | None = None,
    ):
        self._action_runner = action_runner
        self._oracle_evaluator = oracle_evaluator

    def run(self, db: Session, run: ExecutionRun, project_id: int) -> dict[str, Any]:
        from app.modules.aitde.data import cleanup_service
        from app.modules.aitde.data.run_data_integration import prepare_run_data

        state: dict[str, Any] = {}
        prep = prepare_run_data(db, run, project_id)
        fixture_id = prep.get("fixture_id")
        state["data"] = {"prepared": prep.get("prepared", False), "reason": prep.get("reason")}

        try:
            if prep.get("prepared"):
                state.update(self._run_actions_and_oracles(db, run))
            else:
                state["action"] = {"skipped": True, "reason": prep.get("reason")}
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
                result["action"] = {"executed": True, "note": "action_runner_not_configured"}
        except Exception as exc:  # noqa: BLE001 — record; cleanup still runs in finally
            result["action"] = {"error": str(exc)}
        if self._oracle_evaluator:
            try:
                result["oracle"] = self._oracle_evaluator({}, None)
            except Exception as exc:  # noqa: BLE001
                result["oracle"] = {"error": str(exc)}
        return result
