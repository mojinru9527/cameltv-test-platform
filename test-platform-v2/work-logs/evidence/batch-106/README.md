# Batch 106 证据目录

## 生产启用（C104-2/C105-2）

### 迁移演练（SQLite，全链）

命令（退出码 0）：

```powershell
pytest tests/test_organization_migration.py -q        # 2 passed（建表+回填+幂等）
pytest tests/test_project_invite.py -q                # 9 passed（含迁移建表）
pytest tests/test_batch48_requirement_migration.py -q # 3 passed（最小旧库防御）
pytest tests/test_alembic_runbook.py -q               # 3 passed（upgrade/downgrade/单头）
```

覆盖：Batch 104 `sys_invite_code` → 105 组织表 + `sys_project.organization_id` +
存量回填（幂等、个人组织 `personal-{user_id}`）→ 106 `sys_project_invite`；
最终头 `20260806_batch106_project_invite`（`alembic heads` 单头）。

### PostgreSQL 契约

本地 Docker daemon 未运行，PG 16 DDL 契约由 PR required check
`backend-check-pg`（`postgres:16-alpine` service + `test_postgres_migration_reconcile.py`
等）在干净检出上执行；本批 PR 的该 check 结果作为生产 PG 契约证据回填。

### 生产切换

未自动执行：Railway CLI 未安装、生产库执行窗口需用户确认。
详见 [production-enablement-checklist.md](../../../../deploy/production-enablement-checklist.md)。
切换完成后回填 §6 登记表并关闭 C104-2/C105-2。
