# Batch 277a — AIQE §0 P0 代码侧清零：PRD

> **部门**：🟦 Product
> **日期**：2026-11-09
> **Executor**：DeepSeek Harness（agent-team，worktree `DeepSeek_Harness-batch-277-aiqe-ta-000-p0-clearance`）
> **分支**：feature/batch-277-aiqe-ta-000-p0-clearance（从 `origin/main 9cf83ee2e` 切出）
> **批次模式**：**complete**（代码 + 文档 + CI 守卫；六件工件）
> **范围**：14 号 §4.1 batch-277 的**代码侧**（P0-5 / P0-2 代码 / TA-001.5）；P0-1/P0-3 生产操作与 P0-4 `/uitest` 剥离拆为 277b

---

## 1. 问题陈述

13 号 §0 规定 P0-1..5 全部拿到真实证据前禁止进入 Phase 1（M1）。当前：

| P0 | 现状 | 本批处理 |
|----|------|---------|
| P0-1 生产 4 把 Key 轮换 + 真实 LLM 调用 | 需生产凭据与窗口 | ❌ 留给运维（277b-ops） |
| P0-2 备份恢复演练 + DROP 守卫 + downgrade 可执行 | DROP 守卫与可逆性可代码化；演练需生产 | ✅ 代码侧（守卫 + 可逆迁移），演练留运维 |
| P0-3 磁盘水位 | 需生产 | ❌ 运维 |
| P0-4 `/uitest` 剥离控制面浏览器 | 需改 `/uitest` 执行链到 node | ❌ 拆 277b（见 §5） |
| P0-5 ai_gateway 残留清零 | 纯代码 | ✅ 本批 |

**不做的直接后果**：`app/services/ai_gateway/`（8 文件）与 3 个 ai_* model 继续存在，`ai_client` 仍走本地路由/缓存/Shadow，M1 的 `test_runs` 会与旧 AI 基础设施纠缠；`scripts/ci/check-p0-ready.ps1` 不存在，Phase 1 门禁无法 fail-closed。

---

## 2. 成功指标

| 指标 | 阈值 | 结果 |
|------|------|:----:|
| `app/services/ai_gateway/` 删除 | 8 文件 | ✅ |
| `ai_job.py` / `ai_shadow_run.py` / `ai_gateway_cache.py` 删除 | 3 文件 | ✅ |
| 后端代码残留 `ai_gateway\|AiJob\|AiShadowRun\|AiGatewayCache` | **0**（app/tests/scripts） | ✅ |
| `ai_client` 直连 provider，无缓存/Shadow/本地路由 | 1 条路径 | ✅ |
| `ai_agents` 节点注册表保留（类改 `ExecutionNode`） | 生产数据不迁 | ✅ |
| 迁移 `DROP TABLE IF EXISTS` + downgrade 可重建 | up/down/up 退出码 0 | ✅ |
| TA-001.5 `check-p0-ready.ps1` fail-closed | 缺证据 → exit 1；self-test PASS | ✅ |
| 全量后端回归 | 0 new failure | ⏳ |
| 生产 P0-1/3/4 证据 | 277b | ⏳ |

---

## 3. 范围

- **做**：P0-5 全量代码删除 + 迁移 + 文档/ADR；P0-2 的 DROP 守卫与可逆迁移；TA-001.5 守卫脚本（含 self-test）；13 号 §0 P0-5 状态回写。
- **不做**：P0-4 `/uitest` 执行链改造（277b）、P0-1/P0-3 生产操作、C-278-1/2 登记（batch-279）。

---

## 4. 用户已确认事项

- 本会话审批策略 never ask；用户指示「代码侧先执行」→ 允许在无生产凭据前提下先交付代码侧；
- 生产操作（Key 轮换 / 磁盘 / 备份演练）不由 Agent 擅自执行，留运维窗口。

---

## 5. 277b 范围（本批 PR 内记录，不实现）

| 任务 | 原因 |
|------|------|
| T277-4 `/uitest` 剥离 | 需把 `trigger_job → ui_runner_queue → playwright_executor` 改造成 `ExecutionJob(kind=ui) → cameltv-node`，并保持 `UiTestRun` 状态/产物/前端轮询兼容；改动跨 4 个模块，按独立批次做（含回归与 UI 验收） |
| 生产 P0-1 / P0-3 / 备份演练 | 需生产访问与窗口 |

---

## 6. DoD（277a）

- [x] P0-5 代码清零 + `rg` 0（app/tests/scripts）；
- [x] 迁移可升可降（upgrade → downgrade -1 → upgrade 全 0）；
- [x] TA-001.5 守卫脚本 + self-test PASS；
- [x] ADR-0027/0028/0029 → superseded；`docs/ai/local-ai-agent.md` 重写；
- [ ] 全量后端 pytest 0 新增失败；
- [ ] PR checks 全绿 + squash merge。
