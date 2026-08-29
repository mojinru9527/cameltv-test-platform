"""DataSource policy tests (V32-001).

Verifies the V3.2 data-source creation policy:
* Production environment data sources are READONLY only (READWRITE rejected).
* The referenced secret value is never stored or serialized.
* PROD_TEMPLATE is a reserved-only enum and cannot be created in V3.2.
* Data sources are project-scoped.
"""
from __future__ import annotations

import json

import pytest

from app.core.exceptions import APIException
from app.models.environment import Environment
from app.modules.aitde.common.enums import (
    DataSourceAccessMode,
    DataSourceStatus,
    DataSourceType,
)
from app.modules.aitde.data import service
from app.modules.aitde.data.schemas import DataSourceCreate


def _env(db, env_type="test", is_production=False) -> Environment:
    env = Environment(
        project_id=1, name="环境", env_type=env_type, is_production=is_production
    )
    db.add(env)
    db.flush()
    return env


def test_create_plain_readonly_ok(db):
    payload = DataSourceCreate(
        source_type=DataSourceType.MYSQL,
        name="只读订单库",
        network_zone="cn-east",
        secret_ref="sec/order-readonly",
        config={"host": "192.0.2.1", "port": 3306},
    )
    row = service.create_data_source(db, payload, project_id=1, user_id=9)
    assert row.id is not None
    assert row.source_type == "MYSQL"
    assert row.access_mode == "READONLY"
    assert row.status == DataSourceStatus.ACTIVE.value
    assert row.secret_ref == "sec/order-readonly"
    assert json.loads(row.config_json)["port"] == 3306


def test_create_readwrite_on_test_env_ok(db):
    env = _env(db, env_type="test")
    payload = DataSourceCreate(
        source_type=DataSourceType.POSTGRES,
        name="测试写库",
        environment_id=env.id,
        access_mode=DataSourceAccessMode.READWRITE,
    )
    row = service.create_data_source(db, payload, project_id=1, user_id=9)
    assert row.access_mode == "READWRITE"


def test_create_readwrite_on_prod_env_rejected(db):
    env = _env(db, env_type="prod", is_production=True)
    payload = DataSourceCreate(
        source_type=DataSourceType.POSTGRES,
        name="生产写库",
        environment_id=env.id,
        access_mode=DataSourceAccessMode.READWRITE,
    )
    with pytest.raises(APIException) as exc:
        service.create_data_source(db, payload, project_id=1, user_id=9)
    assert exc.value.http_status == 400
    assert "READONLY" in exc.value.msg or "只读" in exc.value.msg


def test_create_readonly_on_prod_env_ok(db):
    env = _env(db, env_type="prod", is_production=True)
    payload = DataSourceCreate(
        source_type=DataSourceType.API,
        name="生产只读",
        environment_id=env.id,
        access_mode=DataSourceAccessMode.READONLY,
    )
    row = service.create_data_source(db, payload, project_id=1, user_id=9)
    assert row.access_mode == "READONLY"


def test_reserved_prod_template_rejected(db):
    payload = DataSourceCreate(source_type=DataSourceType.PROD_TEMPLATE, name="模板")
    with pytest.raises(APIException) as exc:
        service.create_data_source(db, payload, project_id=1, user_id=9)
    assert exc.value.http_status == 400


def test_secret_in_config_rejected_at_create(db):
    payload = DataSourceCreate(
        source_type=DataSourceType.MYSQL,
        name="订单库",
        config={"host": "1.1.1.1", "password": "super-secret"},
    )
    with pytest.raises(APIException) as exc:
        service.create_data_source(db, payload, project_id=1, user_id=9)
    assert exc.value.http_status == 400
    assert "secret_ref" in exc.value.msg


def test_secret_value_never_returned(db):
    payload = DataSourceCreate(
        source_type=DataSourceType.MYSQL,
        name="订单库",
        secret_ref="sec/order",
        config={"host": "1.1.1.1", "port": 3306},
    )
    row = service.create_data_source(db, payload, project_id=1, user_id=9)
    serialized = json.dumps(service.to_dict(row), ensure_ascii=False)
    assert "super-secret" not in serialized
    assert service.to_dict(row)["secret_ref"] == "sec/order"


def test_list_and_get_scoped_to_project(db):
    service.create_data_source(
        db, DataSourceCreate(source_type=DataSourceType.STATIC, name="静态1"),
        project_id=1, user_id=9,
    )
    service.create_data_source(
        db, DataSourceCreate(source_type=DataSourceType.STATIC, name="静态2"),
        project_id=2, user_id=9,
    )
    rows = service.list_data_sources(db, project_id=1)
    assert len(rows) == 1
    assert rows[0].name == "静态1"
    assert service.get_data_source(db, rows[0].id, 1).id == rows[0].id
    with pytest.raises(APIException):
        service.get_data_source(db, rows[0].id, 2)
