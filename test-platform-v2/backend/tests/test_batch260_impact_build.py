"""Batch 260 / B3-2 — 关联构建：需求变更 → 模块 → 用例（含覆盖率证据）。

DoD（backlog B3-2）：体育试点模块关联覆盖率 ≥90%。
本文件用**合成数据**证明度量口径与算法正确（含恰好 90% 的边界），
真实体育资产上的数字由回填脚本在目标环境产出（见 C260-1）。
"""
from __future__ import annotations

import pytest

from app.core.exceptions import APIException
from app.models.release_bundle import ReleaseBundle
from app.models.requirement_module import RequirementModule
from app.models.test_case import TestCase
from app.services import impact_graph_service


def _bundle(db, project_id: int = 1, version: str = "16.1.0") -> ReleaseBundle:
    bundle = ReleaseBundle(project_id=project_id, name=f"v{version}", client_version=version)
    db.add(bundle)
    db.commit()
    db.refresh(bundle)
    return bundle


def _module(db, bundle, name: str, *, node_type="module", change_type="", parent_id=None):
    module = RequirementModule(
        project_id=bundle.project_id,
        release_bundle_id=bundle.id,
        name=name,
        node_type=node_type,
        change_type=change_type,
        parent_module_id=parent_id,
    )
    db.add(module)
    db.commit()
    db.refresh(module)
    return module


def _case(db, project_id: int, *, module_id=None, module_name="", case_type="api"):
    case = TestCase(
        project_id=project_id,
        title=f"case-{module_name or module_id}",
        module=module_name,
        requirement_module_id=module_id,
        case_type=case_type,
    )
    db.add(case)
    db.commit()
    db.refresh(case)
    return case


class TestBuildEdgesFromExistingData:
    def test_changed_edges_come_from_module_change_type(self, db_session):
        bundle = _bundle(db_session)
        _module(db_session, bundle, "体育", change_type="new")
        _module(db_session, bundle, "资讯", change_type="modified")
        _module(db_session, bundle, "未变模块", change_type="")
        result = impact_graph_service.build_edges(db_session, project_id=1, bundle_id=bundle.id)
        changed = impact_graph_service.list_edges(db_session, project_id=1, kind="changed")
        assert result["version"] == "16.1.0"
        assert {e.target_ref for e in changed} == {"module:体育", "module:资讯"}
        assert all(e.source_ref == f"release_bundle:{bundle.id}" for e in changed)

    def test_covers_edges_prefer_requirement_module_id_then_fall_back_to_name(self, db_session):
        bundle = _bundle(db_session)
        sports = _module(db_session, bundle, "体育")
        _case(db_session, 1, module_id=sports.id)
        _case(db_session, 1, module_name="体育")   # 只有名称的旧数据
        _case(db_session, 1, module_name="无关模块")  # 不匹配 → 不建边
        impact_graph_service.build_edges(db_session, project_id=1, bundle_id=bundle.id)
        covers = impact_graph_service.list_edges(db_session, project_id=1, kind="covers")
        assert all(e.target_ref == "module:体育" for e in covers)
        assert len(covers) == 2

    def test_depends_edges_come_from_module_hierarchy(self, db_session):
        bundle = _bundle(db_session)
        parent = _module(db_session, bundle, "赛事")
        child = _module(db_session, bundle, "直播", parent_id=parent.id)
        impact_graph_service.build_edges(db_session, project_id=1, bundle_id=bundle.id)
        depends = impact_graph_service.list_edges(db_session, project_id=1, kind="depends")
        assert [(e.source_ref, e.target_ref) for e in depends] == [("module:直播", "module:赛事")]
        assert child.id != parent.id

    def test_page_nodes_do_not_count_as_modules(self, db_session):
        bundle = _bundle(db_session)
        _module(db_session, bundle, "首页", node_type="page", change_type="new")
        impact_graph_service.build_edges(db_session, project_id=1, bundle_id=bundle.id)
        assert impact_graph_service.list_edges(db_session, project_id=1, kind="changed") == []


class TestIdempotence:
    def test_rebuild_does_not_duplicate(self, db_session):
        bundle = _bundle(db_session)
        sports = _module(db_session, bundle, "体育", change_type="new")
        _case(db_session, 1, module_id=sports.id)
        first = impact_graph_service.build_edges(db_session, project_id=1, bundle_id=bundle.id)
        second = impact_graph_service.build_edges(db_session, project_id=1, bundle_id=bundle.id)
        assert first["created"] == 2 and first["updated"] == 0
        assert second["created"] == 0 and second["updated"] == 2
        assert len(impact_graph_service.list_edges(db_session, project_id=1)) == 2

    def test_dry_run_writes_nothing(self, db_session):
        bundle = _bundle(db_session)
        _module(db_session, bundle, "体育", change_type="new")
        preview = impact_graph_service.build_edges(
            db_session, project_id=1, bundle_id=bundle.id, dry_run=True
        )
        assert preview["dry_run"] is True and preview["planned"] == 1
        assert impact_graph_service.list_edges(db_session, project_id=1) == []

    def test_cross_project_bundle_is_rejected(self, db_session):
        bundle = _bundle(db_session, project_id=2)
        with pytest.raises(APIException):
            impact_graph_service.build_edges(db_session, project_id=1, bundle_id=bundle.id)


class TestModuleCoverage:
    def test_coverage_rate_counts_modules_with_covering_cases(self, db_session):
        bundle = _bundle(db_session)
        for index in range(9):
            module = _module(db_session, bundle, f"模块{index}")
            _case(db_session, 1, module_id=module.id)
        _module(db_session, bundle, "未覆盖模块")  # 第 10 个模块，无用例
        impact_graph_service.build_edges(db_session, project_id=1, bundle_id=bundle.id)
        coverage = impact_graph_service.module_coverage(db_session, project_id=1, bundle_id=bundle.id)
        assert coverage["total_modules"] == 10
        assert coverage["covered_modules"] == 9
        # B3-2 的 DoD 阈值：≥90%
        assert coverage["coverage_rate"] == pytest.approx(0.9)
        assert coverage["coverage_rate"] >= 0.9
        assert coverage["uncovered_modules"] == ["未覆盖模块"]

    def test_empty_bundle_reports_zero_without_dividing_by_zero(self, db_session):
        bundle = _bundle(db_session)
        coverage = impact_graph_service.module_coverage(db_session, project_id=1, bundle_id=bundle.id)
        assert coverage == {
            "total_modules": 0,
            "covered_modules": 0,
            "uncovered_modules": [],
            "coverage_rate": 0.0,
        }
