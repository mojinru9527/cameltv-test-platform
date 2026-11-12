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
