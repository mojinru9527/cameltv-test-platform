# Batch 277b-1 — P0-4 `/uitest` 节点化：PM 计划

> **部门**：🟨 PM
> **日期**：2026-11-09
> **输入**：PRD + 13 号 §0 P0-4 + baseline C-07

---

## 1. 任务拆分

| 任务 | 内容 | 依赖 | 预估 | 状态 |
|------|------|------|------|:----:|
| T277b-1 | `ui_test_run.execution_job_id` 字段 + Alembic（add/drop 可逆） | — | 0.2d | ✅ |
| T277b-2 | `uitest_execution_mode` / `uitest_node_timeout_seconds` 开关 | — | 0.1d | ✅ |
| T277b-3 | `ui_job_dispatch`：build_payload（spec 读取 + guard + env）/ dispatch / sync | T277b-1/2 | 0.4d | ✅ |
| T277b-4 | `trigger_job` node 分支 + runner 恢复排除节点任务 | T277b-3 | 0.2d | ✅ |
| T277b-5 | `execution_job_service.report` 投影钩子 | T277b-3 | 0.1d | ✅ |
| T277b-6 | 节点 `run_spec_files` + `ui` kind 派发 | — | 0.3d | ✅ |
| T277b-7 | 单测 12 条 + 文档（13 号 §0、node README） | 全部 | 0.3d | ✅ |

**合计 ≈ 1.6 人日**。

---

## 2. 依赖与顺序

```text
字段/迁移 ─┐
开关 ──────┼─► dispatch 服务 ─► trigger 分支 ─► report 投影
节点执行器 ─┘（独立，可并行）
```

---

## 3. 风险

| 风险 | 影响 | 缓解 |
|------|------|------|
| 节点环境没有 Playwright/npx | node 模式跑不起来 | 默认 local；277b-2 用真实节点验收后再切 |
| spec 安全拦截在控制面，节点照执行 | 若控制面被绕过仍有风险 | guard 在派发前硬拒绝；节点不解析 spec 语义 |
| 报告解析与 Playwright 版本差异 | 统计不准 | 只依赖 `suites/specs/tests/results.status` 稳定字段；真实节点验收再补 |
| 节点任务被本地 runner 恢复线程重复执行 | 双跑/脏状态 | `_recover_pending_runs` 排除 `execution_job_id != NULL` |
| 证据目录路径依赖 attempt | 产物 404 | `sync` 用 `evidence_store.bundle_dir(job_id, attempt)`，与上传一致 |

---

## 4. 里程碑

| 节点 | 判据 |
|------|------|
| M-277b-A | 迁移 up/down/up 全 0 |
| M-277b-B | 12 条新单测 + 90 条相关回归通过 |
| M-277b-C | 全量 pytest 0 失败 + ratchet increased=0 |
| M-277b-D | 277b-2：真实节点跑通 + 默认切 node + Dockerfile 去 Chromium + evidence |
