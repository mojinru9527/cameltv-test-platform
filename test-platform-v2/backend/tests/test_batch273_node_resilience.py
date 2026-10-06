"""Batch 273 / C269-3 — 节点必须扛住平台 4xx/5xx（不再一次性退进程）。

根因（证据 `work-logs/evidence/batch-269/node-exit-root-cause-20260920.md`）：
`cli.call()` 对 `status>=400 或 code!=0` 抛 `SystemExit(2)`，而轮询循环 `_loop` 只捕 `TransportDown`
→ 平台一次 500/403 就让节点进程无声退出、任务滞留 `pending`。

本文件把该机制写成回归（stub 平台 HTTP，不需要真平台）：
  1. 500 / 403（业务码 != 0）/ 连接重置 / 读超时 → **不退出**，退避后继续轮询；
  2. 连续失败达上限 → 退出非零，且 stderr 与日志文件都留下可读原因；
  3. 已认领任务遇到平台错误 → 只重试**同一任务**，不丢回 `pending`；平台 404（已回收）才放手；
  4. 节点 stderr 必须落盘（Batch 269 的事故无法逐帧回看，就是因为没落盘）；
  5. `--once` 语义保留：单轮失败返回非零，任务结论为失败仍返回 0。

节点代码在 `scripts/node/`（控制面之外），沿用 `test_batch258_node_cli.py` 的 sys.path 引入方式。
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import httpx
import pytest

NODE_ROOT = Path(__file__).resolve().parents[3] / "scripts" / "node"
if str(NODE_ROOT) not in sys.path:
    sys.path.insert(0, str(NODE_ROOT))

from cameltv_node import cli  # noqa: E402


class _FakeResponse:
    def __init__(self, status_code: int, payload=None, text: str = ""):
        self.status_code = status_code
        self._payload = payload
        self.text = text or json.dumps(payload or {}, ensure_ascii=False)

    def json(self):
        if self._payload is None:
            raise ValueError("not json")
        return self._payload


def _ok(data):
    return _FakeResponse(200, {"code": 0, "msg": "ok", "data": data})


class _StubTransport:
    """替换 `cli.httpx`：保留 `TransportError` 语义，按预置序列返回。

    最后一项**粘住**（重复使用），这样"跑飞"的循环不会因为列表耗尽而报错，
    只会让调用次数断言失败；`BaseException` 项直接抛出（用来在指定位置终止循环）。
    """

    TransportError = httpx.TransportError

    def __init__(self, responses: list):
        assert responses, "至少要预置一个响应"
        self._responses = list(responses)
        self.calls: list[dict] = []

    def request(self, method, url, **kwargs):
        self.calls.append({"method": method, "url": url, **kwargs})
        item = self._responses.pop(0) if len(self._responses) > 1 else self._responses[0]
        if isinstance(item, BaseException):
            raise item
        return item

    def calls_to(self, suffix: str) -> list[dict]:
        return [call for call in self.calls if call["url"].endswith(suffix)]


@pytest.fixture
def node_runner(monkeypatch, tmp_path):
    """在隔离的配置/日志/工作目录里跑 `cameltv-node up`，平台侧全走 stub。"""

    def _run(responses: list, *extra_args: str):
        transport = _StubTransport(responses)
        sleeps: list[float] = []
        monkeypatch.setattr(cli, "httpx", transport)
        # 不读写真实的 ~/.cameltv-node.json
        monkeypatch.setattr(cli, "CONFIG_PATH", tmp_path / "cameltv-node.json")
        # 退避不真睡（只记录），否则测试要等几分钟
        monkeypatch.setattr(cli, "_sleep", sleeps.append)
        monkeypatch.setenv("CAMELTV_BASE_URL", "https://platform.test")
        monkeypatch.setenv("CAMELTV_NODE_ID", "node-stub")
        monkeypatch.setenv("CAMELTV_NODE_TOKEN", "token-stub")
        monkeypatch.setenv("CAMELTV_PROJECT_ID", "7")
        monkeypatch.delenv("CAMELTV_JWT", raising=False)
        monkeypatch.delenv("CAMELTV_NODE_LOG_FILE", raising=False)
        monkeypatch.delenv("CAMELTV_NODE_MAX_FAILURES", raising=False)
        argv = [
            "up",
            "--node-id",
            "node-stub",
            "--work-dir",
            str(tmp_path / "work"),
            "--poll-seconds",
            "0.1",
            "--heartbeat-seconds",
            "300",
            "--max-consecutive-failures",
            "3",
            "--log-file",
            str(tmp_path / "node.log"),
            *extra_args,
        ]
        code = cli.main(argv)
        return code, transport, sleeps

    return _run


def _args(*extra: str):
    return cli.build_parser().parse_args(["up", "--node-id", "n", *extra])


class TestCallRaisesRecoverableInsteadOfSystemExit:
    """根因回归：`call()` 不再抛 `SystemExit`（Batch 269 机制复现 A/B/C）。"""

    _CFG = {"base_url": "https://platform.test", "node_id": "n", "token": "t", "project_id": "7"}

    def _call(self, monkeypatch, response):
        monkeypatch.setattr(cli, "httpx", _StubTransport([response]))
        return cli.call(self._CFG, "POST", "/execution-jobs/claim", body={"node_id": "n"})

    def test_http_500_is_platform_error_not_process_exit(self, monkeypatch):
        # 旧实现抛 SystemExit(2)：它不属于 Exception，pytest 会直接判失败——这正是本用例的价值。
        with pytest.raises(cli.PlatformError) as info:
            self._call(monkeypatch, _FakeResponse(500, {"code": 500, "msg": "boom"}))
        assert info.value.status_code == 500
        assert "HTTP 500" in str(info.value)

    def test_http_403_with_business_code_is_platform_error(self, monkeypatch):
        with pytest.raises(cli.PlatformError) as info:
            self._call(monkeypatch, _FakeResponse(403, {"code": 40301, "msg": "无权限"}))
        assert info.value.status_code == 403
        assert info.value.auth_problem is True

    def test_http_200_with_nonzero_business_code_is_platform_error(self, monkeypatch):
        with pytest.raises(cli.PlatformError) as info:
            self._call(monkeypatch, _FakeResponse(200, {"code": 40001, "msg": "业务失败"}))
        assert info.value.code == 40001

    def test_connection_reset_is_transport_down(self, monkeypatch):
        with pytest.raises(cli.TransportDown):
            self._call(monkeypatch, httpx.ConnectError("connection reset by peer"))

    def test_read_timeout_is_transport_down(self, monkeypatch):
        with pytest.raises(cli.TransportDown):
            self._call(monkeypatch, httpx.ReadTimeout("read timeout"))


class TestJobScopeCallMapping:
    def test_404_becomes_job_gone(self, monkeypatch):
        monkeypatch.setattr(cli, "httpx", _StubTransport([_FakeResponse(404, {"code": 404, "msg": "任务不存在"})]))
        with pytest.raises(cli.JobGone) as info:
            cli._fetch_payload({"base_url": "https://platform.test", "node_id": "n", "token": "t"}, 46)
        assert "46" in str(info.value)

    def test_500_stays_platform_error(self, monkeypatch):
        monkeypatch.setattr(cli, "httpx", _StubTransport([_FakeResponse(500, {"code": 500})]))
        with pytest.raises(cli.PlatformError) as info:
            cli._fetch_payload({"base_url": "https://platform.test", "node_id": "n", "token": "t"}, 46)
        assert not isinstance(info.value, cli.JobGone)


class TestLoopSurvivesPlatformFailures:
    """三场景回归：500 / 403 / 连接重置与超时都不能让节点退进程。"""

    def test_claim_500_keeps_polling(self, node_runner, capsys):
        code, transport, _sleeps = node_runner(
            [
                _FakeResponse(500, {"code": 500, "msg": "server restarting"}),
                _ok(None),  # 平台恢复后继续正常轮询（当前无任务）
                KeyboardInterrupt(),  # 终止测试里的无限循环
            ]
        )
        assert code == 130, "500 之后节点应仍在轮询，由 Ctrl+C 正常收尾而不是自杀"
        assert len(transport.calls) == 3, "500 一次就退出的话这里只会看到 1 次调用"
        assert "HTTP 500" in capsys.readouterr().err

    def test_claim_403_with_business_code_keeps_polling(self, node_runner, capsys):
        code, transport, _sleeps = node_runner(
            [
                _FakeResponse(403, {"code": 40301, "msg": "无权限"}),
                _ok(None),
                KeyboardInterrupt(),
            ]
        )
        assert code == 130
        assert len(transport.calls) == 3
        err = capsys.readouterr().err
        assert "HTTP 403" in err
        assert "凭据" in err, "403/401 要在日志里给出排查方向（节点令牌/项目上下文/权限）"

    def test_connection_reset_and_timeout_keep_polling(self, node_runner, capsys):
        code, transport, _sleeps = node_runner(
            [
                httpx.ConnectError("connection reset by peer"),
                httpx.ReadTimeout("read timeout"),
                _ok(None),
                KeyboardInterrupt(),
            ]
        )
        assert code == 130
        assert len(transport.calls) == 4
        err = capsys.readouterr().err
        assert "ConnectError" in err and "ReadTimeout" in err

    def test_consecutive_failures_exit_nonzero_with_reason(self, node_runner, capsys, tmp_path):
        code, transport, sleeps = node_runner(
            [_FakeResponse(500, {"code": 500, "msg": "maintenance"})]
        )
        assert code == cli.EXIT_PLATFORM_ERROR == 4
        assert len(transport.calls) == 3, "达到 --max-consecutive-failures 3 就该退出，不空转"
        assert len(sleeps) == 2, "前两次失败要先退避再重试"
        err = capsys.readouterr().err
        assert "连续失败 3 次" in err
        assert "退出码 4" in err
        logged = (tmp_path / "node.log").read_text(encoding="utf-8")
        assert "连续失败 3 次" in logged and "HTTP 500" in logged, "退出原因必须同时落盘"


class TestClaimedJobIsNeverDropped:
    def test_payload_failures_retry_the_same_job_until_reported(
        self, node_runner, capsys, monkeypatch, tmp_path
    ):
        job = {"id": 46, "kind": "api", "attempt": 1, "env_ref": "test5"}
        monkeypatch.setattr(
            cli,
            "_execute",
            lambda cfg, job, payload, work_dir: {
                "total": 5,
                "passed": 5,
                "failed": 0,
                "all_pass": True,
                "cases": [],
                "error": "",
            },
        )
        code, transport, _sleeps = node_runner(
            [
                _ok(job),
                _FakeResponse(500, {"code": 500, "msg": "payload boom"}),
                _FakeResponse(503, {"code": 503, "msg": "still restarting"}),
                _ok({"job_id": 46, "payload": {"cases": []}}),
                _ok({"job_id": 46, "status": "completed"}),
                _ok(None),
                KeyboardInterrupt(),
            ]
        )
        assert code == 130, "持有任务时遇到平台错误不能退进程"
        assert [call["url"].rsplit("/api/v1", 1)[-1] for call in transport.calls[:5]] == [
            "/execution-jobs/claim",
            "/execution-jobs/46/payload",
            "/execution-jobs/46/payload",
            "/execution-jobs/46/payload",
            "/execution-jobs/46/report",
        ], "失败期间必须重试同一任务，不得回头认领别的任务（任务不会被丢回 pending）"
        reports = transport.calls_to("/report")
        assert len(reports) == 1 and reports[0]["json"]["status"] == "completed"
        err = capsys.readouterr().err
        assert "job 46 执行重试 1/3" in err and "job 46 执行重试 2/3" in err
        assert "不会滞留 pending" in err
        assert (tmp_path / "work" / "job-46-attempt-1" / "results.json").exists()

    def test_report_failure_resends_result_without_rerunning_cases(
        self, node_runner, monkeypatch, tmp_path
    ):
        job = {"id": 47, "kind": "api", "attempt": 1}
        runs: list[int] = []

        def _fake_execute(cfg, job, payload, work_dir):
            runs.append(job["id"])
            return {"total": 1, "passed": 1, "failed": 0, "all_pass": True, "cases": [], "error": ""}

        monkeypatch.setattr(cli, "_execute", _fake_execute)
        code, transport, _sleeps = node_runner(
            [
                _ok(job),
                _ok({"job_id": 47, "payload": {"cases": []}}),
                _FakeResponse(500, {"code": 500, "msg": "report boom"}),
                _ok({"job_id": 47, "status": "completed"}),
                _ok(None),
                KeyboardInterrupt(),
            ]
        )
        assert code == 130
        assert runs == [47], "上报阶段失败只重发结论，不重跑用例"
        assert len(transport.calls_to("/report")) == 2

    def test_404_means_platform_reclaimed_it_and_node_keeps_polling(
        self, node_runner, capsys
    ):
        job = {"id": 48, "kind": "api", "attempt": 2}
        code, transport, _sleeps = node_runner(
            [
                _ok(job),
                _FakeResponse(404, {"code": 404, "msg": "任务不存在或不属于当前节点"}),
                _ok(None),
                KeyboardInterrupt(),
            ]
        )
        assert code == 130
        err = capsys.readouterr().err
        assert "已不在本节点名下" in err and "pending" in err
        assert len(transport.calls_to("/payload")) == 1, "平台已回收就不要再对同一任务刷载荷"


class TestOnceSemanticsPreserved:
    """`--once` 仍是"只跑一轮（CI/自检用）"：单轮平台失败返回非零，任务结论失败仍返回 0。"""

    def test_once_with_no_job_returns_zero(self, node_runner):
        code, transport, _sleeps = node_runner([_ok(None)], "--once")
        assert code == 0
        assert len(transport.calls) == 1

    def test_once_platform_failure_returns_nonzero_without_looping(self, node_runner, capsys):
        code, transport, sleeps = node_runner(
            [_FakeResponse(500, {"code": 500, "msg": "down"})], "--once"
        )
        assert code == cli.EXIT_PLATFORM_ERROR
        assert len(transport.calls) == 1, "--once 不做无限重试"
        assert sleeps == [], "--once 单轮失败即退出，不退避空转"
        assert "HTTP 500" in capsys.readouterr().err

    def test_once_failed_job_still_exits_zero(self, node_runner, monkeypatch):
        job = {"id": 49, "kind": "api", "attempt": 1}
        monkeypatch.setattr(
            cli,
            "_execute",
            lambda cfg, job, payload, work_dir: {
                "total": 1,
                "passed": 0,
                "failed": 1,
                "all_pass": False,
                "cases": [],
                "error": "断言失败",
            },
        )
        code, transport, _sleeps = node_runner(
            [
                _ok(job),
                _ok({"job_id": 49, "payload": {"cases": []}}),
                _ok({"job_id": 49, "status": "failed"}),
            ],
            "--once",
        )
        assert code == 0, "任务失败是任务结论，不是节点崩溃（drill 依赖这条语义）"
        reports = transport.calls_to("/report")
        assert reports[0]["json"]["status"] == "failed"


class TestStderrIsPersisted:
    """C269-3 的硬要求：节点 stderr 落盘，下一次事故可逐帧回看。"""

    def test_log_file_records_platform_failures_with_timestamp(self, node_runner, capsys, tmp_path):
        code, _transport, _sleeps = node_runner([_FakeResponse(500, {"code": 500, "msg": "down"})])
        assert code == cli.EXIT_PLATFORM_ERROR
        err = capsys.readouterr().err
        log_text = (tmp_path / "node.log").read_text(encoding="utf-8")
        assert "HTTP 500" in err and "HTTP 500" in log_text
        assert "连续失败 3 次" in log_text
        assert re.search(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}", log_text), "落盘行要带时间戳"

    def test_log_file_is_appended_across_restarts(self, node_runner, tmp_path):
        node_runner([_ok(None)], "--once")
        node_runner([_ok(None)], "--once")
        lines = [line for line in (tmp_path / "node.log").read_text(encoding="utf-8").splitlines() if line]
        assert len(lines) >= 2, "重启后应追加而不是覆盖上一段日志"

    def test_default_log_path_is_documented_and_in_home(self):
        assert cli.DEFAULT_LOG_PATH.name == "cameltv-node.log"
        assert ".cameltv-node" in str(cli.DEFAULT_LOG_PATH)
        assert cli.LOG_BACKUP_COUNT >= 1 and cli.LOG_MAX_BYTES > 0, "必须轮转，不能无限增长"


class TestBackoffAndBudget:
    def test_default_budget_is_documented(self, monkeypatch):
        monkeypatch.delenv("CAMELTV_NODE_MAX_FAILURES", raising=False)
        assert _args().max_consecutive_failures == cli.DEFAULT_MAX_CONSECUTIVE_FAILURES == 10

    def test_budget_flag_and_env_are_honored(self, monkeypatch):
        assert cli._failure_budget(_args("--max-consecutive-failures", "4")) == 4
        assert cli._failure_budget(_args("--max-consecutive-failures", "0")) == 0, "0 = 不限"
        monkeypatch.setenv("CAMELTV_NODE_MAX_FAILURES", "7")
        assert _args().max_consecutive_failures == 7

    def test_backoff_grows_exponentially_and_is_capped(self):
        args = _args("--backoff-base-seconds", "5", "--max-backoff-seconds", "20")
        for consecutive in range(1, 12):
            ceiling = min(20.0, 5.0 * 2 ** (consecutive - 1))
            delay = cli._backoff_seconds(consecutive, args)
            assert ceiling / 2 <= delay <= ceiling
        assert cli._backoff_seconds(50, args) <= 20.0

    def test_backoff_has_jitter(self):
        args = _args("--backoff-base-seconds", "5")
        assert len({cli._backoff_seconds(6, args) for _ in range(20)}) > 1


class TestLoggingSetupIsFailSafe:
    def test_unwritable_log_path_degrades_to_stderr(self, tmp_path, capsys):
        blocked = tmp_path / "as-a-file"
        blocked.write_text("not a directory", encoding="utf-8")
        # 目录位置被同名文件占住 → 不能因为日志落盘失败就让节点起不来
        assert cli.setup_logging(blocked / "sub" / "node.log") is None
        cli.log_error("仍然要能看到这条")
        assert "仍然要能看到这条" in capsys.readouterr().err
        assert cli.log_file_path() is None
