"""VersionTask AI 方案生成服务（B8 修复 / F-01）。

把「版本验收任务」上下文（标题/版本/变更模块，以及可选的关联需求文档/发布包）
交给项目级 AI 提供方（``ai_config_service.resolve``），产出**可执行**的验收方案条目
（含 ``item_type/title/description/confidence`` 与可选的 ``exec_meta`` 可执行元数据）。

无 AI 配置时抛 ``AIProviderUnconfiguredError``（前端据此提示整备）；不降级为硬编码占位。
"""
from __future__ import annotations

import json
import logging

from app.services.ai_config_service import (
    AIProviderUnconfiguredError,
    EffectiveAiConfig,
    ai_config_service,
)

logger = logging.getLogger("version_task_ai")

_SYSTEM_PROMPT = """你是一位资深的版本验收测试方案设计师。
给定一个版本验收任务的上下文（标题、版本号、变更模块，以及可选的需求文档/发布包内容），
产出**可执行**的验收方案条目 JSON 数组。每个条目：
- item_type: functional（功能）| api（接口）| scenario（自动化场景）| check（核对点）
- title / description: 用业务语言，可被黑盒测试员理解
- confidence: 0-100 的数字，表示你对该条目的确信度
- exec_meta: 仅当能推断出**真实可调用**的目标时填；不能推断就留空对象 {}。
  对于 api 条目，exec_meta 可含 {"method":"GET|POST|PUT|DELETE","path":"/api/v1/xxx","assert":[{"type":"status","expected":200}]}
  或 {"url":"https://host/path","method":"GET","assert":[...]}。
- 禁止臆造不存在的接口/字段；没有依据就不要填 exec_meta。

只输出 JSON 数组，不要用 markdown 代码块包裹，不要输出其他文字。
"""


def _build_user_message(task: dict) -> str:
    parts: list[str] = []
    parts.append(f"版本验收任务标题：{task.get('title', '')}")
    parts.append(f"版本号：{task.get('version', '')}")
    modules = (task.get("scope") or {}).get("modules") or []
    if modules:
        parts.append("变更模块：" + "、".join(str(m) for m in modules))
    context = task.get("context") or ""
    if context:
        parts.append("需求/文档上下文：\n" + str(context)[:6000])
    return "\n".join(parts)


def _call_llm_sync(cfg: EffectiveAiConfig, system_prompt: str, user_message: str, max_tokens: int = 4096) -> list[dict]:
    """单次同步 DeepSeek / OpenAI 兼容 chat/completions 调用，返回解析后的 JSON（list）。"""
    import httpx

    payload = {
        "model": cfg.model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        "max_tokens": max_tokens,
        "temperature": 0.2,
        "response_format": {"type": "json_object"},
    }
    headers = {
        "Authorization": f"Bearer {cfg.api_key}",
        "Content-Type": "application/json",
    }
    with httpx.Client(timeout=120.0) as client:
        resp = client.post(
            f"{cfg.api_base_url.rstrip('/')}/chat/completions", json=payload, headers=headers
        )
        resp.raise_for_status()
        data = resp.json()
        raw = data["choices"][0]["message"]["content"]

    # 优先 json.loads（含顶层数组），失败再走 ai_service 的健壮修复
    try:
        parsed = json.loads(raw)
    except (ValueError, TypeError):
        try:
            from app.services.ai_service import _parse_ai_response

            parsed = _parse_ai_response(raw)
        except Exception:  # noqa: BLE001 - 解析兜底
            parsed = json.loads(raw)

    # _parse_ai_response 会把 JSON 当作对象解析；方案数组可能是 raw["items"] 或直接是数组
    if isinstance(parsed, list):
        return parsed
    if isinstance(parsed, dict):
        for key in ("items", "plan", "scenarios"):
            val = parsed.get(key)
            if isinstance(val, list):
                return val
        # 顶层对象视图：把值列表当作条目
        for val in parsed.values():
            if isinstance(val, list):
                return val
    return []


def _coerce_item(it: dict) -> dict:
    """把 AI 返回的条目归一化为 PlanItemCreate 兼容 dict（含可序列化 exec_meta）。"""
    exec_meta = it.get("exec_meta") or {}
    if not isinstance(exec_meta, dict):
        exec_meta = {}
    return {
        "item_type": str(it.get("item_type") or "functional"),
        "title": str(it.get("title") or "").strip()[:300],
        "description": str(it.get("description") or "")[:2000],
        "confidence": max(0, min(100, int(it.get("confidence") or 0))),
        "question": str(it.get("question") or ""),
        "exec_meta": exec_meta,
    }


def generate_plan_items(db, task, project_id: int) -> list[dict]:
    """由版本任务上下文生成 AI 验收方案条目（F-01）。无 AI 配置时抛错误。"""
    user_msg = _build_user_message(task)
    cfg = ai_config_service.resolve(db, project_id)  # 无配置抛 AIProviderUnconfiguredError
    items = _call_llm_sync(cfg, _SYSTEM_PROMPT, user_msg)
    coerced = [_coerce_item(it) for it in items if isinstance(it, dict) and it.get("title")]
    if not coerced:
        raise RuntimeError("AI 未返回有效方案条目")
    return coerced
