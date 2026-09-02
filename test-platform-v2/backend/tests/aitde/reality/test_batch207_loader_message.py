"""Batch 207 — smart-regression loader error must be actionable.

An unresolvable snapshot ref raises a clear error naming the supported refs
and the Leader C-condition (never a silent empty snapshot).
"""
from __future__ import annotations

import pytest

from app.modules.aitde.smart_regression.providers import change_provider_registry


def test_unresolved_loader_error_is_actionable(db):
    with pytest.raises(ValueError) as exc:
        change_provider_registry.load_and_diff(
            "OPENAPI", db, 1, "store://missing", "store://missing2"
        )
    text = str(exc.value)
    assert "unresolved source_ref" in text
    assert "inline" in text
    assert "C4" in text
