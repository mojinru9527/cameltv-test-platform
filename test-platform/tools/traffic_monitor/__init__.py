"""流量监控器：启动 mitmproxy 抓取站点真实请求，落盘为 JSONL 录制。

录制结果是 api_diff（回放比对）与 mock_server（转 stub）的数据源。
访问 camel1.to 等站点需经上游代理 → mitmproxy 用 upstream 模式串联。
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse

from core import logging as log
from core.models import RunContext

ADDON = Path(__file__).resolve().parent / "addon.py"


def run_capture(ctx: RunContext, port: int = 8081, out: str = "") -> None:
    out = out or f"{ctx.platform.recordings_dir}/{ctx.site}-{ctx.env}.jsonl"
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    host = urlparse(ctx.base_url).hostname or ""

    cmd = [sys.executable, "-m", "mitmproxy.tools.main", "mitmdump",
           "-s", str(ADDON), "--listen-port", str(port)]
    # 经上游代理串联（已连代理才能访问站点）
    if ctx.proxy:
        cmd += ["--mode", f"upstream:{ctx.proxy}"]

    env = dict(os.environ, TP_OUT=out, TP_HOST_FILTER=host)

    log.rule(f"流量监控器 · {ctx.site}/{ctx.env}")
    log.info(f"监听端口 : {port}（把浏览器/App 的代理指向 127.0.0.1:{port}）")
    log.info(f"上游代理 : {ctx.proxy or '(直连)'}")
    log.info(f"仅记录   : host 含 '{host}'")
    log.info(f"输出     : {out}")
    log.warn("首次使用需安装 mitmproxy 证书：浏览器访问 http://mitm.it 下载安装。")
    log.warn("Ctrl+C 结束抓取。")
    try:
        subprocess.run(cmd, env=env, check=False)
    except KeyboardInterrupt:
        pass
    log.ok(f"录制已保存：{out}")
