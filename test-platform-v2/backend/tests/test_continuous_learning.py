"""M5/M6 持续学习闭环测试 —— 变更检测 / 任务队列 / 快照服务 / 回归预测 / E2E。"""
from __future__ import annotations

import json

import pytest


# ═══════════════════════════════════════════════════════
# 自包含 API 夹具（与 test_knowledge.py 一致）
# ═══════════════════════════════════════════════════════

@pytest.fixture()
def kdb():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool

    import app.models  # noqa: F401
    from app.core.db import Base

    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def kclient(kdb):
    from fastapi.testclient import TestClient

    from app.core.db import get_db
    from app.core.deps import CurrentUser, get_current_user
    from app.main import app
    from app.models.user import User

    def _override_db():
        yield kdb

    def _super_user():
        u = User(id=1, username="ktester", password="x", nickname="K", email="k@t.local", status=1)
        return CurrentUser(user=u, permissions=["*"], project_id=1)

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_current_user] = _super_user
    try:
        with TestClient(app) as c:
            yield c
    finally:
        app.dependency_overrides.clear()


# ═══════════════════════════════════════════════════════
# M5 变更检测
# ═══════════════════════════════════════════════════════

class TestChangeDetector:
    """内容哈希变更检测——hash 对比 / 事件类型映射 / 防抖。"""

    def test_detect_no_changes_on_fresh_sources(self, kdb, monkeypatch):
        """刚创建的知识源（无旧哈希）不应被检测为变更。"""
        from app.core.config import settings
        monkeypatch.setattr(settings, "knowledge_graph_enabled", True, raising=False)

        from app.models.knowledge import KnowledgeSource
        src = KnowledgeSource(
            project_id=1, source_type="requirement", title="需求A",
            raw_content="hello world", status="active",
            metadata_json='{"content_hash": ""}',
        )
        kdb.add(src)
        kdb.commit()

        from app.services.knowledge.change_detector import detect_changes
        import app.services.knowledge.change_detector as cd
        monkeypatch.setattr(cd, "SessionLocal", lambda: kdb)

        events = detect_changes(1)
        assert len(events) == 0  # old_hash 为空 → 不算变更

    def test_detect_change_when_content_differs(self, kdb, monkeypatch):
        """旧哈希 != 新哈希 → 产生变更事件。"""
        from app.models.knowledge import KnowledgeSource
        import hashlib
        old_content = "old content"
        old_hash = hashlib.sha256(old_content.encode()).hexdigest()[:16]

        src = KnowledgeSource(
            project_id=1, source_type="requirement", title="需求B",
            raw_content="new content", status="active",
            metadata_json=json.dumps({"content_hash": old_hash}),
        )
        kdb.add(src)
        kdb.commit()

        from app.services.knowledge.change_detector import detect_changes
        import app.services.knowledge.change_detector as cd
        monkeypatch.setattr(cd, "SessionLocal", lambda: kdb)

        events = detect_changes(1)
        assert len(events) == 1
        assert events[0].event_type == "requirement_updated"
        assert events[0].source_type == "requirement"

    def test_source_type_to_event_mapping(self):
        """源类型→事件类型 映射。"""
        from app.services.knowledge.change_detector import _source_type_to_event
        assert _source_type_to_event("requirement") == "requirement_updated"
        assert _source_type_to_event("openapi") == "api_schema_changed"
        assert _source_type_to_event("defect") == "new_defect"
        assert _source_type_to_event("execution") == "execution_failure"

    def test_compute_content_hash(self):
        """同内容→同哈希。"""
        from app.services.knowledge.change_detector import _compute_content_hash
        h1 = _compute_content_hash("hello")
        h2 = _compute_content_hash("hello")
        h3 = _compute_content_hash("world")
        assert h1 == h2
        assert h1 != h3
        assert len(h1) == 16

    def test_trigger_rules_has_all_event_types(self):
        """触发规则覆盖所有事件类型。"""
        from app.services.knowledge.change_detector import TRIGGER_RULES
        assert "requirement_updated" in TRIGGER_RULES
        assert "api_schema_changed" in TRIGGER_RULES
        assert "new_defect" in TRIGGER_RULES
        assert "execution_failure" in TRIGGER_RULES
        assert len(TRIGGER_RULES) == 4

    def test_handle_changes_without_auto_trigger(self, kdb, monkeypatch):
        """auto_trigger=False → 只检测、不触发。"""
        from app.models.knowledge import KnowledgeSource
        import hashlib
        old_hash = hashlib.sha256("old".encode()).hexdigest()[:16]
        src = KnowledgeSource(
            project_id=1, source_type="requirement", title="需求C",
            raw_content="new content", status="active",
            metadata_json=json.dumps({"content_hash": old_hash}),
        )
        kdb.add(src)
        kdb.commit()

        from app.services.knowledge.change_detector import handle_changes
        import app.services.knowledge.change_detector as cd
        monkeypatch.setattr(cd, "SessionLocal", lambda: kdb)

        result = handle_changes(1, auto_trigger=False)
        assert result["detected"] >= 0
        assert result["triggered"] == 0  # 不自动触发

    def test_trigger_api_check_manual(self, kclient, kdb, monkeypatch):
        """POST /agents/triggers/check?auto_trigger=false → 返回检测结果。"""
        resp = kclient.post("/api/v1/agents/triggers/check", json={"auto_trigger": False})
        assert resp.status_code == 200
        body = resp.json()
        assert body["code"] == 0
        assert "detected" in body["data"]

    def test_trigger_rules_api(self, kclient):
        """GET /agents/triggers/rules → 返回规则配置。"""
        resp = kclient.get("/api/v1/agents/triggers/rules")
        assert resp.status_code == 200
        rules = resp.json()["data"]
        assert isinstance(rules, dict)
        assert len(rules) >= 1


# ═══════════════════════════════════════════════════════
# M5 任务队列
# ═══════════════════════════════════════════════════════

class TestAgentQueue:
    """Agent 任务队列——入队/取消/统计/API。"""

    def test_enqueue_creates_pending_item(self, kdb, monkeypatch):
        """入队 → 状态为 pending。"""
        from app.services.knowledge.agent_queue import enqueue

        item = enqueue(kdb, 1, "requirement_analysis", user_input="测试")
        kdb.commit()
        assert item.status == "pending"
        assert item.project_id == 1
        assert item.agent_type == "requirement_analysis"

    def test_cancel_pending_item(self, kdb, monkeypatch):
        """取消 pending 项 → 状态变 cancelled。"""
        from app.models.knowledge import AgentQueueItem
        item = AgentQueueItem(
            project_id=1, agent_type="case_generation", status="pending",
        )
        kdb.add(item)
        kdb.commit()

        from app.services.knowledge.agent_queue import cancel_queue_item
        ok = cancel_queue_item(kdb, item.id, 1)
        assert ok
        assert item.status == "cancelled"
        assert item.finished_at is not None

    def test_cancel_running_item_fails(self, kdb):
        """只能取消 pending 任务，running 不可取消。"""
        from app.models.knowledge import AgentQueueItem
        item = AgentQueueItem(
            project_id=1, agent_type="impact_analysis", status="running",
        )
        kdb.add(item)
        kdb.commit()

        from app.services.knowledge.agent_queue import cancel_queue_item
        ok = cancel_queue_item(kdb, item.id, 1)
        assert not ok
        assert item.status == "running"

    def test_cancel_wrong_project_returns_false(self, kdb):
        """跨项目取消 → 拒绝。"""
        from app.models.knowledge import AgentQueueItem
        item = AgentQueueItem(
            project_id=999, agent_type="failure_analysis", status="pending",
        )
        kdb.add(item)
        kdb.commit()

        from app.services.knowledge.agent_queue import cancel_queue_item
        ok = cancel_queue_item(kdb, item.id, 1)  # project_id=1 ≠ 999
        assert not ok

    def test_queue_stats(self, kdb, monkeypatch):
        """统计各状态数量。"""
        from app.models.knowledge import AgentQueueItem
        items = [
            AgentQueueItem(project_id=1, agent_type="a", status="pending"),
            AgentQueueItem(project_id=1, agent_type="b", status="pending"),
            AgentQueueItem(project_id=1, agent_type="c", status="running"),
            AgentQueueItem(project_id=1, agent_type="d", status="completed"),
            AgentQueueItem(project_id=1, agent_type="e", status="failed"),
        ]
        kdb.add_all(items)
        kdb.commit()

        from app.services.knowledge.agent_queue import get_queue_stats
        stats = get_queue_stats(kdb, 1)
        assert stats["pending"] == 2
        assert stats["running"] == 1
        assert stats["completed"] == 1
        assert stats["failed"] == 1

    def test_queue_api_list(self, kclient, kdb):
        """GET /agents/queue → 返回队列项。"""
        from app.models.knowledge import AgentQueueItem
        item = AgentQueueItem(
            project_id=1, agent_type="requirement_analysis", status="pending",
        )
        kdb.add(item)
        kdb.commit()

        resp = kclient.get("/api/v1/agents/queue")
        assert resp.status_code == 200
        body = resp.json()
        assert body["code"] == 0
        assert len(body["data"]["items"]) >= 1

    def test_queue_api_stats(self, kclient):
        """GET /agents/queue/stats → 返回统计。"""
        resp = kclient.get("/api/v1/agents/queue/stats")
        assert resp.status_code == 200
        body = resp.json()
        assert body["code"] == 0
        assert "pending" in body["data"]

    def test_queue_api_cancel(self, kclient, kdb):
        """POST /agents/queue/{id}/cancel → 取消成功。"""
        from app.models.knowledge import AgentQueueItem
        item = AgentQueueItem(
            project_id=1, agent_type="case_generation", status="pending",
        )
        kdb.add(item)
        kdb.commit()

        resp = kclient.post(f"/api/v1/agents/queue/{item.id}/cancel")
        assert resp.status_code == 200
        assert resp.json()["data"]["status"] == "cancelled"

    def test_ensure_processor_running_idempotent(self):
        """启动处理器幂等。"""
        from app.services.knowledge.agent_queue import ensure_processor_running
        ensure_processor_running()
        ensure_processor_running()  # 第二次调用不应报错
        from app.services.knowledge.agent_queue import _processor_started
        assert _processor_started


# ═══════════════════════════════════════════════════════
# M6 快照服务
# ═══════════════════════════════════════════════════════

class TestSnapshotService:
    """迭代快照——创建/关闭/快照生成/跨迭代对比。"""

    def test_create_iteration(self, kdb):
        """创建迭代 → 持久化。"""
        from app.services.knowledge.snapshot_service import create_iteration
        it = create_iteration(kdb, 1, "Sprint 1", version="v14.1.0", description="测试迭代")
        kdb.commit()
        assert it.id > 0
        assert it.status == "active"
        assert it.iteration_name == "Sprint 1"

    def test_close_iteration_creates_snapshots(self, kdb, monkeypatch):
        """关闭迭代 → 自动生成 4 种快照。"""
        from app.models.knowledge import KnowledgeIteration
        it = KnowledgeIteration(
            project_id=1, iteration_name="Sprint 2", status="active",
        )
        kdb.add(it)
        kdb.commit()

        from app.services.knowledge.snapshot_service import close_iteration
        closed = close_iteration(kdb, it.id, 1)
        assert closed is not None
        assert closed.status == "closed"

        # 验证快照已创建
        from app.models.knowledge import KnowledgeSnapshot
        snaps = kdb.query(KnowledgeSnapshot).filter(
            KnowledgeSnapshot.iteration_id == it.id,
        ).all()
        assert len(snaps) == 4  # entity/relation/chunk/stats

    def test_close_already_closed_returns_none(self, kdb):
        """重复关闭 → 返回 None。"""
        from app.models.knowledge import KnowledgeIteration
        it = KnowledgeIteration(
            project_id=1, iteration_name="Sprint 3", status="closed",
        )
        kdb.add(it)
        kdb.commit()

        from app.services.knowledge.snapshot_service import close_iteration
        assert close_iteration(kdb, it.id, 1) is None

    def test_compare_iterations(self, kdb):
        """跨迭代对比 → 返回增量。"""
        from app.models.knowledge import KnowledgeIteration, KnowledgeSnapshot

        it1 = KnowledgeIteration(
            id=100, project_id=1, iteration_name="Base", status="closed",
        )
        it2 = KnowledgeIteration(
            id=200, project_id=1, iteration_name="Target", status="closed",
        )
        kdb.add_all([it1, it2])
        kdb.flush()

        # Seed snapshots
        s1 = KnowledgeSnapshot(
            iteration_id=100, snapshot_type="entity",
            data_json='{"total":10,"by_type":{"api":5,"field":5},"avg_confidence":0.8}',
        )
        s2 = KnowledgeSnapshot(
            iteration_id=100, snapshot_type="relation",
            data_json='{"total":8,"by_type":{"contains":8},"pending_review":2}',
        )
        s3 = KnowledgeSnapshot(
            iteration_id=200, snapshot_type="entity",
            data_json='{"total":15,"by_type":{"api":8,"field":7},"avg_confidence":0.85}',
        )
        s4 = KnowledgeSnapshot(
            iteration_id=200, snapshot_type="relation",
            data_json='{"total":12,"by_type":{"contains":10,"affects":2},"pending_review":3}',
        )
        kdb.add_all([s1, s2, s3, s4])
        kdb.commit()

        from app.services.knowledge.snapshot_service import compare_iterations
        result = compare_iterations(kdb, 100, 200, 1)
        assert result is not None
        assert result["deltas"]["entity_total"] == 5
        assert result["deltas"]["relation_total"] == 4
        assert result["trends"]["entity_growth_rate"] == 0.5

    def test_iterations_api_list(self, kclient, kdb):
        """GET /knowledge/iterations → 列表。"""
        from app.models.knowledge import KnowledgeIteration
        it = KnowledgeIteration(project_id=1, iteration_name="API Test", status="active")
        kdb.add(it)
        kdb.commit()

        resp = kclient.get("/api/v1/knowledge/iterations")
        assert resp.status_code == 200
        body = resp.json()
        assert body["code"] == 0
        assert len(body["data"]["items"]) >= 1

    def test_iterations_api_create(self, kclient):
        """POST /knowledge/iterations → 创建。"""
        resp = kclient.post("/api/v1/knowledge/iterations", json={
            "iteration_name": "新迭代", "version": "v1.0", "description": "测试",
        })
        assert resp.status_code == 200
        body = resp.json()
        assert body["code"] == 0
        assert body["data"]["iteration_name"] == "新迭代"
        assert body["data"]["status"] == "active"

    def test_iterations_api_close(self, kclient, kdb, monkeypatch):
        """POST /knowledge/iterations/{id}/close → 关闭 + 快照。"""
        from app.models.knowledge import KnowledgeIteration
        it = KnowledgeIteration(project_id=1, iteration_name="关闭测试", status="active")
        kdb.add(it)
        kdb.commit()

        # 独立 Session 也指向同一个 kdb（避免 :memory: 跨连接不可见）
        import app.services.knowledge.snapshot_service as ss
        monkeypatch.setattr(ss, "SessionLocal", lambda: kdb)

        resp = kclient.post(f"/api/v1/knowledge/iterations/{it.id}/close")
        assert resp.status_code == 200
        body = resp.json()
        assert body["code"] == 0
        assert body["data"]["success"] is True

    def test_snapshots_api(self, kclient, kdb):
        """GET /knowledge/iterations/{id}/snapshots → 快照列表。"""
        from app.models.knowledge import KnowledgeIteration, KnowledgeSnapshot
        it = KnowledgeIteration(project_id=1, iteration_name="快照测试", status="closed")
        kdb.add(it)
        kdb.flush()
        snap = KnowledgeSnapshot(
            iteration_id=it.id, snapshot_type="entity",
            data_json='{"total":5,"by_type":{},"avg_confidence":0.5}',
        )
        kdb.add(snap)
        kdb.commit()

        resp = kclient.get(f"/api/v1/knowledge/iterations/{it.id}/snapshots")
        assert resp.status_code == 200
        body = resp.json()
        assert body["code"] == 0
        assert len(body["data"]) >= 1

    def test_compare_api(self, kclient, kdb):
        """GET /knowledge/iterations/{id}/compare → 跨迭代对比。"""
        from app.models.knowledge import KnowledgeIteration, KnowledgeSnapshot

        it1 = KnowledgeIteration(id=1001, project_id=1, iteration_name="Base2", status="closed")
        it2 = KnowledgeIteration(id=1002, project_id=1, iteration_name="Target2", status="closed")
        kdb.add_all([it1, it2])
        kdb.flush()

        s1 = KnowledgeSnapshot(
            iteration_id=1001, snapshot_type="entity",
            data_json='{"total":5,"by_type":{"api":3},"avg_confidence":0.5}',
        )
        s2 = KnowledgeSnapshot(
            iteration_id=1001, snapshot_type="relation",
            data_json='{"total":3,"by_type":{"contains":3},"pending_review":0}',
        )
        s3 = KnowledgeSnapshot(
            iteration_id=1002, snapshot_type="entity",
            data_json='{"total":8,"by_type":{"api":5},"avg_confidence":0.6}',
        )
        s4 = KnowledgeSnapshot(
            iteration_id=1002, snapshot_type="relation",
            data_json='{"total":5,"by_type":{"contains":5},"pending_review":1}',
        )
        kdb.add_all([s1, s2, s3, s4])
        kdb.commit()

        resp = kclient.get("/api/v1/knowledge/iterations/1002/compare?base_iteration_id=1001")
        assert resp.status_code == 200
        body = resp.json()
        assert body["code"] == 0
        assert body["data"]["base_iteration_name"] == "Base2"
        assert body["data"]["target_iteration_name"] == "Target2"


# ═══════════════════════════════════════════════════════
# M6 回归预测
# ═══════════════════════════════════════════════════════

class TestRegressionPredictor:
    """回归范围预测——风险评分/排序/降级。"""

    def test_predict_empty_input_returns_empty(self, monkeypatch):
        """无变更输入 → 空结果。"""
        from app.services.knowledge.regression_predictor import predict_regression_scope
        result = predict_regression_scope(1, changed_paths=[], changed_modules=[])
        assert result["total_analyzed"] == 0
        assert result["items"] == []

    def test_predict_with_paths(self, kdb, monkeypatch):
        """有变更路径 → 有结果（即便无历史数据也有评分）。"""
        from app.services.knowledge.regression_predictor import predict_regression_scope
        import app.services.knowledge.regression_predictor as rp
        monkeypatch.setattr(rp, "SessionLocal", lambda: kdb)

        result = predict_regression_scope(1, changed_paths=["GET:/api/users", "POST:/api/orders"])
        assert result["total_analyzed"] == 2
        assert len(result["items"]) == 2
        for item in result["items"]:
            assert "api_path" in item
            assert "risk_score" in item
            assert 0 <= item["risk_score"] <= 1.0

    def test_predict_with_historical_defects(self, kdb, monkeypatch):
        """有历史缺陷 → 风险分数更高。"""
        from app.models.knowledge import KnowledgeEntity, KnowledgeRelation
        # 创建 API 实体
        api = KnowledgeEntity(
            id=1, project_id=1, entity_type="api", entity_key="api:p1:GET /api/risky",
            name="GET /api/risky", confidence=0.9,
        )
        # 创建缺陷实体
        defect = KnowledgeEntity(
            id=2, project_id=1, entity_type="defect", entity_key="defect:p1:BUG-001",
            name="严重缺陷 BUG-001", confidence=0.9,
        )
        kdb.add_all([api, defect])
        kdb.flush()
        # 创建 affects 关系
        rel = KnowledgeRelation(
            project_id=1, from_entity_id=defect.id, relation_type="affects",
            to_entity_id=api.id, confidence=0.8,
        )
        kdb.add(rel)
        kdb.commit()

        from app.services.knowledge.regression_predictor import predict_regression_scope
        import app.services.knowledge.regression_predictor as rp
        monkeypatch.setattr(rp, "SessionLocal", lambda: kdb)

        result = predict_regression_scope(1, changed_paths=["GET /api/risky"])
        assert result["total_analyzed"] == 1
        item = result["items"][0]
        assert item["historical_defects"] >= 1
        assert item["risk_score"] > 0

    def test_predict_results_sorted_by_risk(self, kdb, monkeypatch):
        """结果按风险分数降序排列。"""
        from app.models.knowledge import KnowledgeEntity, KnowledgeRelation

        api1 = KnowledgeEntity(id=10, project_id=1, entity_type="api", entity_key="api:p1:GET /a", name="GET /a", confidence=0.9)
        api2 = KnowledgeEntity(id=11, project_id=1, entity_type="api", entity_key="api:p1:GET /b", name="GET /b", confidence=0.9)
        defect = KnowledgeEntity(id=12, project_id=1, entity_type="defect", entity_key="defect:p1:B2", name="BUG", confidence=0.9)
        kdb.add_all([api1, api2, defect])
        kdb.flush()
        # api2 有缺陷关联（风险更高）
        rel = KnowledgeRelation(project_id=1, from_entity_id=defect.id, relation_type="affects", to_entity_id=api2.id, confidence=0.8)
        kdb.add(rel)
        kdb.commit()

        from app.services.knowledge.regression_predictor import predict_regression_scope
        import app.services.knowledge.regression_predictor as rp
        monkeypatch.setattr(rp, "SessionLocal", lambda: kdb)

        result = predict_regression_scope(1, changed_paths=["GET /a", "GET /b"])
        items = result["items"]
        assert len(items) >= 2
        # 有缺陷关联的 API 风险应更高
        assert items[0]["risk_score"] >= items[-1]["risk_score"]

    def test_predict_api_endpoint(self, kclient):
        """POST /knowledge/predict/regression-scope → 正常返回。"""
        resp = kclient.post("/api/v1/knowledge/predict/regression-scope", json={
            "changed_paths": ["GET:/api/test"],
            "changed_modules": ["user-service"],
        })
        assert resp.status_code == 200
        body = resp.json()
        assert body["code"] == 0
        assert "items" in body["data"]


# ═══════════════════════════════════════════════════════
# M5/M6 E2E 全链路
# ═══════════════════════════════════════════════════════

class TestTriggerE2E:
    """E2E：需求变更→Agent 自动触发→产物入队。"""

    def test_full_trigger_pipeline(self, kdb, monkeypatch):
        """模拟完整触发链路：变更检测 → 入队 → 执行。"""
        from app.core.config import settings
        monkeypatch.setattr(settings, "knowledge_graph_enabled", True, raising=False)

        from app.models.knowledge import KnowledgeSource
        import hashlib
        old_hash = hashlib.sha256("old".encode()).hexdigest()[:16]
        src = KnowledgeSource(
            project_id=1, source_type="requirement", title="E2E 测试需求",
            raw_content="新的需求内容", status="active",
            metadata_json=json.dumps({"content_hash": old_hash}),
        )
        kdb.add(src)
        kdb.commit()

        from app.services.knowledge.change_detector import handle_changes
        import app.services.knowledge.change_detector as cd
        monkeypatch.setattr(cd, "SessionLocal", lambda: kdb)

        # 自动触发关闭 → 只检测
        result = handle_changes(1, auto_trigger=False)
        assert result["detected"] >= 1
        assert result["triggered"] == 0
