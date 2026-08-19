"""B2 — DSH 产物解析落库服务单测（dsh_artifact_service）。

in-memory SQLite + 手工构造 DshTask 行（沿用 test_dsh_tasks.dsh_db fixture 模式）。
覆盖：合法清单落库、type 覆盖 scene 映射、无清单/非法 JSON、幂等、scene=general 不写入。
"""
from __future__ import annotations

import json

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.core.db import Base
from app.models.dsh_task import DshTask
from app.models.knowledge import AiArtifact
from app.services.dsh.dsh_artifact_service import ingest_artifacts, parse_artifact_list


@pytest.fixture()
def dsh_artifact_db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    maker = sessionmaker(bind=engine)
    return maker


def _make_task(maker, *, scene="functional", output_text="", project_id=1) -> DshTask:
    db = maker()
    try:
        row = DshTask(
            project_id=project_id,
            task="生成用例",
            status="success",
            params_json=json.dumps({"scene": scene}, ensure_ascii=False),
            output_text=output_text,
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        return row
    finally:
        db.close()


def _manifest(entries: list[dict]) -> str:
    return (
        "## 产物清单\n```json\n"
        + json.dumps(entries, ensure_ascii=False)
        + "\n```\n"
    )


def _artifacts(maker) -> list[AiArtifact]:
    db = maker()
    try:
        return list(db.scalars(select(AiArtifact).order_by(AiArtifact.id)).all())
    finally:
        db.close()


# ── parse_artifact_list ──

def test_parse_manifest_extracts_json_list():
    out = _manifest([{"type": "functional_case", "title": "登录用例", "summary": "s", "content": {}}])
    items = parse_artifact_list(out)
    assert len(items) == 1
    assert items[0]["title"] == "登录用例"


def test_parse_manifest_without_header_scans_full_text():
    out = '```json\n[{"type": "api_case", "title": "x"}]\n```'
    items = parse_artifact_list(out)
    assert len(items) == 1 and items[0]["type"] == "api_case"


def test_parse_returns_empty_on_invalid_or_missing():
    assert parse_artifact_list("") == []
    assert parse_artifact_list("## 产物清单\n坏掉的 json") == []
    assert parse_artifact_list(None) == []
    # 非 list（dict）→ 空
    assert parse_artifact_list('```json\n{"a": 1}\n```') == []


# ── ingest_artifacts ──

def test_ingest_writes_pending_with_source_ref(dsh_artifact_db):
    maker = dsh_artifact_db
    task = _make_task(maker, scene="functional", output_text=_manifest([
        {"type": "functional_case", "title": "登录用例", "summary": "s", "content": {"steps": []}},
        {"type": "functional_case", "title": "注册用例", "summary": "s", "content": {}},
    ]))
    db = maker()
    try:
        written, err = ingest_artifacts(db, task)
        db.commit()
    finally:
        db.close()
    assert written == 2
    assert err is None
    rows = _artifacts(maker)
    assert len(rows) == 2
    assert all(r.review_status == "pending" for r in rows)
    assert all(r.project_id == 1 for r in rows)
    assert all(f'"dsh_task:{task.id}"' in r.source_refs for r in rows)


def test_ingest_type_covers_scene_mapping(dsh_artifact_db):
    """清单条目缺失 type → 用 scene 兜底（functional → functional_case）。"""
    maker = dsh_artifact_db
    task = _make_task(maker, scene="functional", output_text=_manifest([
        {"title": "无 type 条目", "summary": "s", "content": {}},
    ]))
    db = maker()
    try:
        written, _ = ingest_artifacts(db, task)
        db.commit()
    finally:
        db.close()
    assert written == 1
    rows = _artifacts(maker)
    assert rows[0].artifact_type == "functional_case"


def test_ingest_scene_api_maps_api_case(dsh_artifact_db):
    maker = dsh_artifact_db
    task = _make_task(maker, scene="api", output_text=_manifest([
        {"type": "api_case", "title": "订单接口", "content": {"api_endpoint": "/x"}},
    ]))
    db = maker()
    try:
        written, _ = ingest_artifacts(db, task)
        db.commit()
    finally:
        db.close()
    assert written == 1
    assert _artifacts(maker)[0].artifact_type == "api_case"


def test_ingest_no_manifest_writes_zero(dsh_artifact_db):
    maker = dsh_artifact_db
    task = _make_task(maker, scene="functional", output_text="普通报告，无清单")
    db = maker()
    try:
        written, _ = ingest_artifacts(db, task)
    finally:
        db.close()
    assert written == 0
    assert _artifacts(maker) == []


def test_ingest_invalid_json_writes_zero_no_raise(dsh_artifact_db):
    maker = dsh_artifact_db
    task = _make_task(maker, scene="functional", output_text="## 产物清单\n```json\n[不是合法json\n```")
    db = maker()
    try:
        written, _ = ingest_artifacts(db, task)  # 不应抛异常
    finally:
        db.close()
    assert written == 0


def test_ingest_general_scene_writes_zero(dsh_artifact_db):
    maker = dsh_artifact_db
    task = _make_task(maker, scene="general", output_text=_manifest([
        {"type": "functional_case", "title": "x", "content": {}},
    ]))
    db = maker()
    try:
        written, _ = ingest_artifacts(db, task)
    finally:
        db.close()
    assert written == 0
    assert _artifacts(maker) == []


def test_ingest_idempotent(dsh_artifact_db):
    maker = dsh_artifact_db
    task = _make_task(maker, scene="functional", output_text=_manifest([
        {"type": "functional_case", "title": "登录用例", "content": {}},
    ]))
    db = maker()
    try:
        w1, _ = ingest_artifacts(db, task)
        db.commit()
        w2, _ = ingest_artifacts(db, task)
        db.commit()
    finally:
        db.close()
    assert w1 == 1
    assert w2 == 0
    assert len(_artifacts(maker)) == 1


def test_ingest_skips_invalid_type_items(dsh_artifact_db):
    """清单条目 type 非法 → 跳过该条，其余正常落库。"""
    maker = dsh_artifact_db
    task = _make_task(maker, scene="functional", output_text=_manifest([
        {"type": "unknown_type", "title": "x", "content": {}},
        {"type": "functional_case", "title": "有效", "content": {}},
    ]))
    db = maker()
    try:
        written, _ = ingest_artifacts(db, task)
        db.commit()
    finally:
        db.close()
    assert written == 1
    assert _artifacts(maker)[0].title == "有效"
