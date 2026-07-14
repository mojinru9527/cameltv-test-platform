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

    def test_update_service_from_other_project_returns_404(self, client, auth_headers, db):
        """P0: service update lookups are scoped to the active project."""
        from app.models.api_asset import ApiService

        service = ApiService(project_id=999, name="foreign-update-service", display_name="Before")
        db.add(service)
        db.commit()

        response = client.put(
            f"/api/v1/apitest/services/{service.id}",
            headers=auth_headers,
            json={"display_name": "After"},
        )

        assert response.status_code == 404
        db.expire_all()
        assert db.get(ApiService, service.id).display_name == "Before"


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

    def test_update_endpoint_from_other_project_returns_404(self, client, auth_headers, db):
        """P0: endpoint update lookups are scoped to the active project."""
        from app.models.api_asset import ApiEndpoint, ApiService

        service = ApiService(project_id=999, name="foreign-target-update-service")
        db.add(service)
        db.flush()
        endpoint = ApiEndpoint(
            project_id=999,
            service_id=service.id,
            method="GET",
            path="/foreign-target",
            summary="Before",
        )
        db.add(endpoint)
        db.commit()

        response = client.put(
            f"/api/v1/apitest/endpoints/{endpoint.id}",
            headers=auth_headers,
            json={"summary": "After"},
        )

        assert response.status_code == 404
        db.expire_all()
        assert db.get(ApiEndpoint, endpoint.id).summary == "Before"

    def test_create_endpoint_rejects_service_from_other_project(self, client, auth_headers, db):
        """P0: creating an endpoint cannot bind it to another project's service id."""
        from app.models.api_asset import ApiEndpoint, ApiService

        foreign_service = ApiService(project_id=999, name="foreign-create-binding")
        db.add(foreign_service)
        db.commit()

        response = client.post(
            "/api/v1/apitest/endpoints",
            headers=auth_headers,
            json={
                "service_id": foreign_service.id,
                "method": "GET",
                "path": "/invalid-binding",
            },
        )

        assert response.status_code == 404
        assert db.query(ApiEndpoint).filter(ApiEndpoint.project_id == 1).count() == 0

    def test_create_endpoint_accepts_service_from_current_project(self, client, auth_headers, db):
        """P0: a current-project service remains a valid endpoint parent."""
        from app.models.api_asset import ApiService

        service = ApiService(project_id=1, name="current-create-binding")
        db.add(service)
        db.commit()

        response = client.post(
            "/api/v1/apitest/endpoints",
            headers=auth_headers,
            json={"service_id": service.id, "method": "GET", "path": "/valid-binding"},
        )

        assert response.status_code == 200
        assert response.json()["data"]["service_id"] == service.id

    def test_update_endpoint_rejects_service_from_other_project(self, client, auth_headers, db):
        """P0: updating an endpoint cannot move it under another project's service id."""
        from app.models.api_asset import ApiEndpoint, ApiService

        current_service = ApiService(project_id=1, name="current-update-binding")
        foreign_service = ApiService(project_id=999, name="foreign-update-binding")
        db.add_all([current_service, foreign_service])
        db.flush()
        endpoint = ApiEndpoint(
            project_id=1,
            service_id=current_service.id,
            method="GET",
            path="/update-binding",
        )
        db.add(endpoint)
        db.commit()
        endpoint_id = endpoint.id
        current_service_id = current_service.id

        response = client.put(
            f"/api/v1/apitest/endpoints/{endpoint_id}",
            headers=auth_headers,
            json={"service_id": foreign_service.id},
        )

        assert response.status_code == 404
        db.expire_all()
        assert db.get(ApiEndpoint, endpoint_id).service_id == current_service_id

    def test_update_endpoint_accepts_service_from_current_project(self, client, auth_headers, db):
        """P1: an endpoint may be moved between services inside the active project."""
        from app.models.api_asset import ApiEndpoint, ApiService

        first_service = ApiService(project_id=1, name="first-update-binding")
        second_service = ApiService(project_id=1, name="second-update-binding")
        db.add_all([first_service, second_service])
        db.flush()
        endpoint = ApiEndpoint(
            project_id=1,
            service_id=first_service.id,
            method="GET",
            path="/valid-update-binding",
        )
        db.add(endpoint)
        db.commit()

        response = client.put(
            f"/api/v1/apitest/endpoints/{endpoint.id}",
            headers=auth_headers,
            json={"service_id": second_service.id},
        )

        assert response.status_code == 200
        assert response.json()["data"]["service_id"] == second_service.id


class TestProjectIsolationCaseGeneration:
    """Generated API cases must never read endpoint assets from another project."""

    def test_generate_cases_rejects_endpoint_from_other_project(self, client, auth_headers, db):
        """P0: a foreign endpoint id is indistinguishable from a missing endpoint."""
        from app.models.api_asset import ApiEndpoint, ApiService
        from app.models.test_case import TestCase

        service = ApiService(project_id=999, name="foreign-generation-service")
        db.add(service)
        db.flush()
        endpoint = ApiEndpoint(
            project_id=999,
            service_id=service.id,
            method="GET",
            path="/private",
        )
        db.add(endpoint)
        db.commit()

        response = client.post(
            "/api/v1/apitest/cases/generate",
            headers=auth_headers,
            json={"endpoint_id": endpoint.id, "templates": ["basic"]},
        )

        assert response.status_code == 404
        assert db.query(TestCase).count() == 0

    def test_batch_generate_treats_foreign_endpoint_as_missing(self, client, auth_headers, db):
        """P0: batch generation reports a foreign id as missing and creates no cases for it."""
        from app.models.api_asset import ApiEndpoint, ApiService
        from app.models.test_case import TestCase

        service = ApiService(project_id=999, name="foreign-batch-service")
        db.add(service)
        db.flush()
        endpoint = ApiEndpoint(
            project_id=999,
            service_id=service.id,
            method="POST",
            path="/private/batch",
        )
        db.add(endpoint)
        db.commit()

        response = client.post(
            "/api/v1/apitest/cases/batch-generate",
            headers=auth_headers,
            json={"endpoint_ids": [endpoint.id], "templates": ["basic"]},
        )

        assert response.status_code == 200
        data = response.json()["data"]
        assert data["total_generated"] == 0
        assert data["imported_case_ids"] == []
        assert data["errors"] == [{"endpoint_id": endpoint.id, "error": "接口资产不存在"}]
        assert db.query(TestCase).count() == 0

    def test_generated_case_persists_endpoint_reference(self, client, auth_headers, db):
        """P0: imported generated cases retain a stable endpoint marker for safe deletion."""
        from app.models.api_asset import ApiEndpoint, ApiService
        from app.models.test_case import TestCase

        service = ApiService(project_id=1, name="reference-generation-service")
        db.add(service)
        db.flush()
        endpoint = ApiEndpoint(
            project_id=1,
            service_id=service.id,
            method="GET",
            path="/referenced",
        )
        db.add(endpoint)
        db.commit()

        response = client.post(
            "/api/v1/apitest/cases/generate",
            headers=auth_headers,
            json={"endpoint_id": endpoint.id, "templates": ["basic"]},
        )

        assert response.status_code == 200
        imported_ids = response.json()["data"]["imported_case_ids"]
        assert imported_ids
        cases = db.query(TestCase).filter(TestCase.id.in_(imported_ids)).all()
        assert {case.api_spec_ref for case in cases} == {f"api_endpoint:{endpoint.id}"}


class TestProjectScopedAssetDeletion:
    """Service and endpoint deletion is project-scoped and reference-safe."""

    def test_delete_service_from_other_project_returns_404(self, client, auth_headers, db):
        """P0: a project cannot delete another project's service."""
        from app.models.api_asset import ApiService

        service = ApiService(project_id=999, name="foreign-delete-service")
        db.add(service)
        db.commit()

        response = client.delete(f"/api/v1/apitest/services/{service.id}", headers=auth_headers)

        assert response.status_code == 404
        assert db.get(ApiService, service.id) is not None

    def test_delete_service_returns_409_when_current_project_endpoint_references_it(
        self, client, auth_headers, db
    ):
        """P0: deleting a service with current-project endpoints is rejected."""
        from app.models.api_asset import ApiEndpoint, ApiService

        service = ApiService(project_id=1, name="referenced-delete-service")
        db.add(service)
        db.flush()
        endpoint = ApiEndpoint(project_id=1, service_id=service.id, method="GET", path="/service-ref")
        db.add(endpoint)
        db.commit()

        response = client.delete(f"/api/v1/apitest/services/{service.id}", headers=auth_headers)

        assert response.status_code == 409
        assert db.get(ApiService, service.id) is not None

    def test_historical_foreign_endpoint_reference_blocks_service_delete(
        self, client, auth_headers, db
    ):
        """P1: historical invalid bindings are retained rather than orphaned by deletion."""
        from app.models.api_asset import ApiEndpoint, ApiService

        service = ApiService(project_id=1, name="isolated-delete-service")
        db.add(service)
        db.flush()
        foreign_endpoint = ApiEndpoint(
            project_id=999,
            service_id=service.id,
            method="GET",
            path="/foreign-service-ref",
        )
        db.add(foreign_endpoint)
        db.commit()
        service_id = service.id

        response = client.delete(f"/api/v1/apitest/services/{service_id}", headers=auth_headers)

        assert response.status_code == 409
        assert db.get(ApiService, service_id) is not None
        assert db.get(ApiEndpoint, foreign_endpoint.id) is not None

    def test_delete_endpoint_from_other_project_returns_404(self, client, auth_headers, db):
        """P0: a project cannot delete another project's endpoint."""
        from app.models.api_asset import ApiEndpoint, ApiService

        service = ApiService(project_id=999, name="foreign-endpoint-delete-service")
        db.add(service)
        db.flush()
        endpoint = ApiEndpoint(project_id=999, service_id=service.id, method="GET", path="/foreign-delete")
        db.add(endpoint)
        db.commit()

        response = client.delete(f"/api/v1/apitest/endpoints/{endpoint.id}", headers=auth_headers)

        assert response.status_code == 404
        assert db.get(ApiEndpoint, endpoint.id) is not None

    def test_delete_endpoint_returns_409_when_generated_case_references_it(
        self, client, auth_headers, db
    ):
        """P0: a generated case's stable marker prevents endpoint deletion."""
        from app.models.api_asset import ApiEndpoint, ApiService
        from app.models.test_case import TestCase

        service = ApiService(project_id=1, name="referenced-endpoint-delete-service")
        db.add(service)
        db.flush()
        endpoint = ApiEndpoint(project_id=1, service_id=service.id, method="GET", path="/endpoint-ref")
        db.add(endpoint)
        db.flush()
        db.add(TestCase(
            project_id=1,
            title="Generated reference",
            case_type="api",
            api_spec_ref=f"api_endpoint:{endpoint.id}",
            source="ai_generated",
        ))
        db.commit()

        response = client.delete(f"/api/v1/apitest/endpoints/{endpoint.id}", headers=auth_headers)

        assert response.status_code == 409
        assert db.get(ApiEndpoint, endpoint.id) is not None

    def test_foreign_case_does_not_block_current_project_endpoint_delete(
        self, client, auth_headers, db
    ):
        """P1: another project's marker cannot block deletion in the active project."""
        from app.models.api_asset import ApiEndpoint, ApiService
        from app.models.test_case import TestCase

        service = ApiService(project_id=1, name="isolated-endpoint-delete-service")
        db.add(service)
        db.flush()
        endpoint = ApiEndpoint(project_id=1, service_id=service.id, method="DELETE", path="/isolated")
        db.add(endpoint)
        db.flush()
        db.add(TestCase(
            project_id=999,
            title="Foreign generated reference",
            case_type="api",
            api_spec_ref=f"api_endpoint:{endpoint.id}",
            source="ai_generated",
        ))
        db.commit()
        endpoint_id = endpoint.id

        response = client.delete(f"/api/v1/apitest/endpoints/{endpoint_id}", headers=auth_headers)

        assert response.status_code == 200
        assert db.get(ApiEndpoint, endpoint_id) is None


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

    def test_task_curl_rejects_item_from_other_project(
        self, client, auth_headers, api_task_factory, db
    ):
        """P0: curl generation must authorize the parent task before reading its item."""
        from app.models.api_asset import ApiExecutionTaskItem

        task = api_task_factory(project_id=999)
        item = ApiExecutionTaskItem(
            task_id=task.id,
            case_id=1,
            status="failed",
            request_snapshot='{"method":"GET","url":"https://private.example/api"}',
        )
        db.add(item)
        db.commit()

        response = client.get(
            f"/api/v1/apitest/tasks/{task.id}/items/{item.id}/curl",
            headers=auth_headers,
        )

        assert response.status_code == 404

    def test_task_failure_analysis_rejects_task_from_other_project(
        self, client, auth_headers, api_task_factory, db
    ):
        """P0: failure analysis must authorize task ownership before loading failed items."""
        from app.models.api_asset import ApiExecutionTaskItem

        task = api_task_factory(project_id=999)
        db.add(ApiExecutionTaskItem(
            task_id=task.id,
            case_id=1,
            status="failed",
            error_message="private upstream failure",
        ))
        db.commit()

        response = client.get(
            f"/api/v1/apitest/tasks/{task.id}/analysis",
            headers=auth_headers,
        )

        assert response.status_code == 404
