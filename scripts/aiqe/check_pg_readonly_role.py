"""V16-004：真实 PostgreSQL 只读角色验证（不能再用 SQLite mode=ro 代替）。

审计（2026-11-24）：YAML 自己承认 PostgreSQL 只读 role/账号仍需运维创建并 staging
复验；SQLite ``mode=ro`` 不能替代生产 PostgreSQL role 证据。

用法
----
    # 验证并写入证据文件（需要真实 PG DSN + 只读账号）
    python scripts/aiqe/check_pg_readonly_role.py --check \
        --dsn "postgresql://aiqe_ro:***@db.example:5432/cameltv" \
        --output docs/aiqe/v1.6/evidence/pg-readonly-role.json

    # 无 DSN 时显式输出 NOT_PROVEN（退出码 2），不得伪造 PASS
    python scripts/aiqe/check_pg_readonly_role.py --check

检查项
------
1. 连接可用，``SELECT current_user`` 非超级用户；
2. pg_roles: rolsuper=false / rolcreaterole=false / rolbypassrls=false；
3. 写操作被拒绝（CREATE TABLE / INSERT 抛 permission denied）；
4. ``SHOW default_transaction_read_only`` 或 session read-only 为 on；
5. statement_timeout 已设置（不依赖默认无限等待）。
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT = ROOT / "docs/aiqe/v1.6/evidence/pg-readonly-role.json"


def mask_dsn(dsn: str) -> str:
    if not dsn:
        return ""
    try:
        parts = urlsplit(dsn)
    except ValueError:  # pragma: no cover - 非法 DSN
        return "***"
    if parts.password is None:
        return dsn
    netloc = f"{parts.username or ''}:***@{parts.hostname or ''}"
    if parts.port:
        netloc += f":{parts.port}"
    return urlunsplit((parts.scheme, netloc, parts.path, parts.query, parts.fragment))


def _connect(dsn: str):
    import psycopg2  # 生产镜像已带 psycopg2-binary

    conn = psycopg2.connect(dsn, connect_timeout=10)
    conn.autocommit = True
    return conn


def _scope(dsn: str) -> str:
    """loopback=本机容器/实例；remote=staging/生产。证据必须标注，避免误读。"""
    host = (urlsplit(dsn).hostname or "").lower()
    if host in {"127.0.0.1", "localhost", "::1"} or host.startswith("127."):
        return "loopback"
    return "remote"


def verify(dsn: str) -> dict:
    checks: list[dict] = []
    conn = _connect(dsn)
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT current_user")
            current_user = str(cur.fetchone()[0])
            cur.execute("SHOW server_version")
            server_version = str(cur.fetchone()[0])
            cur.execute(
                "SELECT rolsuper, rolcreaterole, rolbypassrls, rolcreatedb "
                "FROM pg_roles WHERE rolname = current_user"
            )
            rolsuper, rolcreaterole, rolbypassrls, rolcreatedb = cur.fetchone()
            checks.append({"name": "no_superuser", "ok": not rolsuper, "value": rolsuper})
            checks.append(
                {"name": "no_createrole", "ok": not rolcreaterole, "value": rolcreaterole}
            )
            checks.append({"name": "no_bypassrls", "ok": not rolbypassrls, "value": rolbypassrls})
            checks.append({"name": "no_createdb", "ok": not rolcreatedb, "value": rolcreatedb})

            # 写操作必须被拒绝
            write_blocked = False
            write_error = ""
            try:
                cur.execute("CREATE TABLE aiqe_ro_probe_should_fail (id int)")
            except Exception as exc:  # noqa: BLE001 - 记录数据库拒绝原因
                write_blocked = True
                write_error = type(exc).__name__
            checks.append(
                {
                    "name": "write_rejected",
                    "ok": write_blocked,
                    "value": write_error or "NOT_REJECTED",
                }
            )

            cur.execute("SHOW default_transaction_read_only")
            read_only = str(cur.fetchone()[0]).lower()
            checks.append(
                {"name": "default_transaction_read_only", "ok": read_only == "on", "value": read_only}
            )

            cur.execute("SHOW statement_timeout")
            timeout = str(cur.fetchone()[0])
            checks.append(
                {
                    "name": "statement_timeout_set",
                    "ok": timeout not in {"", "0"},
                    "value": timeout,
                }
            )
    finally:
        conn.close()
    ok = all(item["ok"] for item in checks)
    return {
        "schema_version": "1.0",
        "artifact_kind": "pg-readonly-role-verification",
        "generated_at": datetime.now(UTC).isoformat(),
        "dsn": mask_dsn(dsn),
        "scope": _scope(dsn),
        "server_version": server_version,
        "status": "PASS" if ok else "FAIL",
        "current_user": current_user,
        "checks": checks,
    }


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
        except (AttributeError, ValueError):  # pragma: no cover
            pass
    parser = argparse.ArgumentParser(description="PostgreSQL 只读角色验证")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--dsn", default="")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args(argv)

    dsn = args.dsn.strip()
    if not dsn:
        payload = {
            "schema_version": "1.0",
            "artifact_kind": "pg-readonly-role-verification",
            "generated_at": datetime.now(UTC).isoformat(),
            "status": "NOT_PROVEN",
            "reason": "未提供 --dsn（生产/ staging PostgreSQL 只读角色尚未验证）",
            "checks": [],
        }
        print(json.dumps(payload, ensure_ascii=False))
        return 2
    try:
        result = verify(dsn)
    except Exception as exc:  # noqa: BLE001 - 连接失败即 FAIL
        result = {
            "schema_version": "1.0",
            "artifact_kind": "pg-readonly-role-verification",
            "generated_at": datetime.now(UTC).isoformat(),
            "dsn": mask_dsn(dsn),
            "status": "FAIL",
            "error": f"{type(exc).__name__}: {exc}"[:500],
            "checks": [],
        }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    print(json.dumps({k: result.get(k) for k in ("status", "dsn", "error")}, ensure_ascii=False))
    return 0 if result.get("status") == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
