from __future__ import annotations


def test_superadmin_wildcard_permission_can_approve_case_review(
    client,
    auth_headers,
    db_session,
) -> None:
    from app.models.test_case import TestCase

    case = TestCase(
        project_id=1,
        case_id="B60-REVIEW-001",
        title="Batch 60 体育用例评审权限",
        domain="接口测试",
        module="体育数据",
        case_type="api",
        priority="P0",
        status="active",
        review_status="draft",
    )
    db_session.add(case)
    db_session.commit()

    submitted = client.post(
        f"/api/v1/test-cases/{case.id}/review",
        json={"action": "submit", "comment": ""},
        headers=auth_headers,
    )
    assert submitted.status_code == 200
    assert submitted.json()["data"]["review_status"] == "submitted"

    approved = client.post(
        f"/api/v1/test-cases/{case.id}/review",
        json={"action": "approve", "comment": ""},
        headers=auth_headers,
    )
    assert approved.status_code == 200
    assert approved.json()["data"]["review_status"] == "approved"
