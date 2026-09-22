"""Batch 271 — 已下线菜单权限的存量数据对账（用户选项 C）。

要点：
1. 只解绑 `HIDDEN_MENU_CODES`（硬下线），**不碰**软下线（DISABLED_MENUS，可逆配置）；
2. 保留 `sys_permission` 行（老书签与 ?tab= 深链靠它继续走重定向）；
3. 默认 dry-run，`--apply` 才写库，且幂等；
4. 代码清单复用 `menu_service.HIDDEN_MENU_CODES`（单一事实源，禁止抄第二份）。
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))
sys.path.insert(0, str(BACKEND / "scripts"))

from app.models.rbac import Permission, Role, RolePermission  # noqa: E402
from app.services import menu_service  # noqa: E402

SCRIPT = BACKEND / "scripts" / "retire_legacy_menu_permissions.py"


def _load_script():
    spec = importlib.util.spec_from_file_location("retire_legacy_menu_permissions_under_test", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture()
def db() -> Session:
    # bug-guard：in-memory SQLite 必须 StaticPool，否则多次连接各拿空库
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    for table in (Role.__table__, Permission.__table__, RolePermission.__table__):
        table.create(engine)
    with Session(engine) as session:
        yield session


def _seed(session: Session) -> dict[str, int]:
    """tester 绑 1 个已下线 + 1 个在用 + 1 个软下线；另建 1 个已下线但未绑定的权限行。"""
    tester = Role(code="tester", name="测试")
    session.add(tester)
    session.flush()
    perms = {
        "menu:special": Permission(code="menu:special", name="专项测试", type="menu"),
        "menu:workbench": Permission(code="menu:workbench", name="工作台", type="menu"),
        "menu:notify": Permission(code="menu:notify", name="通知", type="menu"),
        "menu:project": Permission(code="menu:project", name="项目", type="menu"),
    }
    session.add_all(perms.values())
    session.flush()
    for code in ("menu:special", "menu:workbench", "menu:notify"):
        session.add(RolePermission(role_id=tester.id, permission_id=perms[code].id))
    session.commit()
    return {"tester": tester.id, **{code: perm.id for code, perm in perms.items()}}


def test_hidden_codes_source_is_shared_with_menu_service():
    module = _load_script()
    assert module.HIDDEN_MENU_CODES is menu_service.HIDDEN_MENU_CODES, "禁止抄第二份清单"
    assert "menu:special" in module.HIDDEN_MENU_CODES
    assert "menu:notify" not in module.HIDDEN_MENU_CODES, "软下线不属硬下线清单"


def test_collect_reports_only_bound_retired_codes(db: Session):
    ids = _seed(db)
    module = _load_script()
    report = module.collect(db)
    assert report["pending_bindings"] == 1, "只有 menu:special 是『已下线且仍被绑定』"
    assert report["bound_codes"] == [{"code": "menu:special", "roles": ["tester"]}]
    assert report["permission_rows_present"] is True
    assert ids["menu:project"] > 0  # 未绑定的已下线权限行仍存在（不参与解绑）


def test_dry_run_changes_nothing(db: Session):
    _seed(db)
    module = _load_script()
    report = module.retire(db, apply=False)
    assert report["applied"] is False
    assert report["deleted"] == 0
    assert db.scalar(select(RolePermission.id).limit(1)) is not None


def test_apply_unbinds_only_retired_and_keeps_rows(db: Session):
    ids = _seed(db)
    module = _load_script()
    report = module.retire(db, apply=True)
    assert report["applied"] is True
    assert report["deleted"] == 1
    assert report["residual_bindings"] == 0

    bound = set(
        db.scalars(
            select(Permission.code).join(
                RolePermission, RolePermission.permission_id == Permission.id
            )
        ).all()
    )
    assert bound == {"menu:workbench", "menu:notify"}, "在用与软下线绑定必须保留"
    for code in ("menu:special", "menu:project"):
        assert db.scalar(select(Permission.id).where(Permission.code == code)) == ids[code], (
            "权限行必须保留（老书签/?tab= 深链仍靠它）"
        )


def test_apply_is_idempotent(db: Session):
    _seed(db)
    module = _load_script()
    module.retire(db, apply=True)
    second = module.retire(db, apply=True)
    assert second["deleted"] == 0
    assert second["residual_bindings"] == 0


def test_role_menu_counts_counts_only_visible(db: Session):
    _seed(db)
    module = _load_script()
    counts = module.role_menu_counts(db)
    assert counts["tester"] == 1, "hard-hidden(menu:special) 与 soft-hidden(menu:notify) 都不算可见"
