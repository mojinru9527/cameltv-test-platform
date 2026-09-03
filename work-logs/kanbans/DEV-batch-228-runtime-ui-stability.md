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
| 3 | Worker 持续心跳 | ✅ | ✅ | ✅ | ✅ | ⏳ |
| 4 | Runtime/接入状态反馈 | ✅ | ✅ | ✅ | ✅ | ⏳ |
| 5 | QA、PR、合入 | ✅ | ✅ | ✅ | ⏳ | ⏳ |

## 当前位置

`Batch 228 → Slice 5 → 待用户一次总确认`。首轮 QA 已通过；尚未 push、创建 PR 或部署生产。

## 已确认根因

| 根因 | 等级 | 处理 |
|------|------|------|
| effect 依赖自身写入的 loading | P1 | 独立 `reloadVersion`，GET 传 signal |
| Worker 启动后只心跳一次 | P1 | 60 秒持续心跳、失败重试、退出清理 |
| Worker 启动脚本切到仓库根目录，无法导入后端 `app` | P1 | 启动器切到 `test-platform-v2/backend`，测试固定工作目录契约 |
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
| QA 报告 | ✅ |
| Leader 判决 | 🟡 有条件通过 |

## QA 验证

| 项目 | 结果 |
|------|------|
| 前端 | 137 files / 622 tests；typecheck、lint、build 全过 |
| 后端 | 2414 passed / 49 skipped / 1 xfailed；0 failed |
| Runtime 定向 | heartbeat + registry 16 tests passed |
| 迁移/路由 | revision/single-head 8 tests；route guards 4 tests |
| 浏览器 | 12 张三视口；0 console error；Scope/Scenario 各 1 次 GET |
| 门禁 | C 条件审计 PASS；dev-gate PASS_WITH_WARN（0 HARD） |

## 批次记录

| 阶段 | 状态 | 说明 |
|------|------|------|
| Product/PM/Design | ✅ | PRD、计划、设计规范就绪 |
| Dev | ✅ | 4 个功能切片 + 1 个门禁修正切片已本地提交 |
| QA | ✅ | 本地代码与关键路径 PASS |
| Leader | ⏳ | 有条件通过；待总确认、required checks 与最终审计 |
| 远端交付 | ⏳ | 未 push / 未建 PR / 未合入 / 未部署 |
