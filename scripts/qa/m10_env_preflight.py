"""M10 环境前置检查（future-wayu / 真机 / IoT / 业务 Web）。

用途：在 AIQE 执行环境内一键判断 M10 的外部依赖是否就绪；输出结构化 JSON，
任何未就绪项都给出 BLOCKED 与具体原因，避免把环境缺失误判为产品/自动化缺陷。

用法：
  python scripts/qa/m10_env_preflight.py            # 全量检查
  python scripts/qa/m10_env_preflight.py --json      # JSON（默认）
退出码：0 = 全部 READY；2 = 存在 BLOCKED。
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import socket
import ssl
import subprocess
import sys
from typing import Any


def check_tcp(host: str, port: int, timeout: float = 6.0) -> tuple[bool, str, list[str]]:
    try:
        addresses = sorted({info[4][0] for info in socket.getaddrinfo(host, port)})
    except OSError as exc:
        return False, f"DNS 解析失败: {exc}", []
    try:
        with socket.create_connection((host, port), timeout=timeout):
            pass
    except OSError as exc:
        private = [
            ip
            for ip in addresses
            if ip.startswith(("10.", "192.168.", "172.16.", "172.17.", "172.18.", "172.19.", "172.2", "172.30.", "172.31.", "127."))
        ]
        reason = f"TCP 连接失败: {exc}"
        if private:
            reason += f"（DNS 指向内网地址 {', '.join(private)}）"
        return False, reason, addresses
    return True, "", addresses


def check_tls(host: str, port: int, timeout: float = 6.0) -> tuple[bool, str]:
    try:
        context = ssl.create_default_context()
        with socket.create_connection((host, port), timeout=timeout) as raw:
            with context.wrap_socket(raw, server_hostname=host):
                return True, ""
    except OSError as exc:
        return False, f"TLS 握手失败: {exc}"


def check_future_wayu() -> dict[str, Any]:
    base = os.environ.get("FUTURE_WAYU_BASE_URL", "").strip()
    user = os.environ.get("FUTURE_WAYU_USERNAME", "").strip()
    if not base:
        return {
            "id": "future_wayu",
            "name": "future-wayu 第二项目",
            "status": "BLOCKED",
            "reason": "未配置 FUTURE_WAYU_BASE_URL / FUTURE_WAYU_USERNAME / FUTURE_WAYU_PASSWORD",
        }
    host = base.split("//", 1)[-1].split("/", 1)[0]
    port = 443 if base.startswith("https://") else 80
    ok, reason, addresses = check_tcp(host, port)
    if not ok:
        return {"id": "future_wayu", "name": "future-wayu", "status": "BLOCKED", "reason": reason, "resolved": addresses}
    if port == 443:
        tls_ok, tls_reason = check_tls(host, port)
        if not tls_ok:
            return {"id": "future_wayu", "name": "future-wayu", "status": "BLOCKED", "reason": tls_reason}
    if not user:
        return {"id": "future_wayu", "name": "future-wayu", "status": "BLOCKED", "reason": "缺少 FUTURE_WAYU_USERNAME"}
    return {"id": "future_wayu", "name": "future-wayu", "status": "READY", "reason": "", "resolved": addresses}


def check_android() -> dict[str, Any]:
    appium = os.environ.get("APPIUM_URL", "").strip()
    if appium:
        host = appium.split("//", 1)[-1].split("/", 1)[0].split(":", 1)[0]
        ok, reason, addresses = check_tcp(host, 4723)
        if ok:
            return {"id": "android", "name": "Android 真机/Appium", "status": "READY", "reason": "", "resolved": addresses}
        return {"id": "android", "name": "Android 真机/Appium", "status": "BLOCKED", "reason": f"APPIUM_URL 不可达: {reason}"}
    adb = shutil.which("adb")
    if not adb:
        return {"id": "android", "name": "Android 真机", "status": "BLOCKED", "reason": "未安装 adb，且未配置 APPIUM_URL"}
    try:
        out = subprocess.run([adb, "devices"], capture_output=True, text=True, timeout=10).stdout
    except OSError as exc:
        return {"id": "android", "name": "Android 真机", "status": "BLOCKED", "reason": f"adb 执行失败: {exc}"}
    devices = [line.split("\t")[0] for line in out.splitlines()[1:] if "\tdevice" in line]
    if not devices:
        return {"id": "android", "name": "Android 真机", "status": "BLOCKED", "reason": "adb 无已授权设备"}
    return {"id": "android", "name": "Android 真机", "status": "READY", "reason": "", "devices": devices}


def check_iot() -> dict[str, Any]:
    host = os.environ.get("MQTT_HOST", "").strip()
    if not host:
        return {"id": "iot", "name": "IoT/MQTT 实机", "status": "BLOCKED", "reason": "未配置 MQTT_HOST / MQTT_PORT / MQTT_USERNAME"}
    port = int(os.environ.get("MQTT_PORT", "8883") or 8883)
    ok, reason, addresses = check_tcp(host, port)
    if not ok:
        return {"id": "iot", "name": "IoT/MQTT 实机", "status": "BLOCKED", "reason": reason, "resolved": addresses}
    return {"id": "iot", "name": "IoT/MQTT 实机", "status": "READY", "reason": "", "resolved": addresses}


def check_business_web() -> dict[str, Any]:
    host = os.environ.get("BUSINESS_WEB_HOST", "camelive-g3-test5.elelive.cn")
    ok, reason, addresses = check_tcp(host, 443)
    if not ok:
        return {"id": "business_web", "name": "业务 Web（TC-004）", "status": "BLOCKED", "reason": reason, "resolved": addresses}
    tls_ok, tls_reason = check_tls(host, 443)
    if not tls_ok:
        return {"id": "business_web", "name": "业务 Web（TC-004）", "status": "BLOCKED", "reason": tls_reason}
    return {"id": "business_web", "name": "业务 Web（TC-004）", "status": "READY", "reason": "", "resolved": addresses}


CHECKS = {
    "future_wayu": check_future_wayu,
    "android": check_android,
    "iot": check_iot,
    "business_web": check_business_web,
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--only", choices=sorted(CHECKS), help="只检查一项")
    parser.add_argument("--pretty", action="store_true", default=True)
    args = parser.parse_args()

    names = [args.only] if args.only else list(CHECKS)
    results = [CHECKS[name]() for name in names]
    blocked = [row for row in results if row["status"] != "READY"]
    payload = {
        "status": "READY" if not blocked else "BLOCKED",
        "blocked_count": len(blocked),
        "results": results,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if not blocked else 2


if __name__ == "__main__":
    sys.exit(main())
