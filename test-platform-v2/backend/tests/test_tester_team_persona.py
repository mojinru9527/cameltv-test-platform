"""DSH 测试 Agent 框架 — tester-team persona 单测。

tester_team_persona.py 是纯函数（无 IO），与 agent_team_persona 同模式：
覆盖成员集、固定步骤纪律、测试视角约束（skill 自检、平台 Runner、reviewer）。
"""
from __future__ import annotations

from app.services.dsh.tester_team_persona import (
    _CONSTRAINTS,
    _FULL_MEMBERS,
    _LIGHT_MEMBERS,
    _STEPS,
    build_tester_team_persona,
)


class TestBuildTesterTeamPersona:
    def test_full_members(self):
        p = build_tester_team_persona("为登录模块生成用例并执行", "full")
        assert "为登录模块生成用例并执行" in p  # 用户目标原文
        for name, role in _FULL_MEMBERS:
            assert f"{name}（{role}）" in p
        assert len(_FULL_MEMBERS) == 5
        assert "analyst" in p and "case-designer" in p and "reviewer" in p
        assert "api-tester" in p and "ui-tester" in p

    def test_light_members(self):
        p = build_tester_team_persona("轻量用例设计", "light")
        for name, role in _LIGHT_MEMBERS:
            assert f"{name}（{role}）" in p
        assert len(_LIGHT_MEMBERS) == 2
        # 成员集区不含执行/审查成员（约束文本可提及，但成员集只含两员）
        member_section = p.split("【成员集】")[1].split("【产出要求】")[0]
        assert "api-tester" not in member_section
        assert "ui-tester" not in member_section
        assert "reviewer" not in member_section

    def test_fixed_steps_present(self):
        """固定步骤关键词齐备（建团队→加成员→建任务→认领→唤醒→轮询→最终报告）。"""
        p = build_tester_team_persona("x", "full")
        for keyword in ("agent_teams_create", "agent_teams_add_member", "agent_teams_create_task",
                        "agent_teams_claim_task", "agent_teams_send_message", "agent_teams_status", "最终报告"):
            assert keyword in p
        assert "【用户目标】" in p and "【团队档位】full" in p

    def test_wake_and_wait_discipline(self):
        """Batch 191 纪律延续：认领后必须唤醒成员、未完成任务不得结束会话。"""
        p = build_tester_team_persona("x", "light")
        assert "唤醒" in p
        assert "每个认领的任务都必须发送消息" in p
        assert "严禁在存在未完成任务时输出最终报告或结束会话" in p
        assert "必须等到每个任务状态变为 completed" in p

    def test_tester_constraints_present(self):
        """测试视角约束：skill 自检、平台 Runner、reviewer 三触发点。"""
        p = build_tester_team_persona("x", "light")
        assert "test-case-design skill" in p
        assert "tests/test-case-standards/" in p
        assert "trigger_test_execution" in p
        assert "禁止 agent 自行直连测试环境" in p
        assert "reviewer 独立于 case-designer" in p
        assert "对照需求核覆盖" in p and "对照 skill 规则核格式合规" in p
        assert "断链检查" in p
        for c in _CONSTRAINTS:
            assert c in p

    def test_constraints_export_consistent(self):
        """_CONSTRAINTS 导出与 persona 正文一致（防漂移）。"""
        p = build_tester_team_persona("x", "full")
        for c in _CONSTRAINTS:
            assert c in p

    def test_pure_function_no_io(self):
        """纯函数：相同输入两次调用输出一致（无状态）。"""
        a = build_tester_team_persona("目标", "full")
        b = build_tester_team_persona("目标", "full")
        assert a == b

    def test_steps_export_consistent(self):
        p = build_tester_team_persona("x", "full")
        for s in _STEPS:
            assert s in p
