"""AITDE V4.0 Enterprise governance services (V40-009..020).

Deterministic policy/routing/readiness logic. No AI owns a decision here:
retention/expiry is driven by policy, model routing by sensitivity, cost by
budget, and the Platform Readiness Gate by fixed thresholds.
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.aitde.governance.enums import (
    PolicyStatus,
    ReadinessMetric,
    RetentionAction,
)
from app.modules.aitde.governance.models import (
    DrTestRun,
    ModelPolicy,
    ModelUsageLedger,
    RetentionPolicy,
)


def _loads(raw: str) -> list[str]:
    try:
        data = json.loads(raw)
    except (ValueError, TypeError):
        return []
    return data if isinstance(data, list) else []


class RetentionService:
    """V40-012: artifact retention policy + deterministic expiry decision."""

    @staticmethod
    def upsert(
        db: Session,
        project_id: int | None,
        artifact_type: str,
        sensitivity: str,
        retention_days: int,
        archive_action: str = RetentionAction.ARCHIVE.value,
        delete_action: str = RetentionAction.DELETE.value,
    ) -> dict:
        row = db.scalar(
            select(RetentionPolicy).where(
                RetentionPolicy.project_id == project_id,
                RetentionPolicy.artifact_type == artifact_type,
                RetentionPolicy.sensitivity == sensitivity,
            )
        )
        if row is None:
            row = RetentionPolicy(
                project_id=project_id,
                artifact_type=artifact_type,
                sensitivity=sensitivity,
                retention_days=retention_days,
                archive_action=archive_action,
                delete_action=delete_action,
                status=PolicyStatus.ACTIVE.value,
            )
            db.add(row)
        else:
            row.retention_days = retention_days
            row.archive_action = archive_action
            row.delete_action = delete_action
            row.status = PolicyStatus.ACTIVE.value
        db.commit()
        db.refresh(row)
        return RetentionService._out(row)

    @staticmethod
    def evaluate(db: Session, artifact_type: str, sensitivity: str, age_days: int) -> dict:
        """Return the retention action for an artifact (ARCHIVE/DELETE/KEEP)."""
        row = db.scalar(
            select(RetentionPolicy).where(
                RetentionPolicy.artifact_type == artifact_type,
                RetentionPolicy.sensitivity == sensitivity,
                RetentionPolicy.status == PolicyStatus.ACTIVE.value,
            )
        )
        if row is None:
            return {"action": RetentionAction.KEEP.value, "remaining_days": None}
        remaining = row.retention_days - age_days
        if remaining <= 0:
            action = (
                row.delete_action if row.delete_action else RetentionAction.DELETE.value
            )
            return {"action": action, "remaining_days": 0}
        return {"action": RetentionAction.ARCHIVE.value, "remaining_days": remaining}

    @staticmethod
    def _out(row: RetentionPolicy) -> dict:
        return {
            "id": row.id,
            "project_id": row.project_id,
            "artifact_type": row.artifact_type,
            "sensitivity": row.sensitivity,
            "retention_days": row.retention_days,
            "archive_action": row.archive_action,
            "delete_action": row.delete_action,
            "status": row.status,
        }


class ModelPolicyService:
    """V40-014: sensitivity-based model/provider routing, fail-closed."""

    @staticmethod
    def upsert(
        db: Session,
        project_id: int | None,
        sensitivity_level: str,
        allowed_providers: list[str],
        allowed_models: list[str],
        redaction_required: bool = False,
        persistence_allowed: bool = True,
    ) -> dict:
        row = db.scalar(
            select(ModelPolicy).where(
                ModelPolicy.project_id == project_id,
                ModelPolicy.sensitivity_level == sensitivity_level,
            )
        )
        if row is None:
            row = ModelPolicy(
                project_id=project_id,
                sensitivity_level=sensitivity_level,
                allowed_providers_json=json.dumps(allowed_providers, ensure_ascii=False),
                allowed_models_json=json.dumps(allowed_models, ensure_ascii=False),
                redaction_required=redaction_required,
                persistence_allowed=persistence_allowed,
                status=PolicyStatus.ACTIVE.value,
            )
            db.add(row)
        else:
            row.allowed_providers_json = json.dumps(allowed_providers, ensure_ascii=False)
            row.allowed_models_json = json.dumps(allowed_models, ensure_ascii=False)
            row.redaction_required = redaction_required
            row.persistence_allowed = persistence_allowed
        db.commit()
        db.refresh(row)
        return ModelPolicyService._out(row)

    @staticmethod
    def is_allowed(db: Session, provider: str, model: str, sensitivity: str) -> dict:
        """Fail-closed: an unconfigured sensitive level routes to no model."""
        row = db.scalar(
            select(ModelPolicy).where(
                ModelPolicy.sensitivity_level == sensitivity,
                ModelPolicy.status == PolicyStatus.ACTIVE.value,
            )
        )
        if row is None:
            return {"allowed": False, "reason": "no_policy_for_sensitivity"}
        allowed = provider in _loads(row.allowed_providers_json) and model in _loads(
            row.allowed_models_json
        )
        return {
            "allowed": allowed,
            "reason": "allowed" if allowed else "blocked_by_model_policy",
            "redaction_required": row.redaction_required,
            "persistence_allowed": row.persistence_allowed,
        }

    @staticmethod
    def _out(row: ModelPolicy) -> dict:
        return {
            "id": row.id,
            "project_id": row.project_id,
            "sensitivity_level": row.sensitivity_level,
            "allowed_providers": _loads(row.allowed_providers_json),
            "allowed_models": _loads(row.allowed_models_json),
            "redaction_required": row.redaction_required,
            "persistence_allowed": row.persistence_allowed,
            "status": row.status,
        }


class CostLedgerService:
    """V40-015: model/runtime usage ledger + budget guard."""

    @staticmethod
    def record(
        db: Session,
        project_id: int,
        operation_type: str,
        model_ref: str,
        input_units: int = 0,
        output_units: int = 0,
        cost_amount: float | None = None,
        latency_ms: int = 0,
        mission_id: int | None = None,
    ) -> dict:
        row = ModelUsageLedger(
            project_id=project_id,
            mission_id=mission_id,
            operation_type=operation_type,
            model_ref=model_ref,
            input_units=input_units,
            output_units=output_units,
            cost_amount=cost_amount,
            latency_ms=latency_ms,
            created_at=datetime.now(),
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        return {
            "id": row.id,
            "project_id": row.project_id,
            "operation_type": row.operation_type,
            "model_ref": row.model_ref,
            "input_units": row.input_units,
            "output_units": row.output_units,
            "cost_amount": row.cost_amount,
            "latency_ms": row.latency_ms,
        }

    @staticmethod
    def project_usage(db: Session, project_id: int) -> dict:
        rows = list(
            db.scalars(
                select(ModelUsageLedger).where(ModelUsageLedger.project_id == project_id)
            )
        )
        total_cost = sum((r.cost_amount or 0.0) for r in rows)
        return {"entries": len(rows), "total_cost": total_cost}

    @staticmethod
    def check_budget(db: Session, project_id: int, budget: float) -> dict:
        """Return warn/throttle decision; never gates Required tests (caller flag)."""
        usage = CostLedgerService.project_usage(db, project_id)
        if usage["total_cost"] >= budget:
            return {"decision": "THROTTLE_OPTIONAL", "budget_exceeded": True}
        return {"decision": "OK", "budget_exceeded": False}


class DrTestService:
    """V40-017: record disaster-recovery drill RTO/RPO evidence."""

    @staticmethod
    def record(
        db: Session,
        project_id: int,
        test_type: str,
        environment: str,
        status: str,
        rto_seconds: int | None,
        rpo_seconds: int | None,
        evidence_uri: str = "",
    ) -> dict:
        row = DrTestRun(
            project_id=project_id,
            test_type=test_type,
            environment=environment,
            status=status,
            rto_seconds=rto_seconds,
            rpo_seconds=rpo_seconds,
            evidence_uri=evidence_uri,
            executed_at=datetime.now(),
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        return DrTestService._out(row)

    @staticmethod
    def list(db: Session, project_id: int) -> list[dict]:
        rows = db.scalars(
            select(DrTestRun)
            .where(DrTestRun.project_id == project_id)
            .order_by(DrTestRun.executed_at.desc())
        )
        return [DrTestService._out(r) for r in rows]

    @staticmethod
    def _out(row: DrTestRun) -> dict:
        return {
            "id": row.id,
            "test_type": row.test_type,
            "environment": row.environment,
            "status": row.status,
            "rto_seconds": row.rto_seconds,
            "rpo_seconds": row.rpo_seconds,
            "evidence_uri": row.evidence_uri,
            "executed_at": row.executed_at,
        }


class PlatformReadinessEvaluator:
    """V40-018: deterministic Platform Readiness Gate over fixed thresholds."""

    # metric -> (comparison, threshold). lt = value < threshold, gt = value > threshold,
    # eq0 = value must be exactly 0.
    THRESHOLDS: dict[str, tuple[str, float]] = {
        ReadinessMetric.P0_FALSE_PASS_RATE.value: ("lt", 0.01),
        ReadinessMetric.FALSE_FAIL_RATE.value: ("lt", 0.03),
        ReadinessMetric.EVIDENCE_COMPLETENESS.value: ("gt", 0.99),
        ReadinessMetric.REPLAY_AUDIT_CONSISTENCY.value: ("gt", 0.99),
        ReadinessMetric.FIXTURE_CLEANUP_SUCCESS.value: ("gt", 0.99),
        ReadinessMetric.PROD_UNAUTHORIZED_WRITE.value: ("eq0", 0.0),
        ReadinessMetric.SECRET_LEAKAGE.value: ("eq0", 0.0),
        ReadinessMetric.PII_LEAKAGE.value: ("eq0", 0.0),
        ReadinessMetric.CONTRACT_UNAUTHORIZED_MUTATION.value: ("eq0", 0.0),
        ReadinessMetric.MISSION_WORKFLOW_ADOPTION.value: ("gt", 0.80),
    }

    @staticmethod
    def evaluate(metrics: dict[str, float]) -> dict:
        checks: list[dict[str, Any]] = []
        for metric, (cmp_, threshold) in PlatformReadinessEvaluator.THRESHOLDS.items():
            value = metrics.get(metric)
            if value is None:
                checks.append(
                    {"metric": metric, "pass": False, "reason": "missing"}
                )
                continue
            if cmp_ == "eq0":
                ok = value == 0
            elif cmp_ == "lt":
                ok = value < threshold
            else:  # gt
                ok = value > threshold
            checks.append(
                {
                    "metric": metric,
                    "value": value,
                    "threshold": threshold,
                    "pass": ok,
                }
            )
        failed = [c["metric"] for c in checks if not c["pass"]]
        return {"pass": not failed, "failed": failed, "checks": checks}
