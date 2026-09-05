"""Batch 230 / S5 — 缺陷检索支持编号（DEF-20260905-005）。

覆盖三件事：按 `defect_id` 命中、按标题命中不回归、`project_id` 隔离仍在 OR 之外。
"""
from __future__ import annotations

from app.models.defect import Defect
from app.services.defect_service import list_defects


def _mk(db, *, project_id: int, defect_id: str, title: str, severity: str = "P2") -> Defect:
    row = Defect(
        project_id=project_id, defect_id=defect_id, title=title, severity=severity
    )
    db.add(row)
    db.commit()
    return row


def test_keyword_matches_defect_id_prefix_and_exact(db_session):
    _mk(db_session, project_id=1, defect_id="DEF-20260904-010", title="登录会话超时")
    _mk(db_session, project_id=1, defect_id="DEF-20260904-011", title="契约快照空壳")
    _mk(db_session, project_id=1, defect_id="DEF-20260905-001", title="列表页不可达")

    items, total = list_defects(db_session, project_id=1, keyword="DEF-20260904-010")
    assert total == 1
    assert [i["defect_id"] for i in items] == ["DEF-20260904-010"]

    # 日期前缀一次捞出当天全部缺陷，是复测台账最常用的检索形态
    items, total = list_defects(db_session, project_id=1, keyword="DEF-20260904")
    assert total == 2
    assert {i["defect_id"] for i in items} == {"DEF-20260904-010", "DEF-20260904-011"}


def test_keyword_still_matches_title(db_session):
    _mk(db_session, project_id=1, defect_id="DEF-20260904-010", title="契约快照空壳")
    _mk(db_session, project_id=1, defect_id="DEF-20260904-011", title="一键运行假成功")

    items, total = list_defects(db_session, project_id=1, keyword="契约")
    assert total == 1
    assert items[0]["defect_id"] == "DEF-20260904-010"


def test_keyword_is_isolated_per_project(db_session):
    """§6 条件 5：project_id 必须留在 or_ 之外，否则编号检索会跨项目泄漏。"""
    _mk(db_session, project_id=1, defect_id="DEF-20260905-001", title="体育项目列表")
    _mk(db_session, project_id=2, defect_id="DEF-20260905-002", title="电商项目列表")

    items, total = list_defects(db_session, project_id=1, keyword="DEF-20260905")
    assert total == 1
    assert [i["defect_id"] for i in items] == ["DEF-20260905-001"]
    assert all(i["project_id"] == 1 for i in items)

    # 命中另一项目的编号时，本项目返回空而非串数据
    items, total = list_defects(db_session, project_id=1, keyword="DEF-20260905-002")
    assert total == 0
    assert items == []


def test_keyword_ands_with_other_filters(db_session):
    """OR 只包住 title/defect_id，不得吞掉 severity 等同级过滤条件。"""
    _mk(db_session, project_id=1, defect_id="DEF-20260904-010", title="契约空壳", severity="P1")
    _mk(db_session, project_id=1, defect_id="DEF-20260904-011", title="契约重复", severity="P3")

    items, total = list_defects(db_session, project_id=1, keyword="契约", severity="P1")
    assert total == 1
    assert items[0]["defect_id"] == "DEF-20260904-010"

    items, total = list_defects(db_session, project_id=1, keyword="DEF-20260904", severity="P3")
    assert total == 1
    assert items[0]["defect_id"] == "DEF-20260904-011"
