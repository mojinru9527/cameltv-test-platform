"""Review service — test case review state machine + transition history.

Follows the same pattern as defect_service.py transition logic:
  - Module-level _TRANSITIONS dict (from → allowed targets)
  - transition_review() validates, transitions, records history
  - get_review_history() returns transition timeline
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.test_case import TestCase
from app.models.test_case_review import TestCaseReviewTransition
from app.models.user import User

# ── State machine ─────────────────────────────────────

_TRANSITIONS: dict[str, set[str]] = {
    "draft":     {"submitted"},
    "submitted": {"approved", "rejected", "draft"},  # draft = 撤回
    "rejected":  {"submitted", "draft"},             # submitted = 修改重提, draft = 撤回
    # approved = terminal (modifying the case resets to draft)
}

_REVIEW_LABELS: dict[str, str] = {
    "draft": "草稿", "submitted": "已提交", "approved": "已通过", "rejected": "已驳回",
}


def allowed_actions(review_status: str) -> list[str]:
    """Return list of allowed actions from the given review status."""
    targets = _TRANSITIONS.get(review_status, set())
    # Map target status to action name
    action_map = {
        "submitted": "submit",
        "approved": "approve",
        "rejected": "reject",
        "draft": "withdraw",
    }
    return sorted({action_map.get(t, t) for t in targets})


def transition_review(
    db: Session,
    case_id: int,
    action: str,
    *,
    project_id: int,
    operator_id: int = 0,
    operator_name: str = "",
    comment: str = "",
) -> dict | None:
    """Transition a test case's review status.

    Actions: submit (提交评审), approve (通过), reject (驳回), withdraw (撤回)

    Returns the updated case dict, or None if case not found.
    Raises ValueError for invalid transitions.
    """
    # Map action → target status
    action_to_target = {
        "submit":    "submitted",
        "approve":   "approved",
        "reject":    "rejected",
        "withdraw":  "draft",
    }
    if action not in action_to_target:
        raise ValueError(f"无效的评审操作: {action}，允许: submit/approve/reject/withdraw")

    to_status = action_to_target[action]

    case = db.scalar(
        select(TestCase).where(TestCase.id == case_id, TestCase.project_id == project_id)
    )
    if not case:
        return None

    current = case.review_status
    valid_targets = _TRANSITIONS.get(current, set())

    if to_status not in valid_targets:
        allowed_labels = ", ".join(
            f"{_REVIEW_LABELS.get(t, t)}" for t in sorted(valid_targets)
        )
        raise ValueError(
            f"不允许从「{_REVIEW_LABELS.get(current, current)}」"
            f"转为「{_REVIEW_LABELS.get(to_status, to_status)}」。"
            f"允许的流转: {allowed_labels}"
        )

    from_status = case.review_status
    case.review_status = to_status
    case.review_comment = comment
    case.reviewer_id = operator_id

    # Record transition
    t = TestCaseReviewTransition(
        case_id=case_id,
        from_status=from_status,
        to_status=to_status,
        comment=comment,
        reviewer_id=operator_id,
        reviewer_name=operator_name,
    )
    db.add(t)
    db.flush()
    db.refresh(case)

    return _case_review_to_dict(case)


def get_review_history(db: Session, case_id: int, project_id: int) -> list[dict]:
    """Get review transition history for a case (ordered by time asc)."""
    case = db.scalar(
        select(TestCase).where(TestCase.id == case_id, TestCase.project_id == project_id)
    )
    if not case:
        return []

    return [
        {
            "id": t.id,
            "case_id": t.case_id,
            "from_status": t.from_status,
            "from_label": _REVIEW_LABELS.get(t.from_status, t.from_status),
            "to_status": t.to_status,
            "to_label": _REVIEW_LABELS.get(t.to_status, t.to_status),
            "comment": t.comment,
            "reviewer_id": t.reviewer_id,
            "reviewer_name": t.reviewer_name,
            "created_at": t.created_at.isoformat() if t.created_at else None,
        }
        for t in case.review_transitions
    ]


def _case_review_to_dict(case: TestCase) -> dict:
    """Minimal dict for review response — reuse full _row_to_dict when needed."""
    from app.services.test_case_service import _row_to_dict
    return _row_to_dict(case)
