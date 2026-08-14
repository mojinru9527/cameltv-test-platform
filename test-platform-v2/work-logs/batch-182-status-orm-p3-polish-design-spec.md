# Batch 182 — Design Spec：状态机统一 / ORM 收敛 / P3 打磨

> 配套 PRD：`batch-182-status-orm-p3-polish-prd-summary.md`。本文件为可执行技术契约。

---

## 1. P1-06 执行状态机统一

### 1.1 统一词表（DB 规范值）

```
pending | running | passed | failed | skipped | cancelled | blocked
```

### 1.2 表级映射（迁移 `20260816_b182_status_unify`，单头、幂等、可降级）

| 表.列 | 旧值 → 新值 | 说明 |
|--------|------------|------|
| `test_execution.status` | pass→passed, fail→failed, skip→skipped, block→blocked | pending 不变 |
| `test_plan_case.last_status` | 同上 | 与 test_execution 同词表 |
| `api_execution_task.status` | success→passed | pending/running/failed/cancelled 不变 |
| `api_execution_task_item.status` | 无需迁移 | 已是 passed/failed/skipped |
| `ui_test_run.status` | done→passed, fail→failed | pending/running/cancelled 不变 |
| `ui_test_job.status` | idle→pending, done→passed, fail→failed | running 不变 |
| `test_schedule_run.status` | completed→passed | running/failed 不变 |

迁移实现：`UPDATE ... SET status='passed' WHERE status='pass'` 逐值幂等；downgrade 反映射。

### 1.3 写站点转换（全部切新词表）

| 文件:行 | 现状 | 改后 |
|---------|------|------|
| test_plan_service.py:516,552,559,584,1059-1088 等 | status = "pass"/"fail"；pc.last_status | "passed"/"failed" |
| test_plan_service.py 手动批量执行（batch-execute） | 请求 status 直接落库 | 规范化函数 `canonical_exec_status(v)`：旧值/新值→新值 |
| api_task_worker.py:210,225-230 | task.status = "success" | "passed"（汇总终态同步） |
| ui_test_service.py:309-325,363-368 | run.status/job.status = "done"/"fail" | "passed"/"failed" |
| playwright_executor.py:472-477 | 同上 | 同上 |
| ui_runner_queue.py:119-124 | 同上 | 同上 |
| task_worker.py:125-130 | 同上 | 同上 |
| scheduler.py:146 | run.status = "completed" | "passed" |
| open_api.py:285 | run.status = "fail" | "failed" |

### 1.4 open_api 回写向后兼容（CI 契约不变）

- `POST /api/v1/open/results`：接受 `{pass, fail, skip, block, pending}`（旧）∪ `{passed, failed, skipped, blocked, pending}`（新），经 `canonical_exec_status` 规范化后落库。
- `test_plan.py:101` schema `Literal` 扩展为接受双值集合（请求层兼容）。

### 1.5 读站点转换

| 文件 | 现状 | 改后 |
|------|------|------|
| statistics_service.py:57-58,134 | status == "pass"/"fail" | "passed"/"failed" |
| dashboard_service.py:40-41 | 同上 | 同上 |
| trace_service.py:142,170,212,221,231 | "pass" 判定/分组键 | "passed"（分组键同步） |
| triage_service.py:60 | "fail" | "failed" |
| report_service.py:111,328,633,748 | **stats 响应键 pass/fail/skip/block 保留**（API 契约），仅内部计数来源改新词表 | 键不变、查询条件改 |
| scheduler.py:100,123,139 | schedule run 结果统计键 "block" | 核对来源后同步（若为 test_execution 派生则键保留） |
| test_plan_service.py:73,416,422 | stats 键 pass_/fail/skip/block（响应契约） | 键保留，来源改新词表 |
| report_aggregator.py | ui_run result 解析（json 内 status） | 双值兼容解析 |

### 1.6 前端映射收敛

- 新增共享模块 `frontend/src/utils/executionStatus.ts`：`EXEC_STATUS_LABEL`（覆盖新旧双值，中文标签：待执行/执行中/通过/失败/跳过/已取消/阻塞）、`normalizeExecStatus(v)`。
- 消费方替换：apitest/TaskTab STATUS_MAP、testplan 执行结果展示、uitest run 状态、workbench 统计、trace 图例、report 统计卡、defect 不涉及（缺陷状态独立）。
- 后端响应中 status 字段已是新值；旧值兼容映射仅供历史数据/过渡期展示。

### 1.7 测试（`tests/test_status_unify.py` 新增）

1. 迁移幂等 + 反向降级 + 存量值映射断言
2. `canonical_exec_status` 双值规范化单测
3. statistics/dashboard/trace 聚合在新词表下计数正确（构造 passed/failed 行）
4. open_api 回写旧值（pass）→ 落库 passed；新值（passed）→ passed
5. 计划执行链路：auto_execute/execute_all/manual 后 test_execution 与 item 均为新词表
6. UI 执行链路：run/job 终态为新词表

---

## 2. C181-1 路由层 ORM 收敛

### 2.1 剩余清单（实现时以 grep 为准，前缀：`from app.models`/`select(`/`db.query(`/`SessionLocal(`）

路由文件：defect / report / open_api / perf_ws / playground / token / integration / ui_test / auth / organization / project / perf / schedule / dashboard / trace / notify / dataset / version_mission / ops_releases / template / av_check / environment / system / interaction_coverage / agent / dsh_tasks

### 2.2 规则

- 查询收敛到对应 services（薄函数 `(db, ...)`，沿用调用方会话；路由层保留 `db.commit()`）。
- `SessionLocal(` 仅允许 BackgroundTasks 独立会话模式（defect/report/test_plan 既有豁免，逐处标注）。
- 守卫升级：`tests/test_route_layer_orm_ban.py` 从「9 域拆分文件」扩展为 **api/v1 全量**（豁免名单随收敛缩小，本批后应可移除或仅剩 BackgroundTasks 模式）。

---

## 3. P3-03 追溯轴标签统一

- 文件：`frontend/src/pages/trace/index.tsx`、`Drilldown.tsx`。
- 现状：用例类型分布轴标签 functional/接口/功能 混用。
- 改后：统一中文标签（功能/接口/UI 自动化），常量集中到 `executionStatus.ts` 或 trace 本地常量，组件内不散落英文。

## 4. P3-04 域命名体系收敛

- 规范：域标签统一前缀范式——`用户端/xxx`、`运营后台/xxx`、`接口测试/xxx`；裸域（UGC/广告等）归入 `用户端/` 前缀映射表。
- 前端：域下拉分组（batch-178 已做分组/搜索）的组名与 `case_surface` 口径一致；追溯「按域覆盖」轴按前缀分组。
- 数据：`scripts/backfill-domain-naming-b182.py`（dry-run 默认）——按映射表归一 domain 字段；交付不自动执行。
- 映射表来源：`docs/体育平台-关联基座.json` 的 13 用户模块/15 运营模块 + 现有 90+ 域标签聚类（实现时枚举）。

## 5. P3-09 >800 行页面拆分

| 页面 | 行数 | 拆分方案（按组件抽取，行为不变） |
|------|------|------|
| requirement/AiResultModal.tsx | 1509 | 覆盖矩阵/缺口/结果表格/工具栏 抽子组件（补全任务模态、统计卡、导入卡片） |
| requirement/index.tsx | 1202 | 列表/上传/详情抽屉/评审弹窗 抽子组件 |
| uitest/index.tsx | 1150 | 任务列表/运行详情/脚本资产/采集 抽子组件 |
| perftest/index.tsx | 924 | 会话列表/指标图/报告 抽子组件 |
| testcase/index.tsx | 901 | 表格/筛选/批量操作 抽子组件 |
| testcase/CaseDrawer.tsx | 817 | 请求参数/断言/结果三栏 + 评审/版本 抽子组件 |

- 拆分后各文件 <800 行；typecheck/build/vitest 全绿；行为无变化（纯移动）。
- 守卫：新增前端脚本或手动核对（拆分行数断言写入 vitest 或 QA 证据）。

---

## 6. 实施顺序

1. S1 工件（本文件 + PRD + PM + 看板）
2. S2 P1-06 迁移 + `canonical_exec_status` + 写/读站点 + open_api 兼容 + 后端测试
3. S3 P1-06 前端映射收敛 + vitest
4. S4 C181-1 ORM 收敛（子代理按文件组分治）+ 守卫收紧
5. S5 P3-03 追溯轴标签（小，主代理）
6. S6 P3-04 域命名（前端 + 回填脚本）
7. S7 P3-09 页面拆分（子代理）
8. S8 全量回归（后端 pytest + 前端 typecheck/build/vitest）+ 工件
9. S9 Leader 判决 + 总确认 → push/PR/合入
