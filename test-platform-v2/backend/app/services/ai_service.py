"""AI service — call LLM with test-case-design skill context to generate test cases.

Changelog-first extraction pipeline for Lanhu URLs:
  1. Extract changelog (更新日志) pages → identify versions + update content
  2. Match changelog versions to folder structure → extract requirements per version
  3. Detect client scope (App/PC/Web) for each requirement via folder names + AI
  4. Stage 1: Feature extraction (modules + function points with client_scope)
  5. Stage 2: Generate functional test cases only (no API cases)
"""
from __future__ import annotations

import json
import asyncio
import logging
import re

_SESSION_ERROR_HINTS = ("认证", "Cookie", "会话", "登录", "418")


def _is_lanhu_session_error(exc: Exception) -> bool:
    """判定蓝湖会话失效类错误（Cookie 过期 / HTTP 418 被拒），避免被误当图片格式兜底。"""
    text = str(exc)
    return any(hint in text for hint in _SESSION_ERROR_HINTS)


logger = logging.getLogger(__name__)
from pathlib import Path

import httpx

from app.core.config import settings
from app.services import ai_errors
from app.services.ai_config_service import AIProviderUnconfiguredError, ai_config_service
from app.services.ai_errors import ai_health_registry
from app.services.external.lanhu_provider import _extract_lanhu_content  # 蓝湖提取已抽到 provider，委托调用


def _resolve_workspace_root() -> Path:
    """Resolve workspace root from config or auto-detect from this file's location."""
    if settings.workspace_root:
        return Path(settings.workspace_root)
    return Path(__file__).resolve().parent.parent.parent.parent.parent


def _skill_dir() -> Path:
    """Return the test-case-design skill directory."""
    if settings.skill_dir:
        return Path(settings.skill_dir)
    return _resolve_workspace_root() / ".claude" / "skills" / "test-case-design"



def _load_skill_context() -> str:
    """Load functional skill .md files and compose into a system prompt body.

    Only loads functional-testing files — API test case generation is handled
    separately via dedicated tooling.
    """
    return _load_skill_context_for("functional")


def _load_skill_context_for(kind: str) -> str:
    """Load skill files for a specific case type.

    kind = "functional": SKILL.md + case-template.md + functional-checklist.md
                         + 功能测试输出用例要求.md（权威输出要求，7 份功能用例文档）
    kind = "api":        api-checklist.md + 接口测试输出用例要求.md（权威输出要求，接口测试.xmind）
                         + 接口测试考虑点【辅助作用】.md（兜底）+ SKILL.md
    """
    standards_dir = _resolve_workspace_root() / "tests" / "test-case-standards"
    parts: list[str] = []

    if kind == "api":
        # 1) 权威输出要求：接口测试输出用例要求.md（skill 目录或规范中心）
        for fname in ["api-checklist.md", "接口测试输出用例要求.md", "接口测试考虑点【辅助作用】.md"]:
            fpath = _skill_dir() / fname
            if not fpath.exists():
                alt = standards_dir / fname
                if alt.exists():
                    fpath = alt
            if fpath.exists():
                parts.append(fpath.read_text(encoding="utf-8"))
        skill_fpath = _skill_dir() / "SKILL.md"
        if skill_fpath.exists():
            parts.append(skill_fpath.read_text(encoding="utf-8"))
        return "\n\n---\n\n".join(parts)

    # functional：SKILL.md + case-template.md + functional-checklist.md + 功能测试输出用例要求.md
    for fname in [
        "SKILL.md",
        "case-template.md",
        "functional-checklist.md",
        "功能测试输出用例要求.md",
    ]:
        fpath = _skill_dir() / fname
        if not fpath.exists():
            alt = standards_dir / fname
            if alt.exists():
                fpath = alt
        if fpath.exists():
            parts.append(fpath.read_text(encoding="utf-8"))
    return "\n\n---\n\n".join(parts)


def _build_system_prompt(kind: str = "functional") -> str:
    """Build the system prompt for functional test case generation.

    kind is kept for backward compatibility — all modes now generate
    functional test cases only. API test cases are generated separately.

    Phase 1: Extract & decompose requirements → analyze issues per point.
    Phase 2: Generate functional test cases based on the decomposed points.
    """
    skill_ctx = _load_skill_context_for("functional")

    output_schema = """{
  "requirement_analysis": {
    "extracted_requirements": [
      {
        "id": "REQ-1",
        "title": "功能点简短标题",
        "description": "详细的原始需求描述",
        "type": "functional",
        "issues": [
          {"severity": "high", "description": "问题描述", "suggestion": "改进建议"}
        ]
      }
    ],
    "overall_assessment": "对需求整体的完整性、清晰度评估（2-5 句话）"
  },
    "functional_cases": [
      {
        "title": "用例标题",
        "priority": "P0",
        "domain": "业务域",
        "module": "所属模块",
        "case_design_method": "等价类划分",
        "positive_negative": "positive",
        "test_data_note": "本用例使用的数据及其业务含义（禁止无意义占位值）",
        "preconditions": "前提条件",
        "steps": [{"step": 1, "desc": "操作描述", "expected": "该步预期结果"}],
        "expected_result": "整体预期结果",
        "remark": "备注（如正面/负面/边界用例）",
      "client_scope": ["app", "pc"]
    }
  ],
    "api_cases": [
      {
        "title": "接口用例标题",
        "priority": "P0",
        "domain": "业务域",
        "module": "所属模块",
        "api_method": "GET",
        "api_endpoint": "/api/v1/xxx",
        "api_headers": "{\"Content-Type\": \"application/json\"}",
        "api_body": "{\"page\": 1, \"size\": 20}",
        "api_assertions": "[{\"type\": \"status\", \"value\": 200}, {\"type\": \"field\", \"path\": \"data.records\", \"assert\": \"is_array\"}]",
        "case_design_method": "边界值分析",
        "positive_negative": "boundary",
        "test_data_note": "真实业务参数来源与含义说明",
        "preconditions": "前提条件",
        "expected_result": "预期结果（如返回 200 + 数据列表）",
        "remark": "关联的功能点 REQ ID"
    }
  ]
}"""

    focus_rule = "- 专注于生成**功能测试用例**。对于 type=integration 的功能点，同时在 api_cases 中生成对应接口用例建议。"
    kind_rules = (
        "- 覆盖度硬性要求：**每个功能点至少 2 条用例（1 条正向 + 1 条负向或边界）**，"
        "复杂状态机/多分支模块至少 3 条；宁多勿少，禁止合并相似行为导致漏测。\n"
        "- 用例数据要求：每条用例的输入数据必须**贴合业务语义**（可解释该值代表什么业务场景），"
        "禁止用无业务含义的占位值（如随机字符串 'abc'、随意数字 123）。\n"
        "- 对于 type=integration 的功能点，在 api_cases 数组中生成对应的接口测试用例，包含 api_method 和 api_endpoint（建议路径）。\n"
        "- 接口用例必须包含：api_body（请求参数，字段完整、值贴合真实业务）、"
        "api_assertions（断言：状态码 + 响应结构/关键字段 + 业务规则，如业务状态码、记录数/排序、"
        "核心字段非空、success=true、新增数据标识非空）、case_design_method、positive_negative。\n"
        "- 接口用例须覆盖「测试考虑点」辅助清单（见下方 skill_ctx 中的接口检查点）："
        "冒烟/场景串联、健壮性合法非法入参（含增加不存在参数）、安全（加密/越权/CSRF）、"
        "性能（低优先级）、数据入库一致性、稳定性、兼容性、监控告警。\n"
        "- 每个用例需标注 client_scope（适用的客户端：app/pc/web），"
        "如需求未明确指定则根据常识推断。"
    )

    return f"""你是一位资深的测试工程师。你的工作分为两个阶段：

**阶段一：需求提取与问题分析**
1. 仔细阅读需求内容，拆解出所有独立的功能点。
2. 对每个功能点分析潜在问题：需求是否清晰明确？是否有逻辑漏洞或矛盾？是否遗漏关键细节（边界条件、异常处理、权限控制、数据校验等）？
3. 给出整体评估，总结需求质量。

**阶段二：设计功能测试用例**
1. 基于阶段一拆解出的功能点，严格遵循以下团队测试用例设计规范，设计功能测试用例。
2. 每个功能点至少 2 条用例（1 条正向 + 1 条负向或边界），复杂模块 ≥3 条。
3. 综合运用等价类划分、边界值分析、场景法、错误推测等方法。
4. 用例输入数据必须贴合业务语义（明确该值代表的业务场景），禁止无意义占位值。
{focus_rule}

{skill_ctx}

输出格式要求：你 **必须** 返回一个严格的 JSON 对象，格式如下：

{output_schema}

字段说明：
- requirement_analysis.type: 可选值 "functional"(功能) / "ui"(界面) / "data"(数据) / "integration"(集成)
- requirement_analysis.issues[].severity: "high"(高优先级/逻辑漏洞) / "medium"(中优先级/模糊不清) / "low"(低优先级/建议优化)
- functional_cases[].priority: P0(关键路径/基本流) / P1(异常流/边界值) / P2(体验/界面)
- functional_cases[].case_design_method: 等价类划分 / 边界值分析 / 场景法 / 错误推测 / 组合覆盖
- functional_cases[].positive_negative: "positive"(正向) / "negative"(负向) / "boundary"(边界)
- functional_cases[].test_data_note: 说明本条用例输入数据的业务含义与来源（真实数据回填或按语义构造）
- functional_cases[].steps: 每个步骤含 step(序号), desc(操作描述), expected(该步预期)
- functional_cases[].client_scope: 该用例适用的客户端列表，可选值 "app" / "pc" / "web"
- api_cases[].api_method: HTTP 方法 "GET" / "POST" / "PUT" / "DELETE"
- api_cases[].api_endpoint: 建议的 API 路径（如 "/api/v1/matches"）
- api_cases[].api_body: 请求参数 JSON（字段完整、值贴合真实业务，禁止占位）
- api_cases[].api_assertions: 断言数组（状态码、响应结构/关键字段、业务规则）

关键规则：
- **先分析需求，再生成用例** — 阶段一完成后才能进入阶段二。
- 每个需求功能点至少 2 条用例（1 正向 + 1 负向或边界），复杂模块 ≥3 条。
- 每条用例都必须有 case_design_method 与 positive_negative，且 test_data_note 说明数据业务含义。
{kind_rules}
- steps 数组中每项必须包含 step, desc, expected 三个字段。
- 预期结果不可只写"成功""报错"，需含具体判断标准（如"数据库新增对应记录""返回 400 和错误提示"）。
- 只输出 JSON，不要用 markdown 代码块包裹。
- **JSON 转义规则**：字符串内双引号必须转义(\\")；反斜杠必须转义(\\\\)；换行必须转义(\\n)；中文引号请用「」或 ''，切勿在 JSON 字符串内使用未转义的 ASCII 双引号；结尾不可有多余逗号。"""


def _build_extraction_system_prompt() -> str:
    """Build system prompt for Stage 1: feature extraction (modules + function points only).

    Each function point now includes a 'client_scope' field indicating which
    client platforms (app/pc/web) the requirement applies to.
    """
    output_schema = """{
  "modules": [
    {
      "id": "MOD-1",
      "name": "模块名称",
      "description": "模块功能概述（1-3句话）",
      "function_points": [
        {
          "id": "FP-1",
          "title": "功能点简短标题",
          "description": "功能点详细描述（从需求文档中提取的原始需求）",
          "type": "functional",
          "client_scope": ["app", "pc"],
          "issues": [
            {"severity": "high", "description": "问题描述", "suggestion": "改进建议"}
          ]
        }
      ]
    }
  ],
  "overall_assessment": "对需求整体的完整性、清晰度评估（3-5句话）"
}"""

    skill_ctx = _load_skill_context_for("functional")

    return f"""你是一位资深的测试工程师。你的任务是：**仔细阅读需求文档，将其完整、详尽地拆分为测试模块和测试功能点，并对每个功能点进行需求质量分析。**

核心原则：**穷尽提取，宁多勿少。** 需求文档中提到的每一个功能、每一个交互行为、每一个业务规则、每一个边界条件、每一个UI状态变化，都应被提取为独立的功能点。不要概括、不要合并、不要因为觉得「太细节」而跳过。

工作步骤：
1. **整体理解**：通读需求文档，理解业务场景和功能范围。识别所有的用户角色、业务流程、系统交互和涉及的客户端（App端/PC端/Web端）。
2. **模块拆分**：将需求按功能域或业务流程拆分为若干个「测试模块」。每个模块应是一个独立的功能单元（如「活动配置管理」「用户参与流程」「奖励发放」等）。模块数量不限，覆盖文档中所有功能域。
3. **客户端范围识别**：对每个功能点，判断其适用的客户端范围（client_scope）：
   - "app" — 移动 App 端
   - "pc" — 桌面 PC 端
   - "web" — Web/H5 端
   - 如果文档明确标注了适用端，严格按文档标注；如果文档有文件夹/标题提示（如「App端」「PC端」），按其分组判断；如果没有明确说明，根据功能性质合理推断（如「扫码」通常是 app，「拖拽上传」通常是 pc/web）
   - 三端通用的功能点标记为 ["app", "pc", "web"]
4. **功能点提取（最关键步骤）**：在每个模块下，**穷尽地**提取出所有独立的、可验证的「功能点」。功能点应是具体的、可测试的需求条目。
   - 每个页面/界面元素的状态变化都是一个功能点
   - 每个用户操作及其反馈都是一个功能点
   - 每个业务规则/判定逻辑都是一个功能点
   - 每个数据展示/更新场景都是一个功能点
   - 每个角色/权限差异都是一个功能点
   - **每个模块至少提取 4 个功能点**；对于复杂的业务模块，应提取 8-15 个功能点
   - 示例：「配置活动时间范围」「用户提交猜测选项」「判定猜测结果」「活动结束时自动发放奖励」「主播表演阶段UI展示」「猜测阶段倒计时展示」「用户多次提交的限制」「猜对率低于60%时的特殊奖励判定」
5. **问题分析**：对每个功能点，分析潜在的需求问题：
   - 需求是否清晰明确？是否有歧义？
   - 是否有逻辑漏洞或矛盾？
   - 是否遗漏关键细节（边界条件、异常处理、权限控制、数据校验等）？
   - 与其他功能点是否有冲突？
   - **多端一致性**：如果标记为多端适用，不同端之间是否有差异未明确？
6. **整体评估**：给出对需求文档整体的评估，包括完整性、清晰度、可测试性、多端覆盖情况。

{skill_ctx}

输出格式要求：你 **必须** 返回一个严格的 JSON 对象，格式如下：

{output_schema}

字段说明：
- modules[].id: 模块编号，格式 "MOD-1", "MOD-2"...
- modules[].name: 模块的中文名称，简洁明了
- modules[].description: 模块功能概述（1-3句话）
- modules[].function_points[].id: 功能点编号，格式 "FP-1", "FP-2"...
- modules[].function_points[].title: 功能点简短标题（10字以内）
- modules[].function_points[].description: 从需求文档中提取的详细描述
- modules[].function_points[].type: 可选值 "functional"(功能) / "ui"(界面) / "data"(数据) / "integration"(集成)
- modules[].function_points[].client_scope: 字符串数组，可选值 "app" / "pc" / "web"，表示该功能点适用的客户端。至少包含一个值。
- modules[].function_points[].issues[].severity: "high"(高优先级/逻辑漏洞) / "medium"(中优先级/模糊不清) / "low"(低优先级/建议优化)

关键规则：
- 模块和功能点数量不做硬性限制。**宁多勿少**，宁可多提取也不要遗漏。
- 每个模块至少包含 4 个功能点；复杂模块应包含 8-15 个。
- 功能点必须具体可测试，避免抽象笼统的描述。标题必须是可以独立验证的动作或规则。
- 每个功能点至少分析 1 个潜在问题（即使需求很完善，也应提出边界场景的考虑）。
- **每个功能点必须填写 client_scope**，至少包含一个端。
- 只返回 JSON，不要用 markdown 代码块包裹。
- 字符串内双引号必须转义(\\")；反斜杠必须转义(\\\\)；换行必须转义(\\n)。
- 结尾不可有多余逗号。"""


def _build_user_message_with_extraction(content: str, file_type: str, source_ref: str,
                                        extraction: dict) -> str:
    """Build user message for Stage 2: guided test case generation with confirmed extraction."""
    parts = ["请根据以下已确认的测试模块和功能点，设计完整的功能测试用例（仅功能用例，不需要接口用例）。"]

    modules = extraction.get("modules", [])
    overall = extraction.get("overall_assessment", "")

    # Build structured extraction summary
    extraction_lines = ["\n## 已确认的测试模块与功能点\n"]

    # C115：生成前注入知识中心关联基座（模块→接口/后台/konfi），先按关联定位再产出用例
    try:
        from app.services.association_baseline import association_context
        association_lines = []
        for mod in modules:
            ctx = association_context(str(mod.get("name") or ""))
            if ctx:
                association_lines.append(ctx)
        if association_lines:
            extraction_lines.append("")
            extraction_lines.append("## 模块-接口-功能关联基座（生成前按关联定位）")
            extraction_lines.extend(association_lines)
    except Exception as exc:
        logger.warning("关联基座构建失败，继续基础提取: %s", exc)
    for mod in modules:
        mod_id = mod.get("id", "")
        mod_name = mod.get("name", "")
        mod_desc = mod.get("description", "")
        extraction_lines.append(f"### {mod_id}: {mod_name}")
        if mod_desc:
            extraction_lines.append(f"  概述: {mod_desc}")
        extraction_lines.append("")
        for fp in mod.get("function_points", []):
            fp_id = fp.get("id", "")
            fp_title = fp.get("title", "")
            fp_desc = fp.get("description", "")
            fp_type = fp.get("type", "functional")
            fp_clients = fp.get("client_scope", [])
            client_tag = f" [{'/'.join(fp_clients)}]" if fp_clients else ""
            extraction_lines.append(f"  - [{fp_id}] {fp_title} (类型: {fp_type}){client_tag}")
            if fp_desc:
                extraction_lines.append(f"    描述: {fp_desc}")
        extraction_lines.append("")

    if overall:
        extraction_lines.append(f"需求整体评估: {overall}\n")

    parts.append("\n".join(extraction_lines))

    # Include original content for reference (truncated)
    parts.append(f"\n## 原始需求内容（供参考）\n\n{content[:8000]}")

    parts.append(
        "\n\n请严格基于上述已确认的模块和功能点生成功能测试用例。"
        "\n对每个功能点至少生成 1 条正面用例 + 1 条负面用例。"
        "\n按照系统提示中的测试用例设计规范执行。"
        "\n注意：只生成功能测试用例，api_cases 必须为空数组 []。"
    )

    return "\n\n".join(parts)




# ── User Message Construction ────────────────────────────────

def _build_user_message(content: str, file_type: str, source_ref: str,
                        page_filtered: bool = False, folder_name: str = "",
                        changelog: dict | None = None,
                        client_scope: list[str] | None = None) -> str:
    """Build the user message with requirement content.

    For Lanhu URLs, includes changelog and client scope context when available.
    """
    parts = ["请根据以下需求内容设计完整的功能测试用例（仅功能用例，不需要接口用例）。"]
    clients = client_scope or []

    if file_type == "lanhu":
        extraction_success = (
            content and content != source_ref
            and "蓝湖设计稿「" in content
            and ("内容提取：" in content or "模块提取：" in content
                 or "版本化提取：" in content)
            and "内容提取失败" not in content
        )
        version_aware = (
            extraction_success
            and "版本化提取：" in content
        )
        has_changelog = (
            extraction_success
            and "版本更新日志" in content
        )

        if extraction_success:
            if has_changelog:
                parts.append(
                    "以下是从蓝湖设计稿中提取的需求内容。"
                    "文档开头包含「版本更新日志」部分，其中记录了各版本的更新内容，"
                    "请先阅读更新日志了解版本变更范围，再针对各版本的需求进行功能拆分。"
                    "每个「## 版本: xxx」对应一个独立的产品版本。"
                )
                if clients:
                    parts.append(
                        f"检测到涉及以下客户端: {'/'.join(clients)}。"
                        f"请识别每个功能点具体适用于哪些端，并在 client_scope 中标注。"
                    )
                parts.append("\n" + content)
            elif version_aware:
                parts.append(
                    "以下是从蓝湖设计稿中按版本提取的需求内容。"
                    "每个「## 版本: xxx」对应一个独立的产品版本。"
                    "请优先针对各版本分别进行功能拆分和需求分析，"
                    "同时关注版本间的差异和兼容性需求。"
                )
                if clients:
                    parts.append(
                        f"检测到涉及以下客户端: {'/'.join(clients)}。"
                        f"请识别每个功能点具体适用于哪些端。"
                    )
                parts.append("\n" + content)
            elif page_filtered:
                parts.append(
                    f"以下是从蓝湖设计稿的「{folder_name}」模块提取的文档内容，"
                    f"请针对该模块设计功能测试用例。"
                )
                if clients:
                    parts.append(f"该模块涉及客户端: {'/'.join(clients)}。")
                parts.append("\n" + content)
            else:
                parts.append(
                    "以下是从蓝湖设计稿中提取的文档内容。"
                    "请优先关注需求描述、功能规格、交互逻辑等实质性内容，"
                    "忽略版本号、日期、人员等元数据信息。"
                )
                if clients:
                    parts.append(
                        f"检测到涉及以下客户端: {'/'.join(clients)}。"
                        f"请在功能拆分时标注每个功能点的 client_scope。"
                    )
                parts.append("\n" + content)
        else:
            error_detail = content if (content and content != source_ref) else "蓝湖设计稿内容未能提取，请检查蓝湖链接是否正确、Cookie 是否有效，或稍后重试。"
            raise ValueError(error_detail[:500])
    elif file_type == "xlsx":
        parts.append(f"Excel 文档内容:\n\n{content}")
    else:
        parts.append(f"需求文档内容:\n\n{content}")

    if page_filtered:
        parts.append(
            "\n请先对需求进行拆解，提取出每个独立的功能点，并对每个功能点进行问题分析"
            "（需求是否清晰、是否有逻辑漏洞、是否有遗漏细节）。然后基于拆解出的需求点，"
            "按照系统提示中的测试用例设计规范，生成功能测试用例。"
            "\n\n注意：该模块内容量适中，请确保用例覆盖所有功能点，"
            "可适当放宽用例数量上限（功能用例 15-25 条）。"
        )
    else:
        parts.append(
            "\n请先对需求进行拆解，提取出每个独立的功能点，并对每个功能点进行问题分析"
            "（需求是否清晰、是否有逻辑漏洞、是否有遗漏细节）。然后基于拆解出的需求点，"
            "按照系统提示中的测试用例设计规范，生成功能测试用例。"
        )
    return "\n\n".join(parts)


# ── JSON Repair Utilities ────────────────────────────────────

def _repair_llm_json(text: str) -> str:
    """Repair common JSON formatting issues from LLM output."""
    text = re.sub(r",(\s*[}\]])", r"\1", text)

    STRUCTURAL_AFTER = set(":,\\}]")
    result: list[str] = []
    i = 0
    n = len(text)
    while i < n:
        ch = text[i]
        if ch == '"':
            result.append('"')
            j = i + 1
            escaped = False
            while j < n:
                c = text[j]
                if escaped:
                    escaped = False
                    result.append(c)
                    j += 1
                    continue
                if c == '\\':
                    escaped = True
                    result.append(c)
                    j += 1
                    continue
                if c == '"':
                    k = j + 1
                    while k < n and text[k] in ' \t':
                        k += 1
                    if k >= n or text[k] in STRUCTURAL_AFTER:
                        result.append('"')
                        i = k if k < n else n
                        break
                    else:
                        result.append('\\"')
                        j += 1
                        continue
                if c == '\n':
                    result.append('\\n')
                    j += 1
                    continue
                if c == '\r':
                    result.append('\\r')
                    j += 1
                    continue
                if c == '\t':
                    result.append('\\t')
                    j += 1
                    continue
                result.append(c)
                j += 1
            else:
                i = n
        else:
            result.append(ch)
            i += 1
    return "".join(result)


def _iterative_json_repair(text: str, max_attempts: int = 15) -> dict:
    """Iteratively fix JSON syntax errors one at a time."""
    for _ in range(max_attempts):
        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            pos = e.pos
            msg = e.msg

            if "Expecting ',' delimiter" in msg:
                text = text[:pos] + ", " + text[pos:]
            elif "Expecting ':' delimiter" in msg:
                text = text[:pos] + ": " + text[pos:]
            elif "Expecting value" in msg:
                text = text[:pos] + "null" + text[pos:]
            elif "Expecting property name" in msg or "Expecting property name enclosed in double quotes" in msg:
                prev_pos = pos - 1
                while prev_pos > 0 and text[prev_pos] in " \t\n\r":
                    prev_pos -= 1
                if prev_pos > 0 and text[prev_pos] == ",":
                    text = text[:prev_pos] + text[prev_pos + 1:]
            elif "Invalid control character" in msg:
                ch = text[pos]
                esc = {"\n": "\\n", "\r": "\\r", "\t": "\\t"}.get(ch)
                if esc:
                    text = text[:pos] + esc + text[pos + 1:]
                else:
                    text = text[:pos] + " " + text[pos + 1:]
            elif "Unterminated string" in msg:
                text = text[:pos] + '"' + text[pos:]
            elif "Extra data" in msg:
                text = text[:pos]
            else:
                break

    return json.loads(text)


def _pre_repair_truncated_json(text: str) -> str:
    """Fix common truncation issues in AI-generated JSON before structural parsing."""
    last_line = text.split("\n")[-1] if "\n" in text else text[-200:]
    in_str = False
    escaped = False
    for c in last_line:
        if escaped:
            escaped = False
            continue
        if c == '\\':
            escaped = True
            continue
        if c == '"':
            in_str = not in_str
    if in_str:
        text = text + '"'

    balance: list[str] = []
    in_str = False
    escaped = False
    for c in text:
        if escaped:
            escaped = False
            continue
        if c == '\\' and in_str:
            escaped = True
            continue
        if c == '"':
            in_str = not in_str
            continue
        if in_str:
            continue
        if c in ('{', '['):
            balance.append(c)
        elif c == '}':
            if balance and balance[-1] == '{':
                balance.pop()
        elif c == ']':
            if balance and balance[-1] == '[':
                balance.pop()

    closers = {'{': '}', '[': ']'}
    suffix = ''.join(closers[b] for b in reversed(balance))
    return text + suffix


def _salvage_json_parts(text: str) -> dict | None:
    """Last-resort salvage: extract well-formed sub-arrays/objects from broken JSON."""
    result: dict = {
        "requirement_analysis": {"extracted_requirements": [], "overall_assessment": ""},
        "functional_cases": [],
        "api_cases": [],
    }

    text = _pre_repair_truncated_json(text)

    for key in ("functional_cases", "api_cases"):
        pattern = rf'"{key}"\s*:\s*\['
        m = re.search(pattern, text)
        if not m:
            continue
        start = m.end() - 1
        depth = 0
        end = start
        in_str = False
        escaped = False
        for j in range(start, len(text)):
            c = text[j]
            if escaped:
                escaped = False
                continue
            if c == '\\' and in_str:
                escaped = True
                continue
            if c == '"':
                in_str = not in_str
                continue
            if in_str:
                continue
            if c == '[':
                depth += 1
            elif c == ']':
                depth -= 1
                if depth == 0:
                    end = j + 1
                    break
        if end == start and depth > 0:
            end = len(text)
        if end > start:
            array_text = text[start:end]
            try:
                try:
                    arr = json.loads(array_text)
                except json.JSONDecodeError:
                    arr = json.loads(_repair_llm_json(array_text))
                if isinstance(arr, list):
                    result[key] = arr
            except (json.JSONDecodeError, ValueError):
                continue

    pattern = r'"requirement_analysis"\s*:\s*\{'
    m = re.search(pattern, text)
    if m:
        start = m.end() - 1
        depth = 0
        end = start
        in_str = False
        escaped = False
        for j in range(start, len(text)):
            c = text[j]
            if escaped:
                escaped = False
                continue
            if c == '\\' and in_str:
                escaped = True
                continue
            if c == '"':
                in_str = not in_str
                continue
            if in_str:
                continue
            if c == '{':
                depth += 1
            elif c == '}':
                depth -= 1
                if depth == 0:
                    end = j + 1
                    break
        if end == start and depth > 0:
            end = len(text)
        if end > start:
            obj_text = text[start:end]
            try:
                try:
                    obj = json.loads(obj_text)
                except json.JSONDecodeError:
                    obj = json.loads(_repair_llm_json(obj_text))
                if isinstance(obj, dict):
                    result["requirement_analysis"] = obj
            except (json.JSONDecodeError, ValueError):
                logger.warning("requirement_analysis JSON 解析失败，跳过该字段")

    if result["functional_cases"] or result["api_cases"]:
        return result
    return None


# ── AI API Call ──────────────────────────────────────────────

def _dump_failed_ai_response(raw: str, prefix: str) -> None:
    """把无法解析的原始响应落到服务端临时目录，仅记日志。

    P1-4：路径**不得**出现在用户可见错误里——用户无权访问服务器文件系统，
    暴露路径既无用又是信息泄露。
    """
    if not raw:
        return
    import tempfile
    import time

    dump_path = Path(tempfile.gettempdir()) / f"{prefix}_{int(time.time())}.json"
    try:
        dump_path.write_text(raw, encoding="utf-8")
        logger.warning("[ai_service] raw response dumped to %s", dump_path)
    except OSError as exc:  # 落盘失败不影响主流程
        logger.warning("[ai_service] failed to dump raw response: %s", exc)


async def _call_ai_api(db, project_id: int, system_prompt: str, user_message: str,
                       label: str = "", max_tokens: int | None = None) -> dict:
    """Make a single AI API call and return the parsed result."""
    try:
        cfg = ai_config_service.resolve(db, project_id)
    except AIProviderUnconfiguredError as exc:
        ai_health_registry.record_failure(project_id, exc)
        return {"result": None, "raw": "", "finish_reason": "error", "truncated": False,
                "error": str(exc), "error_kind": ai_errors.UNCONFIGURED}

    effective_max_tokens = max_tokens if max_tokens is not None else settings.ai_max_tokens

    try:
        async with httpx.AsyncClient(timeout=180.0) as client:
            resp = await client.post(
                f"{cfg.api_base_url.rstrip('/')}/chat/completions",
                headers={
                    "Authorization": f"Bearer {cfg.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": cfg.model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_message},
                    ],
                    "max_tokens": effective_max_tokens,
                    "temperature": settings.ai_temperature,
                    "response_format": {"type": "json_object"},
                },
            )
            resp.raise_for_status()
            data = resp.json()
            choice = data["choices"][0]
            raw = choice["message"]["content"]
            finish_reason = choice.get("finish_reason", "unknown")
            truncated = finish_reason == "length"

            if truncated:
                logger.warning("[ai_service] WARNING: %s response truncated (finish_reason=length, raw_length=%d chars)", label, len(raw))

            try:
                result = _parse_ai_response(raw)
                ai_health_registry.record_success(project_id, getattr(cfg, "provider_id", None))
                return {"result": result, "raw": raw, "finish_reason": finish_reason,
                        "truncated": truncated, "error": None, "error_kind": None}
            except ValueError as parse_err:
                if truncated:
                    salvaged = _salvage_json_parts(raw)
                    if salvaged is not None:
                        logger.warning("[ai_service] Salvaged partial data from truncated %s response", label)
                        ai_health_registry.record_success(project_id, getattr(cfg, "provider_id", None))
                        return {"result": salvaged, "raw": raw, "finish_reason": finish_reason,
                                "truncated": True, "error": None, "error_kind": None}
                # 真正的解析失败：提供方连得上，只是内容不合法。
                return {"result": None, "raw": raw, "finish_reason": finish_reason,
                        "truncated": truncated, "error": str(parse_err),
                        "error_kind": ai_errors.BAD_RESPONSE}
    except Exception as e:
        # 传输/鉴权/限流等失败——**不得**再被上层当作「JSON 格式异常」。
        # 用 getattr 取提供方标识：健康态登记是旁路观测，不应因配置对象形状
        # （测试替身 / 未来字段调整）而反过来把主流程打挂。
        provider_id = getattr(cfg, "provider_id", None)
        provider_name = getattr(cfg, "provider_name", "") or ""
        kind = ai_errors.classify_ai_error(e)
        logger.warning("[ai_service] %s call failed (kind=%s): %s", label or "ai", kind, e)
        ai_health_registry.record_failure(project_id, e, provider_id, provider_name)
        return {"result": None, "raw": "", "finish_reason": "error", "truncated": False,
                "error": ai_errors.humanize_ai_error(e, provider_name), "error_kind": kind}


def _merge_split_results(func_result: dict | None, api_result: dict | None,
                          req_analysis: dict | None = None) -> dict:
    """Merge results from split calls into a single response.

    Simplified — only functional cases are generated. api_cases is always empty.
    Kept for backward compatibility with any remaining split-call paths.
    """
    merged: dict = {
        "requirement_analysis": {"extracted_requirements": [], "overall_assessment": ""},
        "functional_cases": [],
        "api_cases": [],
    }

    for source in [req_analysis, func_result]:
        if source and isinstance(source.get("requirement_analysis"), dict):
            merged["requirement_analysis"] = source["requirement_analysis"]
            break

    if func_result and isinstance(func_result.get("functional_cases"), list):
        merged["functional_cases"] = func_result["functional_cases"]

    return merged


# C68-3: 分批生成常量与工具（batch-69）
_CHUNK_FP_LIMIT = 12  # Batch 103: 每用例新增设计字段后调小分块，避免输出截断导致覆盖缺口
_CHUNK_CONCURRENCY = 5  # Batch 125: 全量模块生成提速（DeepSeek 并发安全范围内）


def _split_extraction_chunks(
    extraction: dict | None, limit: int = _CHUNK_FP_LIMIT
) -> list[list[dict]]:
    """按功能点数量把 extraction.modules 拆成多块，保证每块 FP 数 <= limit。"""
    modules = (extraction or {}).get("modules") or []
    chunks: list[list[dict]] = []
    current: list[dict] = []
    count = 0
    for mod in modules:
        fps = mod.get("function_points") or []
        if len(fps) > limit:
            if current:
                chunks.append(current)
                current, count = [], 0
            for i in range(0, len(fps), limit):
                chunks.append([{**mod, "function_points": fps[i:i + limit]}])
            continue
        if count + len(fps) > limit and current:
            chunks.append(current)
            current, count = [], 0
        current.append(mod)
        count += len(fps)
    if current:
        chunks.append(current)
    return chunks


def _dedupe_and_renumber(cases: list[dict], start: int = 1) -> list[dict]:
    """按 title 去重并重新编号，保证 id 唯一。"""
    seen: set[str] = set()
    out: list[dict] = []
    idx = start
    for c in cases:
        key = (c.get("title") or "").strip()
        if not key or key in seen:
            continue
        seen.add(key)
        c = dict(c)
        c["id"] = f"TC-{idx:03d}"
        idx += 1
        out.append(c)
    return out


def _parse_ai_response(raw: str) -> dict:
    """Extract JSON from AI response, handling common formatting issues."""
    text = raw.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        if len(lines) > 1:
            text = "\n".join(lines[1:])
        if text.endswith("```"):
            text = text[:-3].strip()
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        text = text[start:end + 1]

    try:
        result = json.loads(text)
    except json.JSONDecodeError as e1:
        try:
            repaired = _repair_llm_json(text)
            result = json.loads(repaired)
        except json.JSONDecodeError:
            try:
                result = _iterative_json_repair(repaired)
            except json.JSONDecodeError as e3:
                salvaged = _salvage_json_parts(repaired)
                if salvaged is not None:
                    result = salvaged
                else:
                    char_pos = e1.pos if e1.pos else e3.pos
                    context_start = max(0, (char_pos or 0) - 200)
                    context_end = min(len(text), (char_pos or 0) + 200)
                    snippet = text[context_start:context_end]
                    snippet = snippet.replace("\n", "\\n").replace("\r", "\\r")
                    raise ValueError(
                        f"AI 返回的 JSON 格式异常，无法解析。\n"
                        f"原始错误: {e1.msg} (行 {e1.lineno}, 列 {e1.colno})\n"
                        f"修复后错误: {e3.msg} (行 {e3.lineno}, 列 {e3.colno})\n"
                        f"错误位置附近内容 (chars {context_start}-{context_end}):\n{snippet}"
                    )

    result.setdefault("requirement_analysis", {"extracted_requirements": [], "overall_assessment": ""})
    result.setdefault("functional_cases", [])
    result.setdefault("api_cases", [])
    analysis = result.get("requirement_analysis")
    if not isinstance(analysis, dict):
        result["requirement_analysis"] = {"extracted_requirements": [], "overall_assessment": ""}
    else:
        analysis.setdefault("extracted_requirements", [])
        analysis.setdefault("overall_assessment", "")
    return result


# ── batch-167: 大文档分块提取与合并 ─────────────────────────

_EXTRACT_CHUNK_CHARS = 24000


def _split_content_chunks(content: str, size: int = _EXTRACT_CHUNK_CHARS) -> list[str]:
    """按段落聚合成不超过 size 字符的块，尽量在标题边界断开。"""
    if len(content) <= size:
        return [content]
    chunks: list[str] = []
    current: list[str] = []
    current_len = 0
    for para in re.split(r"\n\s*\n", content):
        para_len = len(para) + 2
        if current and current_len + para_len > size:
            chunks.append("\n\n".join(current))
            current = []
            current_len = 0
        current.append(para)
        current_len += para_len
    if current:
        chunks.append("\n\n".join(current))
    return chunks or [content]


def _extract_chunk_message(chunk: str, index: int, total: int) -> str:
    return (
        f"以下为同一份需求文档的第 {index}/{total} 部分（局部内容）。"
        f"只提取本部分明确出现的测试模块与功能点，输出 JSON 格式与系统提示一致，"
        f"不要跨部分臆造功能点。\n\n{chunk}"
    )


async def _extract_in_chunks(db, project_id: int, content: str, system_prompt: str) -> list[dict]:
    chunks = _split_content_chunks(content)
    results: list[dict] = []
    for index, chunk in enumerate(chunks, start=1):
        resp = await _call_ai_api(
            db,
            project_id,
            system_prompt,
            _extract_chunk_message(chunk, index, len(chunks)),
            f"extraction-chunk-{index}",
            max_tokens=max(settings.ai_max_tokens, 16384),
        )
        if resp["result"] is not None:
            results.append(resp["result"])
    return results


def _merge_extractions(results: list[dict]) -> dict:
    """合并多块提取结果：模块按名去重、功能点按标题去重并重新编号。"""
    modules: list[dict] = []
    seen_modules: dict[str, int] = {}
    seen_fps: set[str] = set()
    fp_counter = 0
    overall = ""
    for result in results:
        for mod in (result.get("modules") or []):
            if not isinstance(mod, dict):
                continue
            name = str(mod.get("name") or "").strip()
            key = name.lower()
            if not key:
                continue
            if key in seen_modules:
                target = modules[seen_modules[key]]
            else:
                seen_modules[key] = len(modules)
                modules.append({"id": "", "name": name, "description": "", "function_points": []})
                target = modules[-1]
            target["description"] = target.get("description") or mod.get("description") or ""
            for fp in (mod.get("function_points") or []):
                if not isinstance(fp, dict):
                    continue
                title = str(fp.get("title") or fp.get("id") or "").strip()
                sig = f"{key}:{title.lower()}"
                if not title or sig in seen_fps:
                    continue
                seen_fps.add(sig)
                fp_counter += 1
                copy = dict(fp)
                copy["id"] = f"FP-{fp_counter}"
                target["function_points"].append(copy)
        if not overall:
            overall = str(result.get("overall_assessment") or "").strip()

    for index, mod in enumerate(modules, start=1):
        mod["id"] = f"MOD-{index}"
    if not modules:
        modules = [{
            "id": "MOD-1",
            "name": "待人工补充模块",
            "description": "分块提取未能获得有效模块",
            "function_points": [],
        }]
    return {
        "modules": modules,
        "overall_assessment": overall or "分块提取完成，请复核模块合并结果。",
    }
# ── Public API: Stage 1 — Feature Extraction ─────────────────

def _build_local_extraction_fallback(
    content: str,
    error_detail: str,
    source_ref: str,
    client_scope: list[str] | None = None,
) -> dict:
    """Build a deterministic review draft when the external classifier is unavailable.

    The fallback deliberately keeps one source line per function point instead of
    inventing requirements.  Reviewers can therefore continue the workflow while
    clearly seeing that the result still needs human confirmation.
    """
    lines: list[str] = []
    for raw_line in content.splitlines():
        cleaned = re.sub(r"^[\s#>*+\-\d.、（）()]+", "", raw_line).strip()
        if cleaned and cleaned not in lines:
            lines.append(cleaned)

    if not lines:
        lines = ["需求内容待人工补充"]

    scopes = client_scope or ["app", "pc", "web"]
    function_points = [
        {
            "id": f"FP-{index}",
            "title": line[:20],
            "description": line,
            "type": "functional",
            "client_scope": scopes,
            "issues": [
                {
                    "severity": "medium",
                    "description": "外部 AI 暂不可用，本条由本地规则提取",
                    "suggestion": "生成正式测试用例前请人工确认功能边界和异常规则",
                }
            ],
        }
        for index, line in enumerate(lines[:100], start=1)
    ]
    return {
        "modules": [
            {
                "id": "MOD-1",
                "name": "本地降级提取",
                "description": "按原文非空行生成的待评审功能草稿",
                "function_points": function_points,
            }
        ],
        "overall_assessment": "外部 AI 调用失败，已生成不扩写原文的本地待评审草稿。",
        "fallback_used": True,
        "fallback_reason": error_detail,
        "source_ref": source_ref,
        "extraction_progress": 1.0,
    }


async def extract_features(db, project_id: int, content: str, file_type: str = "", source_ref: str = "") -> dict:
    """Stage 1: Extract test modules and function points from requirement content.

    For Lanhu URLs, uses the changelog-first extraction pipeline:
    1. Extract changelog pages to identify versions and update content
    2. Match versions to folders → extract requirements per version
    3. Detect client scope (App/PC/Web)
    4. AI decomposes into modules + function points (with client_scope)

    Returns dict with keys: modules, overall_assessment, extraction_summary,
    changelog, client_scope.
    """
    try:
        ai_config_service.resolve(db, project_id)
    except AIProviderUnconfiguredError as exc:
        raise ValueError(str(exc)) from exc

    effective_content = content
    extraction_summary = ""
    page_filtered = False
    folder_name = ""
    effective_file_type = file_type
    changelog_info = None
    client_scope: list[str] = []

    if file_type == "lanhu" and source_ref:
        try:
            extract_result = await _extract_lanhu_content(source_ref)
            extracted = extract_result["content"]
            if extracted:
                effective_content = extracted
                page_filtered = extract_result.get("page_filtered", False)
                folder_name = extract_result.get("folder_name", "")
                changelog_info = extract_result.get("changelog")
                client_scope = extract_result.get("client_scope", [])
                first_line_end = extracted.find("\n")
                if first_line_end > 0:
                    extraction_summary = extracted[:first_line_end].strip()
                else:
                    extraction_summary = "蓝湖设计稿内容已提取"
        except ValueError as ve:
            if _is_lanhu_session_error(ve):
                # Batch 133：蓝湖会话失效是真实失败，不得伪装成"图片格式"兜底完成
                raise ValueError(
                    "蓝湖会话已失效（Cookie 过期或 HTTP 418 被拒）。"
                    "请重新登录蓝湖后粘贴新 Cookie，或联系管理员更新 LANHU_COOKIE。"
                ) from ve
            if content and content != source_ref and len(content) > len(source_ref) + 10:
                effective_file_type = ""
                extraction_summary = "蓝湖原型页面为图片格式，已使用补充说明文字作为需求内容"
            else:
                raise ValueError(
                    "蓝湖原型页面为图片格式（Axure 导出），无法自动提取文本内容。"
                    "请在提交蓝湖链接时，在「补充说明」中描述原型的页面功能、交互逻辑和业务规则，"
                    "AI 将基于文字描述生成测试用例。"
                )

    user_message = _build_user_message(effective_content, effective_file_type, source_ref,
                                       page_filtered=page_filtered, folder_name=folder_name,
                                       changelog=changelog_info, client_scope=client_scope)
    extraction_instruction = (
        "\n\n请对上述需求内容进行**完整的、穷尽的**模块拆分和功能点提取。"
        "\n\n重要原则："
        "\n- 穷尽提取文档中提到的每一个功能、交互、业务规则和边界条件，不要遗漏任何细节"
        "\n- 不要概括、不要合并相似功能点——每个独立的可验证行为都应是单独的功能点"
        "\n- 每个模块至少提取 4 个功能点，复杂业务模块应提取 8-15 个"
        "\n- 每个页面的每个UI状态变化、每个用户操作及反馈、每个数据展示场景都应被提取"
        "\n- 对每个功能点分析至少 1 个潜在需求问题"
        "\n- **每个功能点必须标注 client_scope（app/pc/web），指明适用的客户端**"
        "\n\n只输出模块和功能点的 JSON，不要生成测试用例。"
    )
    user_message = user_message.rsplit("\n\n", 1)[0] + extraction_instruction

    system_prompt = _build_extraction_system_prompt()

    # batch-167: 大文档直接分块提取，避免单次调用截断丢功能点
    if len(effective_content) >= _EXTRACT_CHUNK_CHARS:
        merged = _merge_extractions(await _extract_in_chunks(db, project_id, effective_content, system_prompt))
        merged["extraction_meta"] = {
            "mode": "chunked",
            "chunks": len(_split_content_chunks(effective_content)),
            "truncated": False,
            "fallback": False,
            "warnings": [],
        }
        if extraction_summary:
            merged["extraction_summary"] = extraction_summary
        if changelog_info:
            merged["changelog"] = changelog_info
        if client_scope:
            merged["client_scope"] = client_scope
        return merged

    extraction_max_tokens = max(settings.ai_max_tokens * 2, 32768)
    resp = await _call_ai_api(db, project_id, system_prompt, user_message, "extraction",
                              max_tokens=extraction_max_tokens)
    if resp["result"] is None and resp.get("truncated"):
        merged = _merge_extractions(await _extract_in_chunks(db, project_id, effective_content, system_prompt))
        merged["extraction_meta"] = {
            "mode": "chunked",
            "chunks": len(_split_content_chunks(effective_content)),
            "truncated": True,
            "fallback": False,
            "warnings": ["单次提取被截断，已自动改为分块提取"],
        }
        if extraction_summary:
            merged["extraction_summary"] = extraction_summary
        if changelog_info:
            merged["changelog"] = changelog_info
        if client_scope:
            merged["client_scope"] = client_scope
        return merged
    if resp["result"] is None:
        error_detail = resp.get("error", "未知错误")
        raw = resp.get("raw", "")
        if settings.ai_fallback_on_failure:
            fallback = _build_local_extraction_fallback(
                effective_content,
                error_detail,
                source_ref,
                client_scope,
            )
            if extraction_summary:
                fallback["extraction_summary"] = extraction_summary
            if changelog_info:
                fallback["changelog"] = changelog_info
            return fallback
        error_kind = resp.get("error_kind") or ai_errors.classify_ai_error(error_detail)
        if error_kind != ai_errors.BAD_RESPONSE:
            raise ValueError(error_detail)
        _dump_failed_ai_response(raw, "ai_extraction_failed")
        raise ValueError(
            "AI 功能拆分返回内容不是合法 JSON，无法解析。已记录原始响应到服务端日志，"
            "可重试或在「AI 配置」更换模型后重试。"
        )

    result = resp["result"]
    if "modules" not in result:
        result["modules"] = []
    if "overall_assessment" not in result:
        result["overall_assessment"] = ""

    if extraction_summary:
        result["extraction_summary"] = extraction_summary
    if changelog_info:
        result["changelog"] = changelog_info
    if client_scope:
        result["client_scope"] = client_scope

    return result


# ── Batch 172: DSH harness 模式（可选，默认关闭；失败自动降级直连）──

async def _run_harness_generation(db, project_id: int, system_prompt: str, user_message: str, label: str = "") -> dict:
    """通过 DeepSeek Harness 执行一次生成任务，返回与 _call_ai_api 同构的结果。

    harness 有工具/执行能力，可读取并校验输出；本处把「系统规范 + 用户任务」作为
    单次任务文本交给 dsh runner 执行，最终回复解析为 JSON。
    """
    from app.services.dsh.dsh_runner import run_dsh_task

    task = (
        "你是一个测试用例生成引擎。严格按给定的系统规范与需求内容，输出指定的 JSON 结构。\n\n"
        f"## 系统规范\n{system_prompt}\n\n"
        f"## 用户任务\n{user_message}\n\n"
        "只输出最终 JSON 对象，不要输出任何解释文本或 markdown 代码块。"
    )
    loop = asyncio.get_running_loop()
    try:
        result = await loop.run_in_executor(None, lambda: run_dsh_task(task))
    except Exception as exc:  # noqa: BLE001 - runner 异常统一降级
        logger.warning("[ai_service] harness 执行异常，降级直连: %s", exc)
        return {"result": None, "raw": "", "finish_reason": "error", "truncated": False, "error": str(exc)}

    if result.exit_code != 0:
        logger.warning("[ai_service] harness %s 失败(exit=%s): %s", label, result.exit_code, result.error)
        return {"result": None, "raw": "", "finish_reason": "error", "truncated": False, "error": result.error}

    raw = result.final_response or ""
    if not raw:
        return {"result": None, "raw": "", "finish_reason": "error", "truncated": False, "error": "harness 返回空输出"}
    try:
        parsed = _parse_ai_response(raw)
        if parsed is None:
            logger.warning("[ai_service] harness %s 输出解析为空，降级直连", label)
            return {"result": None, "raw": raw, "finish_reason": "error", "truncated": False, "error": "harness 输出解析结果为空"}
        return {"result": parsed, "raw": raw, "finish_reason": "completed", "truncated": False, "error": None}
    except Exception as exc:  # noqa: BLE001 - 解析失败统一降级直连（_parse_ai_response 可能抛非 ValueError）
        logger.warning("[ai_service] harness %s 输出解析失败，降级直连: %s", label, exc)
        return {"result": None, "raw": raw, "finish_reason": "error", "truncated": False, "error": str(exc)}


async def _call_ai_api_with_harness(    db,
    project_id: int,
    system_prompt: str,
    user_message: str,
    label: str = "",
    max_tokens: int | None = None,
    use_harness: bool | None = None,
) -> dict:
    """AI 调用入口：harness 模式开启时先走 dsh，失败/解析失败降级直连。

    use_harness=None → 跟随 settings.dsh_enabled（默认 False，行为与现状一致）。
    """
    harness_on = settings.dsh_enabled if use_harness is None else use_harness
    if harness_on:
        harness_resp = await _run_harness_generation(db, project_id, system_prompt, user_message, label)
        if harness_resp["result"] is not None:
            return harness_resp
        logger.warning("[ai_service] %s harness 模式未产出可用结果，降级直连", label)
    return await _call_ai_api(db, project_id, system_prompt, user_message, label, max_tokens)


# ── Public API: Stage 2 — Test Case Generation ───────────────

async def generate_test_cases(db, project_id: int, content: str, file_type: str = "", source_ref: str = "",
                              extraction: dict | None = None,
                              use_harness: bool | None = None) -> dict:
    """Generate test cases from requirement content using AI.

    Generates functional test cases for all requirement types. For integration-type
    requirements (type=integration), also generates API test case suggestions with
    api_method and api_endpoint fields.

    When extraction is provided (Stage 2 guided generation), the confirmed
    modules and function points are injected as context.
    """
    try:
        ai_config_service.resolve(db, project_id)
    except AIProviderUnconfiguredError as exc:
        raise ValueError(str(exc)) from exc

    effective_content = content
    extraction_summary = ""
    page_filtered = False
    folder_name = ""
    effective_file_type = file_type
    changelog_info = None
    client_scope: list[str] = []

    if file_type == "lanhu" and source_ref:
        try:
            extract_result = await _extract_lanhu_content(source_ref)
            extracted = extract_result["content"]
            if extracted:
                effective_content = extracted
                page_filtered = extract_result.get("page_filtered", False)
                folder_name = extract_result.get("folder_name", "")
                changelog_info = extract_result.get("changelog")
                client_scope = extract_result.get("client_scope", [])
                first_line_end = extracted.find("\n")
                if first_line_end > 0:
                    extraction_summary = extracted[:first_line_end].strip()
                else:
                    extraction_summary = "蓝湖设计稿内容已提取"
        except ValueError as ve:
            if _is_lanhu_session_error(ve):
                # Batch 133：蓝湖会话失效是真实失败，不得伪装成"图片格式"兜底完成
                raise ValueError(
                    "蓝湖会话已失效（Cookie 过期或 HTTP 418 被拒）。"
                    "请重新登录蓝湖后粘贴新 Cookie，或联系管理员更新 LANHU_COOKIE。"
                ) from ve
            if content and content != source_ref and len(content) > len(source_ref) + 10:
                effective_file_type = ""
                extraction_summary = "蓝湖原型页面为图片格式，已使用补充说明文字作为需求内容"
            else:
                raise ValueError(
                    "蓝湖原型页面为图片格式（Axure 导出），无法自动提取文本内容。"
                    "请在提交蓝湖链接时，在「补充说明」中描述原型的页面功能、交互逻辑和业务规则，"
                    "AI 将基于文字描述生成测试用例。"
                )

    functional_system = _build_system_prompt("functional")
    warnings: list[str] = []
    chunks = _split_extraction_chunks(extraction) if extraction and extraction.get("modules") else []

    if chunks and len(chunks) > 1:
        # C68-3: 大文档分批生成并合并，块级失败不拖垮整体
        merged: dict = {
            "requirement_analysis": {"extracted_requirements": [], "overall_assessment": ""},
            "functional_cases": [],
            "api_cases": [],
        }
        sem = asyncio.Semaphore(_CHUNK_CONCURRENCY)

        async def _run_chunk(index: int, chunk: list[dict]) -> tuple[int, dict | None, list[str]]:
            chunk_warnings: list[str] = []
            async with sem:
                chunk_user = _build_user_message_with_extraction(
                    effective_content, effective_file_type, source_ref, {"modules": chunk}
                )
                label = f"functional-chunk-{index}"
                func_resp = await _call_ai_api_with_harness(db, project_id, functional_system, chunk_user, label, use_harness=use_harness)
                if func_resp["truncated"]:
                    chunk_warnings.append(f"{label} 生成被截断，已重试")
                    func_resp = await _call_ai_api_with_harness(db, project_id, functional_system, chunk_user, f"{label}-retry", use_harness=use_harness)
                if func_resp["result"] is None:
                    chunk_warnings.append(
                        f"{label} 生成失败：{func_resp.get('error', '未知错误')}（该块未产出用例）"
                    )
                    return index, None, chunk_warnings
                return index, func_resp["result"], chunk_warnings

        results = await asyncio.gather(
            *[_run_chunk(i, c) for i, c in enumerate(chunks, start=1)]
        )
        failed_blocks = 0
        for _index, chunk_result, chunk_warnings in sorted(results, key=lambda r: r[0]):
            warnings.extend(chunk_warnings)
            if chunk_result is None:
                failed_blocks += 1
                continue
            merged["functional_cases"].extend(chunk_result.get("functional_cases") or [])
            merged["api_cases"].extend(chunk_result.get("api_cases") or [])
            if isinstance(chunk_result.get("requirement_analysis"), dict):
                merged["requirement_analysis"] = chunk_result["requirement_analysis"]
        if failed_blocks == len(chunks):
            raise ValueError("AI 分批生成全部失败，请检查 AI 服务后重试")
        merged["functional_cases"] = _dedupe_and_renumber(merged["functional_cases"])
        result = merged
    else:
        if chunks:
            user_message = _build_user_message_with_extraction(
                effective_content, effective_file_type, source_ref, extraction
            )
        else:
            user_message = _build_user_message(
                effective_content, effective_file_type, source_ref,
                page_filtered=page_filtered, folder_name=folder_name,
                changelog=changelog_info, client_scope=client_scope,
            )
        func_resp = await _call_ai_api_with_harness(db, project_id, functional_system, user_message, "functional", use_harness=use_harness)
        if func_resp["truncated"]:
            warnings.append("功能用例生成被截断，结果可能不完整")
        if func_resp["result"] is None:
            error_detail = func_resp.get("error", "未知错误")
            error_kind = func_resp.get("error_kind") or ai_errors.classify_ai_error(error_detail)
            raw = func_resp["raw"]
            # 传输/鉴权/限流类失败直接透传可执行提示，不得伪装成 JSON 解析错误。
            if error_kind != ai_errors.BAD_RESPONSE:
                raise ValueError(error_detail)
            # 真·解析失败：原始响应落到服务端日志目录，**不把路径写进用户可见消息**。
            _dump_failed_ai_response(raw, "ai_response_failed")
            raise ValueError(
                "AI 返回内容不是合法 JSON，无法解析。已记录原始响应到服务端日志，"
                "可重试或在「AI 配置」更换模型后重试。"
            )
        result = func_resp["result"]
    if "api_cases" not in result:
        result["api_cases"] = []

    if extraction_summary:
        result["extraction_summary"] = extraction_summary
    if warnings:
        result["_warnings"] = warnings

    return result



