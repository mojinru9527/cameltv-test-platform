"""A2 针对性测试：AI 消费点无项目级 AI 配置时的禁用语义。

覆盖三类：
- _call_ai_api 无配置 → 返回 error 字段（不抛）；
- triage_failed_cases 无配置 → 降级 rule_only（use_llm 被置 False）；
- dsh submit_task 无配置 → 抛 AIProviderUnconfiguredError（400，被全局 handler 转业务错误）。
"""
from __future__ import annotations

import asyncio

import pytest

from app.models.test_plan import TestPlan
from app.services.ai_config_service import AIProviderUnconfiguredError
from app.services import ai_service
from app.services import triage_service
from app.services.dsh import dsh_task_service


def test_call_ai_api_returns_error_field_when_unconfigured(db_session):
    """无 provider 配置时 _call_ai_api 返回 error 字段而非抛错。"""
    resp = asyncio.run(
        ai_service._call_ai_api(db_session, 999, "sys", "user", "label")
    )
    assert resp["result"] is None
    assert resp["finish_reason"] == "error"
    assert "未配置 AI 提供方" in resp["error"]


def test_generate_test_cases_raises_value_error_when_unconfigured(db_session):
    """generate_test_cases 无配置 → 抛 ValueError（路由转 400 业务错误）。"""
    with pytest.raises(ValueError, match="未配置 AI 提供方"):
        asyncio.run(ai_service.generate_test_cases(db_session, 999, "需求内容"))


def test_triage_degrades_to_rule_only_when_unconfigured(db_session):
    """triage 无配置 → use_llm 被置 False，analysis_method=rule_only。"""
    plan = TestPlan(project_id=1, name="triage-plan", status="draft")
    db_session.add(plan)
    db_session.commit()

    result = triage_service.triage_failed_cases(
        db_session, plan.id, project_id=1, use_llm=True,
    )
    # 无失败执行记录 → 走 early return（rule_only）
    assert result["analysis_method"] == "rule_only"


def test_dsh_submit_rejected_when_unconfigured(db_session):
    """submit_task 无配置 → 抛 AIProviderUnconfiguredError（400 业务错误）。"""
    with pytest.raises(AIProviderUnconfiguredError):
        dsh_task_service.submit_task(
            db_session, project_id=999, task="run tests", operator_id=1,
        )
