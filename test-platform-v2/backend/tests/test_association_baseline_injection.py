"""Batch 115 — 关联基座生成提示注入测试（用户方向：生成前先按关联定位）。"""
from __future__ import annotations

from app.services.association_baseline import association_context, baseline_stats
from app.services import ai_service


def test_baseline_stats() -> None:
    st = baseline_stats()
    assert st["user_modules"] >= 13
    assert st["interface_map"] >= 30


def test_association_context_news() -> None:
    ctx = association_context("资讯")
    assert "资讯" in ctx
    assert "news" in ctx.lower()


def test_user_message_injects_association_context() -> None:
    extraction = {
        "modules": [
            {"id": "M1", "name": "资讯", "description": "资讯列表与详情",
             "function_points": [{"id": "FP1", "name": "资讯列表", "description": "分类列表"}]},
        ],
        "overall_assessment": "ok",
    }
    msg = ai_service._build_user_message_with_extraction(
        content="资讯模块：列表、详情、相关推荐",
        file_type="md",
        source_ref="test",
        extraction=extraction,
    )
    assert "模块-接口-功能关联基座" in msg
    assert "news" in msg.lower()


def test_association_context_unknown_empty() -> None:
    assert association_context("不存在的模块XYZ") == ""