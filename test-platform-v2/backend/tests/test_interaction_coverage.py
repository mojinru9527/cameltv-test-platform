"""Batch 119 — C114-1 交互拓扑覆盖缺口提示。"""
from __future__ import annotations

from app.services.interaction_coverage_service import (
    _edge_covered,
    compute_interaction_gaps,
)


def _cases():
    return [
        {"title": "首页-入口可达：Match Replays 区块跳转回放列表", "module": "首页",
         "steps": "1.打开生产首页 https://www.camel1.tv/\n2.定位 Match Replays 区块\n3.点击首条回放链接", "expected_result": "跳转 /match-replay"},
        {"title": "赛事详情-从首页赛事卡跳转并渲染标题/比分", "module": "赛事详情",
         "steps": "1.打开首页\n2.点击赛事卡片", "expected_result": "进入赛事详情页"},
    ]


def _edges():
    return [
        {"from_module": "首页", "entry": "Match ReplaysShow more", "to": "/match-replay"},
        {"from_module": "首页", "entry": "FIFA World Cup 2026", "to": "/worldcup-2026"},
        {"from_module": "首页", "entry": "AS Monaco Getafe", "to": "/football/as-monaco-vs-getafe/n54qllhn0vwjqvy"},
    ]


def test_edge_covered_matches_to_path():
    cases = _cases()
    assert _edge_covered(_edges()[0], cases) is True      # /match-replay in case text
    assert _edge_covered(_edges()[1], cases) is False     # /worldcup-2026 无用例
    assert _edge_covered(_edges()[2], cases) is True      # /football 类型前缀 + 模块匹配


def test_compute_gaps_summary():
    cases = _cases()
    result = compute_interaction_gaps(_edges(), cases)
    assert result["total_edges"] == 3
    assert result["covered_edges"] == 2
    assert result["gap_edges"] == 1
    assert result["coverage_rate"] == round(2 / 3, 4)
    assert result["gaps"][0]["to"] == "/worldcup-2026"


def test_compute_gaps_empty():
    result = compute_interaction_gaps([], [])
    assert result["total_edges"] == 0
    assert result["coverage_rate"] == 0.0


def test_compute_gaps_prepares_each_case_text_once(monkeypatch):
    """Batch 127 — 边数增长不能重复归一化同一批用例文本。"""
    import app.services.interaction_coverage_service as service

    original = service._case_texts
    calls = 0

    def counted(case):
        nonlocal calls
        calls += 1
        return original(case)

    monkeypatch.setattr(service, "_case_texts", counted)

    result = service.compute_interaction_gaps(_edges(), _cases())

    assert result["total_edges"] == len(_edges())
    assert calls == len(_cases())


def test_endpoint_gaps_with_db_cases(client, auth_headers, db_session):
    from app.models.test_case import TestCase

    db_session.add(TestCase(
        project_id=1,
        title="首页-入口可达：Match Replays 区块跳转回放列表",
        module="首页",
        case_type="manual",
        steps="1.打开生产首页\n2.点击首条回放链接",
        expected_result="跳转 /match-replay",
        tags='["interaction:batch-113"]',
    ))
    db_session.commit()
    resp = client.post(
        "/api/v1/interaction-coverage/gaps",
        json={"edges": [
            {"from_module": "首页", "entry": "Match ReplaysShow more", "to": "/match-replay"},
            {"from_module": "首页", "entry": "FIFA World Cup 2026", "to": "/worldcup-2026"},
        ]},
        headers=auth_headers,
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert data["total_edges"] == 2
    assert data["covered_edges"] == 1
    assert data["gap_edges"] == 1
    assert data["gaps"][0]["to"] == "/worldcup-2026"


# ── C120-1 全量拓扑入库 ──

def _edges_payload():
    return [
        {"from_module": "首页", "entry": "Match ReplaysShow more", "to": "/match-replay", "evidence": "links"},
        {"from_module": "首页", "entry": "FIFA World Cup 2026", "to": "/worldcup-2026", "evidence": "links"},
        {"from_module": "首页", "entry": "All News", "to": "/q/news", "evidence": "links"},
    ]


def test_import_and_load_topology(client, auth_headers, db_session):
    resp = client.post("/api/v1/interaction-coverage/import",
                       json={"edges": _edges_payload(), "source_batch": "batch-113"}, headers=auth_headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert data["added"] == 3
    assert data["skipped"] == 0
    # re-import same → all skipped
    resp = client.post("/api/v1/interaction-coverage/import",
                       json={"edges": _edges_payload(), "source_batch": "batch-113"}, headers=auth_headers)
    assert resp.json()["data"]["added"] == 0
    assert resp.json()["data"]["skipped"] == 3
    resp = client.get("/api/v1/interaction-coverage/topology", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["data"]["total"] == 3


def test_gaps_uses_db_topology_when_body_empty(client, auth_headers, db_session):
    from app.models.test_case import TestCase

    client.post("/api/v1/interaction-coverage/import",
                json={"edges": _edges_payload(), "source_batch": "batch-113"}, headers=auth_headers)
    db_session.add(TestCase(
        project_id=1, title="首页-入口可达：Match Replays 区块跳转回放列表", module="首页",
        case_type="manual", steps="1.打开生产首页\n2.点击首条回放链接",
        expected_result="跳转 /match-replay", tags='["interaction:batch-113"]',
    ))
    db_session.commit()
    resp = client.post("/api/v1/interaction-coverage/gaps", json={"edges": []}, headers=auth_headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert data["total_edges"] == 3
    assert data["covered_edges"] == 1
    assert data["gap_edges"] == 2
