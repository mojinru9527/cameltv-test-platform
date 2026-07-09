---
title: "ADR-0002: SQLite 优先 + PostgreSQL 升级路径"
owner: "tech-lead"
last_reviewed: "2026-07-02"
status: "implemented"
expires: "2027-06-26"
tags: ["adr", "database", "sqlite", "postgresql", "alembic"]
related: ["0001-use-python-fastapi-monostack.md", "0003-frontend-backend-physical-separation.md"]
---

# ADR-0002: SQLite 优先，保留 PostgreSQL 升级路径

## 状态

✅ 已采纳

## 日期

2025-12

## 背景

测试平台需要持久化数据（用户、项目、用例、计划、报告等）。v1 使用裸 sqlite3 直接操作，缺乏迁移工具和升级路径。

v2 需要选择数据库方案，需平衡开发便利性和生产可扩展性。

## 决策

采用 **SQLite (WAL 模式) 作为默认数据库，通过 SQLAlchemy 2.0 + Alembic 保留向 PostgreSQL 的升级路径**：

- 开发/测试环境：SQLite，零配置，即开即用
- 生产环境（未来）：PostgreSQL，通过 Alembic 迁移无缝切换
- ORM 层使用 SQLAlchemy 2.0 抽象，禁止使用 SQLite 特有 SQL
- WAL 模式开启，支持并发读

## 后果

### 正面影响

- ✅ 开发者克隆即可运行，无需安装配置数据库
- ✅ SQLAlchemy 抽象层保证大部分代码与数据库无关
- ✅ Alembic 迁移脚本可直接用于 PostgreSQL
- ✅ WAL 模式解决了 SQLite 的读写并发问题

### 负面影响 / 权衡

- ⚠️ SQLite 不支持某些 PostgreSQL 特性（如枚举类型、数组字段），设计中需注意
- ⚠️ 并发写仍然是串行的，高并发场景需提前升级到 PostgreSQL
- ⚠️ 迁移脚本中的一些操作（如 `ALTER COLUMN`）在 SQLite 中有限制

## 弃选方案

### 方案 A: 直接使用 PostgreSQL

- 优点：一步到位，功能完整
- 缺点：开发者需要安装和配置 PostgreSQL，增加入门门槛
- 放弃原因：降低开发环境搭建复杂度优先

### 方案 B: 纯 SQLite，不考虑升级

- 优点：最简单
- 缺点：后期迁移成本极高，生产环境受限
- 放弃原因：不可逆的架构债

## V2.6 Update (2026-07-02)

PostgreSQL 支持已完整实现：

- ✅ `psycopg2-binary` 驱动已添加（`requirements.txt`）
- ✅ 连接池已配置：`pool_size=10`, `max_overflow=20`, `pool_recycle=3600`
- ✅ SQLite WAL PRAGMA 仅对 SQLite 生效，PG 模式自动跳过
- ✅ Alembic 迁移 0006（`20260702_0006_pg_compat`）确保 PG 类型兼容
- ✅ Docker Compose 新增可选 `postgres:16-alpine` 服务，默认仍使用 SQLite
- ✅ 启动脚本 `startup.sh` 自动执行 `alembic upgrade head`
- ✅ 迁移指南：[PostgreSQL迁移指南.md](../../test-platform-v2/docs/PostgreSQL迁移指南.md)

所有 PG 特性由 `DATABASE_URL` 前缀自动门控，SQLite 开发体验无任何变化。

## 关联

- 后端 CLAUDE.md: [test-platform-v2/backend/CLAUDE.md](../../test-platform-v2/backend/CLAUDE.md)
- 迁移指南: [PostgreSQL迁移指南.md](../../test-platform-v2/docs/PostgreSQL迁移指南.md)
