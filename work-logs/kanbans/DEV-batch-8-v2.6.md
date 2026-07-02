# 🗂️ Dev 部门项目看板 — 批次八: V2.5+V2.6 合入

> **最后更新**: 2026-07-02 | **看板创建**: 2026-07-02
>
> ⚠️ 每次 Dev 部门启动处理本批次时，**先读本看板**确认当前进度。

---

## 📋 项目信息

| 字段 | 值 |
|------|-----|
| **项目名称** | 批次八 — V2.5 测试数据+多项目仪表板 + V2.6 外部集成+PostgreSQL |
| **关联 PM 计划** | N/A（Backlog 驱动） |
| **关联 PRD** | N/A（Backlog 驱动） |
| **总预估工时** | 已编码完成，仅剩合入 |
| **已用批次** | 0 批 |
| **看板创建** | 2026-07-02 |
| **最后更新** | 2026-07-02 |

---

## 🎯 交付切片进度

> 状态图例：⏳ 待开始 | 🔄 进行中 | ✅ 已完成 | ❌ 已取消 | 🔒 阻塞中

| # | Slice | 方案 | 编码 | 自测 | 审批 | 合入 | 备注 |
|---|-------|:----:|:----:|:----:|:----:|:----:|------|
| 1 | V2.5 测试数据集管理 (7 files) | ✅ | ✅ | ✅ | ⏳ | ⏳ | Dataset CRUD + CSV/JSON 解析 + 参数化注入 |
| 2 | V2.5 多项目仪表板 (6 files) | ✅ | ✅ | ✅ | ⏳ | ⏳ | 跨项目聚合 + 对比视图 |
| 3 | V2.5 API 测试集成 (5 files) | ✅ | ✅ | ✅ | ⏳ | ⏳ | 数据集选择器 + 批量结果展示 |
| 4 | V2.6 集成模型+Schema (4 files) | ✅ | ✅ | ✅ | ⏳ | ⏳ | IntegrationConfig + SyncLog + schemas |
| 5 | V2.6 同步引擎 (5 files) | ✅ | ✅ | ✅ | ⏳ | ⏳ | BaseSyncProvider + Jira + TAPD + SyncEngine |
| 6 | V2.6 集成 API+权限 (4 files) | ✅ | ✅ | ✅ | ⏳ | ⏳ | 8 REST 端点 + 3 权限码 + 路由器 |
| 7 | V2.6 缺陷同步端点+调度 (3 files) | ✅ | ✅ | ✅ | ⏳ | ⏳ | defect sync-push/pull + APScheduler 自动同步 |
| 8 | V2.6 PostgreSQL 迁移 (8 files) | ✅ | ✅ | ✅ | ⏳ | ⏳ | psycopg2 + 连接池 + Alembic 0006 + Docker + startup.sh |
| 9 | V2.6 前端集成页面 (6 files) | ✅ | ✅ | ✅ | ⏳ | ⏳ | Integration 配置页 + 缺陷同步按钮 + 路由 |
| 10 | 烟雾测试 + 文档 + Backlog (5 files) | ✅ | ✅ | ✅ | ⏳ | ⏳ | V2.5 quick + V2.6 smoke + PG 迁移指南 + ADR |

---

## 📍 当前位置

```
Batch #1 — V2.5+V2.6 合并合入
├── ✅ 已完成: 全部 10 个 Slice 代码编写完成（31 files）
├── 🔄 进行中: Git commit → PR → merge develop ⬅️
├── ⏳ 待审批: PR review
└── ⏳ 下一步: 合并后更新 backlog 状态
```

---

## 📜 批次记录

_（Dev 部门完成合入后填写）_

---

## ⚠️ 阻塞与风险

| 阻塞项 | 严重度 | 描述 | 需要谁 | 记录时间 |
|--------|:------:|------|--------|----------|
| — | — | 无阻塞项 | — | — |

---

## 🔗 相关工件

| 工件 | 路径 | 状态 |
|------|------|:----:|
| 改进 Backlog | [改进任务backlog.md](../../test-platform-v2/docs/改进任务backlog.md) | 📋 |
| V2.5 烟雾测试 | [test_v25_quick.py](../../test-platform-v2/backend/tests/test_v25_quick.py) | ✅ |
| V2.6 烟雾测试 | [test_v26_smoke.py](../../test-platform-v2/backend/tests/test_v26_smoke.py) | ✅ |
| PG 迁移指南 | [PostgreSQL迁移指南.md](../../test-platform-v2/docs/PostgreSQL迁移指南.md) | ✅ |
