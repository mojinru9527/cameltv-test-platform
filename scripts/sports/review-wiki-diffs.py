"""体育平台承接 — wiki 差异任务结果评审（Batch 111，C110-1 后续）。

拉取 RAG vs Wiki 差异任务 → 差异项评审（采纳/驳回）→ 关键差异转待审 AI 产物。
运行: <venv-python> scripts/sports/review-wiki-diffs.py --password <pw>
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
    args = ap.parse_args()
    if not args.password:
        print("ERROR: 需要 --password / TP_ADMIN_PASSWORD", flush=True)
        return 1

    summary = {"tasks": []}
    with httpx.Client(base_url=args.backend_url.rstrip("/"), timeout=120,
                      headers={"Origin": "https://swiftbugs.cn", "X-Project-Id": "1"}) as c:
        r = c.post("/auth/login", json={"username": args.username, "password": args.password})
        r.raise_for_status()
        c.headers["Authorization"] = f"Bearer {r.json()['data']['access_token']}"

        tasks = c.get("/wiki/diff/tasks", params={"page_size": 50}).json().get("data", {}).get("items", [])
        print(f"[diff] 任务 {len(tasks)} 个", flush=True)
        for t in tasks:
            tid = t.get("id")
            detail = c.get(f"/wiki/diff/tasks/{tid}").json().get("data", {})
            status = detail.get("status")
            items = detail.get("items") or []
            entry = {"id": tid, "title": detail.get("title"), "status": status, "items": len(items)}
            reviewed = 0
            artifacts = []
            for it in items:
                if it.get("review_status") in ("accepted", "rejected"):
                    continue
                # 按严重级评审：P0/P1 采纳并转产物，其余驳回（记录）
                severity = it.get("severity", "P2")
                action = "accept" if severity in ("P0", "P1") else "reject"
                c.post(f"/wiki/diff/items/{it['id']}/{action}", json={"comment": f"Batch 111 评审：{action}"})
                if action == "accept":
                    art = c.post(f"/wiki/diff/items/{it['id']}/create-artifact",
                                 json={"artifact_type": "test_case"}).json().get("data", {})
                    artifacts.append(art.get("artifact_id"))
                reviewed += 1
            entry["reviewed"] = reviewed
            entry["artifacts"] = artifacts
            summary["tasks"].append(entry)
            print(f"[diff] task {tid} {detail.get('title')} status={status} items={len(items)} reviewed={reviewed} artifacts={len(artifacts)}", flush=True)
            time.sleep(1)

    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    out = EVIDENCE_DIR / "wiki-diff-review-summary.json"
    out.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[evidence] {out.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
