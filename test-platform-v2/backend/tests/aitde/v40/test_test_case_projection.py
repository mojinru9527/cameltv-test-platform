"""AITDE V4.0 (V40-004) TestCase projection cutover policy tests."""

from __future__ import annotations

import pytest

from app.core.exceptions import APIException
from app.models.test_case import TestCase as CaseModel
from app.modules.aitde.legacy_cutover.models import LegacyObjectMapping
from app.modules.aitde.legacy_cutover.service import TestCaseProjectionPolicy


def _add_case(db, project_id=1) -> CaseModel:
    case = CaseModel(project_id=project_id, title="旧用例", case_type="manual")
    db.add(case)
    db.commit()
    db.refresh(case)
    return case


def _bind_case(db, case_id, canonical_type="TEST_SCENARIO", status="VERIFIED"):
    mapping = LegacyObjectMapping(
        project_id=1,
        legacy_type="TEST_CASE",
        legacy_id=case_id,
        canonical_type=canonical_type,
        canonical_id=5,
        migration_status=status,
    )
    db.add(mapping)
    db.commit()
    db.refresh(mapping)
    return mapping


def test_unbound_case_allows_business_expected_write(db):
    case = _add_case(db)
    # No mapping -> not scenario-bound -> no raise.
    TestCaseProjectionPolicy.enforce_business_expected_write(
        db, 1, case.id, {"expected_result": "new expectation", "priority": "P1"}
    )


def test_bound_case_blocks_business_expected_write(db):
    case = _add_case(db)
    _bind_case(db, case.id)
    with pytest.raises(APIException) as exc:
        TestCaseProjectionPolicy.enforce_business_expected_write(
            db, 1, case.id, {"expected_result": "mutate expected"}
        )
    assert exc.value.http_status == 409
    assert "scenario" in str(exc.value.msg).lower() or "投影" in str(exc.value.msg)


def test_bound_case_allows_non_business_fields(db):
    case = _add_case(db)
    _bind_case(db, case.id)
    # priority is not a business-expected field -> allowed even when bound.
    TestCaseProjectionPolicy.enforce_business_expected_write(
        db, 1, case.id, {"priority": "P0", "title": "retitle"}
    )


def test_non_scenario_mapping_is_not_bound(db):
    case = _add_case(db)
    _bind_case(db, case.id, canonical_type="API_ASSET")
    binding = TestCaseProjectionPolicy.scenario_binding(db, 1, case.id)
    assert binding is None
    TestCaseProjectionPolicy.enforce_business_expected_write(
        db, 1, case.id, {"expected_result": "ok"}
    )


def test_pending_mapping_is_not_bound(db):
    case = _add_case(db)
    _bind_case(db, case.id, status="PENDING")
    assert TestCaseProjectionPolicy.scenario_binding(db, 1, case.id) is None
