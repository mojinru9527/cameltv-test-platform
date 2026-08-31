"""AITDE V3.9-R2 (DATA-002) — DataPlanExecutor: real provisioning orchestration.

Establishes the plan/fixture as actually executing, then runs every entity's
validated physical effect through the correct executor and VERIFIES it is present
before the fixture may reach ``READY``. A single failed step fails the whole plan
(``FAILED``), never a synthetic success. Physical facts are recorded on each
FixtureEntity (``physical_status`` / ``verification_status`` / ``verified_at``)
and the matching DataPlanStep is marked succeeded/failed.
"""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.modules.aitde.common.enums import DataPlanStatus, FixtureStatus, StepStatus
from app.modules.aitde.data import repository
from app.modules.aitde.data.executors.api_executor import ApiFixtureExecutor
from app.modules.aitde.data.executors.base import (
    PHYSICAL_CREATED,
    PHYSICAL_FAILED,
    PHYSICAL_FOUND,
    VERIFIED,
    VERIFY_FAILED,
    build_data_driver,
)
from app.modules.aitde.data.executors.db_executor import DbFixtureExecutor
from app.modules.aitde.data.executors.existing_executor import ExistingExecutor


class DataPlanExecutor:
    """Orchestrate a DataPlan's provisioning to a real physical state."""

    def __init__(self, db: Session):
        self.db = db

    def execute(
        self, plan: Any, fixture: Any, source: Any
    ) -> dict[str, Any]:
        """Execute the plan's steps and drive the fixture to READY / FAILED.

        The plan is marked EXECUTING during the run; on success it is restored to
        its prior status (so a reusable plan can provision fixtures for multiple
        environments/runs), on failure it is marked FAILED.
        """
        prior_plan_status = plan.status
        plan.status = DataPlanStatus.EXECUTING.value
        fixture.status = FixtureStatus.PROVISIONING.value
        self.db.commit()

        steps = repository.list_steps_by_plan(self.db, plan.id)
        entities = repository.list_fixture_entities(self.db, fixture.id)
        step_by_key = {
            (_step_command(step).get("requirement_key")): step for step in steps
            if _step_command(step).get("requirement_key")
        }
        driver = build_data_driver(source)
        api_config = json.loads(source.config_json or "{}") if source else {}
        get_endpoint = api_config.get("get_endpoint")
        id_field = str(api_config.get("id_field") or "id")

        results: list[dict[str, Any]] = []
        all_ok = True
        for entity in entities:
            outcome = self._run_entity(
                entity,
                driver,
                get_endpoint,
                id_field,
            )
            results.append(outcome)
            step = step_by_key.get(entity.logical_key)
            if step is not None:
                step.status = (
                    StepStatus.SUCCEEDED.value if outcome["ok"] else StepStatus.FAILED.value
                )
            if not outcome["ok"]:
                all_ok = False
                entity.physical_status = PHYSICAL_FAILED
                entity.verification_status = VERIFY_FAILED
                entity.verified_at = datetime.now()
            else:
                entity.physical_status = (
                    PHYSICAL_FOUND if outcome["kind"] == "read" else PHYSICAL_CREATED
                )
                entity.verification_status = VERIFIED
                entity.verified_at = datetime.now()
                if outcome.get("physical"):
                    entity.physical_ref_json = json.dumps(
                        outcome["physical"], ensure_ascii=False
                    )

        if all_ok:
            plan.status = prior_plan_status
            fixture.status = FixtureStatus.READY.value
        else:
            plan.status = DataPlanStatus.FAILED.value
            fixture.status = FixtureStatus.FAILED.value
        self.db.commit()
        self.db.refresh(fixture)
        return {
            "ok": all_ok,
            "strategy": plan.strategy,
            "executed_steps": sum(1 for r in results if r["ok"]),
            "total_steps": len(entities),
            "results": results,
        }

    def _run_entity(
        self,
        entity: Any,
        driver: Any,
        get_endpoint: str | None,
        id_field: str,
    ) -> dict[str, Any]:
        physical = json.loads(entity.physical_ref_json or "{}")
        kind = str(physical.get("kind") or "")
        # Pre-fill so a failure still records a physical effect choice.
        base: dict[str, Any] = {
            "logical_key": entity.logical_key,
            "kind": kind,
            "ok": False,
            "detail": "",
            "physical": physical,
        }
        try:
            if kind == "read":
                rows = ExistingExecutor.execute_find(
                    driver,
                    entity.entity_type,
                    physical.get("where") or {},
                    row_limit=int(physical.get("row_limit") or 100),
                )
                return {**base, "ok": True, "physical": {"kind": "read", "rows": rows["physical_rows"]}}
            if kind == "write":
                result = DbFixtureExecutor.execute_create(
                    driver, physical.get("table") or entity.entity_type, physical.get("set") or {}
                )
                return {**base, "ok": True, "physical": {"kind": "write", "row": result["physical_row"]}}
            if kind == "api_create":
                result = ApiFixtureExecutor.execute_create(
                    driver,
                    physical.get("endpoint") or "",
                    physical.get("payload") or {},
                    get_endpoint=get_endpoint,
                    id_field=id_field,
                )
                return {
                    **base,
                    "ok": True,
                    "physical": {
                        "kind": "api_create",
                        "physical_id": result["physical_id"],
                        "resource": result["resource"],
                    },
                }
            # WORKFLOW has no real physical executor in V3.9-R2; fail closed.
            raise RuntimeError(f"unsupported_executor_kind:{kind or 'none'}")
        except Exception as exc:  # noqa: BLE001 — category, never raw
            return {**base, "detail": _safe_detail(exc)}


def _step_command(step: Any) -> dict[str, Any]:
    try:
        cmd = json.loads(step.command_json or "{}")
    except (ValueError, TypeError):
        cmd = {}
    return cmd if isinstance(cmd, dict) else {}


def _safe_detail(exc: Exception) -> str:
    code = getattr(exc, "code", None)
    if code:
        return f"{code}:{getattr(exc, 'detail', '')}"
    return str(type(exc).__name__)
