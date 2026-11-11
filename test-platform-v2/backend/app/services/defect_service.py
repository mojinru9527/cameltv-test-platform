"""Defect service — list / get / create / update / delete / stats / transitions / comments / attachments."""
from __future__ import annotations

import os
import logging
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.base_service import batch_field_map, batch_user_names, paginate
from app.core.config import settings
from app.models.defect import (
    Defect,
    DefectAttachment,
    DefectComment,
    DefectRegression,
    DefectTransition,
)

logger = logging.getLogger(__name__)
from app.models.test_case import TestCase
from app.models.test_plan import TestExecution, TestPlan, TestPlanCase
from app.models.user import User


def get_user_display_name(db: Session, user_id: int) -> str:
    """返回用户展示名（nickname or username），供路由层组装通知等场景复用。"""
    if not user_id:
        return ""
    u = db.get(User, user_id)
    if not u:
        return ""
    return u.nickname or u.username


def _generate_defect_id(db: Session, project_id: int) -> str:
    """Generate DEF-YYYYMMDD-NNN unique within project."""
    today = datetime.now(timezone.utc).strftime("%Y%m%d")
    count = db.scalar(
        select(func.count(Defect.id)).where(
            Defect.project_id == project_id,
            Defect.defect_id.like(f"DEF-{today}-%"),
        )
    ) or 0
    return f"DEF-{today}-{count + 1:03d}"


def _defect_to_dict(r: Defect, creator_name: str = "", assignee_name: str = "", case_title: str = "") -> dict:
    return {
        "id": r.id,
        "project_id": r.project_id,
        "defect_id": r.defect_id,
        "title": r.title,
        "description": r.description,
        "severity": r.severity,
        "status": r.status,
        "case_id": r.case_id,
        "execution_id": r.execution_id,
        "aitde_run_id": r.aitde_run_id,
        "aiqe_run_id": r.aiqe_run_id,
        "aiqe_node_run_id": r.aiqe_node_run_id,
        "reproduction_steps": r.reproduction_steps_json or [],
        "evidence_refs": r.evidence_refs_json or [],
        "ac_refs": r.ac_refs_json or [],
        "is_draft": bool(r.is_draft),
        "assignee_id": r.assignee_id,
        "external_id": r.external_id,
        "external_url": r.external_url,
        "creator_id": r.creator_id,
        "resolved_at": r.resolved_at,
        "created_at": r.created_at,
        "updated_at": r.updated_at,
        "creator_name": creator_name,
        "assignee_name": assignee_name,
        "case_title": case_title,
    }


def list_defects(
    db: Session,
    project_id: int,
    severity: str | None = None,
    status: str | None = None,
    assignee_id: int | None = None,
    keyword: str = "",
    page: int = 1,
    page_size: int = 20,
):
    """Paginated defect list — batch-loaded names (no N+1)."""
    base = select(Defect).where(Defect.project_id == project_id)
    if severity:
        base = base.where(Defect.severity == severity)
    if status:
        base = base.where(Defect.status == status)
    if assignee_id is not None:
        base = base.where(Defect.assignee_id == assignee_id)
    if keyword:
        # OR 只包住 title/defect_id。project_id 与上面的 severity/status/assignee 靠
        # .where() 累加保持 AND；把隔离条件塞进 or_ 会让编号检索跨项目泄漏数据。
        # 不含 external_id（禅道/Jira 编号）：它不作为编号在列表展示，纳入只会扩大匹配面。
        base = base.where(
            or_(Defect.title.contains(keyword), Defect.defect_id.contains(keyword))
        )

    rows, total = paginate(db, base.order_by(Defect.created_at.desc()), page=page, page_size=page_size)

    # Batch load all referenced users and cases in two queries (was N+1 per row)
    creator_ids = {r.creator_id for r in rows}
    assignee_ids = {r.assignee_id for r in rows}
    all_user_ids = creator_ids | assignee_ids
    case_ids = {r.case_id for r in rows if r.case_id}

    user_map = batch_user_names(db, all_user_ids)
    case_map = batch_field_map(db, TestCase, case_ids, "title")

    items = [
        _defect_to_dict(
            r,
            creator_name=user_map.get(r.creator_id, ""),
            assignee_name=user_map.get(r.assignee_id, ""),
            case_title=case_map.get(r.case_id, "") if r.case_id else "",
        )
        for r in rows
    ]
    return items, total


def list_defects_by_external_id(
    db: Session, project_id: int, *, linked: bool
) -> list[Defect]:
    """按外部同步状态列出缺陷（integration sync-now 复用）。

    linked=True  → external_id 非空（已关联外部系统）；
    linked=False → external_id 为空（未关联）。
    """
    stmt = select(Defect).where(Defect.project_id == project_id)
    if linked:
        stmt = stmt.where(Defect.external_id != "")
    else:
        stmt = stmt.where(Defect.external_id == "")
    return list(db.scalars(stmt).all())


def get_defect(db: Session, defect_id: int, project_id: int) -> dict | None:
    r = db.scalar(select(Defect).where(Defect.id == defect_id, Defect.project_id == project_id))
    if not r:
        return None

    creator_name = ""
    assignee_name = ""
    case_title = ""
    if r.creator_id:
        u = db.get(User, r.creator_id)
        if u:
            creator_name = u.nickname or u.username
    if r.assignee_id:
        u = db.get(User, r.assignee_id)
        if u:
            assignee_name = u.nickname or u.username
    if r.case_id:
        tc = db.get(TestCase, r.case_id)
        if tc:
            case_title = tc.title
    return _defect_to_dict(r, creator_name, assignee_name, case_title)


def _validate_defect_references(
    db: Session,
    *,
    project_id: int,
    case_id: int | None,
    execution_id: int | None,
) -> None:
    """Keep case/execution references inside one project and one case."""
    if case_id is not None:
        case_exists = db.scalar(
            select(TestCase.id).where(
                TestCase.id == case_id,
                TestCase.project_id == project_id,
            )
        )
        if not case_exists:
            raise ValueError("用例不存在或不属于当前项目")

    if execution_id is not None:
        execution_case_id = db.scalar(
            select(TestPlanCase.case_id)
            .join(TestExecution, TestExecution.plan_case_id == TestPlanCase.id)
            .join(TestPlan, TestPlan.id == TestPlanCase.plan_id)
            .join(TestCase, TestCase.id == TestPlanCase.case_id)
            .where(
                TestExecution.id == execution_id,
                TestPlan.project_id == project_id,
                TestCase.project_id == project_id,
            )
        )
        if execution_case_id is None:
            raise ValueError("执行记录不存在或不属于当前项目")
        if case_id is not None and case_id != execution_case_id:
            raise ValueError("执行记录与关联用例不一致")


def create_defect(db: Session, data, creator_id: int, project_id: int) -> dict:
    _validate_defect_references(
        db,
        project_id=project_id,
        case_id=data.case_id,
        execution_id=data.execution_id,
    )

    defect_id = _generate_defect_id(db, project_id)
    r = Defect(
        project_id=project_id,
        defect_id=defect_id,
        title=data.title,
        description=data.description,
        severity=data.severity,
        status="open",
        case_id=data.case_id,
        execution_id=data.execution_id,
        assignee_id=data.assignee_id or 0,
        external_id=data.external_id,
        external_url=data.external_url,
        creator_id=creator_id,
    )
    db.add(r)
    db.flush()
    return _defect_to_dict(r)


def update_defect(db: Session, defect_id: int, data, project_id: int) -> dict | None:
    r = db.scalar(select(Defect).where(Defect.id == defect_id, Defect.project_id == project_id))
    if not r:
        return None

    update_data = data.model_dump(exclude_none=True)
    _validate_defect_references(
        db,
        project_id=project_id,
        case_id=update_data.get("case_id", r.case_id),
        execution_id=update_data.get("execution_id", r.execution_id),
    )

    # B5：status 变更必须走缺陷状态机（非法转移抛明确错误，派生字段仅在合法流转时维护）。
    # 复用 transition_defect 的校验/流转历史/resolved_at 维护；同 status 更新为幂等 no-op。
    if "status" in update_data and update_data["status"] != r.status:
        target_raw = update_data.pop("status")
        transition_defect(
            db, defect_id, target_raw,
            project_id=project_id,
        )
        # 同一 session identity map，r 与 transition_defect 内部对象一致；重新取以防刷新差异
        r = db.scalar(select(Defect).where(Defect.id == defect_id, Defect.project_id == project_id))

    update_fields = [
        "title", "description", "severity",
        "case_id", "execution_id", "assignee_id",
        "external_id", "external_url", "resolved_at",
    ]
    for k in update_fields:
        if k in update_data:
            setattr(r, k, update_data[k])

    db.flush()
    db.refresh(r)

    creator_name = ""
    assignee_name = ""
    case_title = ""
    if r.creator_id:
        u = db.get(User, r.creator_id)
        if u:
            creator_name = u.nickname or u.username
    if r.assignee_id:
        u = db.get(User, r.assignee_id)
        if u:
            assignee_name = u.nickname or u.username
    if r.case_id:
        tc = db.get(TestCase, r.case_id)
        if tc:
            case_title = tc.title
    return _defect_to_dict(r, creator_name, assignee_name, case_title)


def _cascade_knowledge(db, project_id: int, source_id: int) -> None:
    # C147-9: 业务删除级联同步知识切片（缺陷 -> knowledge_source deprecated）
    from app.services.knowledge.knowledge_cleanup import mark_business_deleted

    mark_business_deleted(db, project_id=project_id, source_type="defect", source_id=source_id)


def delete_defect(db: Session, defect_id: int, project_id: int) -> bool:
    r = db.scalar(select(Defect).where(Defect.id == defect_id, Defect.project_id == project_id))
    if not r:
        return False
    db.delete(r)
    _cascade_knowledge(db, project_id, defect_id)
    db.flush()
    return True


def get_defect_stats(db: Session, project_id: int) -> dict:
    rows = db.execute(
        select(Defect.severity, Defect.status)
        .where(Defect.project_id == project_id)
    ).all()

    total = len(rows)
    by_severity: dict[str, int] = {}
    by_status: dict[str, int] = {}
    for sev, st in rows:
        by_severity[sev] = by_severity.get(sev, 0) + 1
        by_status[st] = by_status.get(st, 0) + 1

    return {"total": total, "by_severity": by_severity, "by_status": by_status}


# ── State machine ─────────────────────────────────────

# Allowed transitions: from → {to}
_TRANSITIONS: dict[str, set[str]] = {
    "open":           {"confirmed", "rejected"},
    "confirmed":      {"fixing", "rejected"},
    "fixing":         {"pending_review", "rejected"},
    "pending_review": {"closed", "fixing"},
    "closed":         {"open"},          # reopen
    "rejected":       {"open"},          # reopen
}

# Human-readable labels
_STATUS_LABELS: dict[str, str] = {
    "open": "新建", "confirmed": "已确认", "fixing": "修复中",
    "pending_review": "待回归", "closed": "已关闭", "rejected": "已拒绝",
}

# Old status mapping for backward compatibility
_LEGACY_MAP: dict[str, str] = {
    "in_progress": "fixing",
    "resolved": "closed",
    "wontfix": "rejected",
}


def allowed_transitions(status: str) -> list[str]:
    """Return list of statuses that can be transitioned to from the given status."""
    # Normalize legacy statuses
    current = _LEGACY_MAP.get(status, status)
    return sorted(_TRANSITIONS.get(current, set()))


def transition_defect(
    db: Session,
    defect_id: int,
    to_status: str,
    *,
    project_id: int,
    operator_id: int = 0,
    operator_name: str = "",
    comment: str = "",
) -> dict | None:
    """Transition a defect to a new status, validating the state machine.

    Returns the updated defect dict or None if defect not found.
    Raises ValueError for invalid transitions.
    """
    r = db.scalar(
        select(Defect).where(Defect.id == defect_id, Defect.project_id == project_id)
    )
    if not r:
        return None

    current = _LEGACY_MAP.get(r.status, r.status)
    valid = _TRANSITIONS.get(current, set())

    if to_status not in valid:
        labels = ", ".join(f"{s}({_STATUS_LABELS.get(s, s)})" for s in sorted(valid))
        raise ValueError(
            f"不允许从「{_STATUS_LABELS.get(current, current)}」"
            f"转为「{_STATUS_LABELS.get(to_status, to_status)}」。"
            f"允许的流转: {labels}"
        )

    from_status = r.status
    r.status = to_status

    # Auto-set resolved_at on close, clear on reopen
    if to_status == "closed":
        r.resolved_at = datetime.now(timezone.utc)
    elif to_status == "open" and current in ("closed", "rejected"):
        r.resolved_at = None

    # Record transition
    t = DefectTransition(
        defect_id=defect_id,
        from_status=from_status,
        to_status=to_status,
        comment=comment,
        operator_id=operator_id,
        operator_name=operator_name,
    )
    db.add(t)
    db.flush()
    db.refresh(r)

    return _defect_to_dict(r)


def get_transitions(db: Session, defect_id: int, project_id: int) -> list[dict]:
    """Get transition history for a defect (ordered by time asc)."""
    r = db.scalar(
        select(Defect).where(Defect.id == defect_id, Defect.project_id == project_id)
    )
    if not r:
        return []
    return [
        {
            "id": t.id,
            "from_status": t.from_status,
            "from_label": _STATUS_LABELS.get(t.from_status, t.from_status),
            "to_status": t.to_status,
            "to_label": _STATUS_LABELS.get(t.to_status, t.to_status),
            "comment": t.comment,
            "operator_id": t.operator_id,
            "operator_name": t.operator_name,
            "created_at": t.created_at.isoformat() if t.created_at else None,
        }
        for t in r.transitions
    ]


# ── Comments ──────────────────────────────────────────

def list_comments(db: Session, defect_id: int, project_id: int) -> list[dict]:
    """List comments for a defect."""
    r = db.scalar(
        select(Defect).where(Defect.id == defect_id, Defect.project_id == project_id)
    )
    if not r:
        return []
    rows = db.scalars(
        select(DefectComment).where(DefectComment.defect_id == defect_id)
        .order_by(DefectComment.created_at.asc())
    ).all()
    return [
        {
            "id": c.id, "defect_id": c.defect_id,
            "content": c.content, "author_id": c.author_id,
            "author_name": c.author_name,
            "created_at": c.created_at.isoformat() if c.created_at else None,
        }
        for c in rows
    ]


def create_comment(
    db: Session, defect_id: int, content: str,
    *, project_id: int, author_id: int = 0, author_name: str = "",
) -> dict | None:
    """Add a comment to a defect."""
    r = db.scalar(
        select(Defect).where(Defect.id == defect_id, Defect.project_id == project_id)
    )
    if not r:
        return None
    c = DefectComment(
        defect_id=defect_id, content=content,
        author_id=author_id, author_name=author_name,
    )
    db.add(c)
    db.flush()
    return {
        "id": c.id, "defect_id": c.defect_id,
        "content": c.content, "author_id": c.author_id,
        "author_name": c.author_name,
        "created_at": c.created_at.isoformat() if c.created_at else None,
    }


# ── Attachments ────────────────────────────────────────

def _attachments_dir() -> Path:
    """Resolve the attachments root directory."""
    data_root = settings.data_dir or os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data"
    )
    return Path(data_root) / "attachments" / "defects"


def upload_attachment(
    db: Session,
    defect_id: int,
    filename: str,
    content: bytes,
    *,
    project_id: int,
    uploader_id: int = 0,
    uploader_name: str = "",
) -> dict | None:
    """Save an uploaded file to disk and record metadata in DB."""
    r = db.scalar(
        select(Defect).where(Defect.id == defect_id, Defect.project_id == project_id)
    )
    if not r:
        return None

    # Ensure unique filename on disk
    ext = os.path.splitext(filename)[1]
    stored_name = f"{uuid.uuid4().hex}{ext}"
    target_dir = _attachments_dir() / str(defect_id)
    target_dir.mkdir(parents=True, exist_ok=True)
    file_path = target_dir / stored_name
    file_path.write_bytes(content)

    a = DefectAttachment(
        defect_id=defect_id,
        filename=filename,
        stored_path=str(file_path.relative_to(_attachments_dir().parent)),
        file_size=len(content),
        mime_type=_guess_mime(filename),
        uploader_id=uploader_id,
        uploader_name=uploader_name,
    )
    db.add(a)
    db.flush()
    return _attachment_to_dict(a)


def list_attachments(db: Session, defect_id: int, project_id: int) -> list[dict]:
    """List attachment metadata for a defect."""
    r = db.scalar(
        select(Defect).where(Defect.id == defect_id, Defect.project_id == project_id)
    )
    if not r:
        return []
    rows = db.scalars(
        select(DefectAttachment)
        .where(DefectAttachment.defect_id == defect_id)
        .order_by(DefectAttachment.created_at.asc())
    ).all()
    return [_attachment_to_dict(a) for a in rows]


def get_attachment(db: Session, attachment_id: int, project_id: int) -> tuple[dict, Path] | None:
    """Return (metadata_dict, absolute_file_path) or None if not found."""
    a = db.scalar(
        select(DefectAttachment)
        .join(Defect, Defect.id == DefectAttachment.defect_id)
        .where(DefectAttachment.id == attachment_id, Defect.project_id == project_id)
    )
    if not a:
        return None
    file_path = _attachments_dir().parent / a.stored_path
    if not file_path.exists():
        return None
    return _attachment_to_dict(a), file_path


def delete_attachment(db: Session, attachment_id: int, project_id: int) -> bool:
    """Delete attachment record and its file on disk."""
    a = db.scalar(
        select(DefectAttachment)
        .join(Defect, Defect.id == DefectAttachment.defect_id)
        .where(DefectAttachment.id == attachment_id, Defect.project_id == project_id)
    )
    if not a:
        return False
    file_path = _attachments_dir().parent / a.stored_path
    try:
        file_path.unlink(missing_ok=True)
    except OSError:
        logger.warning("附件文件删除失败: %s", file_path)
    db.delete(a)
    db.flush()
    return True


def _attachment_to_dict(a: DefectAttachment) -> dict:
    return {
        "id": a.id,
        "defect_id": a.defect_id,
        "filename": a.filename,
        "stored_path": a.stored_path,
        "file_size": a.file_size,
        "mime_type": a.mime_type,
        "uploader_id": a.uploader_id,
        "uploader_name": a.uploader_name,
        "created_at": a.created_at.isoformat() if a.created_at else None,
    }


def _guess_mime(filename: str) -> str:
    import mimetypes
    mime, _ = mimetypes.guess_type(filename)
    return mime or "application/octet-stream"


# ── AIQE 失败一键转缺陷（TA-026）────────────────────────────

EVIDENCE_PREFIXES = ("artifact:", "event:", "run:", "node:", "signal:")
AC_REF_PATTERN = re.compile(r"^AC[A-Za-z0-9_-]*$")


def validate_reproduction(
    reproduction_steps: list[dict] | None,
    evidence_refs: list[str] | None,
    ac_refs: list[str] | None,
) -> None:
    if not reproduction_steps:
        raise ValueError("结构化复现步骤不能为空")
    for index, step in enumerate(reproduction_steps, start=1):
        if not isinstance(step, dict):
            raise ValueError(f"复现步骤 #{index} 必须是对象")
        if not str(step.get("action") or "").strip():
            raise ValueError(f"复现步骤 #{index} 缺少 action")
        if not str(step.get("expected") or "").strip():
            raise ValueError(f"复现步骤 #{index} 缺少 expected")
    if not evidence_refs:
        raise ValueError("证据引用不能为空")
    for ref in evidence_refs:
        if not any(str(ref).startswith(prefix) for prefix in EVIDENCE_PREFIXES):
            raise ValueError(f"非法证据引用（需 artifact:/event:/run:/node:/signal:）: {ref}")
    if not ac_refs:
        raise ValueError("必须关联至少 1 条验收标准（AC）")
    for ref in ac_refs:
        if not AC_REF_PATTERN.match(str(ref)):
            raise ValueError(f"非法 AC 引用: {ref}")


def create_draft_from_failure(
    db: Session,
    *,
    project_id: int,
    title: str,
    run_id: str,
    reproduction_steps: list[dict],
    evidence_refs: list[str],
    ac_refs: list[str],
    node_run_id: str | None = None,
    description: str = "",
    severity: str = "P2",
    creator_id: int = 0,
    assignee_id: int = 0,
) -> Defect:
    """失败一键转 Defect Draft：结构化复现步骤 + 证据跳转 + AC 关联。

    同一 Run + 标题重复调用返回已有草稿（幂等）。
    """
    if not str(title or "").strip():
        raise ValueError("缺陷标题不能为空")
    validate_reproduction(reproduction_steps, evidence_refs, ac_refs)
    existing = db.scalar(
        select(Defect).where(
            Defect.project_id == project_id,
            Defect.aiqe_run_id == run_id,
            Defect.title == title,
            Defect.is_draft.is_(True),
        )
    )
    if existing is not None:
        return existing
    row = Defect(
        project_id=project_id,
        defect_id=_generate_defect_id(db, project_id),
        title=title.strip(),
        description=description,
        severity=severity,
        status="open",
        aiqe_run_id=run_id,
        aiqe_node_run_id=node_run_id,
        reproduction_steps_json=reproduction_steps,
        evidence_refs_json=evidence_refs,
        ac_refs_json=ac_refs,
        is_draft=True,
        creator_id=creator_id,
        assignee_id=assignee_id,
    )
    db.add(row)
    db.flush()
    return row


# ── 一键回归（TA-027）─────────────────────────────────────

def create_regression(
    db: Session,
    *,
    defect_id: int,
    fixed_sha: str,
    previous_run_id: str | None = None,
    verification_run_id: str | None = None,
) -> DefectRegression:
    defect = db.get(Defect, defect_id)
    if defect is None:
        raise ValueError(f"缺陷不存在: {defect_id}")
    sha = (fixed_sha or "").strip()
    if len(sha) < 7:
        raise ValueError("fixed_sha 至少 7 位")
    row = DefectRegression(
        defect_id=defect_id,
        fixed_sha=sha,
        previous_run_id=previous_run_id,
        verification_run_id=verification_run_id,
        status="pending" if verification_run_id is None else "passed",
    )
    db.add(row)
    db.flush()
    return row


def compare_runs(
    previous_results: list[dict],
    current_results: list[dict],
) -> dict:
    """对比旧/新 Run 的 assertion 状态；纯函数，不改旧 Run。"""
    prev = {str(r.get("assertion_key")): str(r.get("status")) for r in previous_results}
    curr = {str(r.get("assertion_key")): str(r.get("status")) for r in current_results}
    fixed = sorted(k for k, v in prev.items() if v != "PASS" and curr.get(k) == "PASS")
    regressed = sorted(k for k, v in prev.items() if v == "PASS" and curr.get(k) not in (None, "PASS"))
    still_failing = sorted(k for k, v in prev.items() if v != "PASS" and curr.get(k) not in (None, "PASS"))
    new_assertions = sorted(k for k in curr if k not in prev)
    return {
        "fixed": fixed,
        "regressed": regressed,
        "still_failing": still_failing,
        "new_assertions": new_assertions,
        "total_previous": len(prev),
        "total_current": len(curr),
    }
