# Batch 263 PRD-lite — 老队列遗留面处置裁定（`ui_test_service`）

> **Product/PM** | Date: 2026-09-19 | 档位：**轻量批次**
> `mode: light`
> 豁免理由：零代码改动的**裁定 + 文档对齐 + C 条件登记**——不新增接口/依赖/Schema，不触碰执行链路（判定见 `docs/agent-team/pipeline-modes.md`：内部流程/证据类）。

## 1. 背景

`docs/platform-refactor/10-landing-plan-task-backlog.md` §4-2 与 `09-platform-landing-plan.md` §124 都点名：
「老队列（`ui_test_service` / `api_task_worker`）**冻结不扩展**，B4 后删除」。

B4（#480，`334748bf`）已合入，但 `C-CONDITIONS.md` 里**没有任何条目承接这句话**——用户 2026-09-19 授权开本批「登记为 C 条件并同时裁定删除 or 保留并记录理由」。

## 2. 取证（详见 QA 报告）

| # | 事实 | 证据 |
|---|------|------|
| F1 | B1–B4 期间**未改动**老队列文件 → 冻结成立 | `git log --oneline 2ced1baf..04deca80 -- app/services/ui_test_service.py app/services/api_task_worker.py` 为空 |
| F2 | 执行器侧**已删除** | `api_task_worker.py`、`plan_execution_queue.py` 均不存在；删除提交 `72a3002d`（PR #455）；`tests/test_legacy_delete_gate.py` 2 passed；门禁 fixture 8/8 flags 全 true |
| F3 | `ui_test_service.py` 仍在，被 6 个文件引用 | `scheduler.py` / `playground_service.py` / `open_api.py` / `release_bundles_core.py` / `api/v1/ui_test.py` / `open_knowledge.py` |
| F4 | `playwright_executor.py` 仍在 → 控制面仍可跑浏览器 | 文件存在；`ui_test_service.execute_playwright_async` 调 `run_playwright_test` |
| F5 | AITDE 蓝图**明确复用**这两个模块 | `docs/aitde/architecture/01_Overall_Upgrade_Blueprint.md` §11.2（`playwright_executor` / `ui_test_service` / `ui_runner_queue` 列为复用件） |

## 3. 本次裁定

1. **冻结成立**，无需补救。
2. **执行器删除已完成**（`api_task_worker` / `plan_execution_queue`），删除门禁在测、防回退。
3. **`ui_test_service` 判定「保留」**：它已不承担队列职责（执行面由 B1-4/B1-5/B1-6 的 `ExecutionJob` + `cameltv-node` 承接），而是 `/uitest` 的产品服务层 + AITDE 复用件。删除它会打断 `/uitest` 与 CI 触发链，属产品决策，非本批范围。
4. **残留张力登记 `C263-1`**：控制面仍保留 `playwright_executor.py` 内置浏览器路径，与 09 §3.1「控制面 ❌ 跑浏览器」的**终态**不一致——收口动作是「`/uitest` 执行面切到 node」或「明确长期保留并写进 ADR-0026 修订」，故登记而非就地删除。
5. **文档对齐**：把上述状态写进 09 §124 与 10 §4-2，避免后人重读原文时以为删除已完成。

## 4. 非目标（明确不做）

- ❌ 不删除 `ui_test_service.py` / `playwright_executor.py`（未经 AITDE 迁移即删会打断产品面）
- ❌ 不修改任何控制面代码、不动 Schema、不新增依赖
- ❌ 不改 `/uitest` 的现有行为

## 5. 验收判据

| # | 判据 |
|---|------|
| A1 | `C-CONDITIONS.md` 含 `C263-1`，且带解除条件 |
| A2 | 09 §124 / 10 §4-2 能读到「谁已删、谁保留、为什么」 |
| A3 | 全批零代码改动（`git diff --stat` 只含 docs/work-logs/C-CONDITIONS） |
| A4 | 门禁：`scan-common-bugs` HARD 0、`audit-cconditions` hard 0 / warnings 0、CI 分类为文档域 |
