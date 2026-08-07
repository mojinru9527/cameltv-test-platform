"""体育平台承接 — P0 UI 自动化定时回归（Batch 111）。

创建 production-p0 UI job（绑定生产环境）+ 每日定时任务 + 触发一次验证。
运行: <venv-python> scripts/sports/setup-ui-schedule.py --password <pw>
"""
from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path

import httpx


REPO_ROOT = Path(__file__).resolve().parents[2]
EVIDENCE_DIR = REPO_ROOT / "test-platform-v2" / "work-logs" / "evidence" / "batch-111"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--backend-url", default=os.environ.get("TP_BACKEND_URL", "https://test-platform.up.railway.app/api/v1"))
    ap.add_argument("--username", default="sportsadmin")
    ap.add_argument("--password", default=os.environ.get("TP_ADMIN_PASSWORD", ""))
    args = ap.parse_args()
    if not args.password:
        print("ERROR: 需要 --password / TP_ADMIN_PASSWORD", flush=True)
        return 1

    with httpx.Client(base_url=args.backend_url.rstrip("/"), timeout=180,
                      headers={"Origin": "https://cameltv-test-platform1.vercel.app", "X-Project-Id": "1"}) as c:
        r = c.post("/auth/login", json={"username": args.username, "password": args.password})
        r.raise_for_status()
        c.headers["Authorization"] = f"Bearer {r.json()['data']['access_token']}"

        envs = c.get("/environments").json().get("data", {})
        items = envs.get("items", envs if isinstance(envs, list) else [])
        env = next((e for e in items if "生产" in str(e.get("name", ""))), None)
        if not env:
            print("ERROR: 未找到生产环境", flush=True)
            return 1
        env_id = env["id"]

        # 1) UI job
        jobs = c.get("/ui-tests").json().get("data", {})
        existing = next((j for j in (jobs.get("items") or []) if "P0" in str(j.get("name", ""))), None)
        if existing:
            job = existing
            print(f"[ui-job] exists id={job['id']}", flush=True)
        else:
            r = c.post("/ui-tests", json={
                "name": "体育平台-P0-每日生产只读回归",
                "description": "P0 功能用例 → UI 自动化（Batch 110/111）",
                "test_spec": "specs/production-p0-modules.spec.ts",
                "browser": "chromium",
                "environment_id": env_id,
            })
            r.raise_for_status()
            job = r.json()["data"]
            print(f"[ui-job] created id={job['id']}", flush=True)

        # 2) 定时任务（每日 02:00 UTC）
        scheds = c.get("/schedules").json().get("data", {})
        s_items = scheds.get("items", scheds if isinstance(scheds, list) else [])
        sched = next((s for s in s_items if "P0" in str(s.get("name", ""))), None)
        if sched:
            print(f"[schedule] exists id={sched['id']}", flush=True)
        else:
            r = c.post("/schedules", json={
                "name": "体育平台-P0-每日生产只读回归",
                "description": "P0 UI 自动化每日回归（Batch 111）",
                "cron_expression": "0 2 * * *",
                "enabled": True,
            })
            r.raise_for_status()
            sched = r.json()["data"]
            print(f"[schedule] created id={sched['id']}", flush=True)

        # 3) 触发一次
        r = c.post(f"/ui-tests/{job['id']}/trigger")
        r.raise_for_status()
        run = r.json()["data"]
        print(f"[trigger] run id={run.get('id')}", flush=True)
        time.sleep(5)

    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    out = EVIDENCE_DIR / "ui-schedule-summary.json"
    out.write_text(json.dumps({
        "ui_job_id": job.get("id"), "schedule_id": sched.get("id"), "env_id": env_id,
        "trigger_run_id": run.get("id"),
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[evidence] {out.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
