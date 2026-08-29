"""V33-010 Legacy compiler adapter tests."""
from __future__ import annotations

import pytest

from app.core.exceptions import APIException
from app.modules.aitde.browser.legacy_compiler import LegacyPlaywrightCompilerAdapter


def test_is_legacy_true_for_legacy_types():
    a = LegacyPlaywrightCompilerAdapter()
    for t in ("SPEC", "MANUAL", "PLAYWRIGHT", "spec"):
        assert a.is_legacy(t) is True


def test_is_legacy_false_for_new_command_ir():
    a = LegacyPlaywrightCompilerAdapter()
    assert a.is_legacy(None) is False
    assert a.is_legacy("COMMAND_IR") is False
    assert a.is_legacy("") is False


def test_assert_deterministic_path_blocks_new_scenario():
    with pytest.raises(APIException) as exc:
        LegacyPlaywrightCompilerAdapter.assert_deterministic_path("COMMAND_IR")
    assert exc.value.http_status == 400
    # legacy types keep their path
    LegacyPlaywrightCompilerAdapter.assert_deterministic_path("SPEC")


def test_compile_legacy_rejects_non_legacy_before_llm():
    a = LegacyPlaywrightCompilerAdapter()
    with pytest.raises(APIException) as exc:
        a.compile_legacy(db=None, case={"source_type": "COMMAND_IR"}, base_url="http://x")
    assert exc.value.http_status == 400
