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
    ap.add_argument("--backend-url", default=os.environ.get("TP_BACKEND_URL", "https://swiftbugs.cn/api/v1"))
    ap.add_argument("--username", default="sportsadmin")
    ap.add_argument("--password", default=os.environ.get("TP_ADMIN_PASSWORD", ""))
    ap.add_argument("--label", default="batch-111", help="证据目录标签（如 batch-112）")
    args = ap.parse_args()
    global EVIDENCE_DIR
    EVIDENCE_DIR = REPO_ROOT / "test-platform-v2" / "work-logs" / "evidence" / args.label
    if not args.password:
        print("ERROR: 需要 --password / TP_ADMIN_PASSWORD", flush=True)
        return 1

    with httpx.Client(base_url=args.backend_url.rstrip("/"), timeout=180,
                      headers={"Origin": "https://swiftbugs.cn", "X-Project-Id": "1"}) as c:
        r = c.post("/auth/login", json={"username": args.username, "password": args.password})
        r.raise_for_status()
        c.headers["Authorization"] = f"Bearer {r.json()['data']['access_token']}"

        envs = c.get("/environments").json().get("data", {})
        items = envs.get("items", []) if isinstance(envs, dict) else (envs if isinstance(envs, list) else [])
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

        # 2) 定时任务：平台 /schedules 仅支持 plan_id 绑定（schedule_service 校验 TestPlan），
        #    UiTestJob 无 cron 字段（B112-3 平台能力缺口）——UI job 定时需平台扩展，登记不阻塞。
        sched = None
        print("[schedule] skipped: 平台 /schedules 仅支持 plan 绑定，UI job 定时待平台扩展（B112-3）", flush=True)

        # 3) 触发一次
        r = c.post(f"/ui-tests/{job['id']}/trigger", json={"confirm_prod": True})
        r.raise_for_status()
        run = r.json()["data"]
        run_id = run.get("id") or run.get("run_id")
        print(f"[trigger] run id={run_id}", flush=True)

        # 4) 轮询运行报告（最多 10 分钟）
        run_status = ""
        run_result: dict = {}
        run_error = ""
        run_finished = ""
        for _ in range(60):
            time.sleep(10)
            rd = c.get(f"/ui-tests/runs/{run_id}").json().get("data", {})
            run_status = rd.get("status") or ""
            run_result = rd.get("result") or {}
            run_error = rd.get("error_message") or ""
            run_finished = rd.get("finished_at") or ""
            if run_status in ("success", "failed", "cancelled", "fail", "error"):
                print(f"[run] done status={run_status} finished={run_finished}", flush=True)
                break
            print(f"[run] polling status={run_status}", flush=True)

    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    out = EVIDENCE_DIR / "ui-schedule-summary.json"
    stdout_tail = str(run_result.get("stdout") or "")[-1500:]
    stderr_tail = str(run_result.get("stderr") or "")[-800:]
    out.write_text(json.dumps({
        "ui_job_id": job.get("id"), "schedule_id": (sched or {}).get("id"), "env_id": env_id,
        "schedule_note": "平台 /schedules 仅支持 plan 绑定（B112-3），UI job 定时待平台扩展",
        "trigger_run_id": run_id,
        "run_status": run_status,
        "run_error": run_error,
        "run_finished_at": run_finished,
        "stdout_tail": stdout_tail,
        "stderr_tail": stderr_tail,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[evidence] {out.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
