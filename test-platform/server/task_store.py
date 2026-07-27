"""任务执行记录存储（SQLite）。"""
from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path

from core.config_loader import ROOT

DB_PATH = ROOT / "data" / "task_store.sqlite"


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS tasks(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      task_type TEXT, env TEXT, status TEXT,
      started_at TEXT, finished_at TEXT,
      result_summary TEXT
    );
    """)
    conn.commit()
    return conn


def create_task(task_type: str, env: str) -> int:
    conn = _connect()
    started = datetime.now().isoformat(timespec="seconds")
    cur = conn.execute(
        "INSERT INTO tasks(task_type, env, status, started_at) VALUES (?,?,?,?)",
        (task_type, env, "running", started),
    )
    conn.commit()
    task_id = cur.lastrowid
    conn.close()
    return task_id


def finish_task(task_id: int, status: str, summary: str = "") -> None:
    conn = _connect()
    finished = datetime.now().isoformat(timespec="seconds")
    conn.execute(
        "UPDATE tasks SET status=?, finished_at=?, result_summary=? WHERE id=?",
        (status, finished, summary, task_id),
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
