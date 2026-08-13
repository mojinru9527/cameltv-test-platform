"""Agent 编排引擎（M4）—— Pipeline: RAG 检索 → LLM 推理 → AiArtifact → 人工审核。

每条 Agent 执行在独立 Session 中完成（不绑定主请求事务），由 BackgroundTasks 调度。
核心流程：
  1. agent_run_service.start_run() 写执行记录（status=running）
  2. search_service.hybrid_search() RAG 检索上下文
  3. 组装 LLM prompt（agent_type → system prompt + 检索上下文 + user input）
  4. LLM 调用（DeepSeek / OpenAI 兼容 API）
  5. 结果持久化为 AiArtifact
  6. agent_run_service.finish_run() 更新状态
"""
from __future__ import annotations

import json
import logging
import time

import httpx

from app.core.config import settings
from app.core.db import SessionLocal
from app.models.knowledge import AiArtifact
from app.services.knowledge.artifact_confidence import artifact_confidence_from_output
from app.services.knowledge.agent_prompts import AGENT_META, build_system_prompt
from app.services.knowledge import agent_run_service, search_service

logger = logging.getLogger("knowledge.orchestrator")

# ── LLM 配置 ──
_LLM_TIMEOUT = 180.0  # 秒


def _call_llm_sync(system_prompt: str, user_message: str, max_tokens: int = 4096) -> dict:
    """同步调用 LLM（OpenAI 兼容 API），返回 {"result": dict|None, "raw": str, "error": str|None}。"""
    if not settings.ai_api_key:
        return {"result": None, "raw": "", "error": "AI_API_KEY 未配置"}

    try:
        resp = httpx.post(
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
                "max_tokens": max_tokens,
                "temperature": settings.ai_temperature,
                "response_format": {"type": "json_object"},
            },
            timeout=_LLM_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
        raw = data["choices"][0]["message"]["content"]

        # 尝试解析 JSON
        try:
            result = json.loads(raw)
        except json.JSONDecodeError:
            # 尝试从 markdown 代码块中提取
            import re
            m = re.search(r"```(?:json)?\s*([\s\S]*?)```", raw)
            if m:
                try:
                    result = json.loads(m.group(1))
                except json.JSONDecodeError:
                    result = {"raw_output": raw}
            else:
                result = {"raw_output": raw}

        return {"result": result, "raw": raw, "error": None}
    except httpx.HTTPStatusError as e:
        return {"result": None, "raw": "", "error": f"LLM API 错误: {e.response.status_code}"}
    except httpx.TimeoutException:
        return {"result": None, "raw": "", "error": "LLM 调用超时"}
    except Exception as e:
        logger.exception("LLM call failed")
        return {"result": None, "raw": "", "error": str(e)}


def _rag_retrieve(project_id: int, query: str, top_k: int = 8) -> str:
    """RAG 检索 → 序列化为上下文文本。"""
    if not settings.rag_enabled:
        return ""
    db = SessionLocal()
    try:
        results = search_service.hybrid_search(
            db, project_id=project_id, query=query, top_k=top_k, mode="keyword",
        )
    except Exception:
        logger.exception("RAG retrieve failed")
        return ""
    finally:
        db.close()

    if not results:
        return ""

    lines = []
    for r in results[:top_k]:
        lines.append(
            f"- [{r.chunk_type}] {r.title}: {r.snippet} (source: {r.source_name}, score: {r.score:.2f})"
        )
    return "\n".join(lines)


# ── Batch 172: dsh_execution 执行型 Agent 分支 ──

def _run_dsh_agent(
    db,
    run,
    *,
    project_id: int,
    agent_type: str,
    user_input: str,
    params: dict,
    start: float,
) -> dict[str, any]:
    """dsh_execution：通过 DeepSeek Harness 真实执行任务并持久化 AiArtifact。

    不走 RAG+LLM 推理链路；user_input（或 params.task）即任务文本。执行输出、
    退出码与会话目录写入 AiArtifact。
    """
    from app.services.dsh.dsh_runner import run_dsh_task, runtime_available

    def _finish_failed(message: str, status: str = "failed") -> dict[str, any]:
        duration_ms = int((time.perf_counter() - start) * 1000)
        agent_run_service.finish_run(
            db, run, status=status, error_message=message, duration_ms=duration_ms,
        )
        db.commit()
        return {"run_id": run.id, "artifact_id": None, "status": status, "error": message}

    available, reason = runtime_available()
    if not available:
        return _finish_failed(f"DSH 不可用: {reason}")

    task_text = (user_input or "").strip() or str((params or {}).get("task") or "").strip()
    if not task_text:
        return _finish_failed("DSH 执行任务文本为空")

    try:
        result = run_dsh_task(task_text)
    except Exception as exc:  # noqa: BLE001 - runner 异常统一失败留痕
        logger.exception("dsh_execution run failed")
        return _finish_failed(f"dsh 执行异常: {exc}")

    duration_ms = int((time.perf_counter() - start) * 1000)
    if result.exit_code != 0:
        return _finish_failed(result.error or f"dsh 退出码 {result.exit_code}")

    output_data = {
        "final_response": result.final_response,
        "exit_code": result.exit_code,
        "session_dir": result.session_dir,
    }
    meta = AGENT_META[agent_type]
    title = (result.final_response or "").strip().replace("\n", " ")[:80] or f"{meta['label']} #{run.id}"
    artifact = AiArtifact(
        project_id=project_id,
        artifact_type=meta["artifact_type"],
        title=str(title)[:200],
        content_json=json.dumps(output_data, ensure_ascii=False),
        agent_run_id=run.id,
        review_status="pending",
        confidence=artifact_confidence_from_output(output_data),
    )
    db.add(artifact)
    db.flush()
    agent_run_service.finish_run(
        db, run,
        status="success",
        output_data={
            "artifact_id": artifact.id,
            "summary": str(title)[:200],
            "final_response": result.final_response[:2000],
            "session_dir": result.session_dir,
        },
        duration_ms=duration_ms,
    )
    db.commit()
    logger.info("dsh_execution run completed: run_id=%s artifact_id=%s duration=%sms", run.id, artifact.id, duration_ms)
    return {"run_id": run.id, "artifact_id": artifact.id, "status": "success"}


# ── 主入口：在独立 Session 中运行 Agent ──

def run_agent_in_new_session(
    project_id: int,
    agent_type: str,
    user_input: str = "",
    params: dict | None = None,
    operator_id: int = 0,
) -> dict[str, any]:
    """独立 Session 执行一次 Agent Pipeline。返回 {"run_id": int, "artifact_id": int|None, "status": str}。

    此函数设计为在 BackgroundTasks 中调用，不阻塞 HTTP 响应。
    """
    if agent_type not in AGENT_META:
        return {"run_id": 0, "artifact_id": None, "status": "invalid_type", "error": f"未知 Agent 类型: {agent_type}"}

    db = SessionLocal()
    run = None
    artifact = None
    start = time.perf_counter()

    try:
        # 1. 开始执行记录
        run = agent_run_service.start_run(
            db,
            project_id=project_id,
            agent_type=agent_type,
            trigger_type="manual",
            input_data={"user_input": user_input, "params": params or {}},
            operator_id=operator_id,
        )

        # Batch 172: dsh_execution 走真实执行，不走 RAG+LLM
        if agent_type == "dsh_execution":
            return _run_dsh_agent(
                db, run,
                project_id=project_id,
                agent_type=agent_type,
                user_input=user_input,
                params=params or {},
                start=start,
            )

        # 2. RAG 检索上下文
        query = user_input or (params or {}).get("query", "")
        rag_context = _rag_retrieve(project_id, query) if query else ""

        # 3. 组装 prompt
        system_prompt = build_system_prompt(agent_type, rag_context)
        user_message = user_input or json.dumps(params or {}, ensure_ascii=False)

        # 记录检索上下文
        if rag_context:
            retrieved = {"query": query, "context_snippets": len(rag_context.split("\n")) if rag_context else 0}
        else:
            retrieved = {}

        # 4. LLM 调用
        llm_resp = _call_llm_sync(system_prompt, user_message)

        duration_ms = int((time.perf_counter() - start) * 1000)

        if llm_resp["error"]:
            # LLM 调用失败
            agent_run_service.finish_run(
                db, run,
                status="failed",
                retrieved_context=retrieved,
                error_message=llm_resp["error"],
                duration_ms=duration_ms,
            )
            db.commit()
            return {"run_id": run.id, "artifact_id": None, "status": "failed", "error": llm_resp["error"]}

        # 5. 持久化输出为 AiArtifact
        output_data = llm_resp["result"] or {}
        meta = AGENT_META[agent_type]
        title = output_data.get("summary", f"{meta['label']} #{run.id}")
        if isinstance(title, dict):
            title = json.dumps(title, ensure_ascii=False)[:120]

        artifact = AiArtifact(
            project_id=project_id,
            artifact_type=meta["artifact_type"],
            title=str(title)[:200],
            content_json=json.dumps(output_data, ensure_ascii=False),
            agent_run_id=run.id,
            review_status="pending",
            confidence=artifact_confidence_from_output(output_data),
        )
        db.add(artifact)
        db.flush()

        # 6. 完成执行记录
        agent_run_service.finish_run(
            db, run,
            status="success",
            output_data={"artifact_id": artifact.id, "summary": str(title)[:200]},
            retrieved_context=retrieved,
            duration_ms=duration_ms,
        )

        db.commit()
        logger.info(
            "Agent run completed: type=%s run_id=%s artifact_id=%s duration=%sms",
            agent_type, run.id, artifact.id, duration_ms,
        )

        # 成功后自动将产出物入库为平台研发知识
        try:
            from app.services.knowledge.ingest_service import ingest_agent_task_completed_in_new_session
            ingest_agent_task_completed_in_new_session(project_id, run.id)
        except Exception:
            logger.exception("auto-ingest agent output failed run_id=%s", run.id)

        return {"run_id": run.id, "artifact_id": artifact.id, "status": "success"}

    except Exception:
        logger.exception("Agent run failed: type=%s project=%s", agent_type, project_id)
        duration_ms = int((time.perf_counter() - start) * 1000)
        try:
            if run:
                agent_run_service.finish_run(
                    db, run,
                    status="failed",
                    error_message="Agent 执行异常",
                    duration_ms=duration_ms,
                )
            db.commit()
        except Exception:
            db.rollback()
        return {"run_id": run.id if run else 0, "artifact_id": None, "status": "failed", "error": "Agent 执行异常"}

    finally:
        db.close()
