from __future__ import annotations

import asyncio

import pytest

from app.services.knowledge import (
    attachment_extractor,
    navigates_to_extractor,
    version_differ,
)
from app.services.knowledge.attachment_extractor import AttachmentContent
from app.services.knowledge.llm_json_client import (
    LLMResponseError,
    LLMUnavailableError,
    _parse_json_object,
    call_json_model,
    sanitize_external_text,
)
from app.services.knowledge.navigates_to_extractor import PageInteraction
from app.services.knowledge.version_differ import VersionDiffResult


def test_external_text_sanitizer_removes_credentials_and_contact_data():
    sanitized = sanitize_external_text(
        "email=a@example.com phone=13800138000 token=super-secret "
        "Authorization: Bearer abc.def.ghi"
    )

    assert "a@example.com" not in sanitized
    assert "13800138000" not in sanitized
    assert "super-secret" not in sanitized
    assert "abc.def.ghi" not in sanitized


def test_json_parser_rejects_non_object_response():
    with pytest.raises(LLMResponseError, match="JSON object"):
        _parse_json_object('["not-an-object"]')


def test_json_client_rejects_missing_api_key_before_network(monkeypatch):
    from app.services.knowledge import llm_json_client
    from app.services.ai_config_service import AIProviderUnconfiguredError

    monkeypatch.setattr(llm_json_client.settings, "ai_enabled", True)
    monkeypatch.setattr(
        llm_json_client.ai_config_service,
        "resolve",
        lambda db, project_id: (_ for _ in ()).throw(AIProviderUnconfiguredError()),
    )

    with pytest.raises(LLMUnavailableError, match="未配置 AI 提供方"):
        asyncio.run(
            call_json_model(
                db=None,
                project_id=0,
                system_prompt="仅返回 JSON",
                user_payload={"text": "hello"},
            )
        )


def test_attachment_ai_maps_structured_model_response(monkeypatch):
    async def fake_call(**_kwargs):
        return {
            "summary": "支付失败后可以重试。",
            "functional_points": [
                {
                    "name": "失败重试",
                    "description": "允许用户重新发起支付",
                    "category": "workflow",
                    "priority": "P0",
                }
            ],
            "business_rules": [
                {
                    "rule": "失败订单最多重试三次",
                    "condition": "retry_count < 3",
                    "action": "允许重试",
                    "category": "workflow",
                    "confidence": 0.93,
                }
            ],
            "related_modules": ["订单"],
            "confidence": 0.91,
        }

    monkeypatch.setattr(attachment_extractor, "call_json_model", fake_call)

    result = asyncio.run(
        attachment_extractor._ai_analyze_attachment(
            None,
            1,
            "用户支付失败后可重试，最多三次。",
            "支付说明",
        )
    )

    assert isinstance(result, AttachmentContent)
    assert result.summary == "支付失败后可以重试。"
    assert result.functional_points[0].name == "失败重试"
    assert result.business_rules[0].condition == "retry_count < 3"
    assert result.related_modules == ["订单"]
    assert result.extraction_confidence == pytest.approx(0.91)


def test_attachment_ai_rejects_empty_semantic_result(monkeypatch):
    async def fake_call(**_kwargs):
        return {"summary": "", "functional_points": [], "business_rules": []}

    monkeypatch.setattr(attachment_extractor, "call_json_model", fake_call)

    with pytest.raises(ValueError, match="usable"):
        asyncio.run(
            attachment_extractor._ai_analyze_attachment(None, 1, "有效正文", "空响应附件")
        )


def test_version_diff_records_explicit_warning_when_ai_unavailable(monkeypatch):
    async def unavailable(**_kwargs):
        raise LLMUnavailableError("AI_API_KEY 未配置")

    monkeypatch.setattr(version_differ, "call_json_model", unavailable)
    rule_result = VersionDiffResult(
        new_modules=["资讯管理"],
        deleted_modules=["资讯模块"],
        diff_confidence=0.85,
    )

    result = asyncio.run(version_differ._ai_diff(None, 0, [], [], rule_result))

    assert result is rule_result
    assert result.diff_confidence <= 0.85
    assert any("AI" in warning and "未配置" in warning for warning in result.warnings)


def test_version_diff_applies_validated_module_rename(monkeypatch):
    async def fake_call(**_kwargs):
        return {
            "module_matches": [
                {
                    "current_module": "资讯管理",
                    "parent_module": "资讯模块",
                    "modified_pages": ["详情页"],
                    "confidence": 0.94,
                }
            ],
            "confidence": 0.94,
        }

    monkeypatch.setattr(version_differ, "call_json_model", fake_call)
    parent = type(
        "ParentModule",
        (),
        {"id": 13, "name": "资讯模块", "node_type": "module"},
    )()
    page = type(
        "EvidencePage",
        (),
        {
            "folder": "资讯管理",
            "page_name": "详情页",
            "merged_text": "新闻详情",
            "ocr_text": "",
        },
    )()
    unchanged_page = type(
        "EvidencePage",
        (),
        {
            "folder": "资讯管理",
            "page_name": "列表页",
            "merged_text": "新闻列表",
            "ocr_text": "",
        },
    )()
    rule_result = VersionDiffResult(
        new_modules=["资讯管理"],
        deleted_modules=["资讯模块"],
        diff_confidence=0.85,
        total_pages_diff=2,
    )

    result = asyncio.run(
        version_differ._ai_diff(
            None,
            0,
            [page, unchanged_page],
            [parent],
            rule_result,
        )
    )

    assert result.new_modules == []
    assert result.deleted_modules == []
    assert result.modified_modules[0].module_name == "资讯管理"
    assert result.modified_modules[0].parent_module_id == 13
    assert result.modified_modules[0].modified_pages == ["详情页"]
    assert result.total_pages_diff == 1
    assert result.diff_confidence == pytest.approx(0.94)


def test_navigation_ai_uses_text_and_maps_interactions(monkeypatch):
    captured = {}

    async def fake_call(**kwargs):
        captured.update(kwargs)
        return {
            "interactions": [
                {
                    "trigger": "点击赛程",
                    "target_page": "赛程页",
                    "interaction_type": "navigation",
                    "source_element": "赛程",
                    "description": "导航到赛程",
                }
            ]
        }

    monkeypatch.setattr(navigates_to_extractor, "call_json_model", fake_call)
    page = type("Page", (), {"id": 7, "name": "赛事首页"})()
    evidence = type(
        "Evidence",
        (),
        {"merged_text": "首页 赛程 数据", "ocr_text": "", "dom_text": ""},
    )()

    result = asyncio.run(navigates_to_extractor._p2_ai_multimodal(None, 1, page, evidence))

    assert result == [
        PageInteraction(
            trigger="点击赛程",
            target_page="赛程页",
            interaction_type="navigation",
            source_element="赛程",
            description="导航到赛程",
            extraction_source="ai_text",
        )
    ]
    assert "screenshot" not in str(captured).lower()
    assert "首页 赛程 数据" in str(captured)


def test_dom_extraction_preserves_real_link_targets():
    evidence = type(
        "Evidence",
        (),
        {
            "dom_text": """
                <div>
                  <a href="/news/42">查看新闻</a>
                  <button data-link="schedule">赛程</button>
                  <div data-click="open-profile">我的</div>
                </div>
            """
        },
    )()

    result = navigates_to_extractor._p1_dom_extraction(evidence)

    assert [(item.trigger, item.target_page) for item in result] == [
        ("点击查看新闻", "/news/42"),
        ("点击赛程", "schedule"),
        ("点击我的", "open-profile"),
    ]
    assert all(item.extraction_source == "dom" for item in result)
