"""Query-budget regressions for Batch 244 N+1 removal."""
from __future__ import annotations

from types import SimpleNamespace

from sqlalchemy import event

from app.models.api_asset import ApiEndpoint, ApiService
from app.models.test_case import TestCase
from app.models.test_plan import TestPlan
from app.services import dashboard_service, openapi_import_service, test_plan_service


def _capture_statements(db):
    statements: list[str] = []

    def capture(_conn, _cursor, statement, _parameters, _context, _executemany):
        statements.append(statement)

    engine = db.get_bind()
    event.listen(engine, "before_cursor_execute", capture)
    return statements, lambda: event.remove(engine, "before_cursor_execute", capture)


def test_openapi_confirm_prefetches_existing_endpoints_once(db_session):
    service = ApiService(project_id=1, name="batch244", display_name="batch244")
    db_session.add(service)
    db_session.flush()
    db_session.add(ApiEndpoint(project_id=1, service_id=service.id, method="GET", path="/old"))
    db_session.commit()

    spec = {
        "info": {"version": "1.0"},
        "paths": {
            f"/item-{index}": {"get": {"summary": f"item {index}"}}
            for index in range(40)
        },
    }
    statements, remove = _capture_statements(db_session)
    try:
        result = openapi_import_service.confirm_openapi_import(
            db_session,
            spec,
            project_id=1,
            service_name="batch244",
        )
    finally:
        remove()

    endpoint_selects = [s for s in statements if "FROM API_ENDPOINT" in s.upper()]
    assert len(endpoint_selects) == 1
    assert result["created_count"] == 40


def test_add_cases_loads_test_cases_in_one_batch(db_session):
    plan = TestPlan(project_id=1, name="batch244-plan")
    db_session.add(plan)
    db_session.flush()
    cases = [
        TestCase(project_id=1, title=f"case-{index}", case_type="manual")
        for index in range(30)
    ]
    db_session.add_all(cases)
    db_session.commit()
    case_ids = [case.id for case in cases]
    plan_id = plan.id

    statements, remove = _capture_statements(db_session)
    try:
        added = test_plan_service.add_cases(
            db_session,
            plan_id,
            case_ids,
            project_id=1,
        )
    finally:
        remove()

    case_selects = [s for s in statements if "FROM TEST_CASE" in s.upper()]
    assert added == 30
    assert len(case_selects) == 1


def test_cross_project_trends_use_bounded_queries(monkeypatch):
    class FakeResult:
        def all(self):
            return []

    class FakeDb:
        def __init__(self):
            self.calls = 0

        def execute(self, _statement):
            self.calls += 1
            return FakeResult()

    monkeypatch.setattr(
        dashboard_service,
        "get_dashboard_stats",
        lambda db, project_id, start_date, end_date: {
            "total_cases": 0,
            "total_plans": 0,
            "api_cases": 0,
            "pass_rate": 0.0,
        },
    )
    monkeypatch.setattr(
        dashboard_service,
        "_execution_filter_for_project",
        lambda db, project_id, start_date, end_date: (0, 0, 0),
    )
    monkeypatch.setattr(
        "app.services.project_service.projects_for_user",
        lambda db, user_id, is_superadmin: [
            SimpleNamespace(id=1, code="a", name="A"),
            SimpleNamespace(id=2, code="b", name="B"),
        ],
    )

    db = FakeDb()
    result = dashboard_service.get_cross_project_stats(db, user_id=7)

    assert len(result["trends"]["pass_rate"]) == 7
    assert len(result["trends"]["defects"]) == 7
    assert db.calls == 3  # defect count + execution window + defect window


