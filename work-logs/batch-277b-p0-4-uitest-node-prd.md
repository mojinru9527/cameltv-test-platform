# Batch 277b-1 — P0-4 `/uitest` 节点化（契约 + 执行器）：PRD

> **部门**：🟦 Product
> **日期**：2026-11-09
> **Executor**：DeepSeek Harness（worktree `DeepSeek_Harness-batch-277b-aiqe-p0-4-uitest-node`）
> **分支**：feature/batch-277b-aiqe-p0-4-uitest-node（从 `origin/main 0fbd420fb` 切出）
> **批次模式**：complete（代码 + 文档；六件工件）
> **拆批**：277b-1（本批：契约/执行器/测试）→ 277b-2（真实节点验收 + 默认切 node + Dockerfile 去 Chromium + 证据）

---

## 1. 问题陈述

P0-4 要求 `/uitest` 的执行腿从控制面 `playwright_executor`（subprocess `npx playwright test`，镜像需 Chromium）迁到 `cameltv-node`。当前：

- `UiTestRun` 与 `ExecutionJob` 无关联字段；node 只支持 `api/web`，没有"跑 spec 文件"的能力；
- 因此无法在不动行为的前提下验证"节点能跑 `/uitest`"。

本批先交付**可切换的契约与执行器**，默认模式仍为 `local`（零行为变化），把风险最高的部分（协议、报告解析、状态投影）先落地并用单测锁住。

---

## 2. 成功指标

| 指标 | 阈值 | 结果 |
|------|------|:----:|
| `UiTestRun.execution_job_id` 字段 + 迁移（可升可降） | 1 | ✅ |
| `uitest_execution_mode` 开关（local 默认 / node） | 1 | ✅ |
| node 模式 trigger → `ExecutionJob(kind="ui")` | 1 | ✅ |
| 节点 `run_spec_files`：报告解析/超时/非法路径/无报告 | 4 类用例 | ✅ |
| report → UiTestRun 投影（状态/结果/证据目录/用例回写） | 1 | ✅ |
| 新增单测 | ≥10 | ✅ 12 |
| 全量回归 0 失败 | 0 | ✅ |
| 真实节点 E2E + Dockerfile 去 Chromium | — | ⏳ 277b-2 |

---

## 3. 范围

**做**：迁移字段、开关、payload 构建（含 spec 安全拦截）、派发/投影、节点 spec 执行器、单测、13 号 §0 状态与节点 README。

**不做**：默认切 node、删 `playwright_executor`、改控制面 Dockerfile、真实节点 E2E、P0-4 evidence JSON（均 277b-2）。

---

## 4. 安全约束

- spec 内容在**控制面**先过 `spec_guard.assert_spec_safe`（child_process/fs/网络/process.env 等硬线），不通过直接拒绝；
- 节点只接收相对路径 spec 文件名（拒绝 `..`/绝对路径），写入独立目录后执行；
- 证据沿用 ExecutionJob 的 sha256 manifest 对账；
- 默认 `local`，生产不受本批影响。

---

## 5. DoD

- [x] 契约 + 迁移 + 单测 + 文档；
- [x] 全量回归 0 失败、quality ratchet increased_keys=0；
- [ ] 真机节点跑通 `/uitest`（277b-2）；
- [ ] 默认切 node + Dockerfile 无 Chromium + evidence（277b-2）。
