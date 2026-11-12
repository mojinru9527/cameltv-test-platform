"""M8 / TA-040：Miniapp Adapter 单测。"""
from __future__ import annotations

import pytest

from app.aiqe.adapters.miniapp import (
    CASES,
    WECHAT_MATRIX,
    MiniappAdapter,
    MiniappError,
    resolve_backend,
)


def executor(case):
    return {"passed": True, "evidence": [f"artifact:{case.case_id.lower()}"]}


def test_matrix_covers_versions():
    assert len(WECHAT_MATRIX) >= 3
    assert "8.0.50" in WECHAT_MATRIX


def test_resolve_preferred_minium():
    assert resolve_backend("8.0.47", "minium") == "minium"


def test_resolve_falls_back_to_weapp_mcp():
    assert resolve_backend("8.0.45", "minium") == "weapp_dev_mcp"


def test_unknown_version_and_backend_rejected():
    with pytest.raises(MiniappError):
        resolve_backend("7.0.0")
    with pytest.raises(MiniappError):
        resolve_backend("8.0.47", "unknown")


def test_adapter_runs_five_cases():
    summary = MiniappAdapter(executor).run()
    assert summary["total"] == len(CASES) == 5
    assert summary["all_passed"] is True
    assert all(item["evidence"] for item in summary["results"])
