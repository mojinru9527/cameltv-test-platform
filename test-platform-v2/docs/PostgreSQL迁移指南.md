# PostgreSQL 迁移指南

> V2.6 新增：CamelTv 测试平台现已支持 PostgreSQL 作为生产数据库。
> SQLite 仍为开发环境默认选项，所有 PostgreSQL 相关代码均通过 `DATABASE_URL` 前缀自动切换。

## 前置条件

- Docker 20.10+ 或本地 PostgreSQL 14+
- 已拉取最新 `feature/p1-batch-a-security` 分支（V2.6+）

---

## 方案 A：Docker Compose（推荐）

### 1. 配置环境变量

编辑 `deploy/.env`，取消注释 PostgreSQL 相关行：

```bash
# 数据库连接（从 SQLite 切换为 PostgreSQL）
DATABASE_URL=postgresql://cameltv:<从密码管理器注入>@postgres:5432/cameltv
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=20

# PostgreSQL 凭据（需与 DATABASE_URL 一致）
POSTGRES_USER=cameltv
POSTGRES_PASSWORD=<从密码管理器注入>
POSTGRES_DB=cameltv
```

### 2. 启动

```bash
cd deploy
docker compose up -d
```

PostgreSQL 容器会先启动（约 10 秒），backend 等待 PG 健康检查通过后启动并自动运行 `alembic upgrade head`。

### 3. 验证

```bash
# 检查 backend 启动日志
docker logs cameltv-tp-backend

# 应看到:
#   Running database migrations...  (无报错)
#   Starting application...

# 检查 API 健康状态
curl http://localhost/health
# → {"status": "ok", "version": "2.1.0"}
```

---

## 方案 B：外部 PostgreSQL

### 1. 安装依赖

```bash
cd backend
pip install psycopg2-binary
```

### 2. 配置环境变量

编辑 `backend/.env`：

```bash
DATABASE_URL=postgresql://myuser:mypass@my-pg-host:5432/cameltv
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=20
```

### 3. 运行迁移

```bash
cd backend
alembic upgrade head
```

### 4. 启动

```bash
uvicorn app.main:app --reload --port 8000
```

---

## 数据迁移：SQLite → PostgreSQL

### 推荐方案：导出/导入

由于 SQLite 和 PostgreSQL SQL 方言不同，建议使用数据导出/导入方式：

```bash
# 1. 导出 SQLite 数据为 SQL（SQLite 格式）
sqlite3 backend/data/platform.db .dump > dump.sql

# 2. 手动转换或使用 pgloader 工具
# pgloader 示例配置 (migrate.load):
#   LOAD DATABASE FROM sqlite:///backend/data/platform.db
#   INTO postgresql://cameltv:<从密码管理器注入>@localhost:5432/cameltv
#   WITH data only, create no tables;

# 3. 或者：启动 PG 模式后，通过平台的 Excel/CSV 导出功能重新导入数据
```

### 备选方案：平台导出/导入

1. 在 SQLite 模式下导出关键数据（Excel/CSV）
2. 切换到 PG 模式
3. 通过平台重新导入

---

## 回滚到 SQLite

```bash
# Docker 方式：修改 deploy/.env，设置为 SQLite
DATABASE_URL=sqlite:////data/platform.db

# 本地开发：修改 backend/.env
DATABASE_URL=sqlite:///./data/platform.db

# 重启服务
docker compose restart backend
```

---

## 性能调优

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `DB_POOL_SIZE` | 10 | 连接池大小，按并发量调整 |
| `DB_MAX_OVERFLOW` | 20 | 连接池溢出上限 |
| `pool_recycle` | 3600s | 连接回收时间（硬编码） |

---

## 常见问题

**Q: backend 容器启动失败，日志显示 "could not connect to server"?**
A: PostgreSQL 容器可能尚未就绪。等待 10-20 秒后 backend 会自动重试（`restart: unless-stopped`）。

**Q: 迁移时报错 "relation already exists"?**
A: 说明数据库已有表。检查 PostgreSQL 是否为全新实例。

**Q: 如何同时保留 SQLite 和 PostgreSQL?**
A: 修改 `DATABASE_URL` 即可切换，两个数据库文件独立，互不影响。
