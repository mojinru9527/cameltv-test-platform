"""Project isolation tests for API test routes.

Verify that query `project_id` cannot override `X-Project-Id` header
and that cross-project access to tasks is denied.
"""
import pytest


@pytest.fixture
def db(db_session):
    """Alias db_session as db for test readability."""
    return db_session


@pytest.fixture
def api_task_factory(db_session):
    """Factory to create an ApiExecutionTask with a given project_id."""
    from app.models.api_asset import ApiExecutionTask

    def _create(project_id: int, **kwargs):
        task = ApiExecutionTask(
            project_id=project_id,
            task_id=f"ISO-TASK-{project_id}",
            name=f"Isolation Test Task p{project_id}",
            total=1,
            **kwargs,
        )
        db_session.add(task)
        db_session.commit()
        db_session.refresh(task)
        return task

    return _create


class TestProjectIsolationServices:
    """GET /apitest/services — query project_id must be ignored."""

    def test_services_ignore_query_project_id(self, client, auth_headers, db):
        """Query project_id=999 is ignored; only X-Project-Id:1 services returned."""
        from app.models.api_asset import ApiService

        svc1 = ApiService(project_id=1, name="svc-project1")
        svc999 = ApiService(project_id=999, name="svc-project999")
        db.add_all([svc1, svc999])
        db.commit()

        headers = {**auth_headers, "X-Project-Id": "1"}
        resp = client.get("/api/v1/apitest/services?project_id=999", headers=headers)
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert all(item["project_id"] == 1 for item in data)
        names = [item["name"] for item in data]
        assert "svc-project1" in names
        assert "svc-project999" not in names

    def test_services_without_x_project_id_rejected(self, client, auth_headers):
        """Missing X-Project-Id should trigger 400 when project is required."""
        headers = {k: v for k, v in auth_headers.items() if k != "X-Project-Id"}
        resp = client.get("/api/v1/apitest/services", headers=headers)
        assert resp.status_code in (400, 403)


class TestProjectIsolationEndpoints:
    """GET /apitest/endpoints — query project_id must be ignored."""

    def test_endpoints_ignore_query_project_id(self, client, auth_headers, db):
        """Query project_id=999 is ignored; only header project endpoints returned."""
        from app.models.api_asset import ApiService, ApiEndpoint

        svc1 = ApiService(project_id=1, name="svc-ep-1")
        svc999 = ApiService(project_id=999, name="svc-ep-999")
        db.add_all([svc1, svc999])
        db.flush()

        ep1 = ApiEndpoint(project_id=1, service_id=svc1.id, method="GET", path="/api/p1")
        ep999 = ApiEndpoint(project_id=999, service_id=svc999.id, method="POST", path="/api/p999")
        db.add_all([ep1, ep999])
        db.commit()

        headers = {**auth_headers, "X-Project-Id": "1"}
        resp = client.get("/api/v1/apitest/endpoints?project_id=999", headers=headers)
        assert resp.status_code == 200
        data = resp.json()["data"]["items"]
        paths = [item["path"] for item in data]
        assert "/api/p1" in paths
        assert "/api/p999" not in paths


class TestProjectIsolationTasks:
    """Task endpoints must enforce project isolation."""

    def test_tasks_detail_enforces_current_project(self, client, auth_headers, api_task_factory):
        """Accessing a task from a different project must be denied."""
        task = api_task_factory(project_id=999)
        headers = {**auth_headers, "X-Project-Id": "1"}
        resp = client.get(f"/api/v1/apitest/tasks/{task.id}", headers=headers)
        assert resp.status_code in (403, 404)

    def test_tasks_cancel_enforces_current_project(self, client, auth_headers, api_task_factory):
        """Cancelling a task from a different project must be denied."""
        task = api_task_factory(project_id=999, status="running")
        headers = {**auth_headers, "X-Project-Id": "1"}
        resp = client.post(f"/api/v1/apitest/tasks/{task.id}/cancel", headers=headers)
        assert resp.status_code in (403, 404)

    def test_tasks_list_filters_by_header_project(self, client, auth_headers, db):
        """Task list should only return tasks from the header's project."""
        from app.models.api_asset import ApiExecutionTask

        t1 = ApiExecutionTask(project_id=1, task_id="LIST-1", name="Task P1", total=1)
        t999 = ApiExecutionTask(project_id=999, task_id="LIST-999", name="Task P999", total=1)
        db.add_all([t1, t999])
        db.commit()

        headers = {**auth_headers, "X-Project-Id": "1"}
        resp = client.get("/api/v1/apitest/tasks?project_id=999", headers=headers)
        assert resp.status_code == 200
        data = resp.json()["data"]["items"]
        names = [item["name"] for item in data]
        assert "Task P1" in names
        assert "Task P999" not in names

    def test_tasks_create_uses_header_project(self, client, auth_headers, db):
        """Creating a task should use the header project, not a query param."""
        from app.models.test_case import TestCase

        tc = TestCase(
            project_id=1, title="API Case for create", case_type="api",
            api_method="GET", api_endpoint="https://httpbin.org/get",
            api_assertions='[{"type":"status_code","expected":200,"operator":"eq"}]',
        )
        db.add(tc)
        db.commit()

        headers = {**auth_headers, "X-Project-Id": "1"}
        resp = client.post(
            "/api/v1/apitest/tasks?project_id=999",
            json={"name": "Isolation Create Test", "case_ids": [tc.id]},
            headers=headers,
        )
        # project_id=999 in query is ignored, should use project 1 from header
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["project_id"] == 1

    def test_services_create_uses_header_project(self, client, auth_headers):
        """Creating a service should use the header project."""
        headers = {**auth_headers, "X-Project-Id": "1"}
        resp = client.post(
            "/api/v1/apitest/services?project_id=999",
            json={"name": "header-svc", "display_name": "Header Service"},
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["project_id"] == 1
        assert data["name"] == "header-svc"
