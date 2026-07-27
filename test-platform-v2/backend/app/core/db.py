"""数据库引擎与会话 — SQLAlchemy 2.0。

SQLite 起步（WAL 模式）；升级 PostgreSQL 仅需改 DATABASE_URL。
"""
from __future__ import annotations

from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import settings

_is_sqlite = settings.database_url.startswith("sqlite")

# SQLite 需要确保数据目录存在
if _is_sqlite:
    db_file = settings.database_url.replace("sqlite:///", "", 1)
    Path(db_file).resolve().parent.mkdir(parents=True, exist_ok=True)

_engine_kwargs: dict = {"pool_pre_ping": True}
if _is_sqlite:
    # timeout（秒）：写锁被占用时，sqlite3 底层 busy handler 最长等待时长；
    # 不设则并发写立即抛 "database is locked"（后台采集/嵌入/wiki 编译持锁时尤甚）。
    _engine_kwargs["connect_args"] = {"check_same_thread": False, "timeout": 30}
else:
    # PostgreSQL connection pooling (V2.6)
    _engine_kwargs["pool_size"] = settings.db_pool_size
    _engine_kwargs["max_overflow"] = settings.db_max_overflow
    _engine_kwargs["pool_recycle"] = 3600

engine = create_engine(settings.database_url, **_engine_kwargs)

if _is_sqlite:
    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_conn, _):  # noqa: ANN001
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA journal_mode=WAL")
        cur.execute("PRAGMA foreign_keys=ON")
        # busy_timeout（毫秒）：与 connect timeout 呼应，显式让写者在锁竞争时轮询等待
        # 而非立即失败，消除后台任务与同步请求并发写造成的 500 database is locked。
        cur.execute("PRAGMA busy_timeout=30000")
        # WAL 下 synchronous=NORMAL 安全且显著减少 fsync，降低写锁持有时长。
        cur.execute("PRAGMA synchronous=NORMAL")
        cur.close()

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


class Base(DeclarativeBase):
    """所有 ORM 模型的基类。"""


def get_db():
    """FastAPI 依赖：每请求一个会话。"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
