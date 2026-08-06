"""生产平台管理员恢复（Batch 101，凭据遗忘恢复）。

直接连接 Supabase 生产库：重置既有 admin 密码 + 新建一个管理员账号（admin 角色）。
凭据：DATABASE_URL 从环境变量 TP_DATABASE_URL 读取（不回显）；新密码仅打印一次。
用法: <venv-python> scripts/sports/reset-prod-admin.py
"""
from __future__ import annotations

import datetime
import os
import secrets

import bcrypt
import psycopg2


def _hash(pw: str) -> str:
    return bcrypt.hashpw(pw.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def main() -> int:
    dsn = os.environ.get("TP_DATABASE_URL", "")
    if not dsn:
        print("ERROR: 需要环境变量 TP_DATABASE_URL（production.env 的 DATABASE_URL）", flush=True)
        return 1
    if "sslmode" not in dsn:
        dsn += "?sslmode=require" if "?" not in dsn else "&sslmode=require"

    new_admin_pw = secrets.token_urlsafe(12)
    new_super_pw = secrets.token_urlsafe(12)
    new_username = "sportsadmin"
    now = datetime.datetime.now(datetime.timezone.utc)

    conn = psycopg2.connect(dsn)
    conn.autocommit = False
    try:
        with conn.cursor() as cur:
            # 1) 重置既有 admin 密码
            cur.execute(
                "UPDATE sys_user SET password=%s, must_change_password=false, status=1, updated_at=%s "
                "WHERE username='admin'",
                (_hash(new_admin_pw), now),
            )
            admin_reset = cur.rowcount

            # 2) 新建管理员账号（admin 角色）
            cur.execute("SELECT id FROM sys_role WHERE code='admin' LIMIT 1")
            role_row = cur.fetchone()
            if not role_row:
                print("ERROR: 未找到 admin 角色", flush=True)
                return 1
            admin_role_id = role_row[0]

            cur.execute("SELECT id FROM sys_user WHERE username=%s", (new_username,))
            if cur.fetchone():
                print(f"ERROR: 账号 {new_username} 已存在，请改名后重试", flush=True)
                return 1

            cur.execute(
                "INSERT INTO sys_user (username, password, nickname, email, status, must_change_password, "
                "created_at, updated_at) VALUES (%s,%s,%s,%s,1,false,%s,%s) RETURNING id",
                (new_username, _hash(new_super_pw), "体育平台管理员", "sportsadmin@cameltv.local", now, now),
            )
            new_user_id = cur.fetchone()[0]

            cur.execute(
                "INSERT INTO sys_user_role (user_id, role_id, project_id) VALUES (%s,%s,0)",
                (new_user_id, admin_role_id),
            )

            # 3) 加入默认项目（code='cameltv' 或首个项目）
            cur.execute("SELECT id FROM sys_project WHERE code='cameltv' LIMIT 1")
            proj = cur.fetchone()
            if not proj:
                cur.execute("SELECT id FROM sys_project ORDER BY id LIMIT 1")
                proj = cur.fetchone()
            if proj:
                cur.execute(
                    "INSERT INTO sys_project_member (project_id, user_id, role_id) VALUES (%s,%s,%s) "
                    "ON CONFLICT DO NOTHING",
                    (proj[0], new_user_id, admin_role_id),
                )
                print(f"[project] 已加入项目 id={proj[0]}", flush=True)
            else:
                print("[project] 无项目可加入（保持全局 admin 角色）", flush=True)

        conn.commit()
    except Exception as exc:
        conn.rollback()
        print(f"ERROR: {exc}", flush=True)
        return 1
    finally:
        conn.close()

    print("=" * 50, flush=True)
    print(f"admin 密码已重置（账号 admin / 新密码）: {new_admin_pw}", flush=True)
    print(f"新管理员账号: {new_username} / 密码: {new_super_pw}", flush=True)
    print("请立即登录并妥善保存；如需更新 production.env 请同步。", flush=True)
    print("=" * 50, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
