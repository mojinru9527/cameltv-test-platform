"""Convergence service — B14 D 级收敛：TestPlan 只读归档、资产视图统一为单一事实源（VersionTask）。"""
from __future__ import annotations

import json

from sqlalchemy.orm import Session

from app.models.dataset import Dataset
from app.models.release_bundle import ReleaseBundle
from app.models.test_plan import TestPlan
from app.models.version_task import VersionTask
from app.core.exceptions import not_found


def archive_test_plan(db: Session, test_plan_id: int, version_task_id: int) -> dict:
    """把 TestPlan 标记为只读归档，并绑定到 VersionTask（不双写）。"""
    plan = db.get(TestPlan, test_plan_id)
    if plan is None:
        raise not_found("测试计划不存在")
    task = db.get(VersionTask, version_task_id)
    if task is None:
        raise not_found("版本验收任务不存在")
    plan.status = "archived"
    db.commit()
    return {"test_plan_id": plan.id, "status": plan.status, "converged_to_task": task.id}


def unified_assets_view(db: Session, project_id: int) -> dict:
    """D 级收敛：把 TestPlan/数据集/发布包/环境 收束为一个资产视图（单一事实源视角）。"""
    plans = db.query(TestPlan).filter(TestPlan.project_id == project_id).all()
    datasets = db.query(Dataset).filter(Dataset.project_id == project_id).all()
    bundles = db.query(ReleaseBundle).filter(ReleaseBundle.project_id == project_id).all()
    tasks = db.query(VersionTask).filter(VersionTask.project_id == project_id).all()
    return {
        "version_tasks": [
            {"id": t.id, "title": t.title, "version": t.version, "status": t.status, "verdict": t.verdict}
            for t in tasks
        ],
        "test_plans": [
            {"id": p.id, "name": p.name, "status": p.status, "archived": p.status == "archived"}
            for p in plans
        ],
        "datasets": [{"id": d.id, "name": d.name, "row_count": d.row_count} for d in datasets],
        "release_bundles": [{"id": b.id, "name": b.name, "status": b.status} for b in bundles],
        "single_fact_source": "version_task",
    }


def merged_data_assets(db: Session, project_id: int) -> dict:
    """B14 Dataset/Fixtures 合并视图：把数据集统一为『数据资产』（不双写）。"""
    datasets = db.query(Dataset).filter(Dataset.project_id == project_id).all()
    return {
        "data_assets": [
            {
                "id": d.id, "name": d.name, "source_type": d.source_type,
                "row_count": d.row_count, "columns": json.loads(d.columns_meta or "[]"),
            }
            for d in datasets
        ]
    }
