"""已下线菜单权限的**存量数据对账**（Batch 271，用户选项 C）。

背景：菜单「硬下线」目前只在**读时**过滤（`app/services/menu_service.py` 的 `HIDDEN_MENU_CODES`）。
存量库里的 `sys_role_permission` 仍绑着这些 code —— 表现为"库里还在、界面上没有"，
排查入口数量时极易产生歧义（Batch 271 定位"生产左侧入口为什么这么多"时就撞上了这一点）。

本脚本把**存量数据也对齐**：把已下线菜单从**所有角色**解绑。

- 只删 `sys_role_permission` 关联，**保留 `sys_permission` 行**——老书签与 `?tab=` 深链仍由前端重定向处理；
- 默认 **dry-run（只读）**，必须显式 `--apply` 才写库；
- 幂等：重复执行第二次不会再有可删行；
- 代码清单**复用** `menu_service.HIDDEN_MENU_CODES`（单一事实源，禁止在此再抄一份）；
- 软下线菜单（`DISABLED_MENUS`，如 menu:notify/menu:integration）**不在本脚本范围内**——它们是可逆配置，
  解绑会让"改回配置就能恢复"失效。

用法：

    python scripts/retire_legacy_menu_permissions.py                 # dry-run，打印待解绑明细
    python scripts/retire_legacy_menu_permissions.py --apply         # 执行解绑
    python scripts/retire_legacy_menu_permissions.py --apply --json report.json
    python scripts/retire_legacy_menu_permissions.py --check         # 有残留则 exit 2（可当门禁用）
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import delete, select  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from app.core.db import SessionLocal  # noqa: E402
from app.models.rbac import Permission, Role, RolePermission  # noqa: E402
from app.services.menu_service import HIDDEN_MENU_CODES, effective_hidden_menu_codes  # noqa: E402

EXIT_OK = 0
EXIT_PENDING = 2


def collect(db: Session) -> dict:
    """只读：列出仍被角色绑定的已下线菜单（按 code 聚合角色）。"""
    rows = db.execute(
        select(Permission.code, Role.code)
        .join(RolePermission, RolePermission.permission_id == Permission.id)
        .join(Role, Role.id == RolePermission.role_id)
        .where(Permission.code.in_(sorted(HIDDEN_MENU_CODES)))
        .order_by(Permission.code, Role.code)
    ).all()
    per_code: dict[str, list[str]] = {}
    for code, role_code in rows:
        per_code.setdefault(code, []).append(role_code)

    present_rows = db.scalar(
        select(Permission.id)
        .where(Permission.code.in_(sorted(HIDDEN_MENU_CODES)))
        .limit(1)
    )
    return {
        "retired_codes": sorted(HIDDEN_MENU_CODES),
        "permission_rows_present": bool(present_rows),
        "bound_codes": [
            {"code": code, "roles": roles} for code, roles in sorted(per_code.items())
        ],
        "pending_bindings": len(rows),
    }


def role_menu_counts(db: Session) -> dict[str, int]:
    """各角色**当前可见**菜单数（= 绑定数 − 读时过滤掉的已下线/软下线）。"""
    hidden = effective_hidden_menu_codes()
    rows = db.execute(
        select(Role.code, Permission.code)
        .join(RolePermission, RolePermission.role_id == Role.id)
        .join(Permission, Permission.id == RolePermission.permission_id)
        .where(Permission.type == "menu")
    ).all()
    counts: dict[str, int] = {}
    for role_code, perm_code in rows:
        counts.setdefault(role_code, 0)
        if perm_code not in hidden:
            counts[role_code] += 1
    return dict(sorted(counts.items()))


def retire(db: Session, *, apply: bool) -> dict:
    """解绑所有角色的已下线菜单绑定（`apply=False` 时只报告）。"""
    before = collect(db)
    counts_before = role_menu_counts(db)
    report = {
        "hidden_menu_codes": sorted(HIDDEN_MENU_CODES),
        "before": before,
        "before_role_menu_counts": counts_before,
        "applied": False,
        "deleted": 0,
    }
    if not apply or before["pending_bindings"] == 0:
        report["after"] = before
        report["after_role_menu_counts"] = counts_before
        report["residual_bindings"] = before["pending_bindings"]
        return report

    permission_ids = db.scalars(
        select(Permission.id).where(Permission.code.in_(sorted(HIDDEN_MENU_CODES)))
    ).all()
    result = db.execute(delete(RolePermission).where(RolePermission.permission_id.in_(permission_ids)))
    db.commit()
    report["applied"] = True
    report["deleted"] = int(result.rowcount or 0)
    after = collect(db)
    report["after"] = after
    report["after_role_menu_counts"] = role_menu_counts(db)
    report["residual_bindings"] = after["pending_bindings"]
    return report


def _print_report(report: dict) -> None:
    print(f"已下线菜单 code：{len(report['hidden_menu_codes'])} 个（单一事实源 menu_service.HIDDEN_MENU_CODES）")
    print(f"待解绑绑定：{report['before']['pending_bindings']} 条")
    for row in report["before"]["bound_codes"]:
        print(f"  - {row['code']} <- {', '.join(row['roles'])}")
    print(f"角色可见菜单数（前）：{report['before_role_menu_counts']}")
    if report["applied"]:
        print(f"已删除角色绑定：{report['deleted']} 条")
        print(f"角色可见菜单数（后）：{report['after_role_menu_counts']}")
    else:
        print("（dry-run：未写库；加 --apply 执行）")
    print(f"残留绑定：{report['residual_bindings']}")


def main() -> int:
    parser = argparse.ArgumentParser(description="已下线菜单权限的存量数据对账")
    parser.add_argument("--apply", action="store_true", help="真正执行解绑（默认只读 dry-run）")
    parser.add_argument("--check", action="store_true", help="有残留时 exit 2（不做写操作）")
    parser.add_argument("--json", default="", help="把报告写到该 JSON 文件")
    args = parser.parse_args()

    if args.check and args.apply:
        parser.error("--check 与 --apply 互斥")

    with SessionLocal() as db:
        report = retire(db, apply=args.apply)

    _print_report(report)
    if args.json:
        path = Path(args.json)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"报告已写入 {path}")

    if args.check and report["residual_bindings"] > 0:
        return EXIT_PENDING
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
