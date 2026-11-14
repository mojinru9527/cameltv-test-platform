# AIQE Rollback — 版本锁、备份与回滚

## 1. 版本锁

每次发布前写锁：

```powershell
pwsh scripts/ops/aiqe-version-lock.ps1 -Action write -ImageTag release-m6-20261112
```

锁文件 `config/aiqe-version.lock` 记录：git commit、镜像 tag、alembic head、时间。
发布后校验：

```powershell
pwsh scripts/ops/aiqe-version-lock.ps1 -Action verify
```

## 2. 发布前备份（必须）

```bash
ssh root@<prod>
TS=$(date +%Y%m%d-%H%M%S)
docker exec cameltv-tp-production-postgres-1 sh -c \
  'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc' > /root/backups/pre-release-$TS.dump
sha256sum /root/backups/pre-release-$TS.dump
```

## 3. 回滚

```powershell
pwsh scripts/ops/aiqe-rollback.ps1 -TargetTag prev-m6 -DryRun
pwsh scripts/ops/aiqe-rollback.ps1 -TargetTag prev-m6 -Execute
```

步骤：

1. 记录当前 `alembic current` 与镜像 tag；
2. 回滚镜像（`docker tag <prev> main` + compose up backend）；
3. 迁移回滚：**仅当**新迁移无数据依赖时执行 `alembic downgrade -1`；否则保留 schema，代码兼容旧表；
4. 健康检查 `https://swiftbugs.cn/api/v1/open/health`；
5. 校验版本锁（commit 与镜像一致）。

## 4. 回滚后验证

```bash
curl -s -o /dev/null -w '%{http_code}\n' https://swiftbugs.cn/api/v1/open/health
docker exec cameltv-tp-production-backend-1 alembic current
docker ps --format '{{.Names}} {{.Status}}' | grep backend
```

期望：health=200、`alembic current` 为回滚目标 head、backend healthy。

## 5. v1.4 执行边界回滚

1. **先关闭生产 Run 创建**：从部署环境移除或置 `AIQE_PROD_RUN_CREATE_ENABLED=false`；
2. **关闭进程内执行器**：`AIQE_INPROCESS_EXECUTOR_ENABLED=false`，并重启 backend；
3. **停止外部 Runner**：`aiqe_local_runner.py` 进程退出；确认没有未完成的 AIQE ExecutionJob；
4. **保留历史**：Run/NodeRun/StepAttempt/Assertion/Artifact 是审计事实，回滚不回写、不删除；只把状态收敛（`AIQE_RECONCILER` 或 `scripts/qa/aiqe_reconcile.py`）；
5. **迁移回滚**：`20261124_aiqe_pr595_execution` 为追加字段 + 新表；PostgreSQL 可 `alembic downgrade -1`，SQLite 本地保留追加列（见 `ops.md`）；
6. **验证**：`/api/v1/open/health` 200；`/api/v1/aiqe/runs/{id}` 仍可读；新建 Run 被 403 拒绝（生产默认关闭）；
7. **重新启用**：仅在 Test 环境验证 Preflight/断言/证据后，再按发布窗口打开生产开关，并记录版本锁。

> PR #595 的 `prod-aiqe-inprocess` HTTP health smoke 只作为受控运维验证，不得在回滚后自动恢复为“生产可执行任意 API”。
