# Dev 看板 — Batch 228 Runtime 与任务页稳定性

> Executor: Codex | Workflow: agent-team | Created: 2026-09-03

## 项目信息

| 字段 | 值 |
|------|-----|
| 分支 | `fix/batch-228-runtime-ui-stability` |
| 基线 | `origin/main@7a9c4adc` |
| PRD | `work-logs/batch-228-runtime-ui-stability-prd-summary.md` |
| PM | `work-logs/batch-228-runtime-ui-stability-pm-plan.md` |
| Design | `work-logs/batch-228-runtime-ui-stability-design-spec.md` |
| 预计工时 | 4.5h |

## 切片进度

| # | Slice | 方案 | 编码 | 自测 | 审批 | 合入 |
|---|-------|:----:|:----:|:----:|:----:|:----:|
| 1 | 范围/场景请求稳定性 | ✅ | ✅ | ✅ | ✅ | ⏳ |
| 2 | Worker 列表真实能力 | ✅ | ✅ | ✅ | ✅ | ⏳ |
| 3 | Worker 持续心跳 | ✅ | 🔄 | ⏳ | ⏳ | ⏳ |
| 4 | Runtime/接入状态反馈 | ✅ | ⏳ | ⏳ | ⏳ | ⏳ |
| 5 | QA、PR、合入 | ✅ | ⏳ | ⏳ | ⏳ | ⏳ |

## 当前位置

`Batch 228 → Slice 3 → 编写失败测试`。Slice 2 已通过 10 项 registry 测试、F821 与前端 typecheck；当前固定 Worker 心跳重试和停止契约。

## 已确认根因

| 根因 | 等级 | 处理 |
|------|------|------|
| effect 依赖自身写入的 loading | P1 | 独立 `reloadVersion`，GET 传 signal |
| Worker 启动后只心跳一次 | P1 | 60 秒持续心跳、失败重试、退出清理 |
| Worker 列表遗漏 capabilities | P1 | 后端一次批量查询返回 |
| OFFLINE 操作列空白 | P2 | 恢复说明 + 重新检查 |
| durable blocked 被误解为接入 blocked | P2 | 明确可选能力与不阻断边界 |

## 风险

| 风险 | 等级 | 处理 |
|------|------|------|
| 心跳失败导致 Worker 退出 | P1 | 捕获瞬时错误并继续重试 |
| 列表修复引入 N+1 | P1 | 测试固定 capability 查询数为 1 |
| 网页暗示可启动远程进程 | P1 | 只提供诊断、刷新和 Runbook 指引 |
| 本地修复被误报为生产恢复 | P1 | QA/Leader 明确生产部署后验收条件 |

## 相关工件

| 工件 | 状态 |
|------|:----:|
| PRD | ✅ |
| PM 计划 | ✅ |
| 设计规范 | ✅ |
| 实施计划 | ✅ |
| QA 报告 | ⏳ |
| Leader 判决 | ⏳ |
