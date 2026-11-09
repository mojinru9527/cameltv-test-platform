# 🗂️ Dev 看板：Batch 276 — AIQE Spec Fix P1

> **用途**：batch-274 Leader verdict 指出 13 号规格 12 条 P1，本批 docs-only 修完，把规格从 `v1.1-p0-fixed` 推到 `v1.2-p1-fixed`，为 batch-277（P0 清零）/ batch-278（TA-001 审计）扫清文档障碍。

---

## 📋 项目信息

| 字段 | 值 |
|------|-----|
| **项目名称** | AIQE Spec Fix P1（修 13 号规格 12 条 P1） |
| **批次号** | batch-276 |
| **关联文档** | [docs/platform-refactor/13-ai-quality-agent-merged-spec.md](../../docs/platform-refactor/13-ai-quality-agent-merged-spec.md) |
| **关联 PR** | 本批新建（feature/batch-276-aiqe-spec-fix-p1） |
| **关联 Leader verdict** | [work-logs/batch-274-aiqe-spec-review-leader-verdict.md](../batch-274-aiqe-spec-review-leader-verdict.md) §3 |
| **批次模式** | 轻量批次（PRD-lite + QA + Leader + 看板，docs-only） |
| **Executor** | DeepSeek Harness（agent-team workflow） |
| **分支** | feature/batch-276-aiqe-spec-fix-p1 |
| **声明范围** | docs, work-logs, .github |
| **总预估工时** | 2 天（14 号排期 W0） |
| **看板创建** | 2026-11-09 |

---

## 🎯 交付切片进度

| # | Slice | 方案 | 编码 | 自测 | 审批 | 合入 | 备注 |
|---|-------|:----:|:----:|:----:|:----:|:----:|------|
| 1 | M-6 project 隔离统一（§4 + 附录 B.1） | ✅ | ✅ | ✅ | ✅ | 🔄 | 9 类表逐张归属 |
| 2 | M-12 PR 模板强制问答（§24 + 模板） | ✅ | ✅ | ✅ | ✅ | 🔄 | 3 问 + 模板"架构护栏"节 |
| 3 | M-13 UI_OVERLAY `requires_ui_surface` + capability | ✅ | ✅ | ✅ | ✅ | 🔄 | observe / control 两条能力 |
| 4 | M-15 噪音规则可续期（§4.20 + §11.9） | ✅ | ✅ | ✅ | ✅ | 🔄 | 续期 = 新建行 + 自引用 |
| 5 | M-18 PoC 失败回退列（§14.4） | ✅ | ✅ | ✅ | ✅ | 🔄 | 4 个 PoC 全给回退 |
| 6 | M-19 团队规模换算（§23） | ✅ | ✅ | ✅ | ✅ | 🔄 | MVP 16-20 / V1 32-40 |
| 7 | M-20 TA 优先级档（§19） | ✅ | ✅ | ✅ | ✅ | 🔄 | 9 表 54 行 |
| 8 | D-1 seq 方言拆分（§8.3.1 + 附录 C） | ✅ | ✅ | ✅ | ✅ | 🔄 | SQLite 计数器 / PG advisory |
| 9 | D-4 脱敏实现选型（§16.2） | ✅ | ✅ | ✅ | ✅ | 🔄 | 正则 + YAML，presidio 延后 |
| 10 | D-5 蓝湖证据边界（§4.12） | ✅ | ✅ | ✅ | ✅ | 🔄 | linked_evidence 两列 |
| 11 | D-6 前端路由决策（§18.2） | ✅ | ✅ | ✅ | ✅ | 🔄 | /version-tasks + /runs 并存 |
| 12 | D-7 资源锁预检（§6.4） | ✅ | ✅ | ✅ | ✅ | 🔄 | TA-010.3 自实现 |
| 13 | 附带修复（4 处渲染/残留） | ✅ | ✅ | ✅ | ✅ | 🔄 | 表格 2 + 残留 1 + 表述 1 |

> 状态图例：⏳ 待开始 | 🔄 进行中 | ✅ 已完成 | ❌ 已取消 | 🔒 阻塞中

---

## 📍 当前位置

Slice 1-13 全部 ✅；QA 通过、Leader APPROVED；等待 push → Draft PR → required checks → squash merge。

---

## 📝 本批特殊说明

- **docs-only**：只改 13 号规格 + PR 模板 + work-logs，不动代码 / 迁移 / CI workflow；
- **技术判断有代码事实支撑**：`task_queue.py` 无 advisory lock、`sanitize.py` 已有正则、`lanhu_evidence` 已有 project 维度、router 已有 3 条 version-tasks（证据见 QA §3）；
- **不修 13 条 P2**（batch-274 QA §3.3），不抢 batch-277 / batch-278 的范围；
- **声明范围含 `.github`**：PR 模板是 M-12 唯一可执行落点，已在 PRD-lite 说明。

---

## 📌 下一步

1. push `feature/batch-276-aiqe-spec-fix-p1` → 创建 Draft PR；
2. `audit-ai-pr.ps1 -ExpectedWorkflow agent-team -ExpectedExecutor DeepSeek_Harness`；
3. required checks 全绿后 `-RequireSuccessfulChecks` 复跑 → squash merge；
4. 进入 **batch-277**（§0 P0-1..5 真实清零，完整批次）。
