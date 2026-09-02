"""Batch 134 — lanhu-mcp lanhu_login / _save_cached_cookie 钩子可用性测试。

后端 lanhu_provider 通过 `_load_lanhu_runtime` 取 `module.lanhu_login` /
`module._save_cached_cookie`。本测试验证 pinned 子模块提供这两个钩子：
- 能导入时直接调用：无凭据返回空串、cookie 落盘；
- 无法导入（CI 未装 lanhu-mcp 依赖）时回退源码级断言。
"""
from __future__ import annotations

from pathlib import Path

import pytest

_LANHU_MCP_SERVER = (
    Path(__file__).resolve().parents[3] / "lanhu-mcp" / "lanhu_mcp_server.py"
)
pytestmark = pytest.mark.skipif(
    not _LANHU_MCP_SERVER.exists(),
    reason="lanhu-mcp submodule not initialized (run: git submodule update --init)",
)

import asyncio
import sys
from pathlib import Path

from app.services.external import lanhu_provider


def _lanhu_dir() -> Path:
    return Path(lanhu_provider._lanhu_mcp_dir())


def _try_import():
    sys.path.insert(0, str(_lanhu_dir()))
    try:
        import lanhu_mcp_server as module  # type: ignore
        return module
    except Exception:  # noqa: BLE001 — 依赖缺失时回退源码断言
        return None
    finally:
        sys.path.remove(str(_lanhu_dir()))


class TestLanhuLoginHook:
    def test_provides_login_and_save_hooks(self):
        module = _try_import()
        if module is None:
            # 源码级断言：pinned 子模块包含两个钩子定义
            src = (_lanhu_dir() / "lanhu_mcp_server.py").read_text(encoding="utf-8")
            assert "async def lanhu_login(username: str = "", password: str = "") -> str:" in src
            assert 'def _save_cached_cookie(cookie: str) -> None:' in src
            return
        assert callable(getattr(module, "lanhu_login", None))
        assert callable(getattr(module, "_save_cached_cookie", None))
        # 无凭据时不抛异常且返回空串
        assert asyncio.run(module.lanhu_login()) == ""
        assert asyncio.run(module.lanhu_login("", "")) == ""

    def test_save_cached_cookie_writes_file(self, tmp_path, monkeypatch):
        module = _try_import()
        if module is None:
            src = (_lanhu_dir() / "lanhu_mcp_server.py").read_text(encoding="utf-8")
            assert 'DATA_DIR / "lanhu_cookie.txt"' in src
            return
        monkeypatch.setattr(module, "DATA_DIR", tmp_path)
        module._save_cached_cookie("k=v; s=2")
        assert (tmp_path / "lanhu_cookie.txt").read_text(encoding="utf-8") == "k=v; s=2"
        module._save_cached_cookie("")
        # 空串不覆盖已有内容
        assert (tmp_path / "lanhu_cookie.txt").read_text(encoding="utf-8") == "k=v; s=2"
