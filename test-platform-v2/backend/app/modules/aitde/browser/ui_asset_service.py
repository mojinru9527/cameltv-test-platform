"""AITDE V3.3 UI asset binding service (plan §2 ``ui_asset_bindings``).

Binds a ScenarioAdapter to its pre-existing legacy UI case / script so the
legacy-compiler adapter can resolve the asset a regression run must keep working,
without routing new scenarios through the LLM→Playwright path. Idempotent bind /
unbind / replace with a typed binding status.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import APIException
from app.modules.aitde.browser.models import UiAssetBinding
from app.modules.aitde.common.enums import UiAssetBindingStatus


def get_binding(db: Session, binding_id: int) -> UiAssetBinding:
    b = db.get(UiAssetBinding, binding_id)
    if not b:
        raise APIException(code=404, msg="UI 资产绑定不存在", http_status=404)
    return b


def find_binding(
    db: Session, scenario_adapter_id: int, legacy_ui_case_id: int | None = None
) -> UiAssetBinding | None:
    """Return the binding for a scenario adapter (optionally scoped by case)."""
    stmt = select(UiAssetBinding).where(
        UiAssetBinding.scenario_adapter_id == scenario_adapter_id
    )
    if legacy_ui_case_id is not None:
        stmt = stmt.where(UiAssetBinding.legacy_ui_case_id == legacy_ui_case_id)
    return db.scalar(stmt)


def bind_alias(
    db: Session,
    scenario_adapter_id: int,
    legacy_ui_case_id: int | None = None,
    legacy_ui_script_id: int | None = None,
) -> UiAssetBinding:
    """Idempotently (re)bind a scenario adapter to a legacy UI asset.

    If a binding already exists for the (adapter, case) pair, it is updated to
    BOUND; otherwise a new BOUND row is created.
    """
    existing = find_binding(db, scenario_adapter_id, legacy_ui_case_id)
    if existing is not None:
        existing.legacy_ui_case_id = legacy_ui_case_id
        existing.legacy_ui_script_id = legacy_ui_script_id
        existing.binding_status = UiAssetBindingStatus.BOUND.value
        db.commit()
        db.refresh(existing)
        return existing
    row = UiAssetBinding(
        scenario_adapter_id=scenario_adapter_id,
        legacy_ui_case_id=legacy_ui_case_id,
        legacy_ui_script_id=legacy_ui_script_id,
        binding_status=UiAssetBindingStatus.BOUND.value,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def unbind(db: Session, binding_id: int) -> UiAssetBinding:
    """Mark a binding UNBOUND (keep the row for audit history)."""
    b = get_binding(db, binding_id)
    b.binding_status = UiAssetBindingStatus.UNBOUND.value
    db.commit()
    db.refresh(b)
    return b


def list_bindings(
    db: Session,
    scenario_adapter_id: int | None = None,
    status: str | None = None,
) -> list[UiAssetBinding]:
    stmt = select(UiAssetBinding)
    if scenario_adapter_id is not None:
        stmt = stmt.where(UiAssetBinding.scenario_adapter_id == scenario_adapter_id)
    if status is not None:
        stmt = stmt.where(UiAssetBinding.binding_status == status)
    stmt = stmt.order_by(UiAssetBinding.id.desc())
    return list(db.scalars(stmt).all())


def to_dict(b: UiAssetBinding) -> dict[str, Any]:
    return {
        "id": b.id,
        "scenario_adapter_id": b.scenario_adapter_id,
        "legacy_ui_case_id": b.legacy_ui_case_id,
        "legacy_ui_script_id": b.legacy_ui_script_id,
        "binding_status": b.binding_status,
    }
