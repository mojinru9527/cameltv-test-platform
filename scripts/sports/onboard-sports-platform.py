"""体育平台承接 — 一键接入测试平台（Batch 101）。

流程: 登录 → 项目 → 创建 CI Token → 导入 7 个真实 Test5 契约（API 资产+测试计划）
      → 创建生产环境与变量 → 创建 UI 只读冒烟任务 → 创建音视频任务（可选）
      → 创建每日 API 回归定时任务 → 输出证据 JSON。
运行: <venv-python> scripts/sports/onboard-sports-platform.py --password <pw> [--backend-url ...]
凭据: --password 或环境变量 TP_ADMIN_PASSWORD；Token 明文仅打印一次。
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

import httpx


CONTRACTS_DIR = Path("test-platform-v2/tests/api-testing/specs/test5-contracts")
EXPECTED_TEXT = "Football Today - Watch Live Streaming"
ALLOWED_HOSTS = (
    "www.camel1.tv,api.cameltv.live,www.cameltv.live,livecdn.cameltv.live,img.cameltv.live,"
    "d3q5i0g1zfzd69.cloudfront.net,www.googletagmanager.com,www.google-analytics.com,"
    "stats.g.doubleclick.net,fonts.googleapis.com,fonts.gstatic.com,"
    "accounts.google.com,analytics.google.com,www.facebook.com,www.google.com.sg,sensors.cameltv.live"
)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--backend-url", default="http://127.0.0.1:8048/api/v1")
    ap.add_argument("--username", default="admin")
    ap.add_argument("--password", default=os.environ.get("TP_ADMIN_PASSWORD", ""))
    ap.add_argument("--contracts-dir", default=str(CONTRACTS_DIR))
    ap.add_argument("--ui-spec", default="specs/production-smoke.spec.ts")
    ap.add_argument("--av-url", default="")
    ap.add_argument("--cron", default="0 3 * * *")
    ap.add_argument("--origin", default="http://localhost:5218")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    if not args.password:
        print("ERROR: 需要 --password 或环境变量 TP_ADMIN_PASSWORD", flush=True)
        return 1

    base = args.backend_url.rstrip("/")
    headers = {"X-Project-Id": "0", "Origin": args.origin}
    summary: dict = {"backend": base, "dry_run": args.dry_run}

    def call(method: str, path: str, **kw):
        if args.dry_run:
            print(f"[dry-run] {method} {path} {json.dumps(kw.get('json', {}), ensure_ascii=False)[:200]}", flush=True)
            if path == "/auth/login":
                return {"access_token": "dry-run-token"}
            if path == "/projects":
                return [{"id": 1}]
            if path == "/tokens":
                return {"token": "dry-run-token"}
            if path.startswith("/apitest/import/preview"):
                return {"total": 0, "endpoints_count": 0}
            if path.startswith("/apitest/import/confirm"):
                return {"imported": 0, "plans": []}
            if path.startswith("/environments") and method == "POST":
                return {"id": 1}
            if "/variables" in path and method == "POST":
                return {"id": 1}
            if path == "/ui-tests" and method == "POST":
                return {"id": 1}
            if path.startswith("/av-checks") and method == "POST":
                return {"id": 1}
            if path == "/test-plans":
                return {"items": [{"id": 1, "name": "体育平台-测试"}]}
            if path.startswith("/schedules") and method == "POST":
                return {"id": 1}
            return {"dry_run": True}
        r = httpx.request(method, base + path, headers=headers, timeout=300, **kw)
        if r.status_code >= 400:
            print(f"ERROR {method} {path} -> {r.status_code}: {r.text[:300]}", flush=True)
            raise SystemExit(1)
        return r.json()["data"]

    # 1. 登录
    login = call("POST", "/auth/login", json={"username": args.username, "password": args.password})
    token = login.get("access_token") or "dry-run-token"
    headers["Authorization"] = f"Bearer {token}"
    print("[login] ok", flush=True)

    # 2. 项目
    projects = call("GET", "/projects")
    project_id = projects[0]["id"] if projects else 0
    headers["X-Project-Id"] = str(project_id)
    summary["project_id"] = project_id
    print(f"[project] id={project_id}", flush=True)

    # 3. CI Token（明文仅打印一次）
    tok = call("POST", "/tokens", json={"name": "sports-ci", "scopes": ["trigger", "api"]})
    plain_token = tok.get("token") or tok.get("plain") or tok.get("token_value") or ""
    if plain_token:
        print(f"[token] 请保存（仅此一次）: {plain_token}", flush=True)
    summary["token_name"] = "sports-ci"

    # 4. 契约导入（7 个真实契约；no-contract 跳过）
    imported = []
    skipped = []
    contracts_dir = Path(args.contracts_dir)
    for f in sorted(contracts_dir.glob("*.openapi.json")):
        if f.stat().st_size < 1024:
            skipped.append({"service": f.stem, "note": "no-contract/占位"})
            continue
        service = f.stem.replace(".openapi", "")
        spec = f.read_text(encoding="utf-8")
        try:
            preview = call("POST", "/apitest/import/preview", json={
                "service_name": service, "source_type": "openapi_text",
                "source_ref": f.name, "spec_content": spec,
            })
            confirm = call("POST", "/apitest/import/confirm", json={
                "service_name": service, "source_type": "openapi_text",
                "source_ref": f.name, "spec_content": spec,
                "generate_cases": False, "create_plan": True,
                "plan_name": f"体育平台-{service}",
            })
            imported.append({
                "service": service,
                "preview_endpoints": preview.get("total_count", 0),
                "confirm": confirm,
            })
            print(f"[import] {service}: preview={preview.get('total_count', 0)}", flush=True)
        except Exception as exc:
            print(f"[import] {service}: FAILED {exc}", flush=True)
            skipped.append({"service": service, "note": str(exc)})
    summary["imported"] = imported
    summary["skipped"] = skipped

    # 4b. 生成用例 + 建计划（供每日回归定时任务绑定）
    plan_service = "camel-service"
    plan_file = contracts_dir / f"{plan_service}.openapi.json"
    if plan_file.exists() and plan_file.stat().st_size >= 1024:
        plan_spec = plan_file.read_text(encoding="utf-8")
        plan_confirm = call("POST", "/apitest/import/confirm", json={
            "service_name": plan_service, "source_type": "openapi_text",
            "source_ref": plan_file.name, "spec_content": plan_spec,
            "generate_cases": True, "create_plan": True,
            "plan_name": "体育平台-每日回归",
        })
        summary["plan_import"] = plan_confirm
        print(f"[plan-import] {plan_service}: generated={plan_confirm.get('generated_case_count', '?')}", flush=True)
    else:
        summary["plan_import"] = None
        print("[plan-import] 跳过（camel-service 契约缺失）", flush=True)

    # 5. 生产环境 + 变量
    env = call("POST", "/environments", json={
        "name": "体育平台-生产", "env_type": "prod",
        "base_url": "https://www.camel1.tv", "is_production": True,
        "description": "体育平台生产只读接入（Batch 101）",
    })
    env_id = env["id"]
    for key, value in {
        "PROD_ALLOWED_HOSTS": ALLOWED_HOSTS,
        "PROD_EXPECTED_BUSINESS_TEXT": EXPECTED_TEXT,
        "PROD_SMOKE_OWNER": "sports-integration",
        "PROD_LOGIN_AUTHORIZED": "false",
    }.items():
        call("POST", f"/environments/{env_id}/variables", json={"key": key, "value": value})
    summary["environment_id"] = env_id
    print(f"[environment] id={env_id} (prod)", flush=True)

    # 6. UI 只读冒烟任务
    job = call("POST", "/ui-tests", json={
        "name": "体育平台-生产只读冒烟",
        "description": "真实浏览器访问 www.camel1.tv（Batch 101 承接）",
        "test_spec": args.ui_spec, "browser": "chromium", "environment_id": env_id,
    })
    summary["ui_job_id"] = job["id"]
    print(f"[ui-job] id={job['id']} spec={args.ui_spec}", flush=True)

    # 7. 音视频任务（真实 URL 待业务提供时补全）
    if args.av_url:
        av = call("POST", "/av-checks", json={
            "name": "体育平台-MatchReplays", "stream_url": args.av_url, "protocol": "HLS",
        })
        summary["av_task_id"] = av["id"]
        print(f"[av-task] id={av['id']}", flush=True)
    else:
        summary["av_task_id"] = None
        print("[av-task] 跳过（--av-url 待业务提供真实回放 URL）", flush=True)

    # 8. 每日 API 回归定时任务（绑定导入生成的计划）
    plans = call("GET", "/test-plans")
    items = plans.get("items", plans if isinstance(plans, list) else [])
    plan = next((p for p in items if str(p.get("name", "")).startswith("体育平台-")), None)
    if plan:
        sched = call("POST", "/schedules", json={
            "name": "体育平台-每日API回归", "description": "Batch 101 承接",
            "plan_id": plan["id"], "cron_expression": args.cron, "enabled": True,
        })
        summary["schedule_id"] = sched["id"]
        print(f"[schedule] id={sched['id']} plan={plan['name']} cron={args.cron}", flush=True)
    else:
        summary["schedule_id"] = None
        print("[schedule] 未找到体育平台计划，跳过（请检查导入 create_plan）", flush=True)

    out_dir = Path("test-platform-v2/work-logs/evidence/batch-101")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "sports-onboarding-summary.json"
    out_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[evidence] saved: {out_path}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
