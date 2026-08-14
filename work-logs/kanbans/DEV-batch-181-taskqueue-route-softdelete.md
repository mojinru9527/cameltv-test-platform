# 🗂️ Dev 部门项目看板 — batch-181-taskqueue-route-softdelete

> **用途**：追踪 Batch 181（架构专项：TaskQueue 六队列统一 / 软删三套语义统一 / 路由大文件拆分）进度。

---

## 📋 项目信息

| 字段 | 值 |
|------|-----|
| **项目名称** | batch-181-taskqueue-route-softdelete |
| **关联 PM 计划** | [test-platform-v2/work-logs/batch-181-taskqueue-route-softdelete-pm-plan.md](../test-platform-v2/work-logs/batch-181-taskqueue-route-softdelete-pm-plan.md) |
| **关联 PRD** | [PRD](../test-platform-v2/work-logs/batch-181-taskqueue-route-softdelete-prd-summary.md) |
| **总预估工时** | ~24h（T1-T18） |
| **已用批次** | 1 批 |
| **看板创建** | 2026-08-16 |
| **最后更新** | 2026-08-16 |

---

## 🎯 交付切片进度

> 每个 Slice 经过：📝方案 → 💻编码 → 🔍自测 → ✅审批 → 🚀合入。标注当前停留位置 ⬅️

| # | Slice | 方案 | 编码 | 自测 | 审批 | 合入 | 备注 |
|---|-------|:----:|:----:|:----:|:----:|:----:|------|
| 0 | 工件 PRD/PM/Design/看板 | ✅ | ✅ | ✅ | ⏳ | ⏳ | |
| 1 | P2-06 TaskQueue 基类 + 迁移 + 六队列接入 | ✅ | ✅ | ✅ | ⏳ | ⏳ | commit 81b496a；队列测试 100 通过 |
| 2 | P2-08 软删统一（迁移+转换+测试） | ✅ | ✅ | ✅ | ⏳ | ⏳ | commit 1f41ae0；88 通过 |
| 3 | 路由守卫基线（inventory 420 条） | ✅ | ✅ | ✅ | ⏳ | ⏳ | commit 85c2286 |
| 4-7 | 9 文件拆分（25 新路由 + 9 服务文件） | ✅ | ✅ | ✅ | ⏳ | ⏳ | 4 子代理完成 + 主代理集成 router.py/删旧文件/修引用；守卫 5/5 绿 |
| 8 | QA 全量回归 + 证据 + 门禁 | 🔄 ⬅️ | ⏳ | ⏳ | ⏳ | ⏳ | **当前位置**：全量 pytest 后台运行中 |
| 9 | Leader 判决 + 合入 | ⏳ | ⏳ | ⏳ | ⏳ | ⏳ | |

> 状态图例：⏳ 待开始 | 🔄 进行中 | ✅ 已完成 | ❌ 已取消 | 🔒 阻塞中

---

## 📍 当前位置

```
Batch 181 — Slice 4-7（P2-10 路由拆分）
├── 已完成: P2-06（81b496a）/P2-08（1f41ae0）/路由基线守卫（85c2286）；ADR-0019；backend/CLAUDE.md 三项约定
├── 🔄 进行中: 4 个子代理并行拆分 9 个路由文件（knowledge / requirement×2 / wiki+apitest / 其余 4 文件）
├── ⏳ 待审批: 无（batch 完成前一次总确认）
└── ⏳ 下一步: 主代理集成 router.py + 删除旧文件 → QA 全量回归
```

---

## 📜 批次记录

### Batch 181 — 架构专项（2026-08-16）
- **产出**: worktree `F:\CamelTv-worktrees\DeepSeek_Harness-batch-181-taskqueue-route-softdelete`（feature/batch-181-taskqueue-route-softdelete @ 51e5441）；工件 x4
- **审批**: 进行中
- **耗时**: 进行中
- **记录**: [PM 计划](../test-platform-v2/work-logs/batch-181-taskqueue-route-softdelete-pm-plan.md)

---

## ⚠️ 阻塞与风险

| 阻塞项 | 严重度 | 描述 | 需要谁 | 记录时间 |
|--------|:------:|------|--------|----------|
| 无 | — | — | — | — |

---

## 🔗 相关工件

| 工件 | 路径 | 状态 |
|------|------|:----:|
| PRD | test-platform-v2/work-logs/batch-181-*-prd-summary.md | ✅ |
| PM 计划 | test-platform-v2/work-logs/batch-181-*-pm-plan.md | ✅ |
| Design 规范 | test-platform-v2/work-logs/batch-181-*-design-spec.md | ✅ |
| QA 报告 | test-platform-v2/work-logs/batch-181-*-qa-report.md | ⏳ |
| Leader 判决 | test-platform-v2/work-logs/batch-181-*-leader-verdict.md | ⏳ |
