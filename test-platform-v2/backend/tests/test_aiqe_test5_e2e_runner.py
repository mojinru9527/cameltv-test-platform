"""V16-017 产品级 E2E 运行器的离线配置/报告契约测试（不访问网络）。"""
from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "scripts" / "qa" / "aiqe_test5_e2e.py"


def _load():
    spec = importlib.util.spec_from_file_location("aiqe_test5_e2e", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


MODULE = _load()


def test_missing_config_returns_blocked_without_browser(monkeypatch, capsys):
    for name in (
        "AIQE_TEST5_FRONTEND_URL",
        "AIQE_TEST5_PHONE",
        "AIQE_TEST5_PASSWORD",
        "AIQE_TEST5_ADMIN_URL",
        "AIQE_TEST5_ADMIN_USER",
        "AIQE_TEST5_ADMIN_SMS",
        "AIQE_TEST5_DB_DSN",
    ):
        monkeypatch.delenv(name, raising=False)
    assert set(MODULE.missing_config()) == {
        "AIQE_TEST5_FRONTEND_URL",
        "AIQE_TEST5_PHONE",
        "AIQE_TEST5_PASSWORD",
    }
    assert MODULE.main(["--config-only"]) == 2
    assert '"ready": false' in capsys.readouterr().out


def test_complete_config_ready(monkeypatch, capsys):
    monkeypatch.setenv("AIQE_TEST5_FRONTEND_URL", "https://example.test/")
    monkeypatch.setenv("AIQE_TEST5_PHONE", "+8613800000000")
    monkeypatch.setenv("AIQE_TEST5_PASSWORD", "not-a-real-secret")
    assert MODULE.missing_config() == []
    assert MODULE.main(["--config-only"]) == 0
    assert '"ready": true' in capsys.readouterr().out


def test_partial_admin_config_is_blocked(monkeypatch):
    monkeypatch.setenv("AIQE_TEST5_FRONTEND_URL", "https://example.test/")
    monkeypatch.setenv("AIQE_TEST5_PHONE", "+8613800000000")
    monkeypatch.setenv("AIQE_TEST5_PASSWORD", "x")
    monkeypatch.setenv("AIQE_TEST5_ADMIN_URL", "https://admin.test")
    missing = MODULE.missing_config()
    assert "AIQE_TEST5_ADMIN_USER" in missing
    assert "AIQE_TEST5_ADMIN_SMS" in missing


def test_phone_masking_and_status_precedence():
    assert MODULE._mask_phone("+86 18476944071") == "***4071"
    assert MODULE._mask_phone("") == "***"
    steps = MODULE.Steps()
    steps.add("a", "PASS")
    assert steps.status == "PASS"
    steps.add("b", "BLOCKED", "lock")
    assert steps.status == "BLOCKED"
    steps.add("c", "FAIL", "boom")
    assert steps.status == "FAIL"


def test_report_contains_no_plain_password(tmp_path):
    steps = MODULE.Steps()
    steps.add("front_login", "PASS", "userId=1", phone="***4071")
    report = MODULE._report(steps, tmp_path, 0.0)
    text = repr(report)
    assert "password" not in text.lower()
    assert report["status"] == "PASS"
    assert report["environment"] == "camel-test5"
