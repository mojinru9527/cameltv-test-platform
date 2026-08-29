"""Legacy dataset adapter tests (V32-015)."""
from __future__ import annotations

import pytest

from app.core.exceptions import APIException
from app.models.dataset import Dataset
from app.modules.aitde.common.enums import DataSourceType
from app.modules.aitde.data import legacy_adapter


def _dataset(db, source_type="csv", name="订单数据集"):
    ds = Dataset(project_id=1, name=name, source_type=source_type, row_count=42)
    db.add(ds)
    db.flush()
    return ds


def test_csv_dataset_becomes_static_source(db):
    dataset = _dataset(db, source_type="csv")
    source = legacy_adapter.ensure_legacy_dataset_source(db, dataset, 1, 9)
    assert source.source_type == DataSourceType.STATIC.value
    assert source.access_mode == "READONLY"
    # Idempotent: a second call returns the same source, no duplicate link.
    again = legacy_adapter.ensure_legacy_dataset_source(db, dataset, 1, 9)
    assert again.id == source.id


def test_sql_dataset_rejected(db):
    dataset = _dataset(db, source_type="sql")
    with pytest.raises(APIException) as exc:
        legacy_adapter.ensure_legacy_dataset_source(db, dataset, 1, 9)
    assert exc.value.http_status == 400
    assert "SecretRef" in exc.value.msg


def test_get_data_source_for_legacy(db):
    dataset = _dataset(db, source_type="json")
    source = legacy_adapter.ensure_legacy_dataset_source(db, dataset, 1, 9)
    resolved = legacy_adapter.get_data_source_for_legacy(db, dataset.id, 1)
    assert resolved.id == source.id


def test_get_data_source_for_legacy_missing(db):
    with pytest.raises(APIException) as exc:
        legacy_adapter.get_data_source_for_legacy(db, 9999, 1)
    assert exc.value.http_status == 404
