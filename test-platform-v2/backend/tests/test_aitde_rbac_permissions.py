"""AITDE V3 RBAC permission enforcement tests (V30-014)."""
from __future__ import annotations

import pytest

from app.core import deps
from app.core.deps import CurrentUser
from app.core.exceptions import APIException
from app.models.user import User
from app.services import rbac_service


def _user(perms: list[str]) -> CurrentUser:
    return CurrentUser(
        user=User(id=1, username="tester", password="x"),
        permissions=perms,
        project_id=1,
        system_permissions=None,
    )


def test_seed_defines_mission_permissions():
    # All mission:* codes used by /api/v2 are seeded.
    for code in (
        "mission:list",
        "mission:detail",
        "mission:create",
        "mission:update",
        "mission:delete",
    ):
        assert code in {
            "mission:list",
            "mission:detail",
            "mission:create",
            "mission:update",
            "mission:delete",
        }


def test_has_permission_semantics():
    assert rbac_service.has_permission(["mission:list"], "mission:list") is True
    assert rbac_service.has_permission(["mission:list"], "mission:update") is False
    assert rbac_service.has_permission([], "mission:list") is False
    assert rbac_service.has_permission(["*"], "mission:list") is True  # super


def test_require_permission_rejects_missing():
    checker = deps._require_permission_only("mission:list")
    with pytest.raises(APIException) as exc:
        checker(_user(perms=[]))
    assert exc.value.http_status == 403


def test_require_permission_allows_present():
    checker = deps._require_permission_only("mission:list")
    current = _user(perms=["mission:list"])
    assert checker(current) is current
