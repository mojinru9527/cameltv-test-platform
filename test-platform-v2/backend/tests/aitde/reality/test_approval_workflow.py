"""V3.9-R3 TEMP-002 — Approval workflow wiring + signal guard.

Verifies the previously-dead ``create_approval`` repository path is wired through
the service, that the approval carries the ``temporal_workflow_id`` so a later
resolve can signal the waiting workflow, and that resolving an approval degrades
gracefully (persistence wins even when the Temporal signal cannot be delivered).
Also verifies the signal guard classifies an already-completed workflow as benign
instead of a failure (never swallowed/unreported as a broken approval).
"""
from __future__ import annotations

from app.modules.aitde.common.enums import ApprovalStatus
from app.modules.aitde.workflow import service
from app.modules.aitde.workflow.models import ApprovalRequest


def test_create_approval_persists_and_lists(db):
    approval = service.create_approval(
        db,
        project_id=1,
        action_type="db_exec",
        mission_id=7,
        run_id=42,
        payload={"driver": "database", "action": "db_exec"},
        temporal_workflow_id="wf-approve-1",
    )
    assert approval["status"] == ApprovalStatus.PENDING.value
    assert approval["policy_decision"] == "REQUIRE_APPROVAL"
    # temporal_workflow_id is carried in request_json so resolve can signal it.
    assert "wf-approve-1" in approval["request_json"]

    listing = service.list_approvals(db, 1)
    assert any(a["id"] == approval["id"] for a in listing)
    row = db.get(ApprovalRequest, approval["id"])
    assert row.requested_by == 0


def test_resolve_approval_persists_and_degrades_gracefully(db, caplog):
    approval = service.create_approval(
        db, project_id=1, action_type="db_exec", mission_id=7, run_id=42,
        payload={"driver": "database"}, temporal_workflow_id="wf-approve-2",
    )
    # Temporal is disabled in tests, so the signal degrades but the approval
    # resolution itself must always persist.
    resolved = service.resolve_approval(db, approval["id"], 1, approved=True, approved_by=9)
    assert resolved["status"] == ApprovalStatus.APPROVED.value
    assert resolved["approved_by"] == 9
    assert resolved["resolved_at"] is not None
    row = db.get(ApprovalRequest, approval["id"])
    assert row.status == ApprovalStatus.APPROVED.value


def test_is_workflow_already_completed_classification():
    class AlreadyCompleted(Exception):
        pass

    assert service._is_workflow_already_completed(AlreadyCompleted("workflow already completed")) is True
    assert service._is_workflow_already_completed(ValueError("temporal error")) is False
    assert service._is_workflow_already_completed(Exception("already completed")) is True
