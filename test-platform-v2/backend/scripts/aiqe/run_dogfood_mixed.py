"""AUD-011：混合 Workflow Dogfood CLI（真实测试环境，禁止 Mock PASS）。

用法（在具备真实 Test 环境时）：

```bash
python scripts/aiqe/run_dogfood_mixed.py \
  --base-url http://test.internal \
  --admin-url http://admin.test.internal \
  --admin-username qa_admin --admin-password "$AIQE_ADMIN_PASSWORD" \
  --db-query-key verify_match_status \
  --runs 20 --report work-logs/evidence/aiqe-dogfood.json
```

缺少参数时直接失败（退出码 2），不会写任何"PASS"证据。
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="AIQE AUD-011 mixed workflow dogfood")
    parser.add_argument("--base-url", default="", help="被测 API/前端 base url")
    parser.add_argument("--admin-url", default="", help="运营后台 url")
    parser.add_argument("--admin-username", default="")
    parser.add_argument("--admin-password", default="")
    parser.add_argument("--db-query-key", default="", help="登记的只读 query_key（可选）")
    parser.add_argument("--project-id", type=int, default=1)
    parser.add_argument("--runs", type=int, default=1)
    parser.add_argument("--include-admin-ui", action="store_true")
    parser.add_argument("--include-public-ui", action="store_true")
    parser.add_argument("--allow-private-targets", action="store_true")
    parser.add_argument("--fixture-namespace", default="")
    parser.add_argument("--report", default="", help="报告输出路径（JSON）")
    args = parser.parse_args(argv)

    from app.aiqe.services.dogfood import DogfoodConfig, DogfoodConfigError, run_dogfood
    from app.core.db import SessionLocal

    config = DogfoodConfig(
        project_id=args.project_id,
        base_url=args.base_url,
        admin_url=args.admin_url,
        admin_username=args.admin_username,
        admin_password=args.admin_password,
        db_query_key=args.db_query_key,
        include_admin_ui=args.include_admin_ui,
        include_public_ui=args.include_public_ui,
        allow_private_targets=args.allow_private_targets,
        fixture_namespace=args.fixture_namespace or "aiqe-dogfood",
    )
    try:
        config.validate()
    except DogfoodConfigError as exc:
        print(f"DOGFOOD_CONFIG_ERROR: {exc}", file=sys.stderr)
        return 2

    db = SessionLocal()
    try:
        reports = run_dogfood(db, config, runs=args.runs)
    finally:
        db.close()
    payload = [report.payload() for report in reports]
    summary = {
        "runs": len(payload),
        "completed": sum(1 for item in payload if item["status"] == "COMPLETED"),
        "failed": sum(1 for item in payload if item["status"] != "COMPLETED"),
        "reports": payload,
    }
    text = json.dumps(summary, ensure_ascii=False, indent=2)
    print(text)
    if args.report:
        path = Path(args.report)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    return 0 if summary["failed"] == 0 else 1


if __name__ == "__main__":  # pragma: no cover - CLI 入口
    raise SystemExit(main())
