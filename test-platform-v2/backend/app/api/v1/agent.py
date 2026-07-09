"""Agent 执行记录 API —— /api/v1/agents/*

M0: 执行记录只读查询（GET /runs, GET /runs/{id}）
M4: Agent 触发端点（POST /run/{agent_type}）— 编排 RAG 检索 + LLM 推理 → AiArtifact
"""
from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import CurrentUser, require_permission
from app.schemas.common import Page, R
from app.schemas.knowledge import AgentRunOut
from app.services.knowledge import agent_run_service
from app.services.knowledge.agent_orchestrator import run_agent_in_new_session
from app.services.knowledge.agent_prompts import AGENT_META

router = APIRouter(prefix="/agents", tags=["Agent 工作台"])


# ── 触发请求体 ──

class AgentRunRequest(BaseModel):
    """Agent 触发请求。"""
    query: str = Field("", description="用户输入/要分析的内容")
    params: dict = Field(default_factory=dict, description="附加参数（如 source_id, api_path 等）")


class AgentRunResponse(BaseModel):
    """Agent 触发响应（立即返回 run_id，后台执行）。"""
    run_id: int = 0
    status: str = "running"
    message: str = ""


# ── 执行记录查询（M0） ──

@router.get("/runs", response_model=R[Page[AgentRunOut]], summary="Agent 执行记录列表")
def list_runs(
    agent_type: str | None = Query(None),
    status: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    current: CurrentUser = Depends(require_permission("agent:list")),
    db: Session = Depends(get_db),
):
    rows, total = agent_run_service.list_runs(
        db, current.project_id or 0,
        agent_type=agent_type, status=status, page=page, page_size=page_size,
    )
    return R.ok(Page(
        total=total, page=page, page_size=page_size,
        items=[AgentRunOut.model_validate(r) for r in rows],
    ))


@router.get("/runs/{run_id}", response_model=R[AgentRunOut], summary="Agent 执行记录详情")
def get_run(
    run_id: int,
    current: CurrentUser = Depends(require_permission("agent:list")),
    db: Session = Depends(get_db),
):
    row = agent_run_service.get_run(db, run_id, current.project_id or 0)
    if not row:
        return R(code=404, msg="Agent 执行记录不存在")
    return R.ok(AgentRunOut.model_validate(row))


# ── Agent 触发（M4） ──

@router.post("/run/{agent_type}", response_model=R[AgentRunResponse], summary="触发 Agent 执行")
def trigger_agent(
    agent_type: str,
    body: AgentRunRequest,
    bg: BackgroundTasks,
    current: CurrentUser = Depends(require_permission("agent:run")),
    db: Session = Depends(get_db),
):
    """触发指定类型的 Agent 在后台执行（RAG 检索 → LLM 推理 → AiArtifact）。

    立即返回 run_id，前端可通过 GET /agents/runs/{run_id} 轮询状态。
    支持的类型：requirement_analysis / impact_analysis / case_generation / failure_analysis。
    """
    if agent_type not in AGENT_META:
        return R(code=400, msg=f"未知 Agent 类型: {agent_type}。支持: {', '.join(AGENT_META.keys())}")

    pid = current.project_id or 0
    bg.add_task(
        run_agent_in_new_session,
        project_id=pid,
        agent_type=agent_type,
        user_input=body.query,
        params=body.params,
        operator_id=current.user.id,
    )

    # 创建一个 pending run 记录让前端立即拿到 run_id
    placeholder = agent_run_service.start_run(
        db, project_id=pid, agent_type=agent_type,
        trigger_type="manual",
        input_data={"query": body.query, "params": body.params},
        operator_id=current.user.id,
    )
    placeholder.status = "pending"
    db.commit()
    db.refresh(placeholder)

    return R.ok(AgentRunResponse(
        run_id=placeholder.id,
        status="pending",
        message=f"{AGENT_META[agent_type]['label']}已加入后台执行队列",
    ))


@router.get("/types", response_model=R[list[dict]], summary="获取可用 Agent 类型列表")
def list_agent_types():
    """返回所有可用的 Agent 类型及其元数据（label / description / artifact_type）。"""
    return R.ok([
        {"type": k, "label": v["label"], "description": v["description"], "artifact_type": v["artifact_type"]}
        for k, v in AGENT_META.items()
    ])


# ── M5 变更检测与自动触发 ──

class ChangeCheckRequest(BaseModel):
    """变更检测请求。"""
    auto_trigger: bool = Field(False, description="是否自动触发匹配的 Agent")


@router.post("/triggers/check", response_model=R[dict], summary="手动触发变更检测")
def check_changes(
    body: ChangeCheckRequest,
    current: CurrentUser = Depends(require_permission("agent:run")),
):
    """扫描项目内所有知识源的内容哈希变更，可选自动触发 Agent。"""
    from app.services.knowledge.change_detector import check_changes_manual, handle_changes

    if body.auto_trigger:
        result = handle_changes(current.project_id or 0, auto_trigger=True)
        return R.ok(result)

    result = check_changes_manual(current.project_id or 0)
    return R.ok(result)


@router.get("/triggers/rules", response_model=R[dict], summary="查看触发规则")
def get_trigger_rules():
    """返回当前的触发规则配置。"""
    from app.services.knowledge.change_detector import TRIGGER_RULES
    return R.ok(TRIGGER_RULES)
