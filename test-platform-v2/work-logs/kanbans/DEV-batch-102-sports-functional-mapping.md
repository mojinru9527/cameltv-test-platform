# 🗂️ Dev 部门项目看板 — Batch 102（体育平台功能模块梳理）

## 📋 项目信息

| 字段 | 值 |
|------|-----|
| **项目名称** | 体育平台功能模块梳理（需求导入 / 生产页面联动 / 功能用例 / 脑图与知识中心 / konfi 关联） |
| **关联 PRD** | [batch-102-sports-functional-mapping-prd-summary.md](../batch-102-sports-functional-mapping-prd-summary.md) |
| **看板创建** | 2026-08-06 |
| **执行器** | codex（用户确认未来 10 版本沿用） |
| **Worktree** | F:\CamelTv-worktrees\codex-batch-102-sports-functional-mapping |

## 🎯 交付切片进度

| # | Slice | 方案 | 编码 | 自测 | 审批 | 合入 | 备注 |
|---|-------|:----:|:----:|:----:|:----:|:----:|------|
| 1 | 批次工件 + 需求导入脚本 | ✅ | ✅ | ✅ | ✅ | ✅ | PRD/PM/Design + 3 脚本（import/generate-sync/knowledge-sync + walkthrough） |
| 2 | 需求文档导入生产（用户端/运营后台） | ✅ | ✅ | ✅ | ✅ | ✅ | 4 份文档 upload→extract→confirm |
| 3 | 生产页面功能模块勘察（用户端/运营后台/konfi） | ✅ | ✅ | ✅ | ✅ | ✅ | 10 页面 DOM+截图，证据落盘 |
| 4 | 功能用例生成与导入（AI use_extraction + 脑图） | ✅ | ✅ | ✅ | ✅ | ✅ | 210 条落库 + xmind 导出 |
| 5 | 知识中心与模块关联（sources/graph/admin-links/konfi） | ✅ | ✅ | ✅ | ✅ | ✅ | 5 源/16 实体/15 关系 + 发布包 |
| 6 | 功能地图文档 + 平台障碍登记 + C 条件 | ✅ | ✅ | ✅ | ✅ | ✅ | 地图文档 + SPORT-INT + C102-1~5 |
| 7 | QA + Leader + 一次总确认 | ✅ | ✅ | ✅ | 🔄 ⬅️ | ⏳ | **当前位置**：等一次总确认 |

## 📍 当前位置

```
Batch 102 — 体育平台功能模块梳理（完成，等一次总确认）
├── ✅ 需求 4 份导入并确认提取（用户端 16 模块/92 FP，运营后台 14 模块/108 FP）
├── ✅ 功能用例 210 条落库（用户端 77 + 运营后台 133）+ 脑图 xmind 导出
├── ✅ 知识中心 5 源 / 16 实体 / 15 关系（图谱可查）+ 发布包
├── ✅ 生产页面勘察 10 页（home/news/my/match/live/league/team/replay/search/worldcup）
├── ✅ 功能地图文档 + 平台障碍登记（C102-1~5 / SPORT-INT）
└── 🔄 等一次总确认（push + Draft PR + required checks 后合入）
```
