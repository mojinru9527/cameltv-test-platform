"""日志聚合分析器：按 traceId 跨服务串链路，高亮 ERROR；批量聚类根因。

v2: 日志源从 EnvConfig.elk / ProjectConfig.elk 读取（ELK URL、Kibana URL）
v1: 日志源从 config/sites/<site>/logs.yaml 读取（files 多文件聚合 或 ELK 查询）

失败用例自动生成 Kibana Discover 一键深度链接。
"""
from __future__ import annotations

import glob
import os
import re
import time
from collections import Counter
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlencode

import yaml

from core import logging as log
from core.config_loader import SITES_DIR, ROOT, load_log_config
from core.models import RunContext

_TS_RE = re.compile(r"\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}")
_ERROR_RE = re.compile(r"ERROR|Exception|Traceback|FATAL", re.IGNORECASE)
_EXC_RE = re.compile(r"(\w+(?:Error|Exception))")
_TRACE_RE = re.compile(r"trace[_-]?id[=:\s\"]+([a-zA-Z0-9\-]+)", re.IGNORECASE)
_HEADER_TRACE_RE = re.compile(r"trace[_-]?id[=:\s\"]+([a-zA-Z0-9\-]+)", re.IGNORECASE)


# =========================================================================== #
# Kibana 深度链接
# =========================================================================== #

def build_kibana_discover_link(
    trace_id: str,
    index: str = "*",
    kibana_url: str = "",
    time_range_h: int = 24,
) -> str:
    """生成一键 Kibana Discover 深度链接。

    Args:
        trace_id: 日志 traceId
        index: ES 索引 pattern
        kibana_url: Kibana 根地址（如 https://elk.elelive.cn/app/kibana）
        time_range_h: 时间范围（小时），默认 24h
    """
    if not kibana_url:
        kibana_url = os.environ.get("KIBANA_URL", "")
    if not kibana_url:
        return f"(Kibana URL 未配置 — traceId={trace_id})"

    kibana_url = kibana_url.rstrip("/")

    # 构造 Kibana Discover URL
    # _g: 全局时间范围；_a: 可视化配置（query + index）
    time_from = f"now-{time_range_h}h"
    query = f'traceId:"{trace_id}"'
    app_url = (
        f"{kibana_url}#/discover"
        f"?_g=(time:(from:'{time_from}',to:now))"
        f"&_a=(index:'{index}',query:(language:kuery,query:'{quote(query)}'))"
    )
    return app_url


def collect_trace_ids_from_text(text: str) -> list[str]:
    """从任意文本中提取 traceId。"""
    return [m.group(1) for m in _TRACE_RE.finditer(text)]


# =========================================================================== #
# 日志收集
# =========================================================================== #

def _load_logs_cfg(site: str) -> dict[str, Any]:
    path = SITES_DIR / site / "logs.yaml"
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _collect_files(cfg: dict, trace_id: str) -> list[dict[str, Any]]:
    rows = []
    for src in cfg.get("files", []):
        service = src.get("service", "?")
        for fp in glob.glob(src["path"]):
            try:
                with open(fp, encoding="utf-8", errors="replace") as f:
                    for line in f:
                        if trace_id in line:
                            ts = _TS_RE.search(line)
                            rows.append({
                                "ts": ts.group(0) if ts else "",
                                "service": service,
                                "file": os.path.basename(fp),
                                "line": line.rstrip(),
                                "error": bool(_ERROR_RE.search(line)),
                            })
            except OSError:
                continue
    rows.sort(key=lambda r: r["ts"])
    return rows


def _collect_elk(elk_cfg, trace_id: str) -> list[dict[str, Any]]:
    """从 ELK/Elasticsearch 查询 traceId 关联日志。

    elk_cfg 可以是:
      - dict (v1 兼容)
      - ElkSource 对象 (v2)
      - RunContext.env_cfg.elk (v2)
    """
    from elasticsearch import Elasticsearch

    # 标准化 elk 配置
    if hasattr(elk_cfg, 'url'):
        es_url = elk_cfg.url or os.environ.get("ELASTIC_URL", "")
        api_key = elk_cfg.api_key or os.environ.get("ELASTIC_API_KEY", "") or None
        index = elk_cfg.index
        trace_field = elk_cfg.trace_field
        time_field = elk_cfg.time_field
    elif isinstance(elk_cfg, dict):
        es_url = os.environ.get("ELASTIC_URL", "")
        api_key = os.environ.get("ELASTIC_API_KEY", "") or None
        index = elk_cfg.get("index", "*")
        trace_field = elk_cfg.get("trace_field", "traceId")
        time_field = elk_cfg.get("time_field", "@timestamp")
    else:
        es_url = os.environ.get("ELASTIC_URL", "")
        api_key = os.environ.get("ELASTIC_API_KEY", "") or None
        index = "*"
        trace_field = "traceId"
        time_field = "@timestamp"

    if not es_url:
        return []

    # 认证：优先 api_key，否则用 ELK_USER / ELK_PASSWORD Basic Auth
    elk_user = os.environ.get("ELK_USER", "")
    elk_password = os.environ.get("ELK_PASSWORD", "")
    if api_key:
        es_auth: dict = {"api_key": api_key}
    elif elk_user and elk_password:
        es_auth = {"basic_auth": (elk_user, elk_password)}
    else:
        es_auth = {}

    try:
        es = Elasticsearch(es_url, request_timeout=10, **es_auth)
        resp = es.search(index=index, size=1000, query={
            "match": {trace_field: trace_id}
        }, sort=[{time_field: "asc"}])
    except Exception as exc:
        log.warn(f"ELK 查询失败: {exc}")
        return []

    rows = []
    for hit in resp["hits"]["hits"]:
        s = hit["_source"]
        msg = s.get("message", str(s))
        rows.append({
            "ts": s.get(time_field, ""),
            "service": s.get("service", s.get("kubernetes", {}).get("container_name", "?")),
            "file": hit.get("_index", ""),
            "line": msg,
            "error": bool(_ERROR_RE.search(msg)),
        })
    return rows


_HTML = """<!doctype html><meta charset="utf-8"><title>trace {{tid}}</title>
<style>body{font-family:Consolas,monospace;margin:20px;font-size:13px}
.row{padding:2px 6px;border-left:3px solid #ccc;margin:1px 0}
.err{background:#fff0f0;border-left-color:#d9534f}
.svc{color:#06c;font-weight:bold}.ts{color:#888}
a{color:#06c}</style>
<h2>traceId: {{tid}} &nbsp;<small>{{rows|length}} 条 · {{errs}} 个 ERROR</small></h2>
{% if kibana_link %}
<p>📊 <a href="{{kibana_link}}" target="_blank">在 Kibana 中查看</a></p>
{% endif %}
{% for r in rows %}<div class="row {{'err' if r.error}}">
<span class="ts">{{r.ts}}</span> <span class="svc">[{{r.service}}]</span> {{r.line|e}}</div>{% endfor %}"""


# =========================================================================== #
# 入口
# =========================================================================== #

def trace(ctx: RunContext, trace_id: str, out: str = "") -> None:
    """按 traceId 拉全链路日志并高亮 ERROR。"""
    log.rule(f"日志链路 · {ctx.project.name if ctx.project else ctx.site} · traceId={trace_id}")

    # 确定日志源：v2 env_cfg.elk > v2 project.elk > v1 logs.yaml
    elk_cfg = None
    log_mode = "files"

    # v2
    if ctx.env_cfg.elk and ctx.env_cfg.elk.url:
        elk_cfg = ctx.env_cfg.elk
        log_mode = "elk"
    elif ctx.project and ctx.project.elk and ctx.project.elk.url:
        elk_cfg = ctx.project.elk
        log_mode = "elk"
    else:
        # v1
        cfg = _load_logs_cfg(ctx.site)
        log_mode = cfg.get("mode", "files")

    if log_mode == "elk" and elk_cfg:
        rows = _collect_elk(elk_cfg, trace_id)
    else:
        cfg = _load_logs_cfg(ctx.site)
        if not cfg:
            log.err(f"未找到日志源配置。请检查 config/environments/<env>.yaml 中的 elk 字段。")
            raise SystemExit(1)
        rows = _collect_files(cfg, trace_id)

    if not rows:
        log.warn("未匹配到该 traceId 的日志。")

    errs = sum(1 for r in rows if r["error"])
    out = out or f"{ctx.platform.reports_dir}/trace-{trace_id}.html"

    # 生成 Kibana 深度链接
    kibana_url = ""
    index = "*"
    if elk_cfg:
        kibana_url = getattr(elk_cfg, 'kibana_url', '') or os.environ.get("KIBANA_URL", "")
        index = getattr(elk_cfg, 'index', '*')
    kibana_link = build_kibana_discover_link(trace_id, index=index, kibana_url=kibana_url) if elk_cfg else ""

    from jinja2 import Template
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    Path(out).write_text(Template(_HTML).render(
        tid=trace_id, rows=rows, errs=errs, kibana_link=kibana_link
    ), encoding="utf-8")

    if kibana_link:
        log.info(f"Kibana → {kibana_link}")
    log.ok(f"{len(rows)} 条日志，{errs} 个 ERROR → {out}")


def batch(ctx: RunContext, report: str, cluster: bool = True) -> None:
    """批量按失败用例 traceId 聚类相同根因。"""
    from junitparser import JUnitXml
    log.rule(f"失败用例根因聚类 · {ctx.project.name if ctx.project else ctx.site}")

    xml = JUnitXml.fromfile(report)
    failures = []
    for suite in xml:
        for case in suite:
            res = getattr(case, "result", []) or []
            for r in res:
                if r.__class__.__name__ in ("Failure", "Error"):
                    text = f"{r.message or ''} {getattr(r, 'text', '') or ''}"
                    tid = _TRACE_RE.search(text)
                    exc = _EXC_RE.search(text)
                    failures.append({
                        "case": case.name,
                        "trace_id": tid.group(1) if tid else "",
                        "signature": exc.group(1) if exc else (r.message or "")[:60],
                    })

    if not failures:
        log.ok("无失败用例。")
        return

    log.warn(f"失败用例 {len(failures)} 个")

    # Kibana URL 基础配置
    elk_cfg = None
    if ctx.env_cfg.elk and ctx.env_cfg.elk.url:
        elk_cfg = ctx.env_cfg.elk
    elif ctx.project and ctx.project.elk and ctx.project.elk.url:
        elk_cfg = ctx.project.elk

    if cluster:
        groups = Counter(f["signature"] for f in failures)
        for sig, n in groups.most_common():
            log.info(f"  ×{n}  {sig}")

    for f in failures:
        if f["trace_id"]:
            link = ""
            if elk_cfg:
                kibana_url = getattr(elk_cfg, 'kibana_url', '') or os.environ.get("KIBANA_URL", "")
                index = getattr(elk_cfg, 'index', '*')
                link = build_kibana_discover_link(f["trace_id"], index=index, kibana_url=kibana_url)
            log.info(f"  {f['case']} → traceId {f['trace_id']}")
            if link:
                log.info(f"    ELK: {link}")


# 工具函数导出给 api_tester
def get_elk_link(ctx: RunContext, trace_id: str) -> str:
    """为 API 测试失败用例生成 ELK 查询链接。"""
    elk_cfg = None
    if ctx.env_cfg.elk and ctx.env_cfg.elk.url:
        elk_cfg = ctx.env_cfg.elk
    elif ctx.project and ctx.project.elk and ctx.project.elk.url:
        elk_cfg = ctx.project.elk
    if not elk_cfg:
        return ""

    kibana_url = getattr(elk_cfg, 'kibana_url', '') or os.environ.get("KIBANA_URL", "")
    index = getattr(elk_cfg, 'index', '*')
    return build_kibana_discover_link(trace_id, index=index, kibana_url=kibana_url)
