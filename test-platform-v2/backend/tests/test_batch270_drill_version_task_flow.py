"""Batch 270 — 演练驱动改走版本任务流程（修 C269-1）+ 瞬断重试与增量落盘（修 C269-2）。

背景（Batch 269 只读取证）：驱动只 `POST /execution-jobs`、**不** `POST /version-tasks`，
于是被验收的 3 个版本既没有版本记录，也不产生任何复用建议事件——`hit_rate` 读到的是
别的流程留下的旧数字。本批让每个版本都建版本任务，并按**本版本增量**取数与记录决策。
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import httpx
import pytest

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND / "scripts"))

import drill_three_versions as drill  # noqa: E402


def _resp(status: int, payload: dict, method: str = "GET", url: str = "http://x/api/v1/y") -> httpx.Response:
    return httpx.Response(status, json=payload, request=httpx.Request(method, url))


class FakeClient:
    """按 (method, url) 记录调用并返回预置响应。"""

    def __init__(self, handler):
        self.handler = handler
        self.calls: list[tuple[str, str, dict]] = []

    def request(self, method, url, **kwargs):
        self.calls.append((method, url, kwargs))
        return self.handler(method, url, kwargs)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


# ── C269-2：重试语义 ───────────────────────────────────────────────


def test_retry_recovers_from_transient_transport_error():
    attempts = {"n": 0}

    def handler(method, url, kwargs):
        attempts["n"] += 1
        if attempts["n"] < 3:
            raise httpx.ReadError("connection reset")
        return _resp(200, {"code": 0, "data": {"ok": True}}, method)

    client = FakeClient(handler)
    resp = drill._request_with_retry(client, "GET", "/x", attempts=3, backoff=0.01)
    assert resp.status_code == 200
    assert attempts["n"] == 3, "瞬时读错误必须被重试到成功"


def test_retry_does_not_mask_http_4xx():
    client = FakeClient(lambda m, u, k: _resp(400, {"code": 400, "msg": "bad"}, m))
    resp = drill._request_with_retry(client, "GET", "/x", attempts=3, backoff=0.01)
    assert resp.status_code == 400
    assert len(client.calls) == 1, "4xx 是真问题，不能靠重试掩盖"


def test_retry_retries_get_5xx_but_not_post_5xx():
    get_client = FakeClient(lambda m, u, k: _resp(503, {"code": 503}, m))
    drill._request_with_retry(get_client, "GET", "/x", attempts=3, backoff=0.01)
    assert len(get_client.calls) == 3, "幂等 GET 的 5xx 可重试"

    post_client = FakeClient(lambda m, u, k: _resp(503, {"code": 503}, m))
    drill._request_with_retry(post_client, "POST", "/x", attempts=3, backoff=0.01)
    assert len(post_client.calls) == 1, "POST 不重试，避免重复登记任务"


def test_retry_raises_after_exhausting_attempts():
    def handler(method, url, kwargs):
        raise httpx.ReadTimeout("still broken")

    with pytest.raises(httpx.TransportError):
        drill._request_with_retry(FakeClient(handler), "GET", "/x", attempts=2, backoff=0.01)


# ── C269-1：复用 ref 与决策 ─────────────────────────────────────────


def test_suggestion_refs_match_create_task_format():
    payload = {
        "code": 0,
        "data": [
            {"id": 7, "version": "16.0", "reuse": ["赛事列表", "直播入口"]},
            {"id": 8, "version": "17.0", "reuse": []},
        ],
    }
    client = FakeClient(lambda m, u, k: _resp(200, payload, m))
    refs = drill._suggestion_refs(client, {})
    assert refs == [
        ("knowledge:7:赛事列表", "赛事列表"),
        ("knowledge:7:直播入口", "直播入口"),
    ]


def test_apply_decisions_posts_only_known_titles():
    client = FakeClient(lambda m, u, k: _resp(200, {"code": 0, "data": {}}, m))
    refs = [("knowledge:7:赛事列表", "赛事列表")]
    applied = drill._apply_decisions(
        client,
        {},
        task_id=42,
        refs=refs,
        decisions={"adopted": ["赛事列表", "不存在的条目"], "rejected": [], "reason": "r"},
    )
    posted = [c for c in client.calls if c[0] == "POST"]
    assert len(posted) == 1
    assert posted[0][2]["json"] == {
        "task_id": 42,
        "suggestion_ref": "knowledge:7:赛事列表",
        "decision": "adopted",
    }
    assert applied["adopted"] == ["赛事列表"]
    assert applied["missing"] == ["adopted:不存在的条目"]


def test_decisions_for_falls_back_to_default_and_empty():
    cfg = {"_default": {"adopted": ["A"], "reason": "fallback"}}
    assert drill._decisions_for(cfg, "16.9")["adopted"] == ["A"]
    assert drill._decisions_for({}, "16.9") == {"adopted": [], "rejected": [], "reason": ""}


def test_load_decisions_missing_file_exits(tmp_path):
    with pytest.raises(SystemExit):
        drill._load_decisions(str(tmp_path / "nope.json"))
    assert drill._load_decisions("") == {}


# ── C269-1：整轮流程按"本版本增量"取数 ─────────────────────────────


class _StatsSequence:
    """模拟平台累计读数：建任务 +4 suggested；记 1 条 adopted 后 adopted +1。"""

    def __init__(self):
        self.suggested = 10
        self.adopted = 5

    def snapshot(self) -> dict:
        rate = round(self.adopted / self.suggested, 4) if self.suggested else 0.0
        return {
            "suggested": self.suggested,
            "adopted": self.adopted,
            "rejected": 0,
            "hit_rate": rate,
            "meets_50pct": (rate >= 0.5) if self.suggested else None,
            "pending": self.suggested - self.adopted,
        }


def _run_one_version(tmp_path, stats: _StatsSequence):
    counters = {"jobs": 0}

    def handler(method, url, kwargs):
        if url.endswith("/knowledge/reuse-stats"):
            return _resp(200, {"code": 0, "data": stats.snapshot()}, method)
        if url.endswith("/knowledge/reuse"):
            return _resp(200, {"code": 0, "data": [{"id": 7, "reuse": ["赛事列表"]}]}, method)
        if url.endswith("/version-tasks") and method == "POST":
            stats.suggested += 4
            return _resp(200, {"code": 0, "data": {"id": 99}}, method)
        if url.endswith("/knowledge/reuse-decisions") and method == "POST":
            stats.adopted += 1
            return _resp(200, {"code": 0, "data": {"decision": "adopted"}}, method)
        if url.endswith("/execution-jobs") and method == "POST":
            counters["jobs"] += 1
            return _resp(200, {"code": 0, "data": {"id": 500 + counters["jobs"]}}, method)
        if url.endswith("/evidence/verify"):
            return _resp(
                200,
                {"code": 0, "data": {"verdict": "verified", "completeness": {"complete": True}}},
                method,
            )
        if "/execution-jobs/" in url:
            return _resp(200, {"code": 0, "data": {"status": "completed"}}, method)
        raise AssertionError(f"unexpected call {method} {url}")

    client = FakeClient(handler)
    out = tmp_path / "drill.json"
    args = argparse.Namespace(
        versions=1,
        version_prefix="16.",
        person_hours_per_version=1.5,
        account_slot="sports-tester-01",
        target_url="http://target",
        web_target_url="http://web",
        environment_id=12,
        job_timeout=30,
        out=str(out),
        reuse_mode="version-task",
        decisions_json="",
        reuse_suggested=0,
        reuse_adopted=0,
    )
    dataset = {"api": [{"id": "1"}], "web": [{"id": "2"}]}
    original = (drill._api_client, drill._auth_headers, drill._load_executable_cases)
    drill._api_client = lambda a: client
    drill._auth_headers = lambda a: {}
    drill._load_executable_cases = lambda a, d: (
        [{"id": "case:1", "name": "api", "request": {"method": "GET", "url": "/x"}, "assertions": []}],
        [{"id": "case:2", "name": "web", "steps": [{"action": "goto", "url": "http://web"}]}],
        [],
    )
    try:
        versions = drill.run_versions(args, dataset)
    finally:
        drill._api_client, drill._auth_headers, drill._load_executable_cases = original
    return versions, json.loads(out.read_text(encoding="utf-8"))


def test_run_versions_uses_version_task_delta(tmp_path):
    versions, partial_report = _run_one_version(tmp_path, _StatsSequence())
    entry = versions[0]
    assert entry["version_task_id"] == 99, "每个版本都要建版本任务（C269-1）"
    assert entry["reuse_suggested"] == 4, "分子分母取本版本增量（建任务带来的 4 条建议）"
    assert entry["reuse_adopted"] == 0, "没记决策就是 0，不能用累计数字美化分子"
    assert entry["reuse_source"] == "platform:version-task-delta"
    assert entry["job_ids"] == [501, 502]
    assert entry["evidence_complete"] is True
    assert partial_report["partial"] is True, "跑完一版就落盘（C269-2）"
    assert partial_report["versions"][0]["version"] == "16.1"


def test_version_task_conflict_gives_actionable_error(tmp_path, monkeypatch):
    """实跑命中（Batch 270）：版本号已存在时平台返回 500 裸栈 → 驱动要给可操作提示。"""

    def handler(method, url, kwargs):
        if url.endswith("/knowledge/reuse-stats"):
            return _resp(200, {"code": 0, "data": {"suggested": 0, "adopted": 0}}, method)
        if url.endswith("/version-tasks") and method == "POST":
            return _resp(500, {"detail": "UNIQUE constraint failed"}, method)
        raise AssertionError(f"unexpected call {method} {url}")

    client = FakeClient(handler)
    args = argparse.Namespace(
        versions=1,
        version_prefix="16.",
        person_hours_per_version=1.5,
        account_slot="slot",
        target_url="http://target",
        web_target_url="http://web",
        environment_id=12,
        job_timeout=5,
        out=str(tmp_path / "o.json"),
        reuse_mode="version-task",
        decisions_json="",
        reuse_suggested=0,
        reuse_adopted=0,
    )
    monkeypatch.setattr(drill, "_api_client", lambda a: client)
    monkeypatch.setattr(drill, "_auth_headers", lambda a: {})
    monkeypatch.setattr(
        drill,
        "_load_executable_cases",
        lambda a, d: (
            [{"id": "case:1", "name": "api", "request": {}, "assertions": []}],
            [],
            [],
        ),
    )
    with pytest.raises(SystemExit) as excinfo:
        drill.run_versions(args, {"api": [], "web": []})
    assert "--version-prefix" in str(excinfo.value), "提示必须告诉用户怎么绕开版本号冲突"
