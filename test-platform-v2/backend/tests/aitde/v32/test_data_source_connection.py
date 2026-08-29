"""DataSource connection test tests (V32-004).

Verifies the connection-test contract: STATIC pings ok, DB sources report a
credential-free category on failure, and the secret reference never leaks.
"""
from __future__ import annotations

import json

from app.modules.aitde.common.enums import DataSourceType
from app.modules.aitde.data import service
from app.modules.aitde.data.models import DataSource


def _source(db, source_type, config=None, secret_ref=None):
    ds = DataSource(
        project_id=1,
        source_type=source_type,
        name="s",
        config_json=json.dumps(config or {}, ensure_ascii=False),
        secret_ref=secret_ref,
        created_by=9,
    )
    db.add(ds)
    db.flush()
    return ds


def test_static_connection_ok(db):
    ds = _source(db, DataSourceType.STATIC.value)
    result = service.probe_data_source_connection(db, ds.id, 1)
    assert result["ok"] is True
    assert result["source_type"] == "STATIC"


def test_db_connection_failure_is_categorized_no_secret(db):
    ds = _source(
        db,
        DataSourceType.POSTGRES.value,
        config={"host": "127.0.0.1", "port": 5432, "database": "x", "username": "u"},
        secret_ref="secret/pg",
    )
    result = service.probe_data_source_connection(db, ds.id, 1)
    assert result["ok"] is False
    assert result["detail"].startswith("unavailable:")
    serialized = json.dumps(result, ensure_ascii=False)
    assert "secret/pg" not in serialized
    assert result["secret_leaked"] is False


def test_unsupported_type_reports_category(db):
    ds = _source(db, DataSourceType.API.value)
    result = service.probe_data_source_connection(db, ds.id, 1)
    assert result["ok"] is False
    assert result["detail"] == "unsupported:API"


def test_connection_missing_source_rejected(db):
    import pytest

    from app.core.exceptions import APIException

    with pytest.raises(APIException) as exc:
        service.probe_data_source_connection(db, 9999, 1)
    assert exc.value.http_status == 404
