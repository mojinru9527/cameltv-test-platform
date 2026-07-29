# Alembic 数据库迁移与恢复运行手册

本目录管理测试平台后端的数据库结构版本。SQLite 用于本地开发和部分契约测试，PostgreSQL 是生产级迁移验收对象。迁移命令必须从 `test-platform-v2/backend` 执行，并使用目标环境显式提供的 `DATABASE_URL`。

## 变更前检查

1. 停止会写入数据库的应用进程、任务工作器和定时任务。
2. 确认 `DATABASE_URL` 指向预期环境，记录数据库类型、实例名和当前应用提交 SHA；输出中不得包含密码。
3. 执行以下只读命令：

```powershell
python -m alembic heads
python -m alembic current
python -m alembic history
```

`heads` 必须只有一个结果。出现多个 head 时停止发布，先通过经过评审的 merge revision 恢复单一 head，不能选择其中一条分支继续升级。

4. 在数据库原生工具中完成可恢复备份，并立即验证备份可读：

```powershell
pg_dump --format=custom --file=<backup_file> <database_name>
pg_restore --list <backup_file>
```

本地 SQLite 需要在停止写入后同时复制数据库主体、`-wal` 和 `-shm` 文件，或先执行检查点再复制。备份文件包含真实数据，不得提交到 Git。

5. 记录迁移前关键表行数、约束和索引快照。至少包括用户、项目、需求、用例、计划、执行、报告和审计表。

## staging 演练

生产变更前，必须将脱敏后的真实旧 PostgreSQL 备份恢复到隔离的 staging 数据库：

```powershell
pg_restore --clean --if-exists --no-owner --dbname=<staging_database> <backup_file>
python -m alembic current
python -m alembic upgrade head
python -m alembic current
python -m alembic check
```

验收内容：

- 升级命令退出码为 0，最终为单一 head。
- 关键表迁移前后行数符合预期；结构变更不应造成的行数变化必须为 0。
- 新增列、索引、外键、唯一约束和 server default 与迁移设计一致。
- 使用同一应用提交执行登录、项目切换、需求读取、用例读取和审计读取等应用冒烟。
- 执行受影响模块 Pytest、PostgreSQL 迁移测试和后端全量回归。
- 记录耗时、锁等待和失败日志，证据中移除连接串、Cookie、Token 和个人数据。

临时空数据库不能替代 A10 的真实旧 PostgreSQL 快照升级证据。空库升级只能证明迁移链可执行，不能证明历史数据兼容、行数保持或回滚安全。

## 升级

staging 演练通过且备份恢复经过验证后，才可在批准的维护窗口执行：

```powershell
python -m alembic current
python -m alembic upgrade head
python -m alembic current
python -m alembic check
```

升级后重新核对关键表行数、约束和索引，并执行应用冒烟。任一检查失败时停止流量恢复，保留原始日志和数据库快照。

## 显式修订降级

迁移图包含 merge revision。跨越合并点时相对修订可能对应多个父分支，因此禁止使用 `python -m alembic downgrade -1`。必须先从 `history` 和迁移文件确认目标位于当前 revision 的祖先路径，再使用显式修订：

```powershell
python -m alembic history
python -m alembic downgrade <target_revision>
python -m alembic current
```

降级前必须在 staging 使用同一备份和同一应用版本演练，并检查每个目标迁移的 `downgrade()` 是否会删除列、表或数据。禁止在生产环境直接执行 `downgrade base`。如果降级会丢失数据、迁移没有可逆实现，或旧应用无法读取降级后的结构，应选择恢复已验证备份。

## 恢复

恢复数据库前停止全部写入，保留失败数据库供取证，然后使用已验证备份恢复到新实例或已清理的隔离实例：

```powershell
pg_restore --clean --if-exists --no-owner --dbname=<recovery_database> <backup_file>
python -m alembic current
```

恢复后核对：

1. Alembic revision 与备份时记录一致。
2. 关键表行数、约束和索引与备份清单一致。
3. 旧应用版本完成登录、项目切换、需求读取、用例读取和审计读取的应用冒烟。
4. 连接切换、缓存清理和任务工作器恢复顺序经过发布负责人批准。

不要在未验证恢复结果时覆盖唯一备份或删除失败数据库。

## 新迁移开发规范

```powershell
python -m alembic revision --autogenerate -m "<schema_change>"
python -m alembic upgrade head
python -m alembic check
```

- 自动生成结果必须人工评审，尤其是删除、重命名、类型收窄和 server default。
- 每个迁移应只包含一个可说明的结构变更，并实现经过测试的 `upgrade()` 与 `downgrade()`。
- PostgreSQL 与 SQLite 行为不同时，生产兼容性以 PostgreSQL 演练为准。
- 不在运行手册中固定当前 head 名称或迁移数量；它们由 `alembic heads` 和 `alembic history` 提供。
