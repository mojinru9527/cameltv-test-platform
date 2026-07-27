"""环境健康检查器：并发探活依赖，输出红绿灯。

探测项：DB（ping/读写）、Redis、MQ（RabbitMQ/Kafka）、HTTP 健康+版本、预置基础数据。
绿=通过，红=不通（致命），黄=有风险（如版本不符、预置数据不足）。
任一红 → run_check 返回 False（CLI 据此 fail fast）。
"""
from __future__ import annotations

import asyncio
import re
import time
from typing import Any

from rich.table import Table

from core import logging as log
from core.logging import console
from core.models import RunContext


# --------------------------------------------------------------------------- #
# 版本比较
# --------------------------------------------------------------------------- #
def _ver_tuple(v: str) -> tuple[int, ...]:
    return tuple(int(x) for x in re.findall(r"\d+", v)) or (0,)


def _check_version(expect: str, actual: str) -> bool:
    m = re.match(r"\s*(>=|<=|==|>|<)?\s*([\d.]+)", expect)
    if not m:
        return True
    op, target = m.group(1) or ">=", m.group(2)
    a, t = _ver_tuple(actual), _ver_tuple(target)
    return {
        ">=": a >= t, "<=": a <= t, "==": a == t, ">": a > t, "<": a < t,
    }[op]


# --------------------------------------------------------------------------- #
# 各探测（同步实现，统一用 to_thread 并发）
# --------------------------------------------------------------------------- #
def _probe_db(db) -> dict[str, Any]:
    from sqlalchemy import create_engine, text
    try:
        engine = create_engine(db.dsn, pool_pre_ping=True, connect_args={"connect_timeout": 5})
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            if db.check == "rw":
                conn.execute(text("CREATE TEMPORARY TABLE _tp_check (id INT)"))
                conn.execute(text("DROP TABLE _tp_check"))
        engine.dispose()
        return {"status": "ok", "detail": f"{db.type} {db.check} 正常"}
    except Exception as exc:
        return {"status": "fail", "detail": str(exc)[:120]}


def _probe_redis(r) -> dict[str, Any]:
    import redis
    try:
        client = redis.Redis(host=r.host, port=r.port, password=r.password or None,
                             db=r.db, socket_connect_timeout=5)
        client.ping()
        return {"status": "ok", "detail": "PING 正常"}
    except Exception as exc:
        return {"status": "fail", "detail": str(exc)[:120]}


def _probe_mq(mq) -> dict[str, Any]:
    try:
        if mq.type == "rabbitmq":
            import pika
            params = pika.URLParameters(mq.url)
            params.socket_timeout = 5
            conn = pika.BlockingConnection(params)
            conn.close()
            return {"status": "ok", "detail": "RabbitMQ 连接正常"}
        else:  # kafka
            from kafka import KafkaAdminClient
            admin = KafkaAdminClient(bootstrap_servers=mq.url, request_timeout_ms=5000)
            admin.list_topics()
            admin.close()
            return {"status": "ok", "detail": "Kafka 连接正常"}
    except Exception as exc:
        return {"status": "fail", "detail": str(exc)[:120]}


def _probe_http(h, proxy: str) -> dict[str, Any]:
    import httpx
    try:
        resp = httpx.get(h.url, timeout=8, verify=False, follow_redirects=True,
                         proxy=proxy or None)
        if resp.status_code >= 400:
            return {"status": "fail", "detail": f"HTTP {resp.status_code}"}
        if h.expect_version:
            try:
                actual = str(resp.json().get("version", ""))
            except Exception:
                actual = ""
            if not actual:
                return {"status": "warn", "detail": f"HTTP {resp.status_code}，但无 version 字段"}
            if not _check_version(h.expect_version, actual):
                return {"status": "warn", "detail": f"版本 {actual} 不满足 {h.expect_version}"}
            return {"status": "ok", "detail": f"HTTP {resp.status_code}，版本 {actual} ✓"}
        return {"status": "ok", "detail": f"HTTP {resp.status_code}"}
    except Exception as exc:
        return {"status": "fail", "detail": str(exc)[:120]}


def _probe_preset(pd, dbs) -> dict[str, Any]:
    from sqlalchemy import create_engine, text
    db = next((d for d in dbs if d.name == pd.db), None)
    if not db:
        return {"status": "warn", "detail": f"未找到关联 DB '{pd.db}'"}
    try:
        engine = create_engine(db.dsn, connect_args={"connect_timeout": 5})
        sql = f"SELECT COUNT(*) FROM {pd.table}"
        if pd.where:
            sql += f" WHERE {pd.where}"
        with engine.connect() as conn:
            n = conn.execute(text(sql)).scalar() or 0
        engine.dispose()
        if n >= pd.min_rows:
            return {"status": "ok", "detail": f"{pd.table} 行数 {n} ≥ {pd.min_rows}"}
        return {"status": "warn", "detail": f"{pd.table} 行数 {n} < {pd.min_rows}"}
    except Exception as exc:
        return {"status": "fail", "detail": str(exc)[:120]}


# --------------------------------------------------------------------------- #
# 并发编排
# --------------------------------------------------------------------------- #
async def _run_all(ctx: RunContext) -> list[dict[str, Any]]:
    env = ctx.env_cfg
    tasks: list[tuple[str, str, Any]] = []
    for d in env.dbs:
        tasks.append(("DB", d.name, lambda d=d: _probe_db(d)))
    for r in env.redis:
        tasks.append(("Redis", r.name, lambda r=r: _probe_redis(r)))
    for m in env.mqs:
        tasks.append(("MQ", m.name, lambda m=m: _probe_mq(m)))
    for h in env.https:
        tasks.append(("HTTP", h.name, lambda h=h: _probe_http(h, ctx.proxy)))
    for pd in env.preset_data:
        tasks.append(("预置数据", f"{pd.db}.{pd.table}", lambda pd=pd: _probe_preset(pd, env.dbs)))

    sem = asyncio.Semaphore(ctx.platform.concurrency)

    async def _one(cat, name, fn):
        async with sem:
            t0 = time.perf_counter()
            res = await asyncio.to_thread(fn)
            res.update(category=cat, name=name, ms=int((time.perf_counter() - t0) * 1000))
            return res

    return await asyncio.gather(*[_one(c, n, f) for c, n, f in tasks])


def run_check(ctx: RunContext) -> bool:
    log.rule(f"环境健康检查 · {ctx.site}/{ctx.env}")
    if ctx.env_cfg.expect_version:
        log.info(f"期望版本：{ctx.env_cfg.expect_version}")

    results = asyncio.run(_run_all(ctx))
    if not results:
        log.warn("该环境未配置任何依赖探测项。")
        return True

    table = Table(show_header=True, header_style="bold")
    table.add_column("类型"); table.add_column("名称")
    table.add_column("状态"); table.add_column("耗时"); table.add_column("详情")
    icon = {"ok": "[green]● 正常[/green]", "fail": "[red]● 不通[/red]", "warn": "[yellow]● 风险[/yellow]"}
    results.sort(key=lambda r: {"fail": 0, "warn": 1, "ok": 2}[r["status"]])
    for r in results:
        table.add_row(r["category"], r["name"], icon[r["status"]], f"{r['ms']}ms", r["detail"])
    console.print(table)

    fails = sum(1 for r in results if r["status"] == "fail")
    warns = sum(1 for r in results if r["status"] == "warn")
    if fails:
        log.err(f"{fails} 项不通，{warns} 项风险 → 环境不可用")
        return False
    if warns:
        log.warn(f"全部连通，但 {warns} 项有风险")
    else:
        log.ok("全部正常")
    return True
