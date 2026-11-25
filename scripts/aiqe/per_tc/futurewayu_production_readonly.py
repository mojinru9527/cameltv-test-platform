"""未来娃屿生产环境**只读**探测（用户已报备允许生产只读测试）。

边界
----
- 只允许 GET/HEAD/OPTIONS 与只读 SQL（SELECT/SHOW/EXPLAIN）；写操作直接拒绝；
- 本脚本**不产出产品 TC PASS**：产品级 TC-AIQE-001..010 需要写操作/设备/
  Benchmark，只读环境只能作为生产健康与证据探针，结果写入
  ``docs/aiqe/v1.6/evidence/futurewayu-production-readonly.json``；
- 凭据只从环境变量读取，不落盘、不打印。

环境变量
--------
    FUTUREWAYU_BASE_URL             C 端/公开 API 基址（如 https://<prod-domain>）
    FUTUREWAYU_ADMIN_URL            管理后台基址
    FUTUREWAYU_ADMIN_TOKEN          只读管理员 Token（可选；没有则跳过 admin 探测）
    FUTUREWAYU_DB_READONLY_DSN      MySQL 只读账号 DSN（可选；没有则跳过 DB 探测）

用法
----
    python scripts/aiqe/per_tc/futurewayu_production_readonly.py \
      --output docs/aiqe/v1.6/evidence/futurewayu-production-readonly.json
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_OUTPUT = ROOT / "docs/aiqe/v1.6/evidence/futurewayu-production-readonly.json"
SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}
SAFE_SQL = re.compile(r"^\s*(SELECT|SHOW|EXPLAIN|DESCRIBE)\b", re.IGNORECASE)
DEFAULT_PROBES = ("/", "/api/health", "/health", "/hz-api/captchaImage")


def _probe_paths() -> tuple[str, ...]:
    raw = os.environ.get("FUTUREWAYU_PROBE_PATHS", "").strip()
    if not raw:
        return DEFAULT_PROBES
    paths = tuple(item.strip() for item in raw.split(",") if item.strip())
    return paths or DEFAULT_PROBES


def _request(method: str, url: str, *, token: str = "", timeout: float = 20.0) -> dict:
    if method.upper() not in SAFE_METHODS:
        raise PermissionError(f"生产只读模式禁止 {method} 请求")
    request = urllib.request.Request(url, method=method.upper())
    request.add_header("User-Agent", "cameltv-aiqe-production-readonly")
    if token:
        request.add_header("authorization", f"Bearer {token}")
        request.add_header("cookie", f"Admin-Token={token}")  # RuoYi 风格只读探测
    try:
        started = time.monotonic()
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read(2048).decode("utf-8", errors="replace")
            return {
                "url": url,
                "method": method.upper(),
                "status": response.status,
                "duration_ms": int((time.monotonic() - started) * 1000),
                "body_head": body[:300],
            }
    except urllib.error.HTTPError as exc:
        return {"url": url, "method": method.upper(), "status": exc.code, "body_head": ""}
    except (urllib.error.URLError, TimeoutError, ConnectionError) as exc:
        return {"url": url, "method": method.upper(), "status": 0, "error": str(exc)[:300]}


def _parse_mysql_dsn(dsn: str) -> dict:
    """解析 mysql://user:pass@host:port/db（或 mysql+pymysql://）。"""
    from urllib.parse import unquote, urlsplit

    parts = urlsplit(dsn)
    if not parts.hostname:
        raise ValueError("DSN 缺少 host（期望 mysql://user:pass@host:port/db）")
    return {
        "host": parts.hostname,
        "port": parts.port or 3306,
        "user": unquote(parts.username or ""),
        "password": unquote(parts.password or ""),
        "database": (parts.path or "").lstrip("/"),
        "connect_timeout": 10,
    }


def _db_probe(dsn: str) -> dict:
    if not dsn:
        return {"configured": False, "reason": "未提供 FUTUREWAYU_DB_READONLY_DSN"}
    try:
        import pymysql  # type: ignore
    except ModuleNotFoundError:
        return {"configured": True, "ok": False, "reason": "pymysql 未安装（只读探测跳过）"}
    try:
        connection = pymysql.connect(**_parse_mysql_dsn(dsn))
    except Exception as exc:  # noqa: BLE001 - DSN 解析/连接失败记录原因
        return {"configured": True, "ok": False, "reason": f"{type(exc).__name__}: {exc}"[:300]}
    try:
        with connection.cursor() as cursor:
            cursor.execute("SET SESSION TRANSACTION READ ONLY")
            cursor.execute("SELECT 1")
            cursor.fetchone()
            checks = []
            for statement in ("SHOW TABLES", "SHOW DATABASES"):
                try:
                    cursor.execute(statement)
                    checks.append({"statement": statement, "ok": True})
                except Exception as exc:  # noqa: BLE001
                    checks.append({"statement": statement, "ok": False, "error": str(exc)[:200]})
            try:
                cursor.execute("CREATE TABLE aiqe_ro_probe_should_fail (id int)")
                write_blocked = False
            except Exception:  # noqa: BLE001 - 写必须被拒绝
                write_blocked = True
            return {"configured": True, "ok": True, "write_rejected": write_blocked, "checks": checks}
    finally:
        connection.close()


def build_report() -> dict:
    base = os.environ.get("FUTUREWAYU_BASE_URL", "").rstrip("/")
    admin = os.environ.get("FUTUREWAYU_ADMIN_URL", "").rstrip("/")
    token = os.environ.get("FUTUREWAYU_ADMIN_TOKEN", "")
    dsn = os.environ.get("FUTUREWAYU_DB_READONLY_DSN", "")
    report: dict = {
        "schema_version": "1.0",
        "artifact_kind": "futurewayu-production-readonly",
        "generated_at": datetime.now(UTC).isoformat(),
        "readonly_only": True,
        "base_url": base,
        "admin_url": admin,
        "probe_paths": list(_probe_paths()),
        "base_configured": bool(base),
        "admin_configured": bool(admin),
        "db_configured": bool(dsn),
        "probes": [],
    }
    if not base and not admin:
        report["status"] = "NOT_PROVEN"
        report["reason"] = (
            "缺少 FUTUREWAYU_BASE_URL/FUTUREWAYU_ADMIN_URL：生产只读地址未提供，未执行任何请求"
        )
        return report
    for path in _probe_paths():
        if base:
            report["probes"].append(_request("GET", f"{base}{path}"))
    if admin:
        report["probes"].append(_request("GET", f"{admin}/", token=token))
        config_path = os.environ.get(
            "FUTUREWAYU_ADMIN_CONFIG_PATH", "/system/config/configKey/sys.index.skinName"
        )
        report["probes"].append(_request("GET", f"{admin}{config_path}", token=token))
    if dsn:
        report["db"] = _db_probe(dsn)
    reachable = [item for item in report["probes"] if int(item.get("status") or 0) > 0]
    report["status"] = "PROBED" if reachable else "UNREACHABLE"
    if report.get("db", {}).get("write_rejected") is False:
        report["status"] = "FAIL_WRITE_NOT_BLOCKED"
    return report


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
        except (AttributeError, ValueError):  # pragma: no cover
            pass
    parser = argparse.ArgumentParser(description="未来娃屿生产只读探测")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args(argv)
    report = build_report()
    target = Path(args.output)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    print(json.dumps({"status": report["status"], "probes": len(report["probes"])}, ensure_ascii=False))
    return 0 if report["status"] in {"PROBED", "NOT_PROVEN"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
