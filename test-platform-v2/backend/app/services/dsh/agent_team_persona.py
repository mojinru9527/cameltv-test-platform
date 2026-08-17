"""AgentTeams 船长提示词构建 — Batch 191。

`build_agent_team_persona(task, batch_mode)` 纯函数（无 IO，单测友好），
输出 DSH 船长固定步骤提示词，经 run_dsh_task 的 extra_env["DSH_SYSTEM_PROMPT"]
注入 node / python-sdk 两套运行时。

成员集（PRD §1.3 / 设计文档 §4.2 固化）：
- full（完整批次）：product / pm / design / dev / qa 五名
- light（轻量批次）：product / qa 两名
"""
from __future__ import annotations

_FULL_MEMBERS = [
    ("product", "产品"),
    ("pm", "项目管理"),
    ("design", "设计"),
    ("dev", "开发"),
    ("qa", "测试"),
]

_LIGHT_MEMBERS = [
    ("product", "产品"),
    ("qa", "测试"),
]

# 固定步骤（两运行时共用，全文字面；模型自组织失败由 runner 兜底为 failed + 可读 error，R-5）
_STEPS = [
    "1. agent_teams_create：创建团队（name 用目标主题摘要，description 写用户目标原文）。",
    "2. agent_teams_add_member：按批次模式添加成员（见成员集）；role 字段填对应中文角色。",
    "3. agent_teams_create_task：把用户目标拆成带依赖关系的子任务（如 PRD→计划→设计→实现→测试/门禁），"
    "用 dependencies 参数表达先后依赖。",
    "4. agent_teams_claim_task：按依赖顺序把任务认领派发给对应成员（一次一个任务，"
    "等成员完成后派发下一个依赖就绪的任务）。",
    "5. 收集各成员结论：成员完成任务后用 agent_teams_send_message 汇报，你在收件后继续派发后续任务。",
    "6. 全部任务完成后：汇总各成员结论，写一份【最终报告】（含：团队分工、各任务结果、总体结论），"
    "作为最终回复输出。",
]

_CONSTRAINTS = [
    "不要创建用户目标之外的额外任务；不要删除团队（保留团队档案供平台复盘）。",
]


def build_agent_team_persona(task: str, batch_mode: str) -> str:
    """构建 DSH 船长固定步骤提示词。

    Args:
        task: 用户目标原文。
        batch_mode: full（完整批次，五成员）| light（轻量批次，两成员）。
    """
    members = _FULL_MEMBERS if batch_mode == "full" else _LIGHT_MEMBERS
    member_lines = "\n".join(
        f"   - {name}（{role}）" for name, role in members
    )
    steps = "\n".join(_STEPS)
    constraints = "\n".join(f"- {c}" for c in _CONSTRAINTS)
    return (
        "你是测试平台提交的 DSH 船长（AgentTeams 船长模式）。"
        "请严格按以下步骤用 agent_teams_* 工具自组织团队完成目标。\n\n"
        f"【用户目标】{task}\n"
        f"【批次模式】{batch_mode}\n\n"
        "【固定步骤】（逐步执行，每一步用对应工具，不要跳过）\n"
        f"{steps}\n\n"
        "【成员集】（按批次模式添加）\n"
        f"{member_lines}\n\n"
        "【产出要求】工作产物写入当前工作区 work-logs/ 目录（如无可新建），"
        "最终报告同时作为回复文本输出。\n"
        "【约束】\n"
        f"{constraints}"
    )
