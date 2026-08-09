# 生产启用检查清单（外放 + 租户）

> 归属：Batch 106（C104-2 / C105-2）。目标：把外放轻量模式与租户模式在生产环境
> （Railway 后端 + Supabase PostgreSQL + Vercel 前端）正式启用，并保留可回滚步骤。

## 1. 前置确认（用户/运维）

| # | 项目 | 状态 | 说明 |
|---|------|------|------|
| 1 | 迁移演练 | ✅ Batch 106 完成 | SQLite 全链迁移 + 回填幂等（`test_organization_migration.py` 2/2、`test_project_invite.py` 迁移 1/1、`test_batch48_requirement_migration.py` 3/3）；PostgreSQL DDL 契约由 CI `backend-check-pg`（PG 16）在 PR required checks 中执行 |
| 2 | 备份生产库 | ✅ 2026-08-06 | 清理前快照：`F:/CamelTv-safe-backup/20260806-prod-cleanup-pre.json`（用户授权清理前备份） |
| 3 | 执行窗口 | ✅ 2026-08-06 | 用户确认后低峰执行（注册开关/配额变量已生效） |
| 4 | Railway 环境变量 | ✅ 用户手动（2026-08-06） | 注册/配额变量已配置并生效；Batch 109 新增 `FRONTEND_URL`/`SEED_DEMO_USERS` 待部署后配置（见 §2） |

## 2. 生产环境变量切换（Railway）

在 Railway 服务变量中新增/确认：

```dotenv
REGISTRATION_ENABLED=true        # 开放普通用户注册
INVITE_CODE_REQUIRED=false       # 不强制平台邀请码；受控环境可改为 true
DEFAULT_REGISTRATION_ROLE=tester
MAX_PROJECTS_PER_USER=5
MAX_TEAM_ORGANIZATIONS_PER_USER=5
REGISTER_RATE_LIMIT_MAX=5
REGISTER_RATE_LIMIT_WINDOW_SECONDS=900

# Batch 109 新增：正式前端域名 + 内置演示账号开关
FRONTEND_URL=https://cameltv-test-platform1.vercel.app
SEED_DEMO_USERS=false
```

已有必检项（Batch 58/73 已配置，切换时复核）：
`ENVIRONMENT=production`、`AUTO_CREATE_TABLES=false`、`COOKIE_SECURE=true`、
`COOKIE_SAMESITE=lax`、`ALLOWED_ORIGINS` 含正式域名、`SECRET_KEY`/`ADMIN_PASSWORD`/
`TESTER_PASSWORD` 强密钥（`SEED_DEMO_USERS=false` 后 `TESTER_PASSWORD` 不再必需，保留强值无害）。

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

生产库已应用至单头（2026-08-06 只读核对）：`alembic_version = 20260806_batch106_project_invite`，
本批次无新迁移。

## 4. 上线验证

| # | 验证 | 命令/操作 | 期望 | 结果（2026-08-06 生产实测） |
|---|------|-----------|------|------------------------------|
| 1 | 健康检查 | `GET https://{domain}/api/v1/open/health` | 200 `status=ok` | ✅ 200，version 2.3.0 |
| 2 | 登录 | 管理员登录 | 200，含 organizations | ✅ admin 经临时密码重置后登录 200，permissions 含 `*`，organizations 返回 |
| 3 | 注册开关 | 未登录访问 `/register` | 页面可达；无邀请码注册按配置返回 400 | ✅ 页面 200；无邀请码注册 400「请填写邀请码」 |
| 4 | 邀请码 | 管理员生成邀请码 → 新用户注册 | 注册成功并自动登录 | ✅ 邀请码注册成功，个人组织自动创建 |
| 5 | 组织 | 新用户登录 → 「我的项目/组织管理」 | 个人组织存在；可建团队组织 | ✅ 个人组织 + 团队组织创建成功 |
| 6 | 项目邀请链接 | 负责人生成链接 → 新用户注册 | 自动加入项目与组织 | ✅ 注册自动入项目/组织；⚠️ 修复前 URL 为后端 http 404（B109-1），Batch 109 合入 + `FRONTEND_URL` 配置后复测 |
| 7 | 配额 | 项目/团队组织数 | 超限返回 400 | ✅ 第 6 个项目 / 第 6 个团队组织均返回 400 |
| 8 | 隔离回归 | 非成员访问他人项目 | 403 | ✅ GET 他人项目 403；成员越权修改 403 |

## 5. 回滚

- **代码**：squash 合入 main 后可通过新 PR 回退；迁移为增量建表，不破坏存量数据；
- **数据**：`sys_project.organization_id` 可空，回滚可置 NULL；组织表可停用组织而非删除；
- **开关**：`REGISTRATION_ENABLED=false` 立即关闭注册（不影响已注册用户）；`FRONTEND_URL` 置空回退请求域名；
  `SEED_DEMO_USERS=true` 恢复内置演示账号重建（下次部署生效）。
- **数据清理**：清理前快照 `F:/CamelTv-safe-backup/20260806-prod-cleanup-pre.json` 可恢复被删验收数据。

## 6. 执行登记

| 项 | 结果 | 执行人/日期 |
|----|------|-------------|
| 迁移演练 | ✅ SQLite 全链 + CI PG 契约 | Batch 106 QA，2026-08-06 |
| 生产备份 | ✅ 清理前快照（`20260806-prod-cleanup-pre.json`） | 2026-08-06（用户授权） |
| Railway 环境变量 | ✅ 注册/配额变量已生效（用户 Dashboard 手动）；`FRONTEND_URL`/`SEED_DEMO_USERS` 待 Batch 109 部署后配置 | 2026-08-06 |
| Supabase 迁移 | ✅ 生产库已应用至单头 `20260806_batch106_project_invite`（只读核对，本批无新迁移） | 2026-08-06 |
| 上线验证 | ✅ §4 全部执行（#2 经管理员临时密码重置；#6 链接域名修复见 Batch 109） | 2026-08-06 |
| 验收数据清理 | ✅ 保留 admin/sportsadmin/admin1 + cameltv 项目；删除 4 个验收账号、5 个验证项目、7 个验证组织及邀请记录 | 2026-08-06（用户授权） |
