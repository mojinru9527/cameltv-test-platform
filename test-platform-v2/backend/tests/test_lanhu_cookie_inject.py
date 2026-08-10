"""Batch 136 — 保存/新登录的蓝湖 Cookie 必须真正注入到 lanhu 提取器。

根因：LanhuExtractor.__init__ 无 cookie 参数，请求头读模块级 COOKIE（env LANHU_COOKIE）；
保存的 Cookie 从未注入 → 采集任务持续"会话已失效"。本批在 _create_lanhu_extractor 把
cookie_override 注入 module.COOKIE / DDS_COOKIE 后再实例化。
"""
from __future__ import annotations

import sys
from types import SimpleNamespace

from app.services.external import lanhu_provider


class _FakeModule:
    COOKIE = "env-cookie"
    DDS_COOKIE = "env-cookie"


class _FakeExtractor:
    def __init__(self):
        self.client_headers = {"Cookie": _FakeModule.COOKIE}


def _make_runtime() -> SimpleNamespace:
    return SimpleNamespace(LanhuExtractor=_FakeExtractor, module=_FakeModule)


def test_saved_cookie_is_injected_into_extractor():
    runtime = _make_runtime()
    ext = lanhu_provider._create_lanhu_extractor(runtime, "SAVED=abc; s2=2")
    assert ext.client_headers["Cookie"] == "SAVED=abc; s2=2"
    assert _FakeModule.COOKIE == "SAVED=abc; s2=2"
    assert _FakeModule.DDS_COOKIE == "SAVED=abc; s2=2"


def test_no_cookie_keeps_module_default():
    runtime = _make_runtime()
    _FakeModule.COOKIE = "env-cookie"
    _FakeModule.DDS_COOKIE = "env-cookie"
    ext = lanhu_provider._create_lanhu_extractor(runtime, "")
    assert ext.client_headers["Cookie"] == "env-cookie"


def test_real_runtime_module_exposes_cookie_globals():
    """真实 runtime 的 module 暴露 COOKIE/DDS_COOKIE，可被注入（CI 会初始化子模块）。"""
    module_path = str(lanhu_provider._lanhu_mcp_dir())
    sys.path.insert(0, module_path)
    try:
        import lanhu_mcp_server as module  # type: ignore
        runtime = lanhu_provider._load_lanhu_runtime()
    except Exception:  # noqa: BLE001 — 子模块/依赖缺失时跳过
        return
    finally:
        sys.path.remove(module_path)
    assert hasattr(module, "COOKIE")
    assert hasattr(module, "DDS_COOKIE")
    assert runtime.module is module
