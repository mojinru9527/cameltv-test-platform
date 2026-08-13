"""Batch 167 Phase 3a — 功能用例导入自动生成 UI 变体并三类关联计划。"""
from __future__ import annotations

import json

from app.models.requirement import RequirementDocument
from app.models.test_case import TestCase
from app.models.test_plan import TestPlanCase
from app.services.requirement_service import import_cases, prepare_cases_for_import


def _make_doc(db, title="B167-功能"):
    doc = RequirementDocument(
        project_id=1, title=title, status="generated",
        ai_raw=json.dumps({
            "functional_cases": [{
                "index": 0,
                "title": "首页直播列表加载",
                "priority": "P0",
                "domain": "用户端",
                "module": "首页",
                "steps": json.dumps([{"step": 1, "desc": "打开首页", "expected": "看到直播列表"}]),
                "expected_result": "直播列表展示",
            }],
        }),
    )
    db.add(doc)
    db.commit()
    return doc


def test_import_creates_ui_variant_and_links_plan(db_session):
    doc = _make_doc(db_session)
    selected = prepare_cases_for_import(db_session, doc_id=doc.id, project_id=1, indices=[0])
    result = import_cases(
        db_session, doc.id, selected, project_id=1, create_plan=True, creator_id=1,
    )
    assert result["ui_created"] == 1
    assert result["plan_id"] is not None

    manual = db_session.query(TestCase).filter(
        TestCase.source_doc_id == doc.id, TestCase.case_type == "manual",
    ).one()
    ui = db_session.query(TestCase).filter(
        TestCase.source_doc_id == doc.id, TestCase.case_type == "ui",
    ).one()
    assert ui.title == f"[UI] {manual.title}"
    assert ui.module == manual.module
    linked = {pc.case_id for pc in db_session.query(TestPlanCase).all()}
    assert manual.id in linked and ui.id in linked


def test_ui_variant_idempotent(db_session):
    doc = _make_doc(db_session, title="B167-幂等")
    selected = prepare_cases_for_import(db_session, doc_id=doc.id, project_id=1, indices=[0])
    first = import_cases(db_session, doc.id, selected, project_id=1, create_plan=False)
    # 手动重复导入同索引会被 skip，但 UI 变体不应新增
    ui_count = db_session.query(TestCase).filter(TestCase.case_type == "ui", TestCase.source_doc_id == doc.id).count()
    assert first["ui_created"] == 1
    assert ui_count == 1


def test_low_priority_does_not_create_ui_variant(db_session):
    doc = RequirementDocument(
        project_id=1, title="B167-P2", status="generated",
        ai_raw=json.dumps({"functional_cases": [{
            "index": 0, "title": "P2 用例", "priority": "P2", "module": "X",
            "steps": json.dumps([{"step": 1, "desc": "a", "expected": "b"}]),
        }]}),
    )
    db_session.add(doc)
    db_session.commit()
    selected = prepare_cases_for_import(db_session, doc_id=doc.id, project_id=1, indices=[0])
    result = import_cases(db_session, doc.id, selected, project_id=1, create_plan=False)
    assert result["ui_created"] == 0
    assert db_session.query(TestCase).filter(TestCase.case_type == "ui", TestCase.source_doc_id == doc.id).count() == 0
