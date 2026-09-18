"""Batch 260 / B3-1 — ImpactEdge 模型 + 迁移 + 幂等 upsert。

DoD（backlog B3-1）：迁移单头、可离线校验。
设计约束（Design §1.1）：与 `InteractionEdge`（交互拓扑）**语义不同、不合并**——
前者回答"用户怎么走"，后者回答"改了什么要重测什么"。本文件同时把这条分工固化成断言，
避免后续维护者把两张边表混用。
"""
from __future__ import annotations

import pytest
from sqlalchemy.exc import IntegrityError

from app.core.exceptions import APIException
from app.models.interaction_edge import InteractionEdge
from app.models.impact_edge import EDGE_KINDS, ImpactEdge
from app.services import impact_graph_service


class TestEdgeKinds:
    def test_kinds_are_changed_covers_depends(self):
        assert EDGE_KINDS == frozenset({"changed", "covers", "depends"})

    @pytest.mark.parametrize("kind", ["covers", "changed", "depends"])
    def test_valid_kinds_are_accepted(self, db_session, kind):
        edge, created = impact_graph_service.upsert_edge(
            db_session,
            project_id=1,
            source_ref="module:体育",
            target_ref="case:101",
            kind=kind,
        )
        assert created is True
        assert edge.kind == kind

    def test_unknown_kind_is_rejected(self, db_session):
        with pytest.raises(APIException):
            impact_graph_service.upsert_edge(
                db_session,
                project_id=1,
                source_ref="module:体育",
                target_ref="case:101",
                kind="teleports",
            )

    def test_empty_refs_are_rejected(self, db_session):
        with pytest.raises(APIException):
            impact_graph_service.upsert_edge(
                db_session, project_id=1, source_ref="", target_ref="case:1", kind="covers"
            )


class TestIdempotentUpsert:
    def test_second_upsert_updates_instead_of_duplicating(self, db_session):
        first, created_first = impact_graph_service.upsert_edge(
            db_session,
            project_id=1,
            source_ref="module:体育",
            target_ref="case:101",
            kind="covers",
            version="16.1.0",
            confidence=0.5,
        )
        second, created_second = impact_graph_service.upsert_edge(
            db_session,
            project_id=1,
            source_ref="module:体育",
            target_ref="case:101",
            kind="covers",
            version="16.1.0",
            confidence=1.0,
        )
        assert created_first is True and created_second is False
        assert first.id == second.id
        assert second.confidence == 1.0
        assert db_session.query(ImpactEdge).count() == 1

    def test_same_pair_with_different_kind_or_version_is_a_new_edge(self, db_session):
        for kind, version in (("covers", "16.1.0"), ("depends", "16.1.0"), ("covers", "16.2.0")):
            impact_graph_service.upsert_edge(
                db_session,
                project_id=1,
                source_ref="module:体育",
                target_ref="case:101",
                kind=kind,
                version=version,
            )
        assert db_session.query(ImpactEdge).count() == 3

    def test_db_unique_constraint_backs_the_upsert(self, db_session):
        """即便绕过服务直接插 ORM，数据库也必须挡住重复（唯一约束是最后一道防线）。"""
        impact_graph_service.upsert_edge(
            db_session, project_id=1, source_ref="a", target_ref="b", kind="covers", version="v"
        )
        db_session.add(
            ImpactEdge(project_id=1, source_ref="a", target_ref="b", kind="covers", version="v")
        )
        with pytest.raises(IntegrityError):
            db_session.commit()
        db_session.rollback()


class TestProjectIsolationAndQueries:
    def test_project_isolation(self, db_session):
        impact_graph_service.upsert_edge(
            db_session, project_id=1, source_ref="module:体育", target_ref="case:1", kind="covers"
        )
        impact_graph_service.upsert_edge(
            db_session, project_id=2, source_ref="module:体育", target_ref="case:2", kind="covers"
        )
        assert len(impact_graph_service.list_edges(db_session, project_id=1)) == 1
        assert len(impact_graph_service.list_edges(db_session, project_id=2)) == 1
        assert impact_graph_service.list_edges(db_session, project_id=3) == []

    def test_query_by_source_target_and_kind(self, db_session):
        impact_graph_service.upsert_edge(
            db_session, project_id=1, source_ref="module:体育", target_ref="case:1", kind="covers"
        )
        impact_graph_service.upsert_edge(
            db_session, project_id=1, source_ref="module:体育", target_ref="case:2", kind="depends"
        )
        assert len(impact_graph_service.list_edges(db_session, project_id=1, source_ref="module:体育")) == 2
        assert len(impact_graph_service.list_edges(db_session, project_id=1, kind="covers")) == 1
        assert len(impact_graph_service.list_edges(db_session, project_id=1, target_ref="case:2")) == 1


class TestDistinctFromInteractionEdge:
    """两张边表语义不同：字段与用途都不重叠，禁止互相冒充。"""

    def test_tables_and_columns_differ(self):
        assert ImpactEdge.__tablename__ != InteractionEdge.__tablename__
        impact_columns = {c.name for c in ImpactEdge.__table__.columns}
        interaction_columns = {c.name for c in InteractionEdge.__table__.columns}
        # ImpactEdge 是"变更/覆盖/依赖"图：带 kind/version/confidence；InteractionEdge 是交互拓扑。
        assert {"kind", "version", "confidence"} <= impact_columns
        assert "kind" not in interaction_columns
        assert {"from_module", "entry", "to"} <= interaction_columns

    def test_model_documents_the_division_of_labour(self):
        doc = (ImpactEdge.__doc__ or "").lower()
        assert "interactionedge" in doc.replace(" ", ""), "模型 docstring 必须写明与 InteractionEdge 的分工"
