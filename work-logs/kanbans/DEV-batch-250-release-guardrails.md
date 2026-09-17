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
| 1 | C249-1 `release.ps1 -DryRun` | ✅ | ✅ | ✅ | ✅ | ✅ | 实测零副作用（未构建/未登记/未上传/未发布） |
| 2 | C249-3 控制面测试 E402 清理 | ✅ | ✅ | ✅ | ✅ | ✅ | `ruff check .` 全绿 + 45 tests |
| 3 | C249-4 迁移失败可观测性 | ✅ | ✅ | ✅ | ✅ | ✅ | 51 tests 全绿 + 生产验收通过 |
| 4 | 真实发布验收（新护栏走一遍） | ✅ | ✅ | ✅ | ✅ | ✅ | `release-20260917-0006` → PRODUCTION_VERIFIED；暴露 C250-1 |

> 状态图例：⏳ 待开始 | 🔄 进行中 | ✅ 已完成 | ❌ 已取消 | 🔒 阻塞中

---

## 📍 当前位置

```
Batch 250 — 已收尾（等待证据/C 条件分支推送确认）
├── ✅ 已完成: C249-1 / C249-3 / C249-4 代码 + 单测 + 合入 main（PR #467 → 82aa9f4f）
├── ✅ 已完成: 控制面重建部署 + 真实发布验收（release-20260917-0006，PRODUCTION_VERIFIED）
├── ⚠️ 新发现: C250-1（成功路径迁移状态行被 4000 字符日志窗口截断，P2）
└── ⏳ 下一步: 推送 work-logs 证据 + C-CONDITIONS 关闭（fix/batch-250-closeout-evidence）→ 后续处理 C250-1
```

---

## 📜 批次记录

### Batch 250 — 发布护栏（2026-09-17）
- **产出**：`scripts/ops/release.ps1`（-DryRun）、`deploy/release-console/migrations.py`（状态行 + 诊断解析）、
  `deploy/release-console/app.py`（事件 reason 记录 target/current）、4 个测试文件（51 passed）
- **审批**：用户一次总确认 → PR #467 required checks 全绿 → squash 合入 main（`82aa9f4f`）
- **生产**：控制面 `release-20260917-2` 上线；`release-20260917-0006` → `PRODUCTION_VERIFIED`
- **耗时**：约 5h（含发布验收；两次 runner 构建失败后改为复用已验证镜像）
- **记录**：commit `2580c2ea`（C249-1/-3）、`f186181d`（C249-4）、`7e4c8319`（批次工件）、`82aa9f4f`（合入）

---

## ⚠️ 阻塞与风险

| 阻塞项 | 严重度 | 描述 | 需要谁 | 记录时间 |
|--------|:------:|------|--------|----------|
| `--target runner` 本机不可构建（C248-8） | P1 | 发布验收时复现 `exit 127`；本次以复用已验证 runner/ai-gateway 镜像绕过 | Dev（后续批次） | 2026-09-17 |

---

## 🔗 相关工件

| 工件 | 路径 | 状态 |
|------|------|:----:|
| PRD-lite | [batch-250-release-guardrails-prd-summary.md](../batch-250-release-guardrails-prd-summary.md) | ✅ |
| QA 报告 | [batch-250-release-guardrails-qa-report.md](../batch-250-release-guardrails-qa-report.md) | ✅ |
| Leader 判决 | [batch-250-release-guardrails-leader-verdict.md](../batch-250-release-guardrails-leader-verdict.md) | ✅ |
| 生产验收证据 | [batch-250-release-guardrails-production-evidence-20260917.md](../batch-250-release-guardrails-production-evidence-20260917.md) | ✅ |
