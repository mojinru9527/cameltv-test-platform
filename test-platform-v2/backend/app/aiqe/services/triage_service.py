"""M3 / TA-025：Counterfactual Replay Coordinator（13 号 §19 TA-025）。

- 预置单变量实验 E1-E6；
- 每次实验必须且只能变更 1 个变量（双变量直接拒绝）；
- 每次实验落 `verification_run_id`；
- `idempotency_key` 唯一：重复调用返回原记录，不重复创建验证 Run。
"""
from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.aiqe.models.triage import TriageExperiment

EXPERIMENTS: dict[str, str] = {
    "E1": "replay_same_env",
    "E2": "disable_feature_flag",
    "E3": "isolated_profile",
    "E4": "reset_test_data",
    "E5": "isolate_concurrency",
    "E6": "normalize_network",
}


class ExperimentError(ValueError):
    pass


def validate_change(change: dict[str, Any]) -> tuple[str, str]:
    if not isinstance(change, dict) or len(change) != 1:
        raise ExperimentError("单变量实验必须且只能变更 1 个变量")
    (variable, value), = change.items()
    if not str(variable).strip():
        raise ExperimentError("变更变量名不能为空")
    if value is None:
        raise ExperimentError("变更值不能为空")
    return str(variable), str(value)


def run_experiment(
    db: Session,
    *,
    experiment_key: str,
    change: dict[str, Any],
    idempotency_key: str,
    triage_case_id: str | None = None,
    hypothesis_id: str | None = None,
    profile_id: str | None = None,
    verification_run_id: str | None = None,
) -> TriageExperiment:
    if experiment_key not in EXPERIMENTS:
        raise ExperimentError(f"未知实验: {experiment_key!r}（仅 E1-E6）")
    if not str(idempotency_key).strip():
        raise ExperimentError("idempotency_key 不能为空")

    existing = db.scalar(
        select(TriageExperiment).where(TriageExperiment.idempotency_key == idempotency_key)
    )
    if existing is not None:
        return existing

    variable, value = validate_change(change)
    row = TriageExperiment(
        triage_case_id=triage_case_id,
        hypothesis_id=hypothesis_id,
        experiment_key=experiment_key,
        changed_variable=variable,
        changed_value=value,
        profile_id=profile_id,
        verification_run_id=verification_run_id or str(uuid.uuid4()),
        idempotency_key=str(idempotency_key),
        status="completed",
    )
    db.add(row)
    db.flush()
    return row


def list_experiments(db: Session, triage_case_id: str) -> list[TriageExperiment]:
    return list(
        db.scalars(
            select(TriageExperiment)
            .where(TriageExperiment.triage_case_id == triage_case_id)
            .order_by(TriageExperiment.created_at)
        )
    )
