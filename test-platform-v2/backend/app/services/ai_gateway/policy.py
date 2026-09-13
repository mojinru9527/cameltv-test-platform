"""Convert shadow comparison facts into a conservative routing recommendation."""
from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.ai_shadow_run import AiShadowRun


def evaluate_shadow_policy(
    db: Session,
    project_id: int,
    *,
    namespace: str | None = None,
    min_samples: int = 20,
) -> dict[str, Any]:
    """Recommend a route mode without automatically changing configuration."""
    statement = select(AiShadowRun).where(AiShadowRun.project_id == project_id)
    if namespace:
        statement = statement.where(AiShadowRun.namespace == namespace)
    rows = list(db.scalars(statement.order_by(AiShadowRun.id.desc()).limit(500)).all())
    total = len(rows)
    succeeded = [row for row in rows if row.status == "succeeded"]
    success_count = len(succeeded)
    json_ok = sum(1 for row in succeeded if row.shadow_json_valid)
    exact = sum(1 for row in succeeded if row.exact_match)
    latency_deltas = [int(row.shadow_duration_ms or 0) - int(row.primary_duration_ms or 0) for row in succeeded]
    avg_delta = round(sum(latency_deltas) / len(latency_deltas), 1) if latency_deltas else 0.0
    success_rate = round(success_count / total, 4) if total else 0.0
    json_valid_rate = round(json_ok / success_count, 4) if success_count else 0.0
    exact_match_rate = round(exact / success_count, 4) if success_count else 0.0

    rationale: list[str] = []
    if total < max(1, min_samples):
        recommendation = "shadow_more"
        rationale.append(f"样本不足：{total}/{max(1, min_samples)}")
    elif success_rate < 0.95:
        recommendation = "keep_cloud"
        rationale.append(f"本地成功率偏低：{success_rate:.2%}")
    elif json_valid_rate < 0.99:
        recommendation = "keep_cloud"
        rationale.append(f"本地 JSON 合法率偏低：{json_valid_rate:.2%}")
    elif avg_delta > 0 and avg_delta > 5000:
        recommendation = "shadow_more"
        rationale.append(f"本地平均延迟增量过大：{avg_delta:.0f}ms")
    elif exact_match_rate < 0.80:
        recommendation = "shadow_more"
        rationale.append(f"输出一致率不足：{exact_match_rate:.2%}")
    else:
        recommendation = "local_preferred"
        rationale.append(f"样本与质量达标：一致率 {exact_match_rate:.2%}")
    rationale.append("推荐不会自动改配置；需管理员显式切换 AI_RUNTIME_MODE")

    return {
        "namespace": namespace or "",
        "sample_count": total,
        "min_samples": max(1, min_samples),
        "success_rate": success_rate,
        "json_valid_rate": json_valid_rate,
        "exact_match_rate": exact_match_rate,
        "avg_latency_delta_ms": avg_delta,
        "recommendation": recommendation,
        "rationale": rationale,
    }
