# Staging 双向演练 — 20260710_0017_wiki_tables 迁移

> 目的: 在生产部署前验证 Alembic 迁移 `20260710_0017_wiki_tables.py` 的 upgrade/downgrade 正确性。
> 执行环境: Staging (Docker)
> 前置条件: Staging DB 可连接、Alembic 配置正确

---

## 前置条件

```bash
# 1. 确认 staging 环境可连接
docker compose -f docker-compose.staging.yml ps

# 2. 确认当前 migration 状态
docker compose -f docker-compose.staging.yml exec backend alembic current

# 3. 备份数据库（安全第一）
docker compose -f docker-compose.staging.yml exec db pg_dump -U postgres cameltv_staging > staging_backup_$(date +%Y%m%d_%H%M%S).sql
```

## Step 1: Downgrade（回退到 0016）

```bash
# 回退 0017 迁移（删除 6 张 wiki 表）
docker compose -f docker-compose.staging.yml exec backend alembic downgrade 20260710_0016

# 验证表已删除
docker compose -f docker-compose.staging.yml exec db psql -U postgres -d cameltv_staging -c "
  SELECT table_name FROM information_schema.tables
  WHERE table_name IN ('wiki_raw_source','wiki_page','wiki_link','wiki_ingest_job','wiki_diff_task','wiki_diff_item');
"
# 预期: 0 rows
```

## Step 2: Upgrade（重新创建）

```bash
# 升级回 0017
docker compose -f docker-compose.staging.yml exec backend alembic upgrade 20260710_0017

# 验证表已创建
docker compose -f docker-compose.staging.yml exec db psql -U postgres -d cameltv_staging -c "
  SELECT table_name FROM information_schema.tables
  WHERE table_name IN ('wiki_raw_source','wiki_page','wiki_link','wiki_ingest_job','wiki_diff_task','wiki_diff_item');
"
# 预期: 6 rows

# 验证表结构
docker compose -f docker-compose.staging.yml exec db psql -U postgres -d cameltv_staging -c "\d wiki_page"
docker compose -f docker-compose.staging.yml exec db psql -U postgres -d cameltv_staging -c "\d wiki_diff_item"
```

## Step 3: 验证数据完整性（无数据丢失）

```bash
# 确认 Alembic 版本记录正确
docker compose -f docker-compose.staging.yml exec backend alembic current
# 预期: 20260710_0017

# 确认无 pending 迁移
docker compose -f docker-compose.staging.yml exec backend alembic check
# 预期: 无错误输出
```

## Step 4: 恢复服务

```bash
# 重启 backend 确保新 schema 被 SQLAlchemy 识别
docker compose -f docker-compose.staging.yml restart backend

# 运行 health check
curl -s http://localhost:8000/api/v1/health | jq .
```

---

## 预期结果

| 阶段 | 验证点 | 预期 |
|------|--------|------|
| Downgrade | 6 张表删除 | 0 rows |
| Upgrade | 6 张表重建 | 6 rows |
| 结构 | 列名/类型正确 | 与 models/wiki.py 一致 |
| Alembic | current = 20260710_0017 | 无 diff |
| 服务 | Backend 正常启动 | 200 OK |

## 回滚方案

如果任一步骤失败：
1. `docker compose ... exec db psql ... < staging_backup_*.sql`（恢复备份）
2. `docker compose ... restart backend`
3. 分析失败原因后重新执行
