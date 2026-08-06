# 🗂️ Dev 部门项目看板 — Batch 110（体育平台第一期收口）

## 📋 项目信息

| 字段 | 值 |
|------|-----|
| **项目名称** | 体育平台第一期收口：全模块逻辑 + P0 用例 + 接口用例/测试 + UI 自动化 + RAG/Wiki 知识库 |
| **关联 PRD** | [batch-110-sports-phase1-closeout-prd-summary.md](../batch-110-sports-phase1-closeout-prd-summary.md) |
| **看板创建** | 2026-08-06 |
| **执行器** | codex（用户确认） |
| **Worktree** | F:\CamelTv-worktrees\codex-batch-110-sports-phase1-closeout |
| **分支** | feature/batch-110-sports-phase1-closeout |

## 🎯 交付切片进度

| # | Slice | 方案 | 编码 | 自测 | 审批 | 合入 | 备注 |
|---|-------|:----:|:----:|:----:|:----:|:----:|------|
| 1 | 批次工件 + 看板 + 障碍快照 | ✅ | ✅ | ⏳ | ⏳ | ⏳ | PRD/PM/Design + 看板 |
| 2 | 生产用户端全路由勘察 + XHR 捕获 | ⏳ | ⏳ | ⏳ | ⏳ | ⏳ | 依赖 sportsadmin 凭证 |
| 3 | 识图走查（vision） | ⏳ | ⏳ | ⏳ | ⏳ | ⏳ | 依赖 Slice 2 截图 |
| 4 | 功能地图 v2 | ⏳ | ⏳ | ⏳ | ⏳ | ⏳ | 依赖 Slice 2/3 |
| 5 | 功能用例补齐 + P0 标识 | ⏳ | ⏳ | ⏳ | ⏳ | ⏳ | 本地 AI + 直连库 |
| 6 | 接口真实样本 ≥20 + 接口用例生成 | ⏳ | ⏳ | ⏳ | ⏳ | ⏳ | 依赖 Slice 2 |
| 7 | 接口测试执行回填 | ⏳ | ⏳ | ⏳ | ⏳ | ⏳ | 依赖 Slice 6 |
| 8 | RAG 知识中心入库 | ⏳ | ⏳ | ⏳ | ⏳ | ⏳ | capture/直连双通道 |
| 9 | Wiki 基线（模块树/同步/编译/审批/差异） | ⏳ | ⏳ | ⏳ | ⏳ | ⏳ | 生产 WIKI_ENABLED |
| 10 | UI 自动化（P0 映射 + 生产只读执行） | ⏳ | ⏳ | ⏳ | ⏳ | ⏳ | 依赖 Slice 5 |
| 11 | 障碍登记 + QA + Leader + 一次总确认 | ⏳ | ⏳ | ⏳ | ⏳ | ⏳ | 全部门工件 + PR |

## 📍 当前位置

```
Batch 110 — 体育平台第一期收口
├── ✅ PRD/PM/Design 三件套 + 看板（Slice 1 方案/编码完成）
└── 🔄 下一步：生产用户端全路由勘察 + XHR 捕获（需 sportsadmin 凭证）
```
