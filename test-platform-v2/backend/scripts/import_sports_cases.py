# -*- coding: utf-8 -*-
"""体育全模块用例批量入库（Batch 125 / Slice 4，部署后执行）。

读取 module-cases-consolidated.json（基础用例 + 深度用例），通过 POST /test-cases 批量入库。
幂等：按 case_id 查重（已存在跳过）。

用法:
    python scripts/import_sports_cases.py --password <TP_ADMIN_PASSWORD> [--dry-run]
凭据: --password 或环境变量 TP_ADMIN_PASSWORD。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from pathlib import Path

import httpx

REPO_ROOT = Path(__file__).resolve().parents[3]
BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.test_case_taxonomy import (  # noqa: E402
    CaseTaxonomyLocation,
    canonical_case_location,
    extract_terminal_scopes,
)

CONSOLIDATED = REPO_ROOT / "test-platform-v2" / "work-logs" / "evidence" / "batch-125" / "module-cases-consolidated.json"


def stable_case_id(c: dict, source_module: str, prefix: str = "SP-B125") -> str:
    """Keep curated global IDs; namespace repeated base ``TC-*`` IDs stably."""
    curated = str(c.get("case_id") or "").strip()
    if curated:
        return curated
    identity = {
        "source_module": source_module,
        "legacy_id": c.get("id", ""),
        "title": c.get("title", ""),
        "domain": c.get("domain", ""),
        "module": c.get("module", ""),
        "preconditions": c.get("preconditions", ""),
    }
    digest = hashlib.sha256(
        json.dumps(identity, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()[:16].upper()
    return f"{prefix}-{digest}"


def _terminal_scope_tags(c: dict) -> list[str]:
    values: list[str] = []
    for field in ("platforms", "client_scope"):
        raw = c.get(field) or []
        values.extend(raw if isinstance(raw, list) else [str(raw)])
    joined = " ".join(values)
    scopes = set(extract_terminal_scopes(joined, c.get("domain", ""), c.get("module", "")))
    normalized_tokens = {value.lower().replace("-", "").replace("_", "") for value in values}
    if normalized_tokens & {"app", "android", "ios", "安卓ios", "安卓/ios"}:
        scopes.add("安卓/iOS")
    if normalized_tokens & {"pc", "pcweb", "desktop"}:
        scopes.add("PC Web")
    if normalized_tokens & {"mweb", "mobile", "mobileweb", "h5", "移动端web"}:
        scopes.add("移动 Web")
    order = ("安卓/iOS", "PC Web", "移动 Web")
    return [f"端:{scope}" for scope in order if scope in scopes]


def infer_case_nature(c: dict) -> str:
    explicit = str(c.get("positive_negative") or "").strip().lower()
    if explicit in {"positive", "negative", "boundary"}:
        return explicit
    text = " ".join(str(c.get(field) or "") for field in (
        "title", "preconditions", "expected_result", "remark", "tags",
    ))
    boundary_words = (
        "边界", "上限", "下限", "临界", "最大值", "最小值", "空态", "为空", "无数据",
    )
    negative_words = (
        "未登录", "无权限", "不足", "失败", "异常", "非法", "错误", "被拦截", "拒绝",
        "过期", "已关闭", "超时", "断网", "5xx", "重复", "超限", "不可用", "不一致",
        "缺失", "取消退款", "越权",
    )
    if any(word in text for word in boundary_words):
        return "boundary"
    if any(word in text for word in negative_words):
        return "negative"
    return "positive"


def _location_with_authoritative_source(
    c: dict,
    source_module: str,
) -> CaseTaxonomyLocation:
    """Keep the inventory surface/domain authoritative during full import.

    Names such as ``商城`` and ``UGC`` legitimately exist on both product
    surfaces, so a bare historical domain cannot identify its surface.  The
    consolidated inventory key already carries that missing context.  Raw
    taxonomy remains useful only as the descendant module path.
    """
    case_type = str(c.get("case_type") or "manual")
    location = canonical_case_location(
        str(c.get("domain") or source_module),
        str(c.get("module") or source_module),
        case_type,
    )
    source_location = canonical_case_location(source_module, "", case_type)
    if source_location.surface not in {"用户端", "运营后台"}:
        return location

    if location.domain == source_location.domain:
        module_path = location.module_path
    else:
        module_path = "/".join(
            part for part in (location.domain, location.module_path) if part
        )
    return CaseTaxonomyLocation(
        surface=source_location.surface,
        domain=source_location.domain,
        module_path=module_path,
        terminal_scopes=location.terminal_scopes,
    )


def to_create(c: dict, source_module: str, prefix: str = "SP-B125") -> dict:
    steps = c.get("steps") or []
    if isinstance(steps, str):
        try:
            steps = json.loads(steps)
        except Exception:
            steps = []
    tags = c.get("tags") or []
    if isinstance(tags, str):
        try:
            tags = json.loads(tags)
        except Exception:
            tags = []
    tags = [str(tag) for tag in tags]
    for scope_tag in _terminal_scope_tags(c):
        if scope_tag not in tags:
            tags.append(scope_tag)

    location = _location_with_authoritative_source(c, source_module)
    canonical_domain = (
        f"{location.surface}/{location.domain}"
        if location.surface != "其他"
        else location.domain
    )
    case_nature = infer_case_nature(c)
    design_method = str(c.get("case_design_method") or "").strip()
    if not design_method:
        design_method = {
            "positive": "场景法",
            "negative": "错误推测",
            "boundary": "边界值分析",
        }[case_nature]
    steps_payload = []
    for i, s in enumerate(steps, start=1):
        if isinstance(s, dict):
            steps_payload.append({
                "step": s.get("step") or i,
                "desc": s.get("desc") or s.get("action") or "",
                "expected": s.get("expected", ""),
            })
        else:
            steps_payload.append({"step": i, "desc": str(s), "expected": ""})
    return {
        "case_id": stable_case_id(c, source_module, prefix),
        "title": c.get("title", ""),
        "domain": canonical_domain,
        "module": location.module_path,
        "case_type": c.get("case_type", "manual"),
        "priority": c.get("priority") or "P2",
        "tags": json.dumps(tags, ensure_ascii=False),
        "case_design_method": design_method,
        "positive_negative": case_nature,
        "test_data_note": c.get("test_data_note", ""),
        "preconditions": c.get("preconditions", ""),
        "steps": json.dumps(steps_payload, ensure_ascii=False),
        "expected_result": c.get("expected_result", ""),
        "source": "batch-125",
        "source_req_id": c.get("source_doc", ""),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--backend-url", default=os.environ.get("TP_BACKEND_URL", "https://swiftbugs.cn/api/v1"))
    ap.add_argument("--username", default=os.environ.get("TP_ADMIN_USER", "sportsadmin"))
    ap.add_argument("--password", default=os.environ.get("TP_ADMIN_PASSWORD", ""))
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    if not args.password and not args.dry_run:
        print("缺少 --password", file=sys.stderr)
        return 1
    data = json.loads(CONSOLIDATED.read_text(encoding="utf-8"))
    summary = data.get("summary", {})
    print(f"[import] 汇总: {summary}", flush=True)

    base = args.backend_url.rstrip("/")
    headers = {"X-Project-Id": "0", "Origin": "https://swiftbugs.cn"}
    if not args.dry_run:
        with httpx.Client(timeout=120) as client:
            r = client.post(base + "/auth/login", json={"username": args.username, "password": args.password})
            r.raise_for_status()
            j = r.json()
            token = j.get("data", {}).get("access_token") or j.get("access_token", "")
            headers["Authorization"] = f"Bearer {token}"
            rp = client.get(base + "/projects", headers=headers)
            projects = rp.json().get("data", [])
            pid = projects[0]["id"] if projects else 1
            headers["X-Project-Id"] = str(pid)

    total = created = skipped = failed = 0
    with httpx.Client(timeout=120) as client:
        for mod in data["modules"]:
            for c in mod["base"] + mod["deep"]:
                if args.limit and total >= args.limit:
                    break
                total += 1
                payload = to_create(c, mod["module"])
                if args.dry_run:
                    print(f"[dry-run] POST /test-cases {payload['case_id']} {payload['title'][:30]}", flush=True)
                    created += 1
                    continue
                try:
                    # 幂等：先按 case_id 查
                    q = client.get(base + "/test-cases", params={"case_id": payload["case_id"], "page": 1, "page_size": 1}, headers=headers, timeout=60)
                    if response_contains_exact_case(q.json(), payload["case_id"]):
                        skipped += 1
                        continue
                    r = client.post(base + "/test-cases", json=payload, headers=headers, timeout=120)
                    if r.status_code >= 400:
                        print(f"[fail] {payload['case_id']}: {r.status_code} {r.text[:120]}", flush=True)
                        failed += 1
                    else:
                        created += 1
                except Exception as exc:  # noqa: BLE001
                    print(f"[err] {payload['case_id']}: {exc}", flush=True)
                    failed += 1
            if args.limit and total >= args.limit:
                break
            time.sleep(0.2)
    print(f"[import] 完成：total={total} created={created} skipped={skipped} failed={failed}", flush=True)
    return 0


def response_contains_exact_case(response_data: dict, case_id: str) -> bool:
    """Only an exact returned ID proves idempotent existence.

    Older servers ignored ``case_id`` and returned the first page total.  The
    importer must never interpret that unrelated total as an exact match.
    """
    items = response_data.get("data", {}).get("items") or []
    return any(str(item.get("case_id") or "") == case_id for item in items)


if __name__ == "__main__":
    sys.exit(main())
