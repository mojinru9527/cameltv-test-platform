# Batch 111 — PM Plan（体育平台自动化落地）

> **PM (🟨)** | Date: 2026-08-06

## 规格摘要

**原始需求**: PRD §1（批量执行回填/UI 定时/wiki 评审/Test5 契约/api-regression）
**目标时间**: 1.5 开发日（切片 30–60 分钟）
**执行器**: codex（用户确认沿用）

## 开发任务

### [ ] Task 1: 批次工件 + 看板 + C110-3 后端回填改造（TDD）
**描述**: 写 PRD/PM/Design/看板；`api_task_worker.execute_task` 每条 item 执行后回填
`TestCase.last_response_json/last_run_status`；新增 worker 单测。
**验收标准**: 单测通过（回填字段断言）；`ruff F821` 通过。
**涉及文件**: `backend/app/services/api_task_worker.py`、`backend/tests/test_api_task_worker_backfill.py`（新增）

### [ ] Task 2: 前端批量执行链路验证
**描述**: 验证 apitest「执行任务」Tab：选用例→建任务→结果列表→用例详情「请求结果」联动；
必要时补 UI（先走查再改）。
**验收标准**: typecheck/build 通过；交互截图证据。
**涉及文件**: `frontend/src/pages/apitest/*`

### [ ] Task 3: 生产 170 条批量执行 + 回填验证
**描述**: sportsadmin 调 `/apitest/tasks`（case_ids=170 + 生产环境 + confirm_prod）→ 轮询任务 →
核对 last_response_json/last_run_status 回填数与任务通过率。
**验收标准**: 任务完成；≥150 条回填；用例详情三栏证据。
**涉及文件**: `scripts/sports/run-batch-execution.py`（新增）、证据 JSON

### [ ] Task 4: UI 定时回归（job + schedule + 触发）
**描述**: 创建 production-p0 UI job（绑定生产环境）→ 创建每日定时任务 → 触发一次。
**验收标准**: 运行报告 + 10/10 通过证据。
**涉及文件**: `scripts/sports/setup-ui-schedule.py`（新增）、证据

### [ ] Task 5: wiki 差异评审闭环
**描述**: 拉取 10 组 diff 任务结果 → 差异项评审（采纳/驳回）→ 关键差异转待审产物 ≥3 项。
**验收标准**: 评审记录 + artifact_id 证据。
**涉及文件**: `scripts/sports/review-wiki-diffs.py`（新增）、证据

### [ ] Task 6: Test5 契约补拉 / api-regression 排查
**描述**: 尝试补拉 konfi-service/admin-service 契约并导入；检查 api-regression workflow 配置与失败日志。
**验收标准**: 契约导入成功或 Deferred 登记；workflow 修复或根因+豁免登记。
**涉及文件**: `scripts/sports/pull-test5-contracts.py`（新增）、`.github/workflows/api-regression.yml`（如需）

### [ ] Task 7: C110-4 确认 + QA + Leader + 一次总确认
**描述**: 用户确认 P0 口径；写 QA/Leader；障碍与 C 条件登记；一次总确认 → PR。
**验收标准**: 工件齐全；audit 0 硬错。

## 质量要求

- [ ] TDD：回填改造先写失败测试
- [ ] 后端 pytest（受影响模块）记录退出码（C78-1）；ruff F821
- [ ] 前端 typecheck/build + 相关 vitest（若改前端）
- [ ] 无调试残留；无硬编码密钥；生产操作 confirm_prod 显式
- [ ] 双 404 约定（C86-1）适用于新增断言
