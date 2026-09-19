"""试点数据集与基线（Batch 261 / B4-2）。

09 方案 §2.3 的试点口径：接口 **50** 条 + Web UI **30** 条（P0 冒烟）。

**为什么是"选择器 + 基线快照"而不是一份写死的用例清单**：真实的 50+30 必须从目标环境的
资产库里选出来（本机库为空，见 C261-1）。把清单写死等于凭空造数据；交付**可选可验的选择器**
才能在有环境的机器上产出同一份清单，并且"选了哪些、够不够"是可核对的。

**硬约束（09 §3.1 / H3）**：基线快照里**不得出现任何被测系统凭据**。
账号只以"槽位名"引用（凭据由 `session_credentials_service` 在节点侧/运行时获取），
本服务有测试守着"凭据永不入快照"。
"""
from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import APIException
from app.modules.aitde.environment.fingerprint import (
    compute_fingerprint_hash,
    confidence_from_components,
)
from app.models.test_case import TestCase

# 试点目标（09 §2.3）
PILOT_API_TARGET = 50
PILOT_WEB_TARGET = 30
_PRIORITY_ORDER = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}


def _priority_rank(priority: str) -> int:
    return _PRIORITY_ORDER.get((priority or "").strip().upper(), 9)


def _select(
    db: Session, *, project_id: int, case_type: str, limit: int, module_prefix: str
) -> list[TestCase]:
    """按 P0→P3、再按 id 排序取前 N 条（确定性：同一库同一参数必得同一清单）。"""
    query = select(TestCase).where(
        TestCase.project_id == project_id, TestCase.case_type == case_type
    )
    if module_prefix:
        query = query.where(TestCase.module.like(f"{module_prefix}%"))
    rows = list(db.scalars(query).all())
    rows.sort(key=lambda case: (_priority_rank(case.priority), case.id))
    return rows[: max(0, limit)]


def select_pilot_cases(
    db: Session,
    *,
    project_id: int,
    api_limit: int = PILOT_API_TARGET,
    web_limit: int = PILOT_WEB_TARGET,
    module_prefix: str = "",
) -> dict:
    """选出试点数据集（接口 50 + Web 30）。不足目标时**如实报缺口**，不凑数。"""
    api_cases = _select(
        db, project_id=project_id, case_type="api", limit=api_limit, module_prefix=module_prefix
    )
    # Web 用例在本仓的 case_type 记为 ui（见 app/models/test_case.py:42）
    web_cases = _select(
        db, project_id=project_id, case_type="ui", limit=web_limit, module_prefix=module_prefix
    )

    def _brief(case: TestCase) -> dict:
        return {
            "id": case.id,
            "title": case.title,
            "module": case.module,
            "priority": case.priority,
        }

    shortfall = {
        "api": max(0, api_limit - len(api_cases)),
        "web": max(0, web_limit - len(web_cases)),
    }
    return {
        "project_id": project_id,
        "module_prefix": module_prefix,
        "targets": {"api": api_limit, "web": web_limit},
        "counts": {"api": len(api_cases), "web": len(web_cases)},
        "shortfall": shortfall,
        "meets_target": shortfall["api"] == 0 and shortfall["web"] == 0,
        "api": [_brief(case) for case in api_cases],
        "web": [_brief(case) for case in web_cases],
    }


def build_baseline(
    db: Session,
    *,
    project_id: int,
    environment_id: int,
    dataset: dict | None = None,
    account_slot: str = "",
    components: dict | None = None,
) -> dict:
    """生成基线快照：数据集 + 环境指纹 + 账号槽位**引用**（绝不含凭据）。

    `components` 是环境指纹的非密因子（service_versions / openapi_hash / db_schema_version …），
    直接复用既有 `compute_fingerprint_hash` 与 `confidence_from_components`，不另造指纹算法。
    """
    if environment_id <= 0:
        raise APIException(code=400, msg="environment_id 必填（指纹按环境维度）", http_status=400)
    resolved_dataset = dataset or select_pilot_cases(db, project_id=project_id)
    resolved_components = dict(components or {})
    fingerprint_hash = compute_fingerprint_hash(
        service_versions=resolved_components.get("service_versions"),
        openapi_hash=resolved_components.get("openapi_hash"),
        db_schema_version=resolved_components.get("db_schema_version"),
        config_hash=resolved_components.get("config_hash"),
        static_asset_hash=resolved_components.get("static_asset_hash"),
        frontend_version=resolved_components.get("frontend_version"),
    )
    return {
        "schema_version": 1,
        "generated_at": datetime.now(UTC).isoformat(),
        "project_id": project_id,
        "dataset": {
            "targets": resolved_dataset["targets"],
            "counts": resolved_dataset["counts"],
            "shortfall": resolved_dataset["shortfall"],
            "meets_target": resolved_dataset["meets_target"],
        },
        "environment": {
            "environment_id": environment_id,
            "fingerprint_hash": fingerprint_hash,
            "confidence": confidence_from_components(resolved_components),
            "components": resolved_components,
        },
        # 只放"槽位引用"，不放任何凭据（09 §3.1 / H3）
        "account_slot": {"name": account_slot, "credentials_in_baseline": False},
    }
