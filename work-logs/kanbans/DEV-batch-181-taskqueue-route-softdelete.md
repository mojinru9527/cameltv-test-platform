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
| 1 | P2-06 TaskQueue 基类 + 迁移 + 六队列接入 | ✅ | 🔄 ⬅️ | ⏳ | ⏳ | ⏳ | **当前位置** |
| 2 | P2-08 软删统一（迁移+转换+测试） | ✅ | ⏳ | ⏳ | ⏳ | ⏳ | |
| 3 | 路由守卫基线（inventory + ORM ban） | ✅ | ⏳ | ⏳ | ⏳ | ⏳ | |
| 4 | knowledge.py 拆分 + ORM 收敛 | ✅ | ⏳ | ⏳ | ⏳ | ⏳ | |
| 5 | requirement / requirement_modules 拆分 | ✅ | ⏳ | ⏳ | ⏳ | ⏳ | |
| 6 | wiki / apitest 拆分 | ✅ | ⏳ | ⏳ | ⏳ | ⏳ | |
| 7 | test_case / release_bundles / lanhu_evidence / test_plan 拆分 | ✅ | ⏳ | ⏳ | ⏳ | ⏳ | |
| 8 | QA 全量回归 + 证据 + 门禁 | ⏳ | ⏳ | ⏳ | ⏳ | ⏳ | |
| 9 | Leader 判决 + 合入 | ⏳ | ⏳ | ⏳ | ⏳ | ⏳ | |

> 状态图例：⏳ 待开始 | 🔄 进行中 | ✅ 已完成 | ❌ 已取消 | 🔒 阻塞中

---

## 📍 当前位置

```
Batch 181 — Slice 1（P2-06 TaskQueue）
├── 已完成: PRD/PM/Design/看板四件工件；基线 pytest 摸底（后台运行中）；六队列与软删调用点全量摸底
├── 🔄 进行中: TaskQueue 基类编码 + 锁列迁移 + 六队列接入
├── ⏳ 待审批: 无（batch 完成前一次总确认）
└── ⏳ 下一步: Slice 2（P2-08 软删统一）
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
