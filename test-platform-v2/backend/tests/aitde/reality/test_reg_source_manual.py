"""V3.9-R4 REG-001 — manual caller-supplied change input is untrusted."""
from __future__ import annotations

from app.modules.aitde.smart_regression.schemas import DetectIn


def test_detect_in_defaults_to_manual_untrusted():
    d = DetectIn(change_type="OPENAPI", baseline={"a": 1}, current={"b": 2})
    # A caller-supplied baseline/current is a MANUAL source, never trusted for a Gate.
    assert d.source_type == "MANUAL"
    assert d.trusted is False


def test_detect_in_can_be_marked_trusted_explicitly():
    # Only an explicit provider-driven request may be trusted.
    d = DetectIn(change_type="OPENAPI", source_type="PROVIDER", trusted=True)
    assert d.trusted is True
