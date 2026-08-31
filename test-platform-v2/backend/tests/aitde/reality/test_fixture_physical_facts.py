"""V3.9-R2 DATA-003 — fixture physical-execution fact columns exist."""
from __future__ import annotations

from app.modules.aitde.data.models import FixtureEntity


def test_fixture_entity_carries_physical_facts():
    cols = set(FixtureEntity.__table__.c.keys())
    # An entity must be able to answer "was it really created/found/verified".
    assert "physical_status" in cols
    assert "verification_status" in cols
    assert "provision_step_id" in cols
    assert "verified_at" in cols
    assert "cleanup_status" in cols
    assert "cleanup_verified_at" in cols
