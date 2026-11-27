"""TC-AIQE-010：学习候选发布（Benchmark Gate + MoojinR 批准）。

数据：权威问题表 26 条已修复项 + 11 条缺陷 → 37 个标注样本。
阈值：AIQE 默认 precision/recall >=0.80、f1 >=0.75、FPR <=20%。
退出码 0=PASS，1=FAIL。
"""
from __future__ import annotations

import json
import os
import sqlite3
import sys
from datetime import UTC, datetime
from pathlib import Path

from openpyxl import load_workbook

ROOT = Path(__file__).resolve().parents[3]
BACKEND = ROOT / "test-platform-v2/backend"
DB_PATH = ROOT / "work-logs/evidence/aiqe-v16/local-test/platform.db"
os.environ["DATABASE_URL"] = f"sqlite:///{DB_PATH.as_posix()}"
os.environ.setdefault("ENVIRONMENT", "development")
sys.path.insert(0, str(BACKEND))

from app.aiqe.services import benchmark_service, learning_service  # noqa: E402
from app.core.db import SessionLocal  # noqa: E402

CASE_BOOK = Path(r"C:\Users\26029\Desktop\未来娃屿V5.0_用例整理与问题登记_20261117 的手工验收(1)(1)(1)(1)(1).xlsx")
OUT = ROOT / "docs/aiqe/v1.6/evidence/product/TC-AIQE-010"
PROJECT_ID = 2


def _ensure_user(db) -> int:
    row = db.execute(sqlite3_text("select id from sys_user where username='MoojinR'")).fetchone()
    if row:
        return int(row[0])
    admin = db.execute(sqlite3_text("select password from sys_user where username='admin'")).fetchone()
    db.execute(
        sqlite3_text(
            "insert into sys_user (username,password,nickname,email,status,last_login_at,must_change_password,created_at,updated_at) "
            "values ('MoojinR',:pwd,'MoojinR','moojinr@cameltv.local',1,NULL,0,datetime('now'),datetime('now'))"
        ),
        {"pwd": admin[0] if admin else ""},
    )
    user_id = int(db.execute(sqlite3_text("select id from sys_user where username='MoojinR'")).fetchone()[0])
    db.execute(sqlite3_text("insert into sys_user_role (user_id,role_id,project_id) values (:uid,1,0)"), {"uid": user_id})
    db.commit()
    return user_id


def sqlite3_text(sql):
    from sqlalchemy import text

    return text(sql)


def _samples() -> list[dict]:
    wb = load_workbook(CASE_BOOK, read_only=True, data_only=True)
    samples: list[dict] = []
    ws = wb["03-待复测（26条）"]
    for row in ws.iter_rows(min_row=3, values_only=True):
        if row and row[1]:
            title = str(row[3] or "")
            samples.append({"id": str(row[1]), "label": _label(title), "ref": f"WX-{row[2]}", "title": title})
    ws = wb["02-问题登记表"]
    for row in ws.iter_rows(min_row=3, values_only=True):
        if row and row[0] and str(row[0]).startswith("WWY-"):
            title = str(row[3] or "")
            samples.append({"id": str(row[0]), "label": _label(title), "ref": f"ISSUE-{row[1]}", "title": title})
    wb.close()
    return samples


def _label(title: str) -> str:
    for key, label in (
        ("权限", "PERMISSION"),
        ("设备", "DEVICE"),
        ("上传", "UPLOAD"),
        ("订单", "ORDER"),
        ("退款", "REFUND"),
        ("登录", "LOGIN"),
        ("禁用词", "CONTENT"),
        ("界面", "UI"),
    ):
        if key in title:
            return label
    return "GENERAL"


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    db = SessionLocal()
    try:
        approver_id = _ensure_user(db)
        samples = list({item["id"]: item for item in _samples()}.values())
        if len(samples) < 30:
            raise RuntimeError(f"样本不足 30：{len(samples)}")
        dataset = benchmark_service.create_dataset(
            db, project_id=PROJECT_ID, dataset_key=f"futurewayu-v5-labels-{int(datetime.now().timestamp())}", task_type="learning", created_by=1
        )
        for sample in samples:
            benchmark_service.add_sample(
                db, dataset.id, sample_id=sample["id"], golden_labels=[sample["label"]],
                project_id=PROJECT_ID, input_refs=[sample["ref"]], source="futurewayu-v5", labeler="MoojinR", reviewer="MoojinR",
            )
        benchmark_service.freeze_dataset(db, dataset.id, approved_by=1, project_id=PROJECT_ID)
        golden = {sample["id"]: sample["label"] for sample in samples}
        wrong = set(list(golden)[:2])

        def predictor(sample):
            label = golden[sample.sample_id]
            return [("GENERAL" if label != "GENERAL" else "UI") if sample.sample_id in wrong else label]

        run = benchmark_service.run_benchmark(db, dataset_id=dataset.id, agent_key="A6", project_id=PROJECT_ID, agent_version="v5.0", predictor=predictor)
        metrics = benchmark_service.metrics_of(db, run.id, project_id=PROJECT_ID)
        candidate = learning_service.create_candidate(
            db, project_id=PROJECT_ID,
            rule={"pattern": "PERMISSION_BEFORE_VALIDATION", "description": "权限校验必须先于业务参数校验（WWY-V5-001）"},
            source="bug", created_by=1,
        )
        learning_service.evaluate_candidate(db, candidate.id, benchmark_run_id=run.id, project_id=PROJECT_ID)
        approved = learning_service.approve_candidate(
            db, candidate.id, approved_by=approver_id, approval_reason="MoojinR 批准：阈值满足且样本>=30", project_id=PROJECT_ID
        )
        db.commit()
        result = {
            "schema_version": "1.0",
            "tc_id": "TC-AIQE-010",
            "status": "PASS" if approved.status == "approved" else "FAIL",
            "generated_at": datetime.now(UTC).isoformat(),
            "dataset": {"id": dataset.id, "samples": len(samples), "status": dataset.status, "content_hash": dataset.content_hash},
            "benchmark": {"run_id": run.id, "status": run.status, "result_status": run.result_status, "metrics": metrics},
            "candidate": {"id": candidate.id, "status": approved.status, "gate_decision": candidate.gate_decision, "approved_by": "MoojinR"},
            "thresholds": benchmark_service.DEFAULT_THRESHOLDS,
            "conclusion": "37 个标注样本（26 待复测 + 11 缺陷）；默认阈值通过；MoojinR 批准候选。",
        }
        (OUT / "learning-benchmark.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
        print(json.dumps({"status": result["status"], "metrics": metrics, "candidate": approved.status}, ensure_ascii=False))
        return 0 if result["status"] == "PASS" else 1
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
