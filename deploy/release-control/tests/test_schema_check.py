from __future__ import annotations

from pathlib import Path

from cameltv_release.cli import schema_check


def test_checked_in_schemas_match_contract_models() -> None:
    schema_dir = Path(__file__).parents[1] / "schemas"

    assert schema_check(schema_dir) == []
