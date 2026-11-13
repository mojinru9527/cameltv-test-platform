"""TC-AIQE-004 前置可达性检查（业务 Test Web）。

用途：在 AIQE 执行环境内判断业务 Web 是否可达；不可达时明确输出 BLOCKED 原因，
避免把"环境不可达"误报成产品缺陷或假绿。

用法：
  python scripts/qa/check_business_web_reachability.py \
      --host camelive-g3-test5.elelive.cn --port 443
退出码：0=可达；2=不可达（BLOCKED）。
"""
from __future__ import annotations

import argparse
import json
import socket
import ssl
import sys


def check(host: str, port: int, timeout: float) -> dict:
    result: dict = {"host": host, "port": port}
    try:
        addresses = sorted({info[4][0] for info in socket.getaddrinfo(host, port)})
        result["resolved"] = addresses
    except OSError as exc:
        result.update({"status": "BLOCKED", "reason": f"DNS 解析失败: {exc}"})
        return result

    private = [ip for ip in result["resolved"] if ip.startswith(("10.", "192.168.", "172.16.", "172.17.", "172.18.", "172.19.", "172.2", "172.30.", "172.31.", "127."))]
    result["private_ips"] = private

    try:
        with socket.create_connection((host, port), timeout=timeout):
            pass
    except OSError as exc:
        reason = "TCP 连接失败"
        if private:
            reason += f"（DNS 指向内网地址 {', '.join(private)}，当前执行环境不在该网络）"
        result.update({"status": "BLOCKED", "reason": f"{reason}: {exc}"})
        return result

    try:
        context = ssl.create_default_context()
        with socket.create_connection((host, port), timeout=timeout) as raw:
            with context.wrap_socket(raw, server_hostname=host):
                pass
    except OSError as exc:
        result.update({"status": "BLOCKED", "reason": f"TLS 握手失败: {exc}"})
        return result

    result.update({"status": "REACHABLE", "reason": ""})
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="camelive-g3-test5.elelive.cn")
    parser.add_argument("--port", type=int, default=443)
    parser.add_argument("--timeout", type=float, default=8.0)
    args = parser.parse_args()

    result = check(args.host, args.port, args.timeout)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "REACHABLE" else 2


if __name__ == "__main__":
    sys.exit(main())
