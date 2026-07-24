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
import re
from pathlib import Path

import httpx

from app.core.config import settings
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
    parts: list[str] = []
    for fname in ["SKILL.md", "case-template.md", "functional-checklist.md"]:
        fpath = _skill_dir() / fname
        if fpath.exists():
            parts.append(fpath.read_text(encoding="utf-8"))
    return "\n\n---\n\n".join(parts)


def _load_skill_context_for(kind: str) -> str:
    """Load skill files for a specific case type.

    kind = "functional": SKILL.md + case-template.md + functional-checklist.md
    kind = "api":        Same as functional (API cases generated via dedicated endpoint)
    """
    # Use functional skill context — API cases are generated via AI prompt for integration-type requirements
    files = ["SKILL.md", "case-template.md", "functional-checklist.md"]
    parts: list[str] = []
    for fname in files:
        fpath = _skill_dir() / fname
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
      "preconditions": "前提条件",
      "expected_result": "预期结果（如返回 200 + 数据列表）",
      "remark": "关联的功能点 REQ ID"
    }
  ]
}"""

    focus_rule = "- 专注于生成**功能测试用例**。对于 type=integration 的功能点，同时在 api_cases 中生成对应接口用例建议。"
    kind_rules = (
        "- 功能用例数量不做硬性限制，应覆盖所有功能点，宁多勿少。\n"
        "- 对于 type=integration 的功能点，在 api_cases 数组中生成对应的接口测试用例，包含 api_method 和 api_endpoint（建议路径）。\n"
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
2. 每个功能点至少 1 条正面用例 + 1 条负面用例。
3. 综合运用等价类划分、边界值分析、场景法、错误推测等方法。
{focus_rule}

{skill_ctx}

输出格式要求：你 **必须** 返回一个严格的 JSON 对象，格式如下：

{output_schema}

字段说明：
- requirement_analysis.type: 可选值 "functional"(功能) / "ui"(界面) / "data"(数据) / "integration"(集成)
- requirement_analysis.issues[].severity: "high"(高优先级/逻辑漏洞) / "medium"(中优先级/模糊不清) / "low"(低优先级/建议优化)
- functional_cases[].priority: P0(关键路径/基本流) / P1(异常流/边界值) / P2(体验/界面)
- functional_cases[].steps: 每个步骤含 step(序号), desc(操作描述), expected(该步预期)
- functional_cases[].client_scope: 该用例适用的客户端列表，可选值 "app" / "pc" / "web"
- api_cases[].api_method: HTTP 方法 "GET" / "POST" / "PUT" / "DELETE"
- api_cases[].api_endpoint: 建议的 API 路径（如 "/api/v1/matches"）

关键规则：
- **先分析需求，再生成用例** — 阶段一完成后才能进入阶段二。
- 每个需求功能点至少 1 条正面用例 + 1 条负面用例。
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
                pass

    if result["functional_cases"] or result["api_cases"]:
        return result
    return None


# ── AI API Call ──────────────────────────────────────────────

async def _call_ai_api(system_prompt: str, user_message: str, label: str = "",
                       max_tokens: int | None = None) -> dict:
    """Make a single AI API call and return the parsed result."""
    if not settings.ai_api_key:
        return {"result": None, "raw": "", "finish_reason": "error", "truncated": False,
                "error": "AI_API_KEY 未配置"}

    effective_max_tokens = max_tokens if max_tokens is not None else settings.ai_max_tokens

    try:
        async with httpx.AsyncClient(timeout=180.0) as client:
            resp = await client.post(
                f"{settings.ai_api_base_url.rstrip('/')}/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.ai_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": settings.ai_model,
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
                print(f"[ai_service] WARNING: {label} response truncated (finish_reason=length, "
                      f"raw_length={len(raw)} chars)")

            try:
                result = _parse_ai_response(raw)
                return {"result": result, "raw": raw, "finish_reason": finish_reason,
                        "truncated": truncated, "error": None}
            except ValueError as parse_err:
                if truncated:
                    salvaged = _salvage_json_parts(raw)
                    if salvaged is not None:
                        print(f"[ai_service] Salvaged partial data from truncated {label} response")
                        return {"result": salvaged, "raw": raw, "finish_reason": finish_reason,
                                "truncated": True, "error": None}
                return {"result": None, "raw": raw, "finish_reason": finish_reason,
                        "truncated": truncated, "error": str(parse_err)}
    except Exception as e:
        return {"result": None, "raw": "", "finish_reason": "error", "truncated": False,
                "error": str(e)}


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


async def extract_features(content: str, file_type: str = "", source_ref: str = "") -> dict:
    """Stage 1: Extract test modules and function points from requirement content.

    For Lanhu URLs, uses the changelog-first extraction pipeline:
    1. Extract changelog pages to identify versions and update content
    2. Match versions to folders → extract requirements per version
    3. Detect client scope (App/PC/Web)
    4. AI decomposes into modules + function points (with client_scope)

    Returns dict with keys: modules, overall_assessment, extraction_summary,
    changelog, client_scope.
    """
    if not settings.ai_api_key:
        raise ValueError("AI_API_KEY 未配置，请在 .env 中设置 AI_API_KEY")

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
        except ValueError:
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

    extraction_max_tokens = max(settings.ai_max_tokens * 2, 32768)
    resp = await _call_ai_api(system_prompt, user_message, "extraction",
                              max_tokens=extraction_max_tokens)
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
        import tempfile
        import time
        dump_path = Path(tempfile.gettempdir()) / f"ai_extraction_failed_{int(time.time())}.json"
        if raw:
            dump_path.write_text(raw, encoding="utf-8")
        raise ValueError(
            f"AI 功能拆分 JSON 格式异常，无法解析。\n"
            f"错误: {error_detail}\n"
            f"原始响应已保存至: {dump_path}"
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


# ── Public API: Stage 2 — Test Case Generation ───────────────

async def generate_test_cases(content: str, file_type: str = "", source_ref: str = "",
                              extraction: dict | None = None) -> dict:
    """Generate test cases from requirement content using AI.

    Generates functional test cases for all requirement types. For integration-type
    requirements (type=integration), also generates API test case suggestions with
    api_method and api_endpoint fields.

    When extraction is provided (Stage 2 guided generation), the confirmed
    modules and function points are injected as context.
    """
    if not settings.ai_api_key:
        raise ValueError("AI_API_KEY 未配置，请在 .env 中设置 AI_API_KEY")

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
        except ValueError:
            if content and content != source_ref and len(content) > len(source_ref) + 10:
                effective_file_type = ""
                extraction_summary = "蓝湖原型页面为图片格式，已使用补充说明文字作为需求内容"
            else:
                raise ValueError(
                    "蓝湖原型页面为图片格式（Axure 导出），无法自动提取文本内容。"
                    "请在提交蓝湖链接时，在「补充说明」中描述原型的页面功能、交互逻辑和业务规则，"
                    "AI 将基于文字描述生成测试用例。"
                )

    if extraction and extraction.get("modules"):
        user_message = _build_user_message_with_extraction(
            effective_content, effective_file_type, source_ref, extraction
        )
    else:
        user_message = _build_user_message(effective_content, effective_file_type, source_ref,
                                           page_filtered=page_filtered, folder_name=folder_name,
                                           changelog=changelog_info, client_scope=client_scope)

    functional_system = _build_system_prompt("functional")

    func_resp = await _call_ai_api(functional_system, user_message, "functional")

    warnings: list[str] = []
    if func_resp["truncated"]:
        warnings.append("功能用例生成被截断，结果可能不完整")

    if func_resp["result"] is None:
        import tempfile
        import time
        raw = func_resp["raw"]
        dump_path = Path(tempfile.gettempdir()) / f"ai_response_failed_{int(time.time())}.json"
        if raw:
            dump_path.write_text(raw, encoding="utf-8")
        error_detail = func_resp.get("error", "未知错误")
        raise ValueError(
            f"AI 返回的 JSON 格式异常，无法解析。\n"
            f"错误: {error_detail}\n"
            f"原始响应已保存至: {dump_path}\n"
            f"请检查该文件中的 JSON 语法错误。"
        )

    result = func_resp["result"]
    if "api_cases" not in result:
        result["api_cases"] = []

    if extraction_summary:
        result["extraction_summary"] = extraction_summary
    if warnings:
        result["_warnings"] = warnings

    return result
