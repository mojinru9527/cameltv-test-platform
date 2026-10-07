"""平台级 AI 配额闸门 + 用量台账（P1-6）。

背景（生产审计）：平台此前**没有任何** AI 速率限制或 token 预算——
`app/core/rate_limit.py` 只覆盖登录/注册/开放 API 令牌，`model_usage_ledger`
表建了却从没被写入过（生产 0 行）。于是任何一条自动链路（变更检测 → Agent、
执行失败 → 深度分析）都能无限燃烧密钥；一次密钥泄漏就被外部调用烧穿。

本模块提供两件事，全部挂在唯一出网咽喉（ai-gateway 的 chat handler）与
直连 httpx 的分诊链路上：

- :func:`enforce`：调用**前**的闸门，按项目统计近 60s 台账行数（请求速率）与
  近 24h `input_units + output_units`（token 预算），任一超限即抛
  :class:`AIQuotaExceededError`（调用方映射为 HTTP 429）。台账查询自身报错时
  **失败关闭**（fail closed）：记日志并抛错，绝不静默放行。
- :func:`record`：调用**后**的记账，写一行 `model_usage_ledger`（也就是让这张
  死表真正有数据）。记账使用独立会话（不提交调用方事务），失败只告警，
  绝不把异常抛回业务调用方。

约定的记账口径：**失败的调用也记一行（0 token）**，这样「反复失败重试」同样
消耗每分钟请求额度，速率闸门不会因为异常路径被绕过。
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.db import SessionLocal
from app.models.model_usage import ModelUsageLedger

logger = logging.getLogger("ai.guard")

# 速率统计窗口（秒）
_RATE_WINDOW_SECONDS = 60
# token 预算统计窗口（小时）
_TOKEN_WINDOW_HOURS = 24


class AIQuotaExceededError(RuntimeError):
    """AI 配额超限（或配额校验无法完成时的失败关闭）。

    ``message`` 是面向用户/日志的中文说明，网关会把它原样放进 HTTP 429 的 detail。
    """

    def __init__(self, message: str, *, reason: str = "quota") -> None:
        super().__init__(message)
        self.message = message
        # quota_rate / quota_tokens / check_failed
        self.reason = reason


def _project_scope(project_id: int | None) -> int:
    """项目维度归一：None/非法值一律落到 0（网关的默认 project_id）。"""
    try:
        return int(project_id or 0)
    except (TypeError, ValueError):
        return 0


def _count_recent_requests(db: Session, project_id: int) -> int:
    cutoff = datetime.now() - timedelta(seconds=_RATE_WINDOW_SECONDS)
    return int(
        db.scalar(
            select(func.count())
            .select_from(ModelUsageLedger)
            .where(
                ModelUsageLedger.project_id == project_id,
                ModelUsageLedger.created_at >= cutoff,
            )
        )
        or 0
    )


def _sum_recent_tokens(db: Session, project_id: int) -> int:
    cutoff = datetime.now() - timedelta(hours=_TOKEN_WINDOW_HOURS)
    units = ModelUsageLedger.input_units + ModelUsageLedger.output_units
    return int(
        db.scalar(
            select(func.coalesce(func.sum(units), 0)).where(
                ModelUsageLedger.project_id == project_id,
                ModelUsageLedger.created_at >= cutoff,
            )
        )
        or 0
    )


def enforce(db: Session, project_id: int, *, operation_type: str = "chat") -> None:
    """调用前的配额闸门；超限或校验失败即抛 :class:`AIQuotaExceededError`。

    Args:
        db: 数据库会话（只读用途；本函数不改动调用方事务）
        project_id: 统计维度（按项目计数，operation_type 只用于日志与报错文案）
        operation_type: 业务操作类型，仅用于可观测性

    Raises:
        AIQuotaExceededError: 超过每分钟请求上限 / 24h token 预算，
            或台账查询本身失败（失败关闭）

    注：两个上限配置为非正数时按 1 处理（宁可拒绝也不放任），需要彻底放开请把
    `ai_guard_enabled` 置为 False。
    """
    if not settings.ai_guard_enabled:
        return
    scope = _project_scope(project_id)

    try:
        rate_cap = max(1, int(settings.ai_rate_limit_per_minute))
        recent = _count_recent_requests(db, scope)
        if recent >= rate_cap:
            raise AIQuotaExceededError(
                f"AI 调用过于频繁：项目 {scope} 近 {_RATE_WINDOW_SECONDS} 秒已发起 "
                f"{recent} 次 AI 调用，达到每分钟上限 {rate_cap} 次"
                f"（AI_RATE_LIMIT_PER_MINUTE），请稍后重试",
                reason="quota_rate",
            )

        # 上限 <=0 视为配置错误，按 1 处理（失败关闭方向），而不是当成「不限制」。
        budget = max(1, int(settings.ai_daily_token_budget))
        used = _sum_recent_tokens(db, scope)
        if used >= budget:
            raise AIQuotaExceededError(
                f"AI 每日 token 预算已用尽：项目 {scope} 近 {_TOKEN_WINDOW_HOURS} 小时已消耗 "
                f"{used} tokens，达到预算上限 {budget}（AI_DAILY_TOKEN_BUDGET），"
                "请调整预算或排查异常调用",
                reason="quota_tokens",
            )
    except AIQuotaExceededError:
        raise
    except Exception as exc:
        # 宽泛捕获是有意的：台账查不出来就必须失败关闭，静默放行的配额检查等于没有检查。
        logger.exception(
            "AI 配额校验失败，按失败关闭拒绝本次调用: project=%s operation=%s",
            scope,
            operation_type,
        )
        raise AIQuotaExceededError(
            f"AI 配额校验失败（用量台账查询异常），已按失败关闭拒绝本次调用：{exc}",
            reason="check_failed",
        ) from exc


def record(
    db: Session | None,
    project_id: int,
    *,
    operation_type: str,
    model_ref: str = "",
    input_units: int = 0,
    output_units: int = 0,
    latency_ms: int = 0,
    cost_amount: float = 0.0,
    mission_id: int | None = None,
) -> None:
    """调用后的用量记账；**任何失败都不得抛回调用方**。

    写入使用**独立会话**（本模块的 `SessionLocal()`），刻意不借用、也不提交调用方
    的会话：

    - 本函数会在网关的 `except Exception:` 分支里被调用（调用失败的记账），
      在异常处理路径上提交调用方会话，正是"半成品业务状态被落库"的经典入口；
    - 它是公开 helper，下一个"手上还有未提交 ORM 对象 / 多步事务 / 打算回滚"的
      调用方会被它静默提交，而文档又写着"记账失败不得打断业务"，没人会怀疑它。

    这与仓库既有风格一致——旁路写入自带 `SessionLocal()`，绝不进主请求事务
    （见 `app/services/knowledge/ingest_service.py` 模块 docstring：「每个函数自带
    Session（`SessionLocal()`）…绝不进主请求事务」，其测试也以
    `monkeypatch.setattr(module, "SessionLocal", …)` 注入测试库）。

    `db` 参数保留是为了不改变既有调用点签名，**不参与写入**；`enforce()` 则相反，
    它只读调用方会话、不动其事务。

    即使 `ai_guard_enabled=False`（只关闸门、不关记账），本函数照常写入，
    否则关闭闸门会同时让用量台账失明。
    """
    del db  # 显式说明：调用方会话不参与记账写入（见 docstring）
    session: Session | None = None
    try:
        session = SessionLocal()
        session.add(
            ModelUsageLedger(
                project_id=_project_scope(project_id),
                mission_id=mission_id,
                operation_type=str(operation_type or "")[:32],
                model_ref=str(model_ref or "")[:128],
                input_units=max(0, int(input_units or 0)),
                output_units=max(0, int(output_units or 0)),
                cost_amount=float(cost_amount or 0.0),
                latency_ms=max(0, int(latency_ms or 0)),
                created_at=datetime.now(),
            )
        )
        session.commit()
    except Exception:
        # 宽泛捕获是有意的：记账永远不能打断业务调用。
        logger.warning(
            "AI 用量记账失败（已忽略）: project=%s operation=%s",
            _project_scope(project_id),
            operation_type,
            exc_info=True,
        )
        if session is not None:
            try:
                session.rollback()
            except Exception:
                # 回滚失败也不再上抛。
                logger.warning("AI 用量记账失败后回滚会话也失败（已忽略）", exc_info=True)
    finally:
        if session is not None:
            try:
                session.close()
            except Exception:
                # 关闭失败同样不上抛。
                logger.warning("AI 用量记账会话关闭失败（已忽略）", exc_info=True)
