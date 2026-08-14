# Batch 182 — QA 报告：状态机统一 / ORM 收敛 / P3 打磨

> **mode: full** | 执行：DeepSeek_Harness（direct）| 日期：2026-08-16
> 范围：C181-2（FIX-173-P1-06）/ C181-1（路由 ORM）/ C181-3（P3-03/04/09）
> 分支：`feature/batch-182-status-orm-p3-polish`（基 6c8536e，7 个 commit）

## 0. 结论

- ✅ **P1-06 执行状态机统一**（C181-2）：5 表词表迁移 + 18 文件写/读站点 + open_api 双值兼容 + 前端共享映射（§1）
- ✅ **C181-1 路由层禁 ORM**：12 路由文件收敛 + 守卫 api/v1 全量（§2）
- ✅ **C181-3 P3 打磨**：P3-03 追溯轴标签 / P3-04 域命名体系 / P3-09 大页面拆分（§3）
- 后端全量：**1502 passed / 0 failed / 3 skipped（exit 0）**（batch-181 基线 1495/0，+7 新增测试）
- 前端：typecheck ✅ / build ✅ / 全量 vitest **479 通过** / eslint 0 错误

## 1. P1-06 验收证据

| 验收点 | 证据 |
|--------|------|
| 统一词表 | `app/core/execution_status.py`：pending/running/passed/failed/skipped/cancelled/blocked + canonical_exec_status（旧值兼容） |
| 迁移 | `20260816_b182_status_unify`：test_execution/test_plan_case.last_status/api_execution_task/ui_test_run/ui_test_job/test_schedule_run 六表映射；单头、幂等、downgrade 可逆（升降级循环实测） |
| 写站点 | test_plan_service/api_task_worker/ui_test_service/playwright_executor/ui_runner_queue/task_worker/scheduler/open_api/ui_test/playground 全切新词表 |
| 读站点 | statistics/dashboard/trace/triage/report_aggregator/report_service/version_mission 全切；统计/报告响应键（pass_/fail/skip/block）契约保留（_STATS_RESPONSE_KEY/_REPORT_STATS_KEY/trend 映射） |
| open_api 兼容 | POST /open/results 接受新旧双值（pass/fail/skip/block + 新词表）→ 规范化落库；校验集合扩展；通知判定双值兼容 |
| 前端 | `utils/executionStatus.ts` 共享映射（新旧双值中文标签）；TaskTab/PlanDetail/report/special/uitest/trace 全部收敛 |
| 测试 | `test_status_unify.py` 8 例（canonical/迁移映射/统计口径/open_api 双值/手动执行）+ 存量断言更新 13 个测试文件（c55_4/batch148/154/167/48/59/playwright/report_aggregator/ui_guard/batch155/batch169/test_testcase 等） |

## 2. C181-1 验收证据

| 验收点 | 证据 |
|--------|------|
| 收敛范围 | auth/defect/integration/open_api/organization/perf/perf_ws/playground/project/report/token/ui_test 12 文件全部查询 → services（新增 token_service；defect/playground/project/ui_test/user_service 补薄函数） |
| 守卫 | `test_route_layer_orm_ban.py` api/v1 全量 3/3 绿（模型 import/select/db.query=0；TYPE_CHECKING 类型标注豁免；SessionLocal 限 BackgroundTasks/流式豁免模式） |
| 回归 | token/auth/org/perf/playground/project/rbac/ui_test/report/integration 148 测试绿 |

## 3. P3 验收证据

| 项 | 证据 |
|----|------|
| P3-03 追溯轴标签 | trace/index.tsx CASE_TYPE_LABEL（功能/接口/UI 自动化，旧值别名兼容）；Drilldown 图例/状态统一 execStatusLabel |
| P3-04 域命名体系 | utils/domainNaming.ts（用户端/运营后台/接口测试/其他 分组规范 + 裸域补前缀 + 体育-运营后台兼容）+ 单测 15 例 + trace/testcase 接入；回填脚本 dry-run 幂等 |
| P3-09 页面拆分 | requirement AiResultModal 1509→<800、index 1202→<800（18 组件）；uitest 1152→562（6 组件）；perftest 924→296（8 组件）；testcase index 922→544、CaseDrawer 821→260（9 组件）；**6 个 >800 行页面清零** |

## 4. 硬门禁

| 门禁 | 结果 |
|------|------|
| 后端 pytest 全量 | **1502 passed / 0 failed / 3 skipped（exit 0）** |
| ruff F821 | All checks passed（exit 0） |
| alembic | 单头 `20260816_b182_status_unify`；upgrade→downgrade→upgrade 循环通过 |
| ORM 守卫 | api/v1 全量 3/3 绿；路径集守卫（batch-181 420 条）通过 |
| 前端 typecheck / build | 通过（exit 0） |
| 前端 vitest 全量 | 116 文件 479 测试全过（含 governance 白名单） |
| scan-common-bugs | HARD=3 均为既有基线（main.py:87、lanhu_provider ×2，非本批文件）→ 豁免 |

## 5. 交付物

- commits：`2af5667`（工件）/ `26c8249`+`fcfd963`+`4a5b965`（P1-06）/ `f146b50`（C181-1）/ `bfb5e2b`（P3-03/04 + 前端映射）/ `4ff7d78`（P3-09）
- 文档：ADR 无需新增（沿用 batch-181 ADR-0019 约定扩展）；backend/CLAUDE.md 状态词表小节待 Leader 判决确认；C181-1/2/3 关闭 + C182-1/2 登记

## 6. 复盘卡

| 字段 | 内容 |
|------|------|
| 计划耗时 | ~20h（计划）vs ~12h（实际） |
| 缺陷 | P0:0 / P1:0 / P2:0 / P3:5（子代理中断 4 + 守卫盲区 1，均主代理接管修复） |
| 返工次数 | 4（迁移测试 stamped 场景/open_api 路径与哈希/词表断言批量更新×2/守卫 TYPE_CHECKING 豁免） |
| 根因分类 | 工具链（子代理中断）/ 技术债 |
| 下次避免 | 委托任务按文件粒度拆分并设检查点；守卫测试先落地；词表变更同步扫测试断言 |
