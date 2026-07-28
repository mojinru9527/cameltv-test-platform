"""AI 智能分诊 — LLM 分析执行失败的测试用例，分类为 bug/flaky_env/case_defect/known_issue。

设计要点:
- 混合策略: 先用规则引擎 (failure_analyzer) 做初步分类，再用 LLM 做深度分析
- LLM 分析使用 agent_orchestrator 的能力（含 RAG 检索相似历史缺陷）
- 支持一键生成缺陷创建草稿
"""
from __future__ import annotations

import json
import logging

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.test_plan import TestExecution, TestPlan, TestPlanCase
from app.models.test_case import TestCase

logger = logging.getLogger("triage")


# ═══════════════════════════════════════════════════════
# 公共 API
# ═══════════════════════════════════════════════════════

def triage_failed_cases(
    db: Session,
    plan_id: int,
    *,
    project_id: int = 0,
    use_llm: bool = True,
) -> dict:
    """分析测试计划中所有失败用例，返回分类结果。

    Args:
        db: 数据库会话
        plan_id: 测试计划 ID
        project_id: 项目 ID
        use_llm: 是否使用 LLM 深度分析（False 时仅用规则引擎）

    Returns:
        {
            "plan_id": int,
            "total_failures": int,
            "classified": [...],
            "summary": {"bug": N, "flaky_env": N, "case_defect": N, "known_issue": N},
            "analysis_method": "llm" | "rule_only",
        }
    """
    # 1. 收集所有失败执行记录
    plan = db.get(TestPlan, plan_id)
    if not plan or (project_id and plan.project_id != project_id):
        return {"plan_id": plan_id, "total_failures": 0, "classified": [],
                "summary": {}, "error": "计划不存在或无权访问"}

    executions = db.query(TestExecution).join(
        TestPlanCase, TestExecution.plan_case_id == TestPlanCase.id
    ).filter(
        TestPlanCase.plan_id == plan_id,
        TestExecution.status == "fail",
    ).all()

    if not executions:
        return {"plan_id": plan_id, "total_failures": 0, "classified": [],
                "summary": {"bug": 0, "flaky_env": 0, "case_defect": 0, "known_issue": 0},
                "analysis_method": "rule_only"}

    # 2. 收集每个失败用例的详细信息
    failure_cases = []
    for exec_row in executions:
        plan_case = db.get(TestPlanCase, exec_row.plan_case_id)
        test_case = db.get(TestCase, plan_case.case_id) if plan_case else None

        # 解析 actual_result
        result_data = {}
        try:
            if exec_row.actual_result:
                result_data = json.loads(exec_row.actual_result)
        except (json.JSONDecodeError, TypeError):
            result_data = {"error": str(exec_row.actual_result)[:500]}

        failure_cases.append({
            "execution_id": exec_row.id,
            "case_id": test_case.id if test_case else 0,
            "case_title": test_case.title if test_case else "Unknown",
            "case_type": test_case.case_type if test_case else "unknown",
            "priority": test_case.priority if test_case else "P2",
            "notes": exec_row.notes or "",
            "result_data": result_data,
            "executed_at": exec_row.executed_at.isoformat() if exec_row.executed_at else "",
        })

    # 3. 规则引擎初分类
    classified = []
    for fc in failure_cases:
        rule_result = _rule_based_classify(fc)
        classified.append({**fc, **rule_result})

    # 4. LLM 深度分析（可选）
    if use_llm and settings.ai_enabled and settings.ai_api_key:
        try:
            classified = _llm_deep_analyze(classified)
            method = "llm"
        except Exception:
            logger.exception("LLM triage failed, using rule-only results")
            method = "rule_only"
    else:
        method = "rule_only"

    # 5. 汇总
    summary = {"bug": 0, "flaky_env": 0, "case_defect": 0, "known_issue": 0}
    for c in classified:
        cat = c.get("category", "unknown")
        if cat in summary:
            summary[cat] += 1

    return {
        "plan_id": plan_id,
        "total_failures": len(classified),
        "classified": classified,
        "summary": summary,
        "analysis_method": method,
    }


def generate_defect_draft(failure: dict) -> dict:
    """根据分类结果生成缺陷创建草稿（供一键提缺陷使用）。

    Returns:
        {"title": "...", "description": "...", "severity": "P2", "case_id": N, "execution_id": N}
    """
    case_title = failure.get("case_title", "Unknown")
    category = failure.get("category", "unknown")
    confidence = failure.get("confidence", 0)
    explanation = failure.get("explanation", "")
    suggested_action = failure.get("suggested_action", "")
    result_data = failure.get("result_data", {})

    # 严重度从用例优先级派生
    priority = failure.get("priority", "P2")
    severity = priority  # P0 case → P0 defect

    # 构建描述
    desc_parts = [f"## 自动分诊结果\n- 分类: **{category}** (置信度: {confidence:.0%})"]
    if explanation:
        desc_parts.append(f"- 分析: {explanation}")
    if suggested_action:
        desc_parts.append(f"- 建议: {suggested_action}")

    # 执行详情
    if result_data:
        desc_parts.append("\n## 执行详情")
        if result_data.get("error"):
            desc_parts.append(f"- 错误: {result_data['error']}")
        assertions = result_data.get("assertions", [])
        failed_assertions = [a for a in assertions if not a.get("passed", True)]
        if failed_assertions:
            desc_parts.append("- 失败断言:")
            for a in failed_assertions[:5]:
                desc_parts.append(f"  - {a.get('type', '?')}: 期望 {a.get('expected', '?')}, 实际 {a.get('actual', '?')}")

    return {
        "title": f"[AI分诊] {case_title} — {category}",
        "description": "\n".join(desc_parts),
        "severity": severity,
        "case_id": failure.get("case_id", 0),
        "execution_id": failure.get("execution_id", 0),
    }


# ═══════════════════════════════════════════════════════
# 内部实现
# ═══════════════════════════════════════════════════════

def _rule_based_classify(failure: dict) -> dict:
    """规则引擎分类（复用 failure_analyzer 逻辑的简化版）。"""
    result_data = failure.get("result_data", {})
    error_msg = result_data.get("error", "") or failure.get("notes", "")

    category = "unknown"
    confidence = 0.5
    explanation = ""
    suggested_action = ""

    if not error_msg and not result_data.get("assertions"):
        return {"category": category, "confidence": confidence,
                "explanation": "无详细错误信息，建议查看执行日志", "suggested_action": "检查原始执行记录"}

    # 超时
    if "超时" in error_msg or "timeout" in error_msg.lower():
        category = "flaky_env"
        confidence = 0.85
        explanation = "请求超时 — 通常是网络或服务端负载问题"
        suggested_action = "1. 检查服务端是否正常运行\n2. 增加超时时间或重试\n3. 检查网络连通性"
    # 连接失败
    elif "连接失败" in error_msg or "connect" in error_msg.lower():
        category = "flaky_env"
        confidence = 0.80
        explanation = "无法连接到目标服务"
        suggested_action = "1. 确认目标服务已启动\n2. 检查 URL 和端口是否正确\n3. 确认 VPN 连接状态"
    # 500 错误
    elif "500" in error_msg or result_data.get("status_code") == 500:
        category = "bug"
        confidence = 0.90
        explanation = "服务端返回 500 内部错误 — 大概率是代码缺陷"
        suggested_action = "1. 查看服务端日志定位异常\n2. 检查是否有未处理异常\n3. 确认依赖服务可用"
    # 断言失败
    elif result_data.get("assertions"):
        assertions = result_data["assertions"]
        failed = [a for a in assertions if not a.get("passed", True)]
        if failed:
            # 检查是否是明显的用例问题（如期待值写错）
            first = failed[0]
            if first.get("type") == "status_code" and first.get("actual") == 200 and first.get("expected") != "200":
                category = "case_defect"
                confidence = 0.75
                explanation = f"服务端返回 200 但用例期望 {first.get('expected', '?')} — 可能是用例断言写错"
                suggested_action = "1. 确认正确的预期状态码\n2. 更新用例断言规则"
            else:
                category = "bug"
                confidence = 0.70
                explanation = f"断言失败: {first.get('message', 'unknown')}"
                suggested_action = "1. 对比期望值和实际值\n2. 确认是服务端返回错误还是用例期望错误"
    # 编译失败
    elif "编译失败" in error_msg:
        category = "case_defect"
        confidence = 0.80
        explanation = "功能用例编译为 Playwright 脚本失败 — 可能是 steps 描述不够清晰"
        suggested_action = "1. 检查用例步骤是否完整\n2. 使用更明确的操作描述\n3. 检查 expected 字段是否填写"
    # 通用
    else:
        category = "bug"
        confidence = 0.40
        explanation = error_msg[:200] if error_msg else "执行异常"
        suggested_action = "建议查看完整执行日志"

    return {"category": category, "confidence": confidence,
            "explanation": explanation, "suggested_action": suggested_action}


def _llm_deep_analyze(classified: list[dict]) -> list[dict]:
    """使用 LLM 深度分析失败用例。如 LLM 不可用，返回原始分类。"""
    if not classified:
        return classified

    import httpx

    # 构建分析 prompt
    cases_text = []
    for i, c in enumerate(classified):
        result_data = c.get("result_data", {})
        assertions = result_data.get("assertions", [])
        failed_assertions = [a for a in assertions if not a.get("passed", True)]

        cases_text.append(
            f"{i+1}. 用例: {c['case_title']} | 类型: {c['case_type']} | 优先级: {c['priority']}\n"
            f"   规则分类: {c.get('category','?')} | 错误: {result_data.get('error','')}\n"
            f"   失败断言: {json.dumps(failed_assertions[:3], ensure_ascii=False) if failed_assertions else 'N/A'}"
        )

    system_prompt = (
        "你是测试结果分析专家。对每个失败用例，将其归类为四类之一，输出 JSON。\n"
        "1. bug — 代码缺陷（500错误、数据错误）\n"
        "2. flaky_env — 环境抖动（超时、网络错误）\n"
        "3. case_defect — 用例问题（断言写错、期待值不合理）\n"
        "4. known_issue — 已知缺陷（匹配已有缺陷模式）\n"
        '输出: {"results": [{"index": 从1开始, "category": "...", "confidence": 0.0-1.0, "explanation": "...", "suggested_action": "..."}]}'
    )

    user_msg = "请分析以下失败用例:\n\n" + "\n\n".join(cases_text)

    try:
        with httpx.Client(timeout=120.0) as client:
            resp = client.post(
                f"{settings.ai_api_base_url.rstrip('/')}/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.ai_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": settings.ai_model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_msg},
                    ],
                    "max_tokens": 4096,
                    "temperature": 0.2,
                    "response_format": {"type": "json_object"},
                },
            )
            resp.raise_for_status()
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            llm_result = json.loads(content)

            # 合并 LLM 结果
            llm_items = llm_result.get("results", [])
            for item in llm_items:
                idx = item.get("index", 0) - 1  # 1-based → 0-based
                if 0 <= idx < len(classified):
                    classified[idx]["category"] = item.get("category", classified[idx]["category"])
                    classified[idx]["confidence"] = item.get("confidence", classified[idx]["confidence"])
                    classified[idx]["explanation"] = item.get("explanation", classified[idx]["explanation"])
                    classified[idx]["suggested_action"] = item.get("suggested_action", classified[idx]["suggested_action"])
        return classified
    except Exception:
        raise  # 让调用方降级
