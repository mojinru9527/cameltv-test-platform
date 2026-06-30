"""统一 SQLite 数据库管理层 — 测试用例 / 测试计划 / 计划执行 / 任务历史。

数据库文件: data/platform.db
所有表自动创建（CREATE TABLE IF NOT EXISTS）。
"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

from core.config_loader import ROOT

DB_PATH = ROOT / "data" / "platform.db"


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db() -> None:
    """启动时建表（幂等）。"""
    conn = _connect()
    conn.executescript("""
    -- 任务执行历史（兼容旧 task_store.sqlite）
    CREATE TABLE IF NOT EXISTS tasks(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      task_type TEXT, env TEXT, status TEXT,
      started_at TEXT, finished_at TEXT,
      result_summary TEXT
    );

    -- 测试用例库
    CREATE TABLE IF NOT EXISTS test_cases(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      title TEXT NOT NULL,
      module TEXT DEFAULT '',
      priority TEXT DEFAULT 'P2' CHECK(priority IN ('P0','P1','P2','P3')),
      status TEXT DEFAULT 'draft' CHECK(status IN ('draft','active','archived')),
      type TEXT DEFAULT 'api' CHECK(type IN ('api','ui','manual')),
      tags TEXT DEFAULT '[]',
      preconditions TEXT DEFAULT '',
      steps TEXT DEFAULT '[]',
      expected_result TEXT DEFAULT '',
      api_spec_ref TEXT DEFAULT '',
      created_at TEXT NOT NULL,
      updated_at TEXT NOT NULL
    );

    -- 测试计划
    CREATE TABLE IF NOT EXISTS test_plans(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      name TEXT NOT NULL,
      description TEXT DEFAULT '',
      env TEXT DEFAULT 'test',
      status TEXT DEFAULT 'draft' CHECK(status IN ('draft','active','completed')),
      pass_rate REAL DEFAULT 0,
      created_at TEXT NOT NULL,
      updated_at TEXT NOT NULL
    );

    -- 计划关联用例
    CREATE TABLE IF NOT EXISTS test_plan_items(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      plan_id INTEGER NOT NULL,
      case_id INTEGER NOT NULL,
      sort_order INTEGER DEFAULT 0,
      status TEXT DEFAULT 'pending' CHECK(status IN ('pending','pass','fail','skip')),
      actual_result TEXT DEFAULT '',
      executed_at TEXT DEFAULT '',
      FOREIGN KEY(plan_id) REFERENCES test_plans(id) ON DELETE CASCADE,
      FOREIGN KEY(case_id) REFERENCES test_cases(id) ON DELETE CASCADE
    );

    -- 计划执行记录
    CREATE TABLE IF NOT EXISTS test_plan_runs(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      plan_id INTEGER NOT NULL,
      status TEXT DEFAULT 'running' CHECK(status IN ('running','passed','failed')),
      started_at TEXT NOT NULL,
      finished_at TEXT DEFAULT '',
      summary TEXT DEFAULT '{}',
      FOREIGN KEY(plan_id) REFERENCES test_plans(id) ON DELETE CASCADE
    );
    """)
    conn.commit()
    conn.close()


# ═══════════════════════════════════════════════════════════════════
# 辅助
# ═══════════════════════════════════════════════════════════════════

def _row_to_dict(row: sqlite3.Row) -> dict:
    d = dict(row)
    # 反序列化 JSON 字段
    for key in ("tags", "steps", "summary"):
        if key in d and isinstance(d[key], str):
            try:
                d[key] = json.loads(d[key])
            except (json.JSONDecodeError, TypeError):
                pass
    return d


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


# ═══════════════════════════════════════════════════════════════════
# Tasks（兼容旧 task_store）
# ═══════════════════════════════════════════════════════════════════

def create_task(task_type: str, env: str) -> int:
    conn = _connect()
    cur = conn.execute(
        "INSERT INTO tasks(task_type, env, status, started_at) VALUES (?,?,?,?)",
        (task_type, env, "running", _now()),
    )
    conn.commit()
    tid = cur.lastrowid
    conn.close()
    return tid


def finish_task(task_id: int, status: str, summary: str = "") -> None:
    conn = _connect()
    conn.execute(
        "UPDATE tasks SET status=?, finished_at=?, result_summary=? WHERE id=?",
        (status, _now(), summary, task_id),
    )
    conn.commit()
    conn.close()


def list_tasks(limit: int = 50) -> list[dict]:
    conn = _connect()
    rows = conn.execute(
        "SELECT * FROM tasks ORDER BY id DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ═══════════════════════════════════════════════════════════════════
# Test Cases CRUD
# ═══════════════════════════════════════════════════════════════════

def create_case(data: dict) -> dict:
    conn = _connect()
    now = _now()
    cur = conn.execute(
        """INSERT INTO test_cases
           (title, module, priority, status, type, tags, preconditions, steps,
            expected_result, api_spec_ref, created_at, updated_at)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            data["title"],
            data.get("module", ""),
            data.get("priority", "P2"),
            data.get("status", "draft"),
            data.get("type", "api"),
            json.dumps(data.get("tags", []), ensure_ascii=False),
            data.get("preconditions", ""),
            json.dumps(data.get("steps", []), ensure_ascii=False),
            data.get("expected_result", ""),
            data.get("api_spec_ref", ""),
            now, now,
        ),
    )
    conn.commit()
    case_id = cur.lastrowid
    conn.close()
    return get_case(case_id)


def get_case(case_id: int) -> dict | None:
    conn = _connect()
    row = conn.execute("SELECT * FROM test_cases WHERE id=?", (case_id,)).fetchone()
    conn.close()
    return _row_to_dict(row) if row else None


def update_case(case_id: int, data: dict) -> dict | None:
    existing = get_case(case_id)
    if not existing:
        return None
    conn = _connect()
    conn.execute(
        """UPDATE test_cases SET
           title=?, module=?, priority=?, status=?, type=?, tags=?,
           preconditions=?, steps=?, expected_result=?, api_spec_ref=?,
           updated_at=?
           WHERE id=?""",
        (
            data.get("title", existing["title"]),
            data.get("module", existing.get("module", "")),
            data.get("priority", existing.get("priority", "P2")),
            data.get("status", existing.get("status", "draft")),
            data.get("type", existing.get("type", "api")),
            json.dumps(data.get("tags", existing.get("tags", [])), ensure_ascii=False),
            data.get("preconditions", existing.get("preconditions", "")),
            json.dumps(data.get("steps", existing.get("steps", [])), ensure_ascii=False),
            data.get("expected_result", existing.get("expected_result", "")),
            data.get("api_spec_ref", existing.get("api_spec_ref", "")),
            _now(),
            case_id,
        ),
    )
    conn.commit()
    conn.close()
    return get_case(case_id)


def delete_case(case_id: int) -> bool:
    conn = _connect()
    cur = conn.execute("DELETE FROM test_cases WHERE id=?", (case_id,))
    conn.commit()
    deleted = cur.rowcount > 0
    conn.close()
    return deleted


def list_cases(
    module: str = "",
    priority: str = "",
    status: str = "",
    type: str = "",
    keyword: str = "",
    limit: int = 200,
    offset: int = 0,
) -> tuple[list[dict], int]:
    conn = _connect()
    where = ["1=1"]
    params: list[Any] = []

    if module:
        where.append("module = ?"); params.append(module)
    if priority:
        where.append("priority = ?"); params.append(priority)
    if status:
        where.append("status = ?"); params.append(status)
    if type:
        where.append("type = ?"); params.append(type)
    if keyword:
        where.append("(title LIKE ? OR module LIKE ?)")
        params.extend([f"%{keyword}%", f"%{keyword}%"])

    clause = " AND ".join(where)
    total = conn.execute(f"SELECT COUNT(*) FROM test_cases WHERE {clause}", params).fetchone()[0]
    rows = conn.execute(
        f"SELECT * FROM test_cases WHERE {clause} ORDER BY updated_at DESC LIMIT ? OFFSET ?",
        params + [limit, offset],
    ).fetchall()
    conn.close()
    return [_row_to_dict(r) for r in rows], total


def list_modules() -> list[str]:
    conn = _connect()
    rows = conn.execute(
        "SELECT DISTINCT module FROM test_cases WHERE module != '' ORDER BY module"
    ).fetchall()
    conn.close()
    return [r["module"] for r in rows]


# ═══════════════════════════════════════════════════════════════════
# Test Plans CRUD
# ═══════════════════════════════════════════════════════════════════

def create_plan(data: dict) -> dict:
    conn = _connect()
    now = _now()
    cur = conn.execute(
        """INSERT INTO test_plans (name, description, env, status, created_at, updated_at)
           VALUES (?,?,?,?,?,?)""",
        (data["name"], data.get("description", ""), data.get("env", "test"),
         data.get("status", "draft"), now, now),
    )
    plan_id = cur.lastrowid

    # 关联用例
    case_ids = data.get("case_ids", [])
    for i, cid in enumerate(case_ids):
        conn.execute(
            "INSERT INTO test_plan_items (plan_id, case_id, sort_order) VALUES (?,?,?)",
            (plan_id, cid, i),
        )
    conn.commit()
    conn.close()
    return get_plan(plan_id)


def get_plan(plan_id: int) -> dict | None:
    conn = _connect()
    row = conn.execute("SELECT * FROM test_plans WHERE id=?", (plan_id,)).fetchone()
    if not row:
        conn.close(); return None
    plan = dict(row)
    # 关联用例
    items = conn.execute(
        """SELECT tpi.*, tc.title as case_title, tc.module as case_module,
                  tc.priority as case_priority, tc.type as case_type
           FROM test_plan_items tpi
           JOIN test_cases tc ON tc.id = tpi.case_id
           WHERE tpi.plan_id = ?
           ORDER BY tpi.sort_order""",
        (plan_id,),
    ).fetchall()
    plan["items"] = [dict(it) for it in items]
    # 执行历史
    runs = conn.execute(
        "SELECT * FROM test_plan_runs WHERE plan_id=? ORDER BY id DESC LIMIT 10",
        (plan_id,),
    ).fetchall()
    plan["runs"] = [_row_to_dict(r) for r in runs]
    conn.close()
    return plan


def update_plan(plan_id: int, data: dict) -> dict | None:
    existing = get_plan(plan_id)
    if not existing:
        return None
    conn = _connect()
    conn.execute(
        """UPDATE test_plans SET name=?, description=?, env=?, status=?, updated_at=?
           WHERE id=?""",
        (
            data.get("name", existing["name"]),
            data.get("description", existing.get("description", "")),
            data.get("env", existing.get("env", "test")),
            data.get("status", existing.get("status", "draft")),
            _now(),
            plan_id,
        ),
    )
    # 更新用例关联（全量替换）
    if "case_ids" in data:
        conn.execute("DELETE FROM test_plan_items WHERE plan_id=?", (plan_id,))
        for i, cid in enumerate(data["case_ids"]):
            conn.execute(
                "INSERT INTO test_plan_items (plan_id, case_id, sort_order) VALUES (?,?,?)",
                (plan_id, cid, i),
            )
    conn.commit()
    conn.close()
    return get_plan(plan_id)


def delete_plan(plan_id: int) -> bool:
    conn = _connect()
    cur = conn.execute("DELETE FROM test_plans WHERE id=?", (plan_id,))
    conn.commit()
    deleted = cur.rowcount > 0
    conn.close()
    return deleted


def list_plans(status: str = "", limit: int = 50, offset: int = 0) -> tuple[list[dict], int]:
    conn = _connect()
    if status:
        total = conn.execute(
            "SELECT COUNT(*) FROM test_plans WHERE status=?", (status,)
        ).fetchone()[0]
        rows = conn.execute(
            "SELECT * FROM test_plans WHERE status=? ORDER BY updated_at DESC LIMIT ? OFFSET ?",
            (status, limit, offset),
        ).fetchall()
    else:
        total = conn.execute("SELECT COUNT(*) FROM test_plans").fetchone()[0]
        rows = conn.execute(
            "SELECT * FROM test_plans ORDER BY updated_at DESC LIMIT ? OFFSET ?",
            (limit, offset),
        ).fetchall()

    plans = []
    for row in rows:
        plan = dict(row)
        # 附上用例句数
        cnt = conn.execute(
            "SELECT COUNT(*) FROM test_plan_items WHERE plan_id=?", (row["id"],)
        ).fetchone()[0]
        plan["case_count"] = cnt
        plans.append(plan)
    conn.close()
    return plans, total


# ═══════════════════════════════════════════════════════════════════
# Test Plan Runs
# ═══════════════════════════════════════════════════════════════════

def create_plan_run(plan_id: int) -> int:
    conn = _connect()
    cur = conn.execute(
        "INSERT INTO test_plan_runs (plan_id, status, started_at) VALUES (?,?,?)",
        (plan_id, "running", _now()),
    )
    # 重置所有用例项状态为 pending
    conn.execute(
        "UPDATE test_plan_items SET status='pending', actual_result='', executed_at='' WHERE plan_id=?",
        (plan_id,),
    )
    conn.commit()
    run_id = cur.lastrowid
    conn.close()
    return run_id


def finish_plan_run(run_id: int, status: str, summary: dict | None = None) -> None:
    conn = _connect()
    conn.execute(
        "UPDATE test_plan_runs SET status=?, finished_at=?, summary=? WHERE id=?",
        (status, _now(), json.dumps(summary or {}, ensure_ascii=False), run_id),
    )
    conn.commit()
    conn.close()


def update_plan_item(item_id: int, status: str, actual_result: str = "") -> None:
    conn = _connect()
    conn.execute(
        "UPDATE test_plan_items SET status=?, actual_result=?, executed_at=? WHERE id=?",
        (status, actual_result, _now(), item_id),
    )
    conn.commit()
    conn.close()


# ═══════════════════════════════════════════════════════════════════
# Workspace Stats
# ═══════════════════════════════════════════════════════════════════

def workspace_stats() -> dict:
    conn = _connect()

    total_cases = conn.execute("SELECT COUNT(*) FROM test_cases").fetchone()[0]
    active_cases = conn.execute(
        "SELECT COUNT(*) FROM test_cases WHERE status='active'"
    ).fetchone()[0]
    total_plans = conn.execute("SELECT COUNT(*) FROM test_plans").fetchone()[0]
    active_plans = conn.execute(
        "SELECT COUNT(*) FROM test_plans WHERE status='active'"
    ).fetchone()[0]

    # 今日执行次数
    today = datetime.now().strftime("%Y-%m-%d")
    today_runs = conn.execute(
        "SELECT COUNT(*) FROM test_plan_runs WHERE started_at LIKE ?",
        (f"{today}%",),
    ).fetchone()[0]

    # 最近通过率趋势（近 7 天，按天聚合）
    trend_rows = conn.execute(
        """SELECT DATE(started_at) as day,
                  COUNT(*) as total,
                  SUM(CASE WHEN status='passed' THEN 1 ELSE 0 END) as passed
           FROM test_plan_runs
           WHERE started_at >= DATE('now', '-7 days')
           GROUP BY day ORDER BY day"""
    ).fetchall()
    trend = [
        {"day": r["day"], "total": r["total"],
         "passed": r["passed"],
         "rate": round(r["passed"] / r["total"] * 100, 1) if r["total"] else 0}
        for r in trend_rows
    ]

    # 模块用例分布
    modules_rows = conn.execute(
        "SELECT module, COUNT(*) as cnt FROM test_cases WHERE module != '' GROUP BY module ORDER BY cnt DESC"
    ).fetchall()
    modules = [{"module": r["module"], "count": r["cnt"]} for r in modules_rows]

    conn.close()
    return {
        "total_cases": total_cases,
        "active_cases": active_cases,
        "total_plans": total_plans,
        "active_plans": active_plans,
        "today_runs": today_runs,
        "trend": trend,
        "modules": modules,
    }


# ═══════════════════════════════════════════════════════════════════
# 初始化
# ═══════════════════════════════════════════════════════════════════
init_db()
