"""M3 / TA-018：Keploy Driver 单测（mock subprocess/report，跨平台）。"""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.aiqe.drivers import keploy_driver as keploy


def make_driver(**kwargs) -> keploy.KeployDriver:
    return keploy.KeployDriver("keploy", cwd=kwargs.pop("cwd", None), **kwargs)


def patch_run(monkeypatch, *, returncode=0):
    calls: list[list[str]] = []

    def fake_run(argv, **kwargs):
        calls.append(argv)
        return SimpleNamespace(returncode=returncode, stdout="out", stderr="err")

    monkeypatch.setattr(keploy.subprocess, "run", fake_run)
    return calls


def patch_reports(monkeypatch, reports: list[dict]):
    queue = list(reports)

    def fake_load(self):
        return queue.pop(0)

    monkeypatch.setattr(keploy.KeployDriver, "_load_report", fake_load)


def test_record_dependency_and_redaction(monkeypatch):
    calls = patch_run(monkeypatch)
    patch_reports(
        monkeypatch,
        [
            {
                "dependencies": [
                    {"request": {"headers": {"Authorization": "Bearer secret"}}, "response": {"code": 200}}
                ]
            }
        ],
    )
    result = make_driver().record(["python", "app.py"], test_set="smoke")
    assert len(result.dependencies) == 1
    assert result.dependencies[0]["request"]["headers"]["Authorization"] == "***"
    assert result.dependencies[0]["response"]["code"] == 200
    assert calls[0][:4] == ["keploy", "record", "--test-set", "smoke"]


def test_record_without_dependencies_rejected(monkeypatch):
    patch_run(monkeypatch)
    patch_reports(monkeypatch, [{"dependencies": []}])
    with pytest.raises(keploy.KeployDependencyMissing):
        make_driver().record(["python", "app.py"])


def test_replay_stable(monkeypatch):
    calls = patch_run(monkeypatch)
    report = {"tests": {"passed": 2, "failed": 0}, "dependencies": []}
    patch_reports(monkeypatch, [dict(report), dict(report)])
    result = make_driver().replay(times=2)
    assert result.tests == {"passed": 2, "failed": 0}
    assert len(calls) == 2
    assert calls[0][:3] == ["keploy", "replay", "--test-set"]


def test_replay_unstable_rejected(monkeypatch):
    patch_run(monkeypatch)
    patch_reports(
        monkeypatch,
        [
            {"tests": {"passed": 2, "failed": 0}},
            {"tests": {"passed": 2, "failed": 1}},
        ],
    )
    with pytest.raises(keploy.KeployReplayUnstable):
        make_driver().replay(times=2)


def test_redact_payload_nested():
    payload = {
        "headers": {"Cookie": "sid=1", "X-Trace": "t"},
        "body": {"password": "p", "nested": [{"token": "t"}]},
        "ok": True,
    }
    redacted = keploy.redact_payload(payload)
    assert redacted["headers"]["Cookie"] == "***"
    assert redacted["headers"]["X-Trace"] == "t"
    assert redacted["body"]["password"] == "***"
    assert redacted["body"]["nested"][0]["token"] == "***"


def test_audit_ebpf_fields(monkeypatch):
    monkeypatch.setattr(keploy.platform, "system", lambda: "Linux")
    monkeypatch.setattr(keploy.os, "geteuid", lambda: 0, raising=False)
    monkeypatch.setattr(keploy, "_read_capeff", lambda: 0)
    audit = keploy.audit_ebpf()
    assert audit.system == "Linux" and audit.is_root is True and audit.ready is True


def test_assert_ebpf_ready_rejects_non_linux():
    audit = keploy.EbpfAudit(
        system="Windows", euid=0, is_root=True, cap_bpf=False, cap_sys_admin=False,
        ready=False, notes="no",
    )
    with pytest.raises(keploy.KeployPermissionError):
        keploy.assert_ebpf_ready(audit)


def test_missing_report_raises(tmp_path, monkeypatch):
    patch_run(monkeypatch)
    with pytest.raises(keploy.KeployError):
        make_driver(cwd=tmp_path).record(["python", "app.py"])
