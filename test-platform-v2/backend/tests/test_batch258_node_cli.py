"""Batch 258 / B1-5 — cameltv-node 本地执行节点（CLI + 执行器 + 证据 + 平台端点）。

节点代码在 `scripts/node/`（控制面之外），按仓库既有惯例通过 sys.path 引入后单测。
浏览器不参与测试：Web 执行器的步骤解释器与 Playwright 解耦（`page_factory` 可注入）。
"""
from __future__ import annotations

import contextlib
import json
import sys
from pathlib import Path

import pytest

NODE_ROOT = Path(__file__).resolve().parents[3] / "scripts" / "node"
if str(NODE_ROOT) not in sys.path:
    sys.path.insert(0, str(NODE_ROOT))

from cameltv_node import evidence as node_evidence  # noqa: E402
from cameltv_node import executor as node_executor  # noqa: E402

from app.core.config import settings  # noqa: E402
from app.services import execution_evidence_store as store  # noqa: E402


class _FakeResponse:
    def __init__(self, status_code: int, payload=None, text: str = ""):
        self.status_code = status_code
        self._payload = payload
        self.text = text or json.dumps(payload or {}, ensure_ascii=False)
        self.headers = {"content-type": "application/json"}
        self.elapsed = None

    def json(self):
        if self._payload is None:
            raise ValueError("not json")
        return self._payload


class _FakeClient:
    def __init__(self, responses: list):
        self._responses = list(responses)
        self.requests: list[dict] = []

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def request(self, method, url, **kwargs):
        self.requests.append({"method": method, "url": url, **kwargs})
        if not self._responses:
            raise AssertionError("没有预置响应")
        return self._responses.pop(0)


class _FakePage:
    """最小页面替身：只实现执行器用到的动作。"""

    def __init__(self):
        self.actions: list[tuple] = []
        self.visible: dict[str, bool] = {}
        self.texts: dict[str, str] = {}
        self.screenshot_bytes = b"\x89PNG-fake"

    def on(self, event, handler):
        self.actions.append(("on", event))

    def goto(self, url, wait_until=None):
        self.actions.append(("goto", url, wait_until))

    def click(self, selector):
        self.actions.append(("click", selector))

    def fill(self, selector, value):
        self.actions.append(("fill", selector, value))

    def press(self, selector, key):
        self.actions.append(("press", selector, key))

    def wait_for_selector(self, selector, state=None, timeout=None):
        self.actions.append(("wait_visible", selector))

    def wait_for_timeout(self, ms):
        self.actions.append(("wait", ms))

    def is_visible(self, selector):
        return self.visible.get(selector, False)

    def inner_text(self, selector):
        return self.texts.get(selector, "")

    def screenshot(self, path=None, full_page=True):
        Path(path).write_bytes(self.screenshot_bytes)


class TestAssertionEvaluation:
    def test_status_and_json_path_and_not_empty(self):
        results = node_executor.evaluate_assertions(
            status_code=200,
            text='{"status": 200}',
            payload={"status": 200, "data": {"list": [1]}},
            assertions=[
                {"type": "status", "expected": 200},
                {"type": "json_path", "path": "$.status", "expected": 200},
                {"type": "json_path", "path": "$.data.list[0]", "expected": 1},
                {"type": "not_empty", "path": "$.data.list"},
            ],
        )
        assert all(item["passed"] for item in results)

    def test_failed_assertions_are_reported_not_swallowed(self):
        results = node_executor.evaluate_assertions(
            status_code=500,
            text="boom",
            payload=None,
            assertions=[{"type": "status", "expected": 200}],
        )
        assert results[0]["passed"] is False
        assert results[0]["actual"] == 500

    def test_unknown_assertion_type_fails_loudly(self):
        results = node_executor.evaluate_assertions(
            status_code=200, text="", payload={}, assertions=[{"type": "regex"}]
        )
        assert results[0]["passed"] is False
        assert "未识别" in str(results[0]["actual"])

    def test_missing_path_yields_none(self):
        assert node_executor._dig({"a": {"b": 1}}, "$.a.missing") is None
        assert node_executor._dig({"a": [1, 2]}, "$.a[5]") is None


class TestRunApiCases:
    def _runner(self, tmp_path, responses):
        client = _FakeClient(responses)
        results = node_executor.run_api_cases(
            [
                {
                    "id": "case-1",
                    "name": "首页",
                    "request": {"method": "GET", "url": "/api/home"},
                    "assertions": [{"type": "status", "expected": 200}],
                }
            ],
            evidence_dir=tmp_path,
            client_factory=lambda timeout: client,
            base_url="https://example.com",
        )
        return client, results

    def test_passing_case_writes_request_and_response_evidence(self, tmp_path):
        client, results = self._runner(tmp_path, [_FakeResponse(200, {"status": 200})])
        assert results["all_pass"] is True
        assert client.requests[0]["url"] == "https://example.com/api/home"
        assert (tmp_path / "case-1.request.json").exists()
        body = json.loads((tmp_path / "case-1.response.json").read_text(encoding="utf-8"))
        assert body["status_code"] == 200

    def test_failing_case_is_not_faked_as_pass(self, tmp_path):
        _client, results = self._runner(tmp_path, [_FakeResponse(500, None, "boom")])
        assert results["all_pass"] is False
        assert results["failed"] == 1
        assert results["cases"][0]["assertions"][0]["passed"] is False

    def test_transport_exception_is_recorded(self, tmp_path):
        class _Boom:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def request(self, *args, **kwargs):
                raise TimeoutError("connect timeout")

        results = node_executor.run_api_cases(
            [{"id": "c", "request": {"method": "GET", "url": "https://x/y"}, "assertions": [{"type": "status", "expected": 200}]}],
            evidence_dir=tmp_path,
            client_factory=lambda timeout: _Boom(),
        )
        assert results["all_pass"] is False
        assert "timeout" in results["cases"][0]["error"].lower()


class TestRunWebCases:
    def test_steps_execute_and_screenshot_is_saved(self, tmp_path):
        page = _FakePage()
        page.visible[".banner"] = True
        page.texts["h1"] = "赛事首页"
        results = node_executor.run_web_cases(
            [
                {
                    "id": "ui-1",
                    "steps": [
                        {"action": "goto", "url": "/"},
                        {"action": "wait_visible", "selector": ".banner"},
                        {"action": "expect_visible", "selector": ".banner"},
                        {"action": "expect_text", "selector": "h1", "expected": "赛事"},
                    ],
                }
            ],
            evidence_dir=tmp_path,
            page_factory=lambda: contextlib.nullcontext(page),
        )
        assert results["all_pass"] is True
        assert (tmp_path / "ui-1.png").read_bytes() == page.screenshot_bytes
        assert (tmp_path / "ui-1.console.json").exists()

    def test_failing_step_stops_case_and_keeps_screenshot(self, tmp_path):
        page = _FakePage()  # .banner 默认不可见
        results = node_executor.run_web_cases(
            [
                {
                    "id": "ui-2",
                    "steps": [
                        {"action": "goto", "url": "/"},
                        {"action": "expect_visible", "selector": ".banner"},
                        {"action": "click", "selector": "should-not-run"},
                    ],
                }
            ],
            evidence_dir=tmp_path,
            page_factory=lambda: contextlib.nullcontext(page),
        )
        assert results["all_pass"] is False
        assert ("click", "should-not-run") not in page.actions
        assert (tmp_path / "ui-2.png").exists()

    def test_unknown_action_fails_loudly(self, tmp_path):
        page = _FakePage()
        results = node_executor.run_web_cases(
            [{"id": "ui-3", "steps": [{"action": "teleport"}]}],
            evidence_dir=tmp_path,
            page_factory=lambda: contextlib.nullcontext(page),
        )
        assert results["all_pass"] is False
        assert "未知动作" in results["cases"][0]["error"]

    def test_missing_playwright_is_reported_not_faked(self, tmp_path, monkeypatch):
        def _unavailable():
            raise node_executor.ExecutorUnavailable("未安装 Playwright")

        with pytest.raises(node_executor.ExecutorUnavailable):
            node_executor.run_web_cases(
                [{"id": "ui-4", "steps": [{"action": "goto", "url": "/"}]}],
                evidence_dir=tmp_path,
                page_factory=_unavailable,
            )


class TestLocalEvidencePackaging:
    def test_collect_manifest_and_verification(self, tmp_path):
        (tmp_path / "a.txt").write_bytes(b"hello")
        (tmp_path / "b.png").write_bytes(b"png")
        (tmp_path / "manifest.json").write_text("{}", encoding="utf-8")
        files = node_evidence.collect_files(tmp_path)
        names = sorted(name for name, _ in files)
        assert names == ["a.txt", "b.png"]  # manifest 自身不入清单
        local = node_evidence.local_manifest(files)
        assert local["file_count"] == 2

        tampered = {
            "files": [
                {"name": "a.txt", "size": 5, "sha256": "0" * 64},
                {"name": "b.png", "size": 3, "sha256": local["files"][1]["sha256"]},
            ]
        }
        problems = node_evidence.verify_against(tampered, local)
        assert any("sha256 不一致: a.txt" == item for item in problems)

    def test_empty_directory_is_rejected(self, tmp_path):
        with pytest.raises(ValueError):
            node_evidence.collect_files(tmp_path)


class TestEvidenceStore:
    @pytest.fixture(autouse=True)
    def _isolated_root(self, tmp_path, monkeypatch):
        monkeypatch.setattr(settings, "execution_evidence_storage_dir", str(tmp_path / "ev"))

    def test_save_and_reload_manifest(self):
        manifest = store.save_bundle(job_id=3, attempt=2, files=[("a.txt", b"abc")])
        assert manifest["file_count"] == 1
        assert manifest["files"][0]["sha256"]
        assert store.load_manifest(3, 2)["job_id"] == 3
        assert [bundle["attempt"] for bundle in store.list_bundles(3)] == [2]

    @pytest.mark.parametrize(
        "name",
        ["../evil.txt", "..\\evil.txt", "sub/dir.txt", "", ".", "..", "a b.txt"],
    )
    def test_unsafe_file_names_are_rejected(self, name):
        with pytest.raises(store.EvidenceStoreError):
            store.safe_file_name(name)

    def test_manifest_name_is_reserved(self):
        with pytest.raises(store.EvidenceStoreError):
            store.save_bundle(job_id=1, attempt=1, files=[("manifest.json", b"{}")])

    def test_oversized_file_is_rejected(self):
        big = b"x" * (store.MAX_EVIDENCE_FILE_BYTES + 1)
        with pytest.raises(store.EvidenceStoreError):
            store.save_bundle(job_id=1, attempt=1, files=[("big.bin", big)])

    def test_resolve_file_blocks_traversal(self):
        store.save_bundle(job_id=1, attempt=1, files=[("ok.txt", b"x")])
        assert store.resolve_file(1, 1, "ok.txt").read_bytes() == b"x"
        with pytest.raises(store.EvidenceStoreError):
            store.resolve_file(1, 1, "../../../etc/passwd")


class TestNodeProtocolOverHttp:
    """端到端：登记载荷 → 认领 → 拉载荷 → 上传证据 → 下载证据。"""

    def _register_node(self, client, auth_headers, node_id: str) -> str:
        resp = client.post(
            "/api/v1/ai/agents/register",
            json={"agent_id": node_id, "capabilities": ["api"]},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        return resp.json()["data"]["token"]

    def test_payload_and_evidence_roundtrip(
        self, db_session, client, auth_headers, tmp_path, monkeypatch
    ):
        monkeypatch.setattr(settings, "execution_evidence_storage_dir", str(tmp_path / "ev"))
        token = self._register_node(client, auth_headers, "node-e2e")

        created = client.post(
            "/api/v1/execution-jobs",
            json={
                "kind": "api",
                "case_refs": ["case-A"],
                "env_ref": "test5",
                "payload": {"base_url": "https://example.com", "cases": [{"id": "case-A"}]},
            },
            headers=auth_headers,
        )
        assert created.status_code == 200
        job_id = created.json()["data"]["id"]
        assert created.json()["data"]["has_payload"] is True

        node_headers = {"X-AI-Agent-Token": token}
        assert (
            client.post(
                "/api/v1/execution-jobs/claim", json={"node_id": "node-e2e"}, headers=node_headers
            ).status_code
            == 200
        )

        payload = client.get(
            f"/api/v1/execution-jobs/{job_id}/payload",
            params={"node_id": "node-e2e"},
            headers=node_headers,
        )
        assert payload.status_code == 200
        assert payload.json()["data"]["payload"]["cases"] == [{"id": "case-A"}]
        assert payload.json()["data"]["attempt"] == 1

        uploaded = client.post(
            f"/api/v1/execution-jobs/{job_id}/evidence",
            params={"node_id": "node-e2e"},
            headers=node_headers,
            files=[("files", ("case-A.response.json", b'{"status":200}', "application/json"))],
        )
        assert uploaded.status_code == 200
        manifest = uploaded.json()["data"]
        assert manifest["file_count"] == 1
        assert manifest["files"][0]["name"] == "case-A.response.json"

        listed = client.get(f"/api/v1/execution-jobs/{job_id}/evidence", headers=auth_headers)
        assert listed.status_code == 200
        assert len(listed.json()["data"]["bundles"]) == 1

        downloaded = client.get(
            f"/api/v1/execution-jobs/{job_id}/evidence/case-A.response.json",
            params={"attempt": 1},
            headers=auth_headers,
        )
        assert downloaded.status_code == 200
        assert downloaded.content == b'{"status":200}'

    def test_payload_requires_node_token(self, client, auth_headers):
        created = client.post(
            "/api/v1/execution-jobs",
            json={"kind": "api", "case_refs": [], "payload": {"cases": []}},
            headers=auth_headers,
        )
        job_id = created.json()["data"]["id"]
        resp = client.get(
            f"/api/v1/execution-jobs/{job_id}/payload", params={"node_id": "someone"}
        )
        assert resp.status_code == 401

    def test_evidence_upload_rejects_traversal_name(
        self, db_session, client, auth_headers, tmp_path, monkeypatch
    ):
        monkeypatch.setattr(settings, "execution_evidence_storage_dir", str(tmp_path / "ev"))
        token = self._register_node(client, auth_headers, "node-trav")
        created = client.post(
            "/api/v1/execution-jobs",
            json={"kind": "api", "case_refs": []},
            headers=auth_headers,
        )
        job_id = created.json()["data"]["id"]
        resp = client.post(
            f"/api/v1/execution-jobs/{job_id}/evidence",
            params={"node_id": "node-trav"},
            headers={"X-AI-Agent-Token": token},
            files=[("files", ("../escape.txt", b"x", "text/plain"))],
        )
        assert resp.status_code == 400

    def test_evidence_download_blocks_traversal(self, client, auth_headers):
        created = client.post(
            "/api/v1/execution-jobs",
            json={"kind": "api", "case_refs": []},
            headers=auth_headers,
        )
        job_id = created.json()["data"]["id"]
        resp = client.get(
            f"/api/v1/execution-jobs/{job_id}/evidence/..%2F..%2Fetc%2Fpasswd",
            headers=auth_headers,
        )
        assert resp.status_code in (403, 404)
