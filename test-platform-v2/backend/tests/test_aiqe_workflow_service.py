"""M2 / TA-010：Workflow 定义存储/审批冻结单测。"""
from __future__ import annotations

import pytest

from app.aiqe.services.workflow_service import (
    WorkflowImmutableError,
    approve_workflow,
    create_workflow,
    get_workflow,
    update_graph,
)
from app.aiqe.services.workflow_validator import workflow_checksum


def graph(version_note: str = "v1") -> dict:
    return {
        "schema_version": "1.0",
        "nodes": [
            {
                "key": "a",
                "driver": "http",
                "depends_on": [],
                "input": {"method": "GET"},
                "outputs": {"x": "$.x"},
            }
        ],
        "edges": [],
        "run_policy": {"max_parallel_nodes": 1, "fail_fast": False},
        "note": version_note,
    }


def test_create_and_checksum(db_session):
    row = create_workflow(db_session, project_id=1, graph=graph())
    assert row.version == 1
    assert row.checksum == workflow_checksum(graph())
    assert row.approval_status == "pending"
    assert get_workflow(db_session, row.id).id == row.id


def test_approve_freezes_graph(db_session):
    row = create_workflow(db_session, project_id=1, graph=graph())
    approve_workflow(db_session, row.id, approved_by=1)
    assert row.approval_status == "approved"
    assert row.approved_at is not None
    with pytest.raises(WorkflowImmutableError):
        update_graph(db_session, row.id, graph("changed"))


def test_update_pending_allowed(db_session):
    row = create_workflow(db_session, project_id=1, graph=graph())
    update_graph(db_session, row.id, graph("v2"))
    assert row.checksum == workflow_checksum(graph("v2"))


def test_new_version_autoincrements(db_session):
    create_workflow(db_session, project_id=1, graph=graph())
    second = create_workflow(db_session, project_id=1, graph=graph())
    assert second.version == 2
