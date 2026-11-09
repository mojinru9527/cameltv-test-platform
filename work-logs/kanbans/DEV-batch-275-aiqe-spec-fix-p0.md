# 🗂️ Dev 看板：Batch 275 — AIQE Spec Fix P0

> **用途**：batch-274 Leader verdict 指出 13 号规格 7 条 P0 阻塞，本批 docs-only 修完，让 status: proposal → active。

---

## 📋 项目信息

| 字段 | 值 |
|------|-----|
| **项目名称** | AIQE Spec Fix P0（修 13 号规格 7 条 P0） |
| **批次号** | batch-275 |
| **关联文档** | [docs/platform-refactor/13-ai-quality-agent-merged-spec.md](../../docs/platform-refactor/13-ai-quality-agent-merged-spec.md) |
| **关联 PR** | #497（同一分支追加提交） |
| **关联 Leader verdict** | [work-logs/batch-274-aiqe-spec-review-leader-verdict.md](../batch-274-aiqe-spec-review-leader-verdict.md) §2 |
| **批次模式** | 轻量批次（PRD-lite + QA + Leader + 看板，docs-only） |
| **Executor** | Claude Code |
| **分支** | feature/ai-quality-agent-landing-plan |
| **总预估工时** | ≤ 1 天 |
| **看板创建** | 2026-11-09 |

---

## 🎯 交付切片进度

| # | Slice | 方案 | 编码 | 自测 | 审批 | 合入 | 备注 |
|---|-------|:----:|:----:|:----:|:----:|:----:|------|
| 1 | M-2 §4.7 加 version_task_run 对账 | ✅ | ✅ | ✅ | ✅ | 🔄 | 待 push |
| 2 | M-3 §4.8 加 execution_job_id 字段 | ✅ | ✅ | ✅ | ✅ | 🔄 | 待 push |
| 3 | M-4 §4.14 改为扩 environment（删 target_environments 新表） | ✅ | ✅ | ✅ | ✅ | 🔄 | **A 方案已入**；全文 3 处引用已改 |
| 4 | M-5 §4.19 + §0 P0-5 明示 ai_job/ai_shadow_run/ai_gateway_cache 一并删 | ✅ | ✅ | ✅ | ✅ | 🔄 | 待 push |
| 5 | M-16 §14 加 TestZeus AGPL 法务硬门禁 | ✅ | ✅ | ✅ | ✅ | 🔄 | §14.1 + §14.4 双处 |
| 6 | D-3 §4.12 加对象存储选型（本地 FS + prod 待定） | ✅ | ✅ | ✅ | ✅ | 🔄 | **C 方案已入** |
| 7 | D-9 §21 加 benchmark 数据集来源 | ✅ | ✅ | ✅ | ✅ | 🔄 | §21.0 新节 |
| 8 | status: proposal → active；version: v1.0 → v1.1-p0-fixed | ✅ | ✅ | ✅ | ✅ | 🔄 | frontmatter + banner |

> 状态图例：⏳ 待开始 | 🔄 进行中 | ✅ 已完成 | ❌ 已取消 | 🔒 阻塞中

---

## 📍 当前位置

Slice 1-8 全部 ✅；QA + Leader APPROVED；等待 push 到 PR #497 → 用户总确认 → merge。

---

## 📝 本批特殊说明

- **docs-only**：只改 13 号规格，不动代码；
- **同 PR 继续**：不新建 PR，复用 #497；完成后本 PR 转 Ready for review；
- **CI 门禁**：轻量批次 + docs-only → 复用 #497 已通过的 GitHub Actions；
- **用户决定已入库**：
  - M-4 = A 方案（扩 environment.py）
  - D-3 = C 方案（本地 FS + prod 待定）

---

## 📌 下一步

Slice 1-8 顺序执行；全部完成后：

1. 更新本看板全 ✅；
2. 产 QA 报告（docs 一致性复核）+ Leader verdict；
3. 将 PR #497 转 Ready for review；
4. 用户一次总确认后 squash merge。
