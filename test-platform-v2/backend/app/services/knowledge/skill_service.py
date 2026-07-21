"""知识库 Skills 模板服务（Layer 9）

预置 AI 能力模板，可一键应用到知识库。每个 Skill 定义：
- name: 唯一标识
- label: 展示名称
- description: 功能描述
- input_schema: 输入参数 schema
- prompt_template: AI 提示词模板（调用 agent_orchestrator 执行）
"""

from __future__ import annotations

import json
import logging
from typing import Any

logger = logging.getLogger("knowledge.skills")

# ── 预置 Skills 模板 ──

SKILL_TEMPLATES: dict[str, dict[str, Any]] = {
    "generate-testcases": {
        "name": "generate-testcases",
        "label": "生成测试用例",
        "description": "基于项目知识库中的需求文档和 API 契约，自动生成结构化测试用例",
        "icon": "TestTube",
        "category": "生成",
        "input_params": [
            {"key": "requirement_ids", "label": "需求文档 ID", "type": "int_array", "required": False,
             "description": "留空则使用所有需求知识源"},
            {"key": "max_cases", "label": "最大用例数", "type": "int", "default": 20, "required": False},
            {"key": "priority_filter", "label": "优先级过滤", "type": "select",
             "options": ["P0", "P1", "P2", "P3", "all"], "default": "all", "required": False},
        ],
        "prompt_template": (
            "你是一个测试用例设计专家。请基于以下知识库内容，生成 {max_cases} 条结构化测试用例（优先级：{priority_filter}）。\n\n"
            "知识库内容：\n{knowledge_context}\n\n"
            "输出格式：每条用例包含 title（用例标题）、preconditions（前置条件）、steps（测试步骤）、"
            "expected_result（预期结果）、priority（P0-P3）、case_type（api/functional）。\n"
            "用 JSON 数组格式输出。"
        ),
    },
    "analyze-defect-patterns": {
        "name": "analyze-defect-patterns",
        "label": "分析缺陷模式",
        "description": "分析历史缺陷数据，识别高频缺陷模式、受影响模块和根因聚类",
        "icon": "Bug",
        "category": "分析",
        "input_params": [
            {"key": "time_range_days", "label": "时间范围（天）", "type": "int", "default": 90, "required": False},
            {"key": "min_frequency", "label": "最小频次", "type": "int", "default": 3,
             "description": "出现少于此频次的模式将被过滤"},
        ],
        "prompt_template": (
            "你是一个缺陷分析专家。请分析以下缺陷数据，识别高频缺陷模式（至少出现 {min_frequency} 次）、"
            "受影响最严重的模块、以及根因聚类。\n\n"
            "缺陷数据（近 {time_range_days} 天）：\n{knowledge_context}\n\n"
            "输出 JSON 格式：{{\"patterns\": [...], \"top_modules\": [...], \"root_causes\": [...], \"summary\": \"...\"}}"
        ),
    },
    "extract-api-contracts": {
        "name": "extract-api-contracts",
        "label": "提取 API 契约",
        "description": "从接口导入知识中提取 API 契约规范，生成接口文档摘要",
        "icon": "FileCode",
        "category": "提取",
        "input_params": [
            {"key": "service_name", "label": "服务名过滤", "type": "str", "required": False,
             "description": "留空则处理所有服务"},
        ],
        "prompt_template": (
            "你是一个 API 文档专家。请从以下接口知识中提取 API 契约规范，按服务/模块分组整理。\n\n"
            "服务过滤: {service_name}\n"
            "接口知识：\n{knowledge_context}\n\n"
            "输出 JSON 格式：{{\"services\": [{{\"name\": \"...\", \"endpoints\": [...], \"schemas\": [...]}}], \"summary\": \"...\"}}"
        ),
    },
    "detect-contradictions": {
        "name": "detect-contradictions",
        "label": "检测知识矛盾",
        "description": "扫描知识库中的矛盾信息（如需求冲突、API 定义不一致），输出矛盾清单",
        "icon": "AlertTriangle",
        "category": "治理",
        "input_params": [
            {"key": "domains", "label": "检查域", "type": "multi_select",
             "options": ["requirement", "api_schema", "test_case", "defect_case", "all"],
             "default": "all", "required": False},
        ],
        "prompt_template": (
            "你是一个知识质量审查专家。请扫描以下知识库内容，检测其中的矛盾和不一致（如需求冲突、"
            "API 定义不一致、用例与需求不匹配等）。\n\n"
            "检查域: {domains}\n"
            "知识库内容：\n{knowledge_context}\n\n"
            "输出 JSON 格式：{{\"contradictions\": [{{\"type\": \"...\", \"source_a\": \"...\", \"source_b\": \"...\", "
            "\"description\": \"...\", \"severity\": \"high|medium|low\"}}], \"summary\": \"...\"}}"
        ),
    },
    "summarize-iteration": {
        "name": "summarize-iteration",
        "label": "迭代知识摘要",
        "description": "对指定迭代的所有知识源生成结构化摘要（变更内容、影响范围、风险提示）",
        "icon": "FileText",
        "category": "总结",
        "input_params": [
            {"key": "iteration_id", "label": "迭代 ID", "type": "int", "required": True,
             "description": "要总结的迭代 ID"},
        ],
        "prompt_template": (
            "你是一个技术文档撰写专家。请对以下迭代的所有知识源生成结构化摘要，包括："
            "变更内容清单、影响范围评估、风险提示。\n\n"
            "迭代 #{iteration_id} 知识内容：\n{knowledge_context}\n\n"
            "输出 JSON 格式：{{\"changes\": [...], \"impact\": \"...\", \"risks\": [...], \"summary\": \"...\"}}"
        ),
    },
    "suggest-regression-scope": {
        "name": "suggest-regression-scope",
        "label": "回归范围建议",
        "description": "基于变更文件和模块，预测回归测试范围及风险排序",
        "icon": "Target",
        "category": "预测",
        "input_params": [
            {"key": "changed_paths", "label": "变更文件路径", "type": "str_array", "required": True,
             "description": "一行一个文件路径"},
            {"key": "changed_modules", "label": "变更模块", "type": "str_array", "required": True,
             "description": "一行一个模块名"},
        ],
        "prompt_template": (
            "你是一个回归测试策略专家。基于以下变更信息和知识库历史数据，预测回归测试范围，"
            "按风险从高到低排序。\n\n"
            "变更文件: {changed_paths}\n"
            "变更模块: {changed_modules}\n"
            "历史缺陷与知识：\n{knowledge_context}\n\n"
            "输出 JSON 格式：{{\"items\": [{{\"module\": \"...\", \"risk\": \"high|medium|low\", "
            "\"reason\": \"...\", \"suggested_cases\": [...]}}], \"summary\": \"...\"}}"
        ),
    },
}


def list_skills() -> list[dict[str, Any]]:
    """列出所有可用 Skills 模板（不含 prompt_template 细节）。"""
    return [
        {
            "name": s["name"],
            "label": s["label"],
            "description": s["description"],
            "icon": s["icon"],
            "category": s["category"],
            "input_params": s["input_params"],
        }
        for s in SKILL_TEMPLATES.values()
    ]


def get_skill(name: str) -> dict[str, Any] | None:
    """获取单个 Skill 模板的完整定义。"""
    return SKILL_TEMPLATES.get(name)


def build_skill_knowledge_context(
    db, project_id: int, skill_name: str, params: dict[str, Any]
) -> str:
    """为 Skill 构建知识上下文（从知识库检索相关内容）。"""
    from app.models.knowledge import KnowledgeChunk, KnowledgeSource
    from sqlalchemy import select

    # 根据 skill 类型决定检索哪些 chunk_type
    type_map = {
        "generate-testcases": ["requirement_rule", "api_schema"],
        "analyze-defect-patterns": ["defect_case"],
        "extract-api-contracts": ["api_schema"],
        "detect-contradictions": ["requirement_rule", "api_schema", "test_case", "defect_case"],
        "summarize-iteration": ["platform_knowledge", "agent_output_*"],
        "suggest-regression-scope": ["defect_case", "test_case", "execution_result"],
    }

    chunk_types = type_map.get(skill_name, ["platform_knowledge"])

    stmt = (
        select(KnowledgeChunk)
        .where(
            KnowledgeChunk.project_id == project_id,
            KnowledgeChunk.status == "active",
            KnowledgeChunk.chunk_type.in_(chunk_types),
        )
        .limit(50)
    )

    chunks = list(db.scalars(stmt).all())

    parts: list[str] = []
    for c in chunks:
        source = db.get(KnowledgeSource, c.source_id) if c.source_id else None
        source_title = source.title if source else "未知来源"
        parts.append(f"## {source_title}\n{c.content}")

    return "\n\n".join(parts)


async def apply_skill_in_new_session(
    project_id: int, skill_name: str, params: dict[str, Any] | None = None
) -> dict[str, Any]:
    """应用 Skill 模板，执行 AI 处理并返回结果。

    使用独立的 DB Session 获取知识上下文，然后调用 Agent 执行。
    """
    from app.core.db import SessionLocal

    skill = get_skill(skill_name)
    if not skill:
        return {"error": f"未知 Skill: {skill_name}", "success": False}

    params = params or {}

    # 填充默认参数
    filled_params: dict[str, Any] = {}
    for p in skill["input_params"]:
        key = p["key"]
        filled_params[key] = params.get(key, p.get("default", ""))
    # 也传递原始参数中的额外值
    for k, v in params.items():
        if k not in filled_params:
            filled_params[k] = v

    db = SessionLocal()
    try:
        # 构建知识上下文
        knowledge_context = build_skill_knowledge_context(db, project_id, skill_name, filled_params)

        # 构建完整的 prompt
        prompt = skill["prompt_template"].format(
            knowledge_context=knowledge_context,
            **{k: (json.dumps(v, ensure_ascii=False) if isinstance(v, (list, dict)) else str(v))
               for k, v in filled_params.items()},
        )

        # 尝试通过 agent_orchestrator 执行（如可用）
        try:
            from app.services.knowledge.agent_orchestrator import run_agent_in_new_session
            result = run_agent_in_new_session(
                project_id=project_id,
                agent_type="knowledge_skill",
                input_prompt=prompt,
                metadata={
                    "skill_name": skill_name,
                    "params": filled_params,
                },
            )
            if result and result.get("success"):
                return {
                    "success": True,
                    "skill": skill_name,
                    "result": result.get("output", ""),
                    "agent_run_id": result.get("run_id"),
                }
        except Exception as e:
            logger.warning("Agent orchestrator unavailable for skill %s: %s", skill_name, e)

        # 降级：返回上下文和 prompt（供手动使用）
        return {
            "success": True,
            "skill": skill_name,
            "knowledge_context": knowledge_context[:2000],
            "prompt": prompt[:2000],
            "params": filled_params,
            "note": "Agent 执行器不可用，返回原始知识上下文和分析提示词",
        }
    except Exception as e:
        logger.exception("Apply skill %s failed", skill_name)
        return {"error": str(e), "success": False}
    finally:
        db.close()
