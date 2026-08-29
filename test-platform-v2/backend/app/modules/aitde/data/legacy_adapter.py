"""LegacyDatasetAdapter (V32-015).

Existing CSV/JSON datasets become a STATIC DataSource. An old ``source_type=sql``
dataset is *not* treated as a V3.2 DB runtime source — a formal DB DataSource
must be created through SecretRef / Policy / Typed Driver.
"""
from __future__ import annotations

import json

from sqlalchemy.orm import Session

from app.core.exceptions import APIException
from app.models.dataset import Dataset
from app.modules.aitde.common.enums import (
    DataSourceAccessMode,
    DataSourceStatus,
    DataSourceType,
)
from app.modules.aitde.data import repository
from app.modules.aitde.data.models import DataSource

_STATIC_TYPES = {"csv", "json"}


def ensure_legacy_dataset_source(
    db: Session, dataset: Dataset, project_id: int, user_id: int
) -> DataSource:
    """Find or create a STATIC DataSource backing a legacy CSV/JSON dataset.

    Idempotent via the ``legacy_dataset_links`` unique key. ``sql`` datasets are
    rejected (never silently mapped to a DB runtime source).
    """
    if dataset.source_type == "sql":
        raise APIException(
            code=400,
            msg="SQL 数据集不能直接映射为 V3.2 DB Runtime，请通过 SecretRef/Policy/Typed Driver 创建正式 DB DataSource",
            http_status=400,
        )
    if dataset.source_type not in _STATIC_TYPES:
        raise APIException(
            code=400, msg=f"不支持的数据集类型：{dataset.source_type}", http_status=400
        )

    existing_link = repository.get_legacy_link_by_dataset(db, dataset.id)
    if existing_link:
        row = repository.get_data_source(db, existing_link.data_source_id, project_id)
        if row:
            return row
        raise APIException(code=404, msg="关联数据源不存在", http_status=404)

    data_source = repository.create_data_source(
        db,
        {
            "environment_id": None,
            "source_type": DataSourceType.STATIC.value,
            "name": f"legacy-dataset-{dataset.name or dataset.id}",
            "network_zone": "",
            "secret_ref": None,
            "access_mode": DataSourceAccessMode.READONLY.value,
            "config_json": json.dumps(
                {
                    "legacy_dataset_id": dataset.id,
                    "legacy_source_type": dataset.source_type,
                    "row_count": dataset.row_count,
                },
                ensure_ascii=False,
            ),
            "policy_ref": None,
            "status": DataSourceStatus.ACTIVE.value,
        },
        project_id,
        user_id,
    )
    repository.create_legacy_link(
        db, {"data_source_id": data_source.id, "legacy_dataset_id": dataset.id}
    )
    db.commit()
    db.refresh(data_source)
    return data_source


def get_data_source_for_legacy(
    db: Session, legacy_dataset_id: int, project_id: int
) -> DataSource:
    link = repository.get_legacy_link_by_dataset(db, legacy_dataset_id)
    if not link:
        raise APIException(code=404, msg="遗留数据集未关联数据源", http_status=404)
    row = repository.get_data_source(db, link.data_source_id, project_id)
    if not row:
        raise APIException(code=404, msg="关联数据源不存在", http_status=404)
    return row
