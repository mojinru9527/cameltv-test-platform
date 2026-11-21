"""V16-022 验收：依赖/环境可复现与测试分层。"""
from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "scripts" / "ci" / "run_aiqe_layer.py"
BACKEND = ROOT / "test-platform-v2" / "backend"


def _module():
    spec = importlib.util.spec_from_file_location("run_aiqe_layer", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_lockfile_pins_runtime_and_test_dependencies():
    lock = (BACKEND / "requirements.lock").read_text(encoding="utf-8")
    for pinned in ("bcrypt==", "playwright==", "pytest=="):
        assert pinned in lock, pinned
    requirements = (BACKEND / "requirements.txt").read_text(encoding="utf-8")
    assert "bcrypt" in requirements
    assert "playwright==1.61.0" in requirements


def test_pytest_layers_are_declared():
    ini = (BACKEND / "pytest.ini").read_text(encoding="utf-8")
    for marker in ("unit:", "integration:", "browser:", "device:", "e2e:", "security:"):
        assert marker in ini, marker


def test_layer_listing_and_dry_run():
    listed = subprocess.run(
        [sys.executable, str(SCRIPT), "--list"],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert listed.returncode == 0, listed.stderr
    assert "unit:" in listed.stdout and "browser:" in listed.stdout and "security:" in listed.stdout

    dry = subprocess.run(
        [sys.executable, str(SCRIPT), "security", "--junit", "security.xml", "--dry-run"],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert dry.returncode == 0, dry.stderr
    assert "test_aiqe_v16_001_policy_fail_closed.py" in dry.stdout
    assert "--junitxml=security.xml" in dry.stdout
    assert "-p no:cacheprovider" in dry.stdout


def test_unknown_layer_and_empty_layer_fail():
    unknown = subprocess.run(
        [sys.executable, str(SCRIPT), "no-such-layer", "--dry-run"],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert unknown.returncode == 2
    module = _module()
    module.LAYERS["empty-layer"] = ["tests/definitely-not-exist-*.py"]
    assert module.resolve_files("empty-layer") == []
    try:
        module.command_for("empty-layer", None)
    except FileNotFoundError:
        pass
    else:  # pragma: no cover - 明确失败
        raise AssertionError("空 layer 必须失败")


def test_reproducibility_doc_exists():
    doc = ROOT / "docs" / "aiqe" / "v1.6" / "Environment-Reproducibility.md"
    text = doc.read_text(encoding="utf-8")
    assert "3.12.10" in text
    assert "requirements.lock" in text
    assert "Playwright" in text
    assert "run_aiqe_layer.py" in text
    assert "JUnit" in text
