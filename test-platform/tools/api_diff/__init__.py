"""接口 Diff 比对器：同一批请求打两个环境，JSON 逐字段比对，分级出 HTML 报告。

输入二选一：
- 录制流量（.jsonl/.json，来自 traffic_monitor）→ 回放真实请求
- cases.yaml（引用 _base/site 的接口名）→ 按定义构造请求

差异分级：字段消失/数组元素消失/状态码不同=高危；值变化/类型变化=中危；新增字段=低危。
有高危差异时退出码非 0，便于接 CI。
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import httpx
import yaml
from deepdiff import DeepDiff

from core import logging as log
from core.config_loader import build_context
from core.http_client import build_client
from core.recording import load_entries

SEVERITY_ORDER = {"high": 0, "medium": 1, "low": 2}


# --------------------------------------------------------------------------- #
# 输入解析
# --------------------------------------------------------------------------- #
def _load_requests(cases: str, ctx) -> list[dict[str, Any]]:
    path = Path(cases)
    if path.suffix in (".yaml", ".yml"):
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        reqs = []
        for c in raw.get("cases", []):
            api = ctx.api(c["api"])
            reqs.append({
                "label": c.get("label", api.name),
                "method": api.method,
                "path": api.path,
                "query": {**api.query, **c.get("query", {})},
                "body": {**api.body, **c.get("body", {})},
            })
        return reqs
    # 录制流量
    reqs = []
    for e in load_entries(path):
        req = e["request"]
        reqs.append({
            "label": f"{req['method']} {req['path']}",
            "method": req["method"],
            "path": req["path"],
            "query": req.get("query", {}),
            "body": req.get("body", {}) if isinstance(req.get("body"), dict) else {},
        })
    return reqs


def _send(client: httpx.Client, r: dict[str, Any]) -> httpx.Response:
    kwargs: dict[str, Any] = {"params": r["query"]}
    if r["method"] in ("POST", "PUT", "PATCH"):
        kwargs["json"] = r["body"]
    return client.request(r["method"], r["path"], **kwargs)


def _json_or_text(resp: httpx.Response) -> Any:
    try:
        return resp.json()
    except Exception:
        return resp.text


# --------------------------------------------------------------------------- #
# 比对 + 分级
# --------------------------------------------------------------------------- #
def _compare(base_resp, target_resp, ignore_paths, tolerance) -> dict[str, Any]:
    findings: list[dict[str, str]] = []

    if base_resp.status_code != target_resp.status_code:
        findings.append({
            "severity": "high",
            "type": "status_code",
            "detail": f"{base_resp.status_code} → {target_resp.status_code}",
        })

    b, t = _json_or_text(base_resp), _json_or_text(target_resp)
    dd_kwargs: dict[str, Any] = {"exclude_paths": ignore_paths or []}
    if tolerance.get("array_unordered"):
        dd_kwargs["ignore_order"] = True
    if tolerance.get("float_abs") is not None:
        dd_kwargs["math_epsilon"] = tolerance["float_abs"]
    if tolerance.get("ignore_type_str_num"):
        dd_kwargs["ignore_string_type_changes"] = True
        dd_kwargs["ignore_numeric_type_changes"] = True

    diff = DeepDiff(b, t, **dd_kwargs)

    sev_map = {
        "dictionary_item_removed": "high",
        "iterable_item_removed": "high",
        "dictionary_item_added": "low",
        "iterable_item_added": "low",
        "values_changed": "medium",
        "type_changes": "medium",
        "repetition_change": "low",
    }
    for change_type, items in diff.items():
        sev = sev_map.get(change_type, "medium")
        if isinstance(items, dict):
            for path, info in items.items():
                detail = path
                if isinstance(info, dict) and "old_value" in info:
                    detail = f"{path}: {info.get('old_value')!r} → {info.get('new_value')!r}"
                findings.append({"severity": sev, "type": change_type, "detail": detail})
        else:  # set
            for path in items:
                findings.append({"severity": sev, "type": change_type, "detail": str(path)})

    findings.sort(key=lambda f: SEVERITY_ORDER[f["severity"]])
    return {
        "findings": findings,
        "high": sum(1 for f in findings if f["severity"] == "high"),
        "medium": sum(1 for f in findings if f["severity"] == "medium"),
        "low": sum(1 for f in findings if f["severity"] == "low"),
    }


# --------------------------------------------------------------------------- #
# HTML 报告
# --------------------------------------------------------------------------- #
_TEMPLATE = """<!doctype html><html><head><meta charset="utf-8">
<title>API Diff {{site}} {{base}}→{{target}}</title>
<style>
body{font-family:-apple-system,Segoe UI,Arial;margin:24px;color:#222}
h1{font-size:20px} .sum span{display:inline-block;padding:4px 10px;margin-right:8px;border-radius:4px;color:#fff}
.high{background:#d9534f}.medium{background:#f0ad4e}.low{background:#5bc0de}
table{border-collapse:collapse;width:100%;margin-top:8px}
th,td{border:1px solid #ddd;padding:6px 8px;font-size:13px;text-align:left;vertical-align:top}
th{background:#f5f5f5} .case{margin-top:20px}
.tag{padding:2px 6px;border-radius:3px;color:#fff;font-size:12px}
.ok{color:#5cb85c}
</style></head><body>
<h1>API Diff — {{site}} ({{base}} → {{target}})</h1>
<div class="sum">
  <span class="high">高危 {{total_high}}</span>
  <span class="medium">中危 {{total_medium}}</span>
  <span class="low">低危 {{total_low}}</span>
  <span style="background:#777">用例 {{cases|length}}</span>
</div>
{% for c in cases %}
<div class="case">
<h3>{{loop.index}}. {{c.label}}
  {% if c.result.findings %}
  <span class="tag high">{{c.result.high}}</span>
  <span class="tag medium">{{c.result.medium}}</span>
  <span class="tag low">{{c.result.low}}</span>
  {% else %}<span class="ok">✓ 无差异</span>{% endif %}
</h3>
{% if c.result.findings %}
<table><tr><th>等级</th><th>类型</th><th>差异</th></tr>
{% for f in c.result.findings %}
<tr><td><span class="tag {{f.severity}}">{{f.severity}}</span></td><td>{{f.type}}</td><td>{{f.detail}}</td></tr>
{% endfor %}
</table>{% endif %}
</div>
{% endfor %}
</body></html>"""


def _render(site, base, target, cases, report_path):
    from jinja2 import Template
    html = Template(_TEMPLATE).render(
        site=site, base=base, target=target, cases=cases,
        total_high=sum(c["result"]["high"] for c in cases),
        total_medium=sum(c["result"]["medium"] for c in cases),
        total_low=sum(c["result"]["low"] for c in cases),
    )
    Path(report_path).parent.mkdir(parents=True, exist_ok=True)
    Path(report_path).write_text(html, encoding="utf-8")


# --------------------------------------------------------------------------- #
# 入口
# --------------------------------------------------------------------------- #
def run_diff(site: str, base_env: str, target_env: str, cases: str, report: str = "") -> None:
    base_ctx = build_context(site, base_env)
    target_ctx = build_context(site, target_env)
    report = report or f"{base_ctx.platform.reports_dir}/{site}-diff-{base_env}-{target_env}.html"

    requests = _load_requests(cases, base_ctx)
    log.rule(f"API Diff · {site} · {base_env} → {target_env}")
    log.info(f"请求数：{len(requests)}")

    results = []
    with build_client(base_ctx) as bc, build_client(target_ctx) as tc:
        for r in requests:
            try:
                bresp, tresp = _send(bc, r), _send(tc, r)
                res = _compare(bresp, tresp, base_ctx.site_cfg.ignore_paths, base_ctx.site_cfg.tolerance)
            except Exception as exc:  # 请求失败也作为一条高危记录
                res = {"findings": [{"severity": "high", "type": "request_error", "detail": str(exc)}],
                       "high": 1, "medium": 0, "low": 0}
            results.append({"label": r["label"], "result": res})
            mark = "✓" if not res["findings"] else f"H{res['high']} M{res['medium']} L{res['low']}"
            log.info(f"  {r['label']:<32} {mark}")

    _render(site, base_env, target_env, results, report)
    total_high = sum(c["result"]["high"] for c in results)
    log.ok(f"报告：{report}")
    if total_high:
        log.err(f"发现 {total_high} 处高危差异")
        raise SystemExit(2)
    log.ok("无高危差异")
