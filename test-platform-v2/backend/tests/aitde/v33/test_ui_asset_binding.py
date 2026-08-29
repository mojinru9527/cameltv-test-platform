"""V3.3 UI asset binding service tests (plan §2 ``ui_asset_bindings``).

Covers idempotent bind/replace, unbind, list filtering, and the UNBOUND default.
"""

from __future__ import annotations

import pytest

from app.core.exceptions import APIException
from app.modules.aitde.browser import ui_asset_service
from app.modules.aitde.common.enums import UiAssetBindingStatus


def test_bind_creates_bound_row(db):
    b = ui_asset_service.bind_alias(
        db, scenario_adapter_id=7, legacy_ui_case_id=101, legacy_ui_script_id=202
    )
    assert b.id is not None
    assert b.scenario_adapter_id == 7
    assert b.legacy_ui_case_id == 101
    assert b.legacy_ui_script_id == 202
    assert b.binding_status == UiAssetBindingStatus.BOUND.value


def test_bind_idempotent_updates_same_adapter_case(db):
    b1 = ui_asset_service.bind_alias(
        db, 7, legacy_ui_case_id=101, legacy_ui_script_id=202
    )
    b2 = ui_asset_service.bind_alias(
        db, 7, legacy_ui_case_id=101, legacy_ui_script_id=999
    )
    assert b1.id == b2.id
    assert b2.legacy_ui_script_id == 999
    rows = ui_asset_service.list_bindings(db)
    assert len(rows) == 1


def test_unbind_sets_status(db):
    b = ui_asset_service.bind_alias(db, 7, legacy_ui_case_id=101)
    unbound = ui_asset_service.unbind(db, b.id)
    assert unbound.binding_status == UiAssetBindingStatus.UNBOUND.value


def test_list_filters_by_adapter_and_status(db):
    ui_asset_service.bind_alias(db, 7, legacy_ui_case_id=101)
    ui_asset_service.bind_alias(db, 7, legacy_ui_case_id=102)
    ui_asset_service.bind_alias(db, 9, legacy_ui_case_id=201)

    assert len(ui_asset_service.list_bindings(db)) == 3
    assert len(ui_asset_service.list_bindings(db, scenario_adapter_id=7)) == 2
    assert (
        len(
            ui_asset_service.list_bindings(
                db, scenario_adapter_id=7, status=UiAssetBindingStatus.UNBOUND.value
            )
        )
        == 0
    )


def test_find_binding_scoped_by_case(db):
    b = ui_asset_service.bind_alias(db, 7, legacy_ui_case_id=101)
    found = ui_asset_service.find_binding(db, 7, 101)
    assert found is not None and found.id == b.id
    assert ui_asset_service.find_binding(db, 7, 999) is None
    assert ui_asset_service.find_binding(db, 88) is None


def test_missing_binding_raises_404(db):
    with pytest.raises(APIException) as exc:
        ui_asset_service.get_binding(db, 9999)
    assert exc.value.http_status == 404


def test_to_dict_round_trips(db):
    b = ui_asset_service.bind_alias(db, 7, legacy_ui_case_id=101)
    d = ui_asset_service.to_dict(b)
    assert d["scenario_adapter_id"] == 7
    assert d["legacy_ui_case_id"] == 101
    assert d["binding_status"] == UiAssetBindingStatus.BOUND.value
