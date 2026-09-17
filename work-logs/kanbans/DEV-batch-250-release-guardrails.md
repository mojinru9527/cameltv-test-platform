# 🗂️ Dev 部门项目看板 — batch-250-release-guardrails

> **用途**：追踪多批次开发的进度节点，防止上下文丢失。每次 Dev 部门启动时**必须先读取本看板**。

---

## 📋 项目信息

| 字段 | 值 |
|------|-----|
| **项目名称** | Batch 250 — 发布护栏（C249-1 / C249-3 / C249-4） |
| **关联 PM 计划** | 见 PRD-lite §5「纳入本批的 C 条件」（轻量批次无独立 PM 工件） |
| **关联 PRD** | [batch-250-release-guardrails-prd-summary.md](../batch-250-release-guardrails-prd-summary.md) |
| **总预估工时** | 3h（含发布验收的等待时间） |
| **已用批次** | 1 批 |
| **看板创建** | 2026-09-17 |
| **最后更新** | 2026-09-17 |

---

## 🎯 交付切片进度

| # | Slice | 方案 | 编码 | 自测 | 审批 | 合入 | 备注 |
|---|-------|:----:|:----:|:----:|:----:|:----:|------|
| 1 | C249-1 `release.ps1 -DryRun` | ✅ | ✅ | ✅ | ✅ | ⏳ | 实测零副作用（未构建/未登记/未上传/未发布） |
| 2 | C249-3 控制面测试 E402 清理 | ✅ | ✅ | ✅ | ✅ | ⏳ | `ruff check .` 全绿 + 45 tests |
| 3 | C249-4 迁移失败可观测性 | ✅ | ✅ | ✅ | ⏳ | ⏳ | **当前位置**：51 tests 全绿，待真实发布验收 |
| 4 | 真实发布验收（新护栏走一遍） | ✅ | ⏳ | ⏳ | ⏳ | ⏳ | 合入后执行：console 换新 → 真实小版本发布 |

> 状态图例：⏳ 待开始 | 🔄 进行中 | ✅ 已完成 | ❌ 已取消 | 🔒 阻塞中

---

## 📍 当前位置

```
Batch 250 — C249-4 迁移失败可观测性
├── 已完成: C249-1（-DryRun）/ C249-3（E402）/ C249-4（事件记录 target vs current，51 tests）
├── 🔄 进行中: 批次工件（PRD-lite/QA/Leader）+ 一次总确认
├── ⏳ 待审批: 用户一次总确认（推送 + Draft PR + checks 全绿后合入 main）
└── ⏳ 下一步: 合入后重建控制面镜像 → 真实发布一次验收 C249-1/-3/-4 → C-CONDITIONS 关闭
```

---

## 📜 批次记录

### Batch 250 — 发布护栏（2026-09-17）
- **产出**：`scripts/ops/release.ps1`（-DryRun）、`deploy/release-console/migrations.py`（状态行 + 诊断解析）、
  `deploy/release-console/app.py`（事件 reason 记录 target/current）、4 个测试文件（51 passed）
- **审批**：待用户一次总确认
- **耗时**：进行中
- **记录**：commit `2580c2ea`（C249-1/-3）、`f186181d`（C249-4）

---

## ⚠️ 阻塞与风险

| 阻塞项 | 严重度 | 描述 | 需要谁 | 记录时间 |
|--------|:------:|------|--------|----------|
| 发布验收需本机 Docker 引擎 + 生产 SSH 密钥 + 控制面令牌 | P2 | 本地 Docker Desktop 需先启动（验收前置） | 本机环境 | 2026-09-17 |

---

## 🔗 相关工件

| 工件 | 路径 | 状态 |
|------|------|:----:|
| PRD-lite | [batch-250-release-guardrails-prd-summary.md](../batch-250-release-guardrails-prd-summary.md) | ✅ |
| QA 报告 | [batch-250-release-guardrails-qa-report.md](../batch-250-release-guardrails-qa-report.md) | 🔄 |
| Leader 判决 | [batch-250-release-guardrails-leader-verdict.md](../batch-250-release-guardrails-leader-verdict.md) | ⏳ |
| 生产验收证据 | batch-250-release-guardrails-production-evidence-20260917.md（合入后） | ⏳ |
