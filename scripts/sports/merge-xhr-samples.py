"""体育平台承接 — 合并全部生产 XHR 真实样本为最终样本集（Batch 110）。

来源：walkthrough v2 / 滚动交互 / 定向交互 / 生产回填探测（去重 method+host+path）。
输出：evidence/batch-110/xhr-samples/xhr-samples-final.json + 按功能模块归类摘要。
"""
from __future__ import annotations

import json
import time
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = REPO_ROOT / "test-platform-v2" / "work-logs" / "evidence" / "batch-110" / "xhr-samples"
WALK = EVIDENCE.parent / "production-walkthrough-v2"

SOURCES = [
    WALK / "xhr-samples.json",
    EVIDENCE / "xhr-samples-merged.json",
    EVIDENCE / "xhr-samples-interactions.json",
    EVIDENCE / "xhr-samples-probed.json",
]

# 已知批 103 用户提供的真实样本（保留基线）
KNOWN = [
    {
        "module": "资讯-列表(翻页+语言过滤)", "method": "POST",
        "host": "api.cameltv.live", "path": "/camel-service/ee/news/list_visible",
        "post_data": json.dumps({
            "sorts": [{"key": "top", "sort": "desc"}, {"key": "updateTime", "sort": "desc"}],
            "page": 2, "size": 30,
            "queryList": [{"isOrNotRange": 0, "key": "language", "type": "String", "value1": "0", "value2": ""}],
            "locale": "en",
        }, ensure_ascii=False),
        "source": "用户提供真实请求样本（Batch 103）",
    },
]


def main() -> int:
    merged: dict[str, dict] = {}
    for f in SOURCES:
        if not f.exists():
            continue
        data = json.loads(f.read_text(encoding="utf-8"))
        for s in data.get("samples", []):
            if s.get("host") == "sensors.cameltv.live":
                continue  # 埋点信标不作为接口用例基线
            path = (s.get("path") or "").split("?")[0]
            key = f"{s.get('method')}|{s.get('host')}|{path}"
            if key in merged:
                # 保留响应更丰富的样本
                old = merged[key]
                if len(s.get("response") or "") > len(old.get("response") or ""):
                    merged[key] = s
            else:
                merged[key] = s
    for k in KNOWN:
        key = f"{k['method']}|{k['host']}|{k['path']}"
        if key not in merged:
            merged[key] = {**k, "response": "", "status": 200, "ts": int(time.time() * 1000)}

    samples = sorted(merged.values(), key=lambda s: f"{s.get('module') or ''}|{s.get('path') or ''}")
    out = EVIDENCE / "xhr-samples-final.json"
    out.write_text(json.dumps({"captured_at": time.strftime("%Y-%m-%dT%H:%M:%S"), "total": len(samples), "samples": samples}, ensure_ascii=False, indent=2), encoding="utf-8")

    # 摘要
    summary = []
    for s in samples:
        resp_len = len(s.get("response") or "")
        summary.append({
            "module": s.get("module", ""),
            "method": s.get("method"),
            "path": (s.get("path") or "").split("?")[0],
            "host": s.get("host"),
            "has_body": bool(s.get("post_data")),
            "response_len": resp_len,
            "source": s.get("source", ""),
        })
    sum_out = EVIDENCE / "xhr-samples-summary.json"
    sum_out.write_text(json.dumps({"total": len(summary), "interfaces": summary}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[merge] total unique interfaces: {len(samples)}")
    for row in summary:
        print(f"  {row['method']} {row['path']} | {row['module']} | body={row['has_body']} resp={row['response_len']}")
    print(f"[evidence] {out.relative_to(REPO_ROOT)} / {sum_out.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
