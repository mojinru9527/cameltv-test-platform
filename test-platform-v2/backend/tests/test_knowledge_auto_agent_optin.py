"""P1-9 — 知识变更 → 自动 Agent（出网 LLM）链路的三道闸门。

1. 无人值守触发必须显式 opt-in（`knowledge_auto_agent_enabled`，默认 False），
   `knowledge_graph_enabled` 不得再顺带触发 LLM；
2. 防抖从进程内 dict 换成 DB 持久化（重启不能绕过）；
3. Agent 产出物再入库不得反向触发新 Agent（自喂环断路器）。
"""
from __future__ import annotations

from datetime import datetime, timedelta

from app.core import config
from app.core.config import Settings
from app.models.knowledge import KnowledgeTriggerDebounce
from app.services.knowledge import change_detector, ingest_service


def _stub_post_ingest_hooks(monkeypatch, trigger_calls: list, graph_calls: list | None = None):
    calls = graph_calls if graph_calls is not None else []
    monkeypatch.setattr(
        ingest_service, "embed_pending_chunks_in_new_session", lambda *a, **k: None
    )
    monkeypatch.setattr(
        ingest_service,
        "extract_and_build_graph_in_new_session",
        lambda *a, **k: calls.append(1),
    )
    monkeypatch.setattr(
        ingest_service,
        "_auto_trigger_agents",
        lambda project_id, auto_trigger=False: trigger_calls.append((project_id, auto_trigger)),
    )
    return calls


# ── 1. 显式 opt-in ─────────────────────────────────────────────

def test_auto_agent_default_is_off(monkeypatch) -> None:
    monkeypatch.delenv("KNOWLEDGE_AUTO_AGENT_ENABLED", raising=False)
    assert Settings(_env_file=None).knowledge_auto_agent_enabled is False


def test_post_ingest_hooks_does_not_trigger_agent_by_default(monkeypatch) -> None:
    trigger_calls: list = []
    _stub_post_ingest_hooks(monkeypatch, trigger_calls)
    monkeypatch.setattr(config.settings, "knowledge_auto_agent_enabled", False)

    ingest_service._post_ingest_hooks(3, source_id=9)

    assert trigger_calls == []


def test_graph_enabled_alone_does_not_trigger_agent(monkeypatch) -> None:
    """回归：knowledge_graph_enabled=True 不得再连带产生一次出网 LLM 调用。"""
    trigger_calls: list = []
    graph_calls = _stub_post_ingest_hooks(monkeypatch, trigger_calls)
    monkeypatch.setattr(config.settings, "knowledge_auto_agent_enabled", False)
    monkeypatch.setattr(config.settings, "knowledge_graph_enabled", True)

    ingest_service._post_ingest_hooks(3, source_id=9)

    assert graph_calls == [1]  # 图谱照常建
    assert trigger_calls == []  # 但不触发 Agent


def test_post_ingest_hooks_triggers_when_explicitly_enabled(monkeypatch) -> None:
    trigger_calls: list = []
    _stub_post_ingest_hooks(monkeypatch, trigger_calls)
    monkeypatch.setattr(config.settings, "knowledge_auto_agent_enabled", True)

    ingest_service._post_ingest_hooks(3, source_id=9)

    assert trigger_calls == [(3, True)]


# ── 2. 持久化防抖 ──────────────────────────────────────────────

def test_persistent_debounce_blocks_within_window(db_session) -> None:
    assert change_detector._debounce_blocks(11, 22, "failure_analysis", db=db_session) is False
    # 第二次（窗口内）必须被挡住；状态在 DB 里，不依赖进程内存
    assert change_detector._debounce_blocks(11, 22, "failure_analysis", db=db_session) is True

    row = (
        db_session.query(KnowledgeTriggerDebounce)
        .filter(
            KnowledgeTriggerDebounce.project_id == 11,
            KnowledgeTriggerDebounce.source_id == 22,
            KnowledgeTriggerDebounce.agent_type == "failure_analysis",
        )
        .one()
    )
    assert row.triggered_at is not None
    # 旧的进程内防抖字典必须已被移除（否则重启仍可绕过）
    assert not hasattr(change_detector, "_last_trigger")


def test_persistent_debounce_isolated_per_key(db_session) -> None:
    assert change_detector._debounce_blocks(11, 22, "failure_analysis", db=db_session) is False
    assert change_detector._debounce_blocks(11, 23, "failure_analysis", db=db_session) is False
    assert change_detector._debounce_blocks(11, 22, "impact_analysis", db=db_session) is False
    assert change_detector._debounce_blocks(12, 22, "failure_analysis", db=db_session) is False
    assert db_session.query(KnowledgeTriggerDebounce).count() == 4


def test_persistent_debounce_expires_after_window(db_session) -> None:
    assert change_detector._debounce_blocks(11, 22, "failure_analysis", db=db_session) is False
    row = db_session.query(KnowledgeTriggerDebounce).one()
    row.triggered_at = datetime.now() - timedelta(
        seconds=change_detector._DEBOUNCE_SECONDS + 5
    )
    db_session.commit()

    assert change_detector._debounce_blocks(11, 22, "failure_analysis", db=db_session) is False
    db_session.refresh(row)
    assert row.triggered_at > datetime.now() - timedelta(seconds=30)


def test_debounce_fails_closed_when_store_unavailable(monkeypatch) -> None:
    """防抖状态读不出来时宁可漏触发，也不能重复烧钱。"""

    class _BrokenSession:
        def scalar(self, *_args, **_kwargs):
            raise RuntimeError("debounce store down")

        def add(self, *_args, **_kwargs):  # pragma: no cover - scalar 先失败
            raise RuntimeError("debounce store down")

        def commit(self):  # pragma: no cover
            raise RuntimeError("debounce store down")

        def rollback(self):  # pragma: no cover
            raise RuntimeError("rollback down too")

        def close(self):
            return None

    monkeypatch.setattr(change_detector, "SessionLocal", lambda: _BrokenSession())

    assert change_detector._debounce_blocks(1, 2, "failure_analysis") is True


# ── 3. 自喂环断路器 ────────────────────────────────────────────

def _one_failure_event():
    return change_detector.ChangeEvent(
        source_id=5,
        source_type="execution",
        event_type="execution_failure",
        title="UI 用例失败",
        project_id=1,
    )


def test_agent_run_does_not_re_feed_change_detection(monkeypatch) -> None:
    monkeypatch.setattr(change_detector, "detect_changes", lambda project_id: [_one_failure_event()])
    monkeypatch.setattr(change_detector, "_debounce_blocks", lambda *a, **k: False)
    runs: list[dict] = []
    scope_seen: list[bool] = []

    def _fake_run(**kwargs):
        runs.append(kwargs)
        # Agent 运行期间必须处于「已在自动触发链路」的作用域内，
        # 这样它产出物入库时的变更检测才会被断路器拦下。
        scope_seen.append(change_detector.in_agent_trigger_scope())

    monkeypatch.setattr(change_detector, "run_agent_in_new_session", _fake_run)

    # 顶层（例如 UI 执行失败触发的入库）可以正常触发一次
    assert change_detector.handle_changes(1, auto_trigger=True) == {
        "detected": 1,
        "triggered": 1,
    }
    assert len(runs) == 1
    assert scope_seen == [True]

    # 嵌套（= Agent 产出物再入库）不再触发，链路在此断开
    with change_detector.agent_trigger_scope():
        assert change_detector.handle_changes(1, auto_trigger=True) == {
            "detected": 1,
            "triggered": 0,
        }
    assert len(runs) == 1
    # 作用域退出后必须复位，不能污染后续调用
    assert change_detector.in_agent_trigger_scope() is False
    assert change_detector.handle_changes(1, auto_trigger=True)["triggered"] == 1
