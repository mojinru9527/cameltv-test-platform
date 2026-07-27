"""Opt-in PostgreSQL concurrency regressions for Batch 48.

These tests are skipped unless both variables are explicitly supplied:

* ``BATCH48_RUN_PG_INTEGRATION=1``
* ``BATCH48_PG_INTEGRATION_URL=postgresql+psycopg2://...``

Always point the URL at a disposable database on a cloned PostgreSQL volume.
The URL is read from the environment and is never printed by this module.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import json
import os
from threading import Barrier
from uuid import uuid4

from fastapi.testclient import TestClient
import pytest
import sqlalchemy as sa
from sqlalchemy import func, select
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

from app.core.db import get_db
from app.core.security import create_access_token, hash_password
from app.main import app
from app.models.audit import AuditLog
from app.models.rbac import Permission, Role, RolePermission, UserRole
from app.models.release_bundle import ReleaseBundle
from app.models.requirement import RequirementDocument
from app.models.requirement_module import ModuleAdminLink, RequirementModule
from app.models.test_case import TestCase as CaseModel
from app.models.user import User
from app.services import requirement_service


_RUN_ENABLED = os.getenv("BATCH48_RUN_PG_INTEGRATION") == "1"
_DATABASE_URL = os.getenv("BATCH48_PG_INTEGRATION_URL", "")

pytestmark = pytest.mark.skipif(
    not (_RUN_ENABLED and _DATABASE_URL),
    reason="set explicit Batch 48 PostgreSQL integration environment",
)


@pytest.fixture(scope="module")
def pg_session_factory():
    assert make_url(_DATABASE_URL).get_backend_name() == "postgresql"
    engine = sa.create_engine(
        _DATABASE_URL,
        pool_size=12,
        max_overflow=4,
        pool_pre_ping=True,
        hide_parameters=True,
    )
    with engine.connect() as connection:
        assert connection.scalar(sa.text("SELECT 1")) == 1
    factory = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
        future=True,
    )
    try:
        yield factory
    finally:
        engine.dispose()


def test_parallel_import_is_idempotent_and_counts_do_not_drift(
    pg_session_factory,
) -> None:
    project_id = uuid4().int % 1_000_000_000 + 1
    with pg_session_factory.begin() as db:
        document = RequirementDocument(
            project_id=project_id,
            creator_id=1,
            title=f"batch48-pg-import-{uuid4().hex}",
            file_type="md",
            source_ref="integration-only",
            content="integration-only",
            status="generated",
        )
        db.add(document)
        db.flush()
        document_id = document.id

    case = {
        "index": 0,
        "title": "parallel source identity",
        "domain": "需求服务",
        "module": "并发导入",
        "case_type": "manual",
        "priority": "P0",
        "preconditions": "独立 PostgreSQL 测试库",
        "steps": [{"step": 1, "desc": "并行导入", "expected": "仅一条"}],
        "expected_result": "最终仅保留一条",
    }
    workers = 4
    start = Barrier(workers)

    def import_once() -> dict:
        with pg_session_factory() as db:
            start.wait(timeout=10)
            return requirement_service.import_cases(
                db,
                document_id,
                [case],
                project_id,
            )

    with ThreadPoolExecutor(max_workers=workers) as pool:
        results = list(pool.map(lambda _index: import_once(), range(workers)))

    assert sorted(
        (result["imported"], result["skipped"], result["total"])
        for result in results
    ) == [(0, 1, 1)] * (workers - 1) + [(1, 0, 1)]

    with pg_session_factory() as db:
        assert db.scalar(
            select(func.count(CaseModel.id)).where(
                CaseModel.project_id == project_id,
                CaseModel.source_doc_id == document_id,
                CaseModel.source_case_index == 0,
            )
        ) == 1
        document = db.get(RequirementDocument, document_id)
        assert document is not None
        assert document.imported_count == 1
        assert document.imported_func_count == 1
        assert document.imported_api_count == 0
        assert json.loads(document.imported_func_indices) == [0]
        assert json.loads(document.imported_api_indices) == []


def test_parallel_admin_link_requests_return_one_success_and_conflicts(
    pg_session_factory,
) -> None:
    run_key = uuid4().hex
    project_id = uuid4().int % 1_000_000_000 + 1
    with pg_session_factory.begin() as db:
        user = User(
            username=f"batch48_pg_{run_key}",
            password=hash_password(uuid4().hex),
            nickname="Batch 48 PG",
            email=f"{run_key}@integration.invalid",
            status=1,
        )
        wildcard = db.scalar(select(Permission).where(Permission.code == "*"))
        if wildcard is None:
            wildcard = Permission(code="*", name="Super", type="api")
            db.add(wildcard)
        role = Role(
            code=f"batch48-pg-{run_key}",
            name="Batch 48 PG",
            data_scope="global",
        )
        db.add_all([user, role])
        db.flush()
        db.add_all(
            [
                RolePermission(role_id=role.id, permission_id=wildcard.id),
                UserRole(user_id=user.id, role_id=role.id, project_id=0),
            ]
        )
        bundle = ReleaseBundle(
            project_id=project_id,
            name=f"batch48-pg-{run_key}",
        )
        db.add(bundle)
        db.flush()
        client_module = RequirementModule(
            project_id=project_id,
            release_bundle_id=bundle.id,
            name="client",
            node_type="module",
            platform="WEB",
        )
        admin_module = RequirementModule(
            project_id=project_id,
            release_bundle_id=bundle.id,
            name="admin",
            node_type="module",
            platform="ADMIN",
        )
        db.add_all([client_module, admin_module])
        db.flush()
        user_id = user.id
        client_module_id = client_module.id
        admin_module_id = admin_module.id

    def override_get_db():
        with pg_session_factory() as db:
            yield db

    previous_overrides = dict(app.dependency_overrides)
    app.dependency_overrides[get_db] = override_get_db
    workers = 6
    start = Barrier(workers)
    payload = {
        "client_module_id": client_module_id,
        "admin_module_id": admin_module_id,
        "relation_type": "links_to_admin",
    }
    headers = {
        "Authorization": f"Bearer {create_access_token(user_id)}",
        "X-Project-Id": str(project_id),
    }

    try:
        with TestClient(app) as client:
            def create_once() -> tuple[int, dict]:
                start.wait(timeout=10)
                response = client.post(
                    "/api/v1/requirement-modules/admin-links",
                    headers=headers,
                    json=payload,
                )
                return response.status_code, response.json()

            with ThreadPoolExecutor(max_workers=workers) as pool:
                responses = list(
                    pool.map(lambda _index: create_once(), range(workers))
                )
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous_overrides)

    successes = [body for status, body in responses if status == 200]
    conflicts = [body for status, body in responses if status == 409]
    assert len(successes) == 1
    assert len(conflicts) == workers - 1
    assert all(
        body.get("code") == 409 and "已存在" in str(body)
        for body in conflicts
    )

    with pg_session_factory() as db:
        identity = (
            ModuleAdminLink.project_id == project_id,
            ModuleAdminLink.client_module_id == client_module_id,
            ModuleAdminLink.admin_module_id == admin_module_id,
            ModuleAdminLink.relation_type == "links_to_admin",
        )
        assert db.scalar(
            select(func.count(ModuleAdminLink.id)).where(*identity)
        ) == 1
        assert db.scalar(
            select(func.count(AuditLog.id)).where(
                AuditLog.project_id == project_id,
                AuditLog.action == "module:admin_link_create",
            )
        ) == 1
