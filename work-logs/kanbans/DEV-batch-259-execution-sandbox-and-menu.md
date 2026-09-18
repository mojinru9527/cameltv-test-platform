# 🗂️ Dev 部门项目看板 — Batch 259

> **用途**：追踪本批次开发进度，防止上下文丢失。每次 Dev 部门启动时**必须先读取本看板**。

---

## 📋 项目信息

| 字段 | 值 |
|------|-----|
| **项目名称** | batch-259-execution-sandbox-and-menu（B2 落地批次） |
| **关联 PM 计划** | [batch-259-execution-sandbox-and-menu-pm-plan.md](../batch-259-execution-sandbox-and-menu-pm-plan.md) |
| **关联 PRD** | [batch-259-execution-sandbox-and-menu-prd-summary.md](../batch-259-execution-sandbox-and-menu-prd-summary.md) |
| **批次档位** | 完整批次（六件） |
| **总预估工时** | 22h |
| **看板创建** | 2026-09-18 |
| **最后更新** | 2026-09-18 |

---

## 🎯 交付切片进度

| # | Slice | 方案 | 编码 | 自测 | 审批 | 合入 | 备注 |
|---|-------|:----:|:----:|:----:|:----:|:----:|------|
| 1 | 对象存储路径收敛 S4（B2-4） | ✅ | 🔄 ⬅️ | ⏳ | ⏳ | ⏳ | **当前位置** |
| 2 | 密钥派生统一 + fail-fast S5（B2-5） | ✅ | ⏳ | ⏳ | ⏳ | ⏳ | 依赖 Slice 1 完成后同批提交 |
| 3 | dry-run≠沙箱 + 计划路径 validate（B2-3） | ✅ | ⏳ | ⏳ | ⏳ | ⏳ | |
| 4 | 危险 API 静态拦截（B2-2） | ✅ | ⏳ | ⏳ | ⏳ | ⏳ | 执行链路变更 |
| 5 | 执行沙箱硬化 H1（B2-1） | ✅ | ⏳ | ⏳ | ⏳ | ⏳ | 执行链路变更 |
| 6 | 一级菜单收敛 4 入口（B2-6） | ✅ | ⏳ | ⏳ | ⏳ | ⏳ | 前端 |

> 状态图例：⏳ 待开始 | 🔄 进行中 | ✅ 已完成 | ❌ 已取消 | 🔒 阻塞中

---

## 📍 当前位置

```
Batch 259 — Slice 1：对象存储路径收敛（审计 S4）
├── 已完成: worktree 验证（base=origin/main@2ced1baf）；PRD/PM/Design 工件；B2 目标复核
├── 🔄 进行中: local.py 路径收敛 + 回归用例
├── ⏳ 待审批: 本批次一次总确认（推送 + Draft PR + required checks 通过后合入）
└── ⏳ 下一步: Slice 2/3（S5、dry-run）→ Slice 4/5（拦截、沙箱）→ Slice 6（菜单）→ QA/Leader
```

---

## 📜 批次记录

### Batch 258 — B1 落地（2026-09-18，已合入）
- **产出**: PR #477 → squash `2ced1baf`（16 commits / 43 文件 / +5091 −68）；三条安全硬线 S1/S2/S3 闭合
- **审批**: 用户一次总确认通过；required checks 全绿（后端 16m55s / 前端 3m55s）
- **耗时**: ~21h（计划 16h）
- **遗留**: `C258-1`（Test5 真机验收，需 VPN）、`C258-2`（节点侧凭据隔离 → 本批 B2-1）

### Batch 259 — B2 落地（2026-09-18，进行中）
- **产出**: 待补
- **审批**: 待一次总确认
- **耗时**: 进行中

---

## ⚠️ 阻塞与风险

| 阻塞项 | 严重度 | 描述 | 需要谁 | 记录时间 |
|--------|:------:|------|--------|----------|
| 环境代理/直连均不稳定 | P3 | GitHub 直连期间 `Connection reset`，环境代理 `127.0.0.1:7688` 期间恢复；未改全局配置 | — | 2026-09-18 |
| C258-2 继承 | P2 | 节点侧凭据隔离由本批 B2-1 关闭（H1 沙箱） | 本批 | 2026-09-18 |

---

## 🔗 相关工件

| 工件 | 路径 | 状态 |
|------|------|:----:|
| PRD | [link](../batch-259-execution-sandbox-and-menu-prd-summary.md) | ✅ |
| PM 计划 | [link](../batch-259-execution-sandbox-and-menu-pm-plan.md) | ✅ |
| 设计规范 | [link](../batch-259-execution-sandbox-and-menu-design-spec.md) | ✅ |
| QA 报告 | `../batch-259-execution-sandbox-and-menu-qa-report.md` | ⏳ |
| Leader 判决 | `../batch-259-execution-sandbox-and-menu-leader-verdict.md` | ⏳ |
