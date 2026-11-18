"""AIQE 状态对账 CLI（生产/测试环境建议每 1-5 分钟由 cron 执行）。

用法：
  python scripts/qa/aiqe_reconcile.py [--stale-seconds 900] [--limit 200]

退出码：0 = 执行成功（即使收敛了悬挂记录）；2 = 执行异常。
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_BACKEND = Path(__file__).resolve().parents[2] / "test-platform-v2" / "backend"
if str(REPO_BACKEND) not in sys.path:
    sys.path.insert(0, str(REPO_BACKEND))

from app.aiqe.services.reconciler import reconcile  # noqa: E402
from app.core.db import SessionLocal  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stale-seconds", type=int, default=900)
    parser.add_argument("--limit", type=int, default=200)
    args = parser.parse_args()
    db = SessionLocal()
    try:
        stats = reconcile(db, stale_seconds=args.stale_seconds, limit=args.limit)
        db.commit()
        print(json.dumps({"ok": True, **stats}, ensure_ascii=False))
        return 0
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        print(
            json.dumps(
                {"ok": False, "error": f"{type(exc).__name__}: {exc}"},
                ensure_ascii=False,
            )
        )
        return 2
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
