# 生产启用检查清单（外放 + 租户）

> 归属：Batch 106（C104-2 / C105-2）。目标：把外放轻量模式与租户模式在生产环境
> （Railway 后端 + Supabase PostgreSQL + Vercel 前端）正式启用，并保留可回滚步骤。

## 1. 前置确认（用户/运维）

| # | 项目 | 状态 | 说明 |
|---|------|------|------|
| 1 | 迁移演练 | ✅ 本批完成 | SQLite 全链迁移 + 回填幂等（`test_organization_migration.py` 2/2、`test_project_invite.py` 迁移 1/1、`test_batch48_requirement_migration.py` 3/3）；PostgreSQL DDL 契约由 CI `backend-check-pg`（PG 16）在 PR required checks 中执行 |
| 2 | 备份生产库 | ⏳ 人工 | 执行迁移前对 Supabase 库做一次 PITR/导出备份（Supabase 控制台或 `pg_dump`） |
| 3 | 执行窗口 | ⏳ 人工 | 低峰窗口执行迁移与切换，避免与 UI/API 执行任务重叠 |
| 4 | Railway 环境变量 | ⏳ 人工 | 见 §2；Railway CLI 未安装，需在 Dashboard 或凭据就绪后执行 |

## 2. 生产环境变量切换（Railway）

在 Railway 服务变量中新增/确认：

```dotenv
REGISTRATION_ENABLED=true        # 放开注册（未确认前保持 false）
INVITE_CODE_REQUIRED=true        # 强制平台邀请码
DEFAULT_REGISTRATION_ROLE=tester
MAX_PROJECTS_PER_USER=5
MAX_TEAM_ORGANIZATIONS_PER_USER=5
REGISTER_RATE_LIMIT_MAX=5
REGISTER_RATE_LIMIT_WINDOW_SECONDS=900
```

已有必检项（Batch 58/73 已配置，切换时复核）：
`ENVIRONMENT=production`、`AUTO_CREATE_TABLES=false`、`COOKIE_SECURE=true`、
`COOKIE_SAMESITE=lax`、`ALLOWED_ORIGINS` 含正式域名、`SECRET_KEY`/`ADMIN_PASSWORD`/
`TESTER_PASSWORD` 强密钥。

## 3. 数据库迁移（Supabase）

```bash
# 在含 production 配置的 backend 环境执行（先备份！）
DATABASE_URL="postgresql://..." AUTO_CREATE_TABLES=false \
  python -m alembic upgrade head
# 期望：批量应用 Batch 104/105/106 迁移，最终单头
# 20260806_batch106_project_invite (head)

# 校验
python -m alembic current          # 单头
python -m alembic heads            # 1 个头
```

迁移内容：`sys_invite_code`（104）、`sys_organization`/`sys_organization_member` +
`sys_project.organization_id` + 存量回填（105）、`sys_project_invite`（106）。

## 4. 上线验证

| # | 验证 | 命令/操作 | 期望 |
|---|------|-----------|------|
| 1 | 健康检查 | `GET https://{domain}/api/v1/open/health` | 200 `status=ok` |
| 2 | 登录 | 管理员登录 | 200，含 organizations |
| 3 | 注册开关 | 未登录访问 `/register` | 页面可达；无邀请码注册按配置返回 400 |
| 4 | 邀请码 | 管理员生成邀请码 → 新用户注册 | 注册成功并自动登录 |
| 5 | 组织 | 新用户登录 → 「我的项目/组织管理」 | 个人组织存在；可建团队组织 |
| 6 | 项目邀请链接 | 负责人生成链接 → 新用户注册 | 自动加入项目与组织 |
| 7 | 配额 | 项目/团队组织数 | 超限返回 400 |
| 8 | 隔离回归 | 非成员访问他人项目 | 403 |

## 5. 回滚

- **代码**：squash 合入 main 后可通过新 PR 回退；迁移为增量建表，不破坏存量数据；
- **数据**：`sys_project.organization_id` 可空，回滚可置 NULL；组织表可停用组织而非删除；
- **开关**：`REGISTRATION_ENABLED=false` 立即关闭注册（不影响已注册用户）。

## 6. 执行登记

| 项 | 结果 | 执行人/日期 |
|----|------|-------------|
| 迁移演练 | ✅ SQLite 全链 + CI PG 契约 | Batch 106 QA，2026-08-06 |
| 生产备份 | ⏳ | 用户确认窗口后执行 |
| Railway 环境变量 | ⏳ | 用户/运维（CLI 未安装） |
| Supabase 迁移 | ⏳ | 用户确认窗口后执行 |
| 上线验证 | ⏳ | 迁移后按 §4 执行 |
