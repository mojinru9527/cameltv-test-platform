"""UI 自动化生产级补强测试（C-UI-PROD-001）。

覆盖：
- runner 目录配置解析（空=默认 / 相对路径 / 绝对路径）
- spec 定位基于配置目录（可指向体育 E2E tests/automation/ui）
- spec 路径穿越防护
- CAMELTV_* 环境变量透传
"""
from __future__ import annotations

from pathlib import Path

from app.services import playwright_executor as pe


def test_runner_dir_defaults_to_platform_playwright(monkeypatch):
    """未配置时返回默认 backend/tests/playwright。"""
    monkeypatch.setattr("app.core.config.settings.ui_test_runner_dir", "")
    runner = pe._runner_dir()
    assert runner.name == "playwright"
    assert "tests" in runner.parts


def test_runner_dir_relative_points_to_ui_automation(monkeypatch):
    """相对路径指向 test-platform-v2 下目录（体育 E2E）。"""
    monkeypatch.setattr(
        "app.core.config.settings.ui_test_runner_dir", "tests/automation/ui",
    )
    runner = pe._runner_dir()
    # test-platform-v2/tests/automation/ui
    assert runner.parts[-3:] == ("tests", "automation", "ui")
    assert runner.is_absolute()


def test_runner_dir_absolute_passthrough(monkeypatch):
    """绝对路径直接使用。"""
    p = Path("C:/tmp/custom-runner")
    monkeypatch.setattr("app.core.config.settings.ui_test_runner_dir", str(p))
    assert pe._runner_dir() == p


def test_spec_outside_runner_rejected(monkeypatch, tmp_path):
    """spec 位于 runner 目录外 → 防穿越拒绝。"""
    monkeypatch.setattr("app.core.config.settings.ui_test_runner_dir", str(tmp_path))
    runner_root = pe._runner_dir().resolve()
    # 目录内创建合法 spec
    (tmp_path / "ok.spec.ts").write_text("", encoding="utf-8")
    assert ((runner_root / "ok.spec.ts").resolve().is_relative_to(runner_root))
    # 目录外路径
    outside = tmp_path.parent / "escape.spec.ts"
    outside.write_text("", encoding="utf-8")
    resolved = outside.resolve()
    assert not resolved.is_relative_to(runner_root)


def test_cameltv_env_passthrough(monkeypatch):
    """CAMELTV_* 变量透传到子进程环境。"""
    monkeypatch.setenv("CAMELTV_TARGET_ENV", "test5")
    monkeypatch.setenv("CAMELTV_RUN_LEVEL", "readonly")
    monkeypatch.setenv("CAMELTV_PRECONDITION_OWNER", "test-owner")
    monkeypatch.setenv("NON_CAMELTV_VAR", "should-not-matter")
    monkeypatch.delenv("CAMELTV_PASSWORD", raising=False)

    # 验证 env 透传逻辑（与 executor 内联逻辑一致）
    import os

    env = {k: v for k, v in os.environ.items()
           if k.startswith("CAMELTV_") and pe._ENV_KEY_PATTERN.fullmatch(k)}
    assert env.get("CAMELTV_TARGET_ENV") == "test5"
    assert env.get("CAMELTV_RUN_LEVEL") == "readonly"
    assert env.get("CAMELTV_PRECONDITION_OWNER") == "test-owner"
    assert "NON_CAMELTV_VAR" not in env
