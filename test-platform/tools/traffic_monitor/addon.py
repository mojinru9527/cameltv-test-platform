"""mitmproxy addon：抓取目标站点请求/响应，按 JSONL 落盘。

由 mitmdump 通过 `-s addon.py` 加载。运行参数经环境变量传入：
    TP_OUT          录制输出文件路径
    TP_HOST_FILTER  仅记录该 host 的流量（来自站点 base_url；空=全记录）
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

# 让 addon 子进程能 import 到 core
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from core.recording import append_entry  # noqa: E402

OUT = os.environ.get("TP_OUT", "data/recordings/capture.jsonl")
HOST_FILTER = os.environ.get("TP_HOST_FILTER", "")


def _parse_body(raw: bytes) -> object:
    if not raw:
        return ""
    try:
        return json.loads(raw.decode("utf-8"))
    except Exception:
        try:
            return raw.decode("utf-8", "replace")
        except Exception:
            return "<binary>"


def response(flow) -> None:  # mitmproxy 钩子：每个完成的响应触发
    req = flow.request
    if HOST_FILTER and HOST_FILTER not in req.pretty_host:
        return
    entry = {
        "request": {
            "method": req.method,
            "url": req.pretty_url,
            "path": req.path.split("?")[0],
            "query": dict(req.query),
            "headers": dict(req.headers),
            "body": _parse_body(req.raw_content or b""),
        },
        "response": {
            "status": flow.response.status_code,
            "headers": dict(flow.response.headers),
            "body": _parse_body(flow.response.raw_content or b""),
        },
    }
    append_entry(OUT, entry)
