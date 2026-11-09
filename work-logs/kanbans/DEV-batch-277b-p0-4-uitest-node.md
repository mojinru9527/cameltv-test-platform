# 🗂️ Dev 看板：Batch 277b-1 — P0-4 `/uitest` 节点化（契约 + 执行器）

> **用途**：把 `/uitest` 执行腿从控制面 Playwright 迁到 cameltv-node 的**第一批**：派发契约、状态投影、节点 spec 执行器（默认仍 local）。真机验收与切默认在 277b-2。

---

## 📋 项目信息

| 字段 | 值 |
|------|-----|
| **项目名称** | P0-4 `/uitest` 节点化（277b-1） |
| **批次号** | batch-277b（拆 1/2，本批 1） |
| **关联文档** | [13 号 §0 P0-4](../../docs/platform-refactor/13-ai-quality-agent-merged-spec.md)、[baseline C-07](../../docs/aiqe/baseline.md) |
| **关联 PR** | 本批新建（feature/batch-277b-aiqe-p0-4-uitest-node） |
| **批次模式** | 完整（PRD/PM/Design/Dev/QA/Leader + 看板） |
| **Executor** | DeepSeek Harness（agent-team） |
| **分支 / 基线** | feature/batch-277b-aiqe-p0-4-uitest-node / origin/main `0fbd420fb` |
| **看板创建** | 2026-11-09 |

---

## 🎯 交付切片进度

| # | 任务 | 方案 | 编码 | 自测 | 审批 | 合入 | 备注 |
|---|------|:----:|:----:|:----:|:----:|:----:|------|
| 1 | `execution_job_id` 字段 + 可逆迁移 | ✅ | ✅ | ✅ | ✅ | 🔄 | up/down/up 全 0 |
| 2 | `uitest_execution_mode` 开关（默认 local） | ✅ | ✅ | ✅ | ✅ | 🔄 | node 分支显式启用 |
| 3 | `ui_job_dispatch`（build/dispatch/sync） | ✅ | ✅ | ✅ | ✅ | 🔄 | 含 spec_guard |
| 4 | `trigger_job` node 分支 + 恢复排除 | ✅ | ✅ | ✅ | ✅ | 🔄 | 不检查控制面 Playwright |
| 5 | `report` → UiTestRun 投影 | ✅ | ✅ | ✅ | ✅ | 🔄 | 幂等 |
| 6 | 节点 `run_spec_files` + ui kind | ✅ | ✅ | ✅ | ✅ | 🔄 | 报告解析/超时/路径 |
| 7 | 单测 12 条 + 文档 | ✅ | ✅ | ✅ | ✅ | 🔄 | 13 号 §0 + node README |

> 状态图例：⏳ 待开始 | 🔄 进行中 | ✅ 已完成 | ❌ 已取消 | 🔒 阻塞中

---

## 📍 当前位置

切片 1-7 全部 ✅；全量回归绿；等待 PR → checks → merge。

---

## 📝 本批特殊说明

- **默认 local**：生产行为零变化；node 模式需显式 `UITEST_EXECUTION_MODE=node`。
- **P0-4 未闭环**：Dockerfile 仍装 Chromium、无真实节点 E2E —— 277b-2 处理。
- **安全**：spec 在控制面先过 `spec_guard`；节点拒绝 `..`/绝对路径；env 剔除 SECRET/TOKEN/PASSWORD。

---

## 📌 下一步（277b-2）

1. 测试环境真实节点跑通 `/uitest`（report + 截图 + sha256）；
2. 处理 `xhr_capture`/playground 本地 Chromium；
3. Dockerfile 去 `playwright install` → 镜像无 Chromium；
4. 默认切 node + 产出 P0-4 evidence → 守卫转绿。
