"""TC-AIQE-010 **本地 Service 测试**（evidence_kind=local_service_test）。

诚实边界（V1.6.2 / FIX-006）
---------------------------
- 本脚本直接调用 ``benchmark_service`` / ``learning_service``，属于 **本地 Service 测试**，
  不是产品 Agent workflow，也**不是** TC-AIQE-010 的产品级 PASS；
- 产品级结论固定输出 ``product_status=BLOCKED``：必须经正式 API
  （``POST /api/v1/aiqe/benchmarks/*``、``POST /api/v1/aiqe/learning/candidates/*``）
  由两个不同真实用户完成 benchmark/evaluate/approve/publish 才能主张产品级证据；
- 不再强制 ``DATABASE_URL`` 指向 ``work-logs/evidence/aiqe-v16/local-test/platform.db``：
  数据库必须显式指定（``--database-url`` / ``AIQE_LOCAL_SERVICE_TEST_DB``），默认使用
  独立的 ``local-service-test.db``；显式拒绝复用产品验收库；
- 样本口径：``总数 = 有效样本 + 剔除样本``，重复/非法样本逐条记录剔除原因，
  不再出现“数据集 N 条、结论写 M 条”的无记录差异；
- 预测器是确定性 stub（``controlled_predictor``），指标只证明服务端复算链路，
  不能作为模型质量结论。

用法::

    python scripts/aiqe/per_tc/futurewayu_learning_benchmark.py \
        --database-url sqlite:///./work-logs/evidence/aiqe-v162/local-service-test/local-service-test.db \
        --case-book "<用例整理 xlsx>"

退出码：0 = local_service_test PASS（仅当显式 ``--allow-local-only``）；
1 = local_service_test FAIL；2 = BLOCKED（产品级未接通 / 输入缺失）。
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BACKEND = ROOT / "test-platform-v2/backend"
DEFAULT_OUTPUT = (
    ROOT
    / "work-logs/evidence/aiqe-v162/local-service-test/TC-AIQE-010"
    / "learning-benchmark.local-service-test.json"
)
DEFAULT_DB = ROOT / "work-logs/evidence/aiqe-v162/local-service-test/local-service-test.db"
DEFAULT_CASE_BOOK = Path(
    r"C:\Users\26029\Desktop\未来娃屿V5.0_用例整理与问题登记_20261117 的手工验收(1)(1)(1)(1)(1).xlsx"
)

PROJECT_ID = 2
EVIDENCE_KIND = "local_service_test"
PRODUCT_TC_ID = "TC-AIQE-010"
PRODUCT_STATUS = "BLOCKED"
PRODUCT_OWNER = "qa-automation"
PRODUCT_BLOCKED_REASON = (
    "产品级 Benchmark/审批/发布链路未由本脚本经正式 API 执行：本脚本是本地 Service 测试，"
    "其 PASS 不能折算为 TC-AIQE-010 产品级 PASS"
)
PRODUCT_UNBLOCK_ACTION = (
    "在隔离 Test 项目配置 AI Provider 后，经 POST /api/v1/aiqe/benchmarks/datasets|freeze|runs 与 "
    "POST /api/v1/aiqe/learning/candidates|evaluate 由不同真实用户完成 approve/activate，"
    "并把机器产物归档到 docs/aiqe/v1.6/evidence/product/TC-AIQE-010/"
)

LABEL_PATTERN = re.compile(r"^[A-Z][A-Z0-9_]{0,63}$")
SAMPLE_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,119}$")
#: 标题关键词 → 标签（与历史口径一致）。
LABEL_RULES: tuple[tuple[str, str], ...] = (
    ("权限", "PERMISSION"),
    ("设备", "DEVICE"),
    ("上传", "UPLOAD"),
    ("订单", "ORDER"),
    ("退款", "REFUND"),
    ("登录", "LOGIN"),
    ("禁用词", "CONTENT"),
    ("界面", "UI"),
)


def label_of(title: str) -> str:
    for key, label in LABEL_RULES:
        if key in title:
            return label
    return "GENERAL"


def read_case_book(path: Path) -> list[dict]:
    """读取权威问题表（待复测 26 + 问题登记 WWY-*），保留原始顺序。"""
    from openpyxl import load_workbook

    rows: list[dict] = []
    workbook = load_workbook(path, read_only=True, data_only=True)
    try:
        sheet = workbook["03-待复测（26条）"]
        for row in sheet.iter_rows(min_row=3, values_only=True):
            if not row or not row[1]:
                continue
            title = str(row[3] or "")
            rows.append(
                {
                    "id": str(row[1]),
                    "title": title,
                    "label": label_of(title),
                    "ref": f"WX-{row[2]}",
                    "source": "sheet:03-待复测（26条）",
                }
            )
        sheet = workbook["02-问题登记表"]
        for row in sheet.iter_rows(min_row=3, values_only=True):
            if not row or not row[0] or not str(row[0]).startswith("WWY-"):
                continue
            title = str(row[3] or "")
            rows.append(
                {
                    "id": str(row[0]),
                    "title": title,
                    "label": label_of(title),
                    "ref": f"ISSUE-{row[1]}",
                    "source": "sheet:02-问题登记表",
                }
            )
    finally:
        workbook.close()
    return rows


def account_samples(raw_rows: list[dict]) -> tuple[list[dict], dict]:
    """样本口径：total = effective + duplicates + invalid（逐条记录剔除原因）。"""
    effective: list[dict] = []
    duplicates: list[dict] = []
    invalid: list[dict] = []
    seen: dict[str, dict] = {}
    for row in raw_rows:
        sample_id = str(row.get("id") or "").strip()
        label = str(row.get("label") or "").strip().upper()
        source = str(row.get("source") or "")
        if not sample_id or not SAMPLE_ID_PATTERN.match(sample_id):
            invalid.append(
                {"sample_id": sample_id, "source": source, "reason": "INVALID_SAMPLE_ID"}
            )
            continue
        if not label or not LABEL_PATTERN.match(label):
            invalid.append(
                {"sample_id": sample_id, "source": source, "reason": "INVALID_LABEL"}
            )
            continue
        if sample_id in seen:
            duplicates.append(
                {
                    "sample_id": sample_id,
                    "first_source": seen[sample_id]["source"],
                    "duplicate_source": source,
                    "reason": "DUPLICATE_SAMPLE_ID",
                }
            )
            continue
        normalized = {**row, "id": sample_id, "label": label}
        seen[sample_id] = normalized
        effective.append(normalized)
    composition = {
        "total_raw_rows": len(raw_rows),
        "effective_samples": len(effective),
        "duplicates_removed": duplicates,
        "invalid_rows_removed": invalid,
        "excluded_total": len(duplicates) + len(invalid),
        "by_source": dict(Counter(item["source"] for item in effective)),
        "by_label": dict(Counter(item["label"] for item in effective)),
        "accounting_ok": len(raw_rows) == len(effective) + len(duplicates) + len(invalid),
    }
    return effective, composition


def _resolve_database_url(cli_value: str | None) -> str:
    url = str(cli_value or os.environ.get("AIQE_LOCAL_SERVICE_TEST_DB") or "").strip()
    if not url:
        url = f"sqlite:///{DEFAULT_DB.as_posix()}"
    if "platform.db" in url:
        raise SystemExit(
            "REFUSED: 不得把 local_service_test 指向产品验收库 platform.db；"
            "请显式传入 --database-url（独立 local-service-test 库）"
        )
    return url


def _load_services(database_url: str) -> dict:
    """显式设置 DATABASE_URL 后加载服务（本地 Service 测试库，可重复执行）。"""
    os.environ["DATABASE_URL"] = database_url
    os.environ.setdefault("ENVIRONMENT", "development")
    if str(BACKEND) not in sys.path:
        sys.path.insert(0, str(BACKEND))
    import app.models  # noqa: F401 — 注册全部 ORM 模型
    from app.aiqe.services import benchmark_service, learning_service
    from app.core.db import Base
    from app.core.db import SessionLocal

    return {
        "Base": Base,
        "SessionLocal": SessionLocal,
        "benchmark_service": benchmark_service,
        "learning_service": learning_service,
    }


def _ensure_base_rows(db) -> tuple[int, int]:
    """创建隔离的 Project/两个真实用户（Owner != Approver）。"""
    from sqlalchemy import select

    from app.models.project import Project
    from app.models.user import User

    project = db.get(Project, PROJECT_ID)
    if project is None:
        db.add(
            Project(
                id=PROJECT_ID,
                code=f"AIQE-LOCAL-{PROJECT_ID}",
                name="AIQE local service test",
                owner_id=1,
                status=1,
            )
        )
        db.flush()
    owner = db.get(User, 1)
    if owner is None:
        owner = User(
            id=1,
            username="aiqe-local-owner",
            password="!local-service-test-only!",
            nickname="owner",
            email="owner@local.test",
            status=1,
        )
        db.add(owner)
        db.flush()
    approver = db.scalar(select(User).where(User.username == "aiqe-local-approver"))
    if approver is None:
        approver = User(
            username="aiqe-local-approver",
            password="!local-service-test-only!",
            nickname="approver",
            email="approver@local.test",
            status=1,
        )
        db.add(approver)
        db.flush()
    if int(owner.id) == int(approver.id):
        raise RuntimeError("Owner 与 Approver 必须是不同用户（双人审批）")
    return int(owner.id), int(approver.id)


def _controlled_predictor(golden: dict[str, str], *, wrong: int = 2):
    """确定性 stub 预测器（controlled_predictor）：只验证服务端复算链路。"""

    flipped = set(list(golden)[:wrong])

    def predict(sample):
        label = golden[sample.sample_id]
        if sample.sample_id in flipped:
            return [("GENERAL" if label != "GENERAL" else "UI")]
        return [label]

    return predict


def run_local_service_test(*, case_book: Path, database_url: str) -> dict:
    if not case_book.exists():
        return {
            "local_service_test_status": "BLOCKED",
            "blocked_reason": f"权威用例/问题表不存在: {case_book}",
            "sample_accounting": {},
        }
    raw_rows = read_case_book(case_book)
    samples, composition = account_samples(raw_rows)
    if not composition["accounting_ok"]:
        return {
            "local_service_test_status": "FAIL",
            "failure_reason": "样本口径不一致（total != effective + excluded）",
            "sample_accounting": composition,
        }
    if len(samples) < 30:
        return {
            "local_service_test_status": "BLOCKED",
            "blocked_reason": f"有效样本不足 30：{len(samples)}",
            "sample_accounting": composition,
        }

    services = _load_services(database_url)
    Base = services["Base"]
    db = services["SessionLocal"]()
    try:
        Base.metadata.create_all(bind=db.get_bind())
        owner_id, approver_id = _ensure_base_rows(db)
        benchmark_service = services["benchmark_service"]
        learning_service = services["learning_service"]

        dataset = benchmark_service.create_dataset(
            db,
            project_id=PROJECT_ID,
            dataset_key=f"futurewayu-v5-labels-local-{int(datetime.now(UTC).timestamp())}",
            task_type="learning",
            created_by=owner_id,
        )
        for sample in samples:
            benchmark_service.add_sample(
                db,
                dataset.id,
                sample_id=sample["id"],
                golden_labels=[sample["label"]],
                project_id=PROJECT_ID,
                input_refs=[sample["ref"]],
                source="futurewayu-v5",
                labeler="local-service-test",
                reviewer="local-service-test",
            )
        benchmark_service.freeze_dataset(
            db, dataset.id, approved_by=owner_id, project_id=PROJECT_ID
        )
        dataset = benchmark_service.get_dataset(db, dataset.id, project_id=PROJECT_ID)
        if int(dataset.sample_count or 0) != len(samples):
            raise RuntimeError(
                f"冻结后样本口径不一致: dataset={dataset.sample_count} effective={len(samples)}"
            )
        golden = {sample["id"]: sample["label"] for sample in samples}
        run = benchmark_service.run_benchmark(
            db,
            dataset_id=dataset.id,
            agent_key="A6",
            project_id=PROJECT_ID,
            agent_version="local-service-test",
            predictor=_controlled_predictor(golden),
        )
        metrics = benchmark_service.metrics_of(db, run.id, project_id=PROJECT_ID)
        candidate = learning_service.create_candidate(
            db,
            project_id=PROJECT_ID,
            rule={
                "pattern": "PERMISSION_BEFORE_VALIDATION",
                "description": "权限校验必须先于业务参数校验（WWY-V5-001）",
            },
            source="bug",
            created_by=owner_id,
        )
        learning_service.evaluate_candidate(
            db, candidate.id, benchmark_run_id=run.id, project_id=PROJECT_ID
        )
        approved = learning_service.approve_candidate(
            db,
            candidate.id,
            approved_by=approver_id,
            approval_reason="local_service_test 双人审批（Owner != Approver）",
            project_id=PROJECT_ID,
        )
        pattern = learning_service.publish_candidate(
            db, candidate.id, approved_by=approver_id, project_id=PROJECT_ID
        )
        db.commit()
        return {
            "local_service_test_status": "PASS",
            "sample_accounting": composition,
            "dataset": {
                "id": dataset.id,
                "sample_count": int(dataset.sample_count or 0),
                "content_hash": dataset.content_hash,
                "status": dataset.status,
                "gate_eligible": bool(dataset.gate_eligible),
            },
            "benchmark": {
                "run_id": run.id,
                "result_status": run.result_status,
                "metrics": metrics,
                "controlled_predictor": True,
            },
            "candidate": {
                "id": candidate.id,
                "owner_user_id": owner_id,
                "approver_user_id": approver_id,
                "status": approved.status,
                "published": pattern is not None,
                "gate_decision": approved.gate_decision,
            },
        }
    finally:
        db.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="TC-AIQE-010 local_service_test（非产品级）")
    parser.add_argument("--case-book", default=str(DEFAULT_CASE_BOOK))
    parser.add_argument("--database-url", default=None)
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument(
        "--allow-local-only",
        action="store_true",
        help="显式承认只有本地 Service 证据时返回 0（产品级仍为 BLOCKED）",
    )
    args = parser.parse_args(argv)

    database_url = _resolve_database_url(args.database_url)
    result = run_local_service_test(
        case_book=Path(args.case_book), database_url=database_url
    )
    local_status = str(result.get("local_service_test_status") or "BLOCKED")
    payload = {
        "schema_version": "1.0",
        "evidence_kind": EVIDENCE_KIND,
        "not_a_product_pass": True,
        "tc_id": PRODUCT_TC_ID,
        "product_status": PRODUCT_STATUS,
        "product_blocked_reason": PRODUCT_BLOCKED_REASON,
        "product_owner": PRODUCT_OWNER,
        "product_unblock_action": PRODUCT_UNBLOCK_ACTION,
        "local_service_test_status": local_status,
        "generated_at": datetime.now(UTC).isoformat(),
        "case_book": str(args.case_book),
        "database_url_kind": "explicit_local_service_test_sqlite",
        "run_command": (
            "python scripts/aiqe/per_tc/futurewayu_learning_benchmark.py "
            "--database-url <local-service-test sqlite> --case-book <xlsx>"
        ),
        **result,
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, default=str) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(
        json.dumps(
            {
                "evidence_kind": EVIDENCE_KIND,
                "local_service_test_status": local_status,
                "product_status": PRODUCT_STATUS,
                "sample_accounting": {
                    key: payload.get("sample_accounting", {}).get(key)
                    for key in ("total_raw_rows", "effective_samples", "excluded_total")
                },
                "output": str(output),
            },
            ensure_ascii=False,
        )
    )
    if local_status != "PASS":
        return 1
    if not args.allow_local_only:
        print(
            "BLOCKED: 产品级 TC-AIQE-010 证据未由正式 API 产生；"
            "本地 Service PASS 不能作为产品级通过（使用 --allow-local-only 仅表示接受本地证据）",
            file=sys.stderr,
        )
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
