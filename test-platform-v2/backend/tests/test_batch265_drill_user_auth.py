"""Batch 265 / C264-3 — 演练驱动必须用**用户凭据**登记任务。

回归点：`POST /api/v1/execution-jobs` 依赖 `require_permission("execution:manage")`，
只认用户 JWT；早期驱动发的是 `X-AI-Agent-Token`（节点令牌）→ 必然 401，
导致 §5 第 ⑦ 条按文档命令永远跑不通。
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[1]
SCRIPT = BACKEND / "scripts" / "drill_three_versions.py"


def _load_driver():
    spec = importlib.util.spec_from_file_location("drill_three_versions_under_test", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class _Args:
    def __init__(self, **overrides):
        self.user_token = ""
        self.username = ""
        self.password = ""
        self.node_token = "node-token-not-a-user-jwt"
        self.project_id = 7
        self.base_url = "http://127.0.0.1:1"
        for key, value in overrides.items():
            setattr(self, key, value)


def test_user_token_builds_bearer_headers_with_project_scope():
    driver = _load_driver()
    headers = driver._auth_headers(_Args(user_token="jwt-abc"))
    assert headers["Authorization"] == "Bearer jwt-abc"
    assert headers["X-Project-Id"] == "7"
    assert "X-AI-Agent-Token" not in headers


def test_node_token_alone_is_rejected_with_actionable_message():
    driver = _load_driver()
    with pytest.raises(SystemExit) as exc:
        driver._auth_headers(_Args())
    message = str(exc.value)
    assert "--user-token" in message
    assert "node-token" in message


def test_run_versions_uses_auth_headers_not_agent_token():
    source = SCRIPT.read_text(encoding="utf-8")
    assert "headers = _auth_headers(args)" in source
    assert 'headers = {"X-AI-Agent-Token"' not in source


def test_report_path_parent_is_created(tmp_path):
    """--out 指向不存在的子目录时不应崩（Batch 265 实跑时命中）。

    Batch 270 把"建父目录 + 落盘"收敛进 `_write_report`（顺带支持每完成一版就增量落盘，
    修 C269-2），所以本用例改为**验行为**而不是匹配源码字符串。
    """
    driver = _load_driver()
    target = tmp_path / "nested" / "deeper" / "drill.json"
    driver._write_report(str(target), {"status": "running", "versions": []})
    assert target.exists()
    assert json.loads(target.read_text(encoding="utf-8"))["status"] == "running"
    # 空路径是 no-op（不写文件、不报错）
    driver._write_report("", {"ignored": True})
