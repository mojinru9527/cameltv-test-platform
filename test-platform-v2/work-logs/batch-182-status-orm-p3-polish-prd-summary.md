# Batch 182 — 收尾批次：执行状态机统一 / 路由 ORM 收敛 / P3 打磨三项

> **mode: full**（重构 + Schema 变更，六部门工件）
> **来源**：C181-2（P1-06 状态机统一，P1）/ C181-1（路由 ORM 收敛，P2）/ C181-3（P3-03 追溯轴标签、P3-04 域命名体系、P3-09 >800 行页面）
> **执行**：DeepSeek Harness（direct）| 日期：2026-08-16

---

## 1. 问题陈述

Batch 181（PR #254）已合入 TaskQueue 统一/软删统一/路由拆分，Leader 登记三项后续条件。本批按优先级收尾：

1. **C181-2 / FIX-173-P1-06 执行状态机 4 套取值并存**：同一执行事实在 5 张表 4 套词表——
   `test_execution`/`test_plan_case.last_status`（pass/fail/skip/block）、`api_execution_task`（success/failed/cancelled）、`api_execution_task_item`（passed/failed/skipped，已达标）、`ui_test_run`/`ui_test_job`（done/fail）、`test_schedule_run`（completed/failed）。
   前端状态映射、统计/追溯/报告聚合层必须做映射（如 `ui_test_service.writeback_case_result` 的 status_map），口径易漂移。
2. **C181-1 路由层禁 ORM 剩余收敛**：batch-181 仅收敛 9 个拆分域；剩余路由文件（defect/report/open_api/ui_test/auth/organization/project/perf/token/integration/schedule/dashboard/trace/notify/dataset/version_mission/playground/av_check 等）仍含直连查询（~25 文件）。
3. **C181-3 P3 打磨三项**：追溯轴标签中英混排（P3-03）、域命名体系五种范式并存（P3-04）、6 个 >800 行页面（P3-09：AiResultModal 1509/requirement 1202/uitest 1150/perftest 924/testcase 901/CaseDrawer 817）。

## 2. 成功指标

| 指标 | 当前 | 目标 |
|------|------|------|
| 执行状态词表 | 4 套（pass/fail…、success…、done/fail…、completed…） | **1 套**：`pending/running/passed/failed/skipped/cancelled/blocked`（7 值，DB 规范值） |
| 存量数据 | 旧值行 | 迁移幂等映射到新值（downgrade 可逆） |
| open_api 回写契约 | 接受 pass/fail/skip/block | **向后兼容**：继续接受旧值 + 新值，内部规范化为新词表 |
| 前端状态映射 | 各页各自 statusMap | 收敛为共享映射（兼容新旧值展示） |
| 路由层直连 ORM | ~25 文件残留 | 全部收敛到 services（静态守卫全 api/v1 通过） |
| 追溯轴标签 | functional/接口/功能混排 | 全中文统一标签 |
| 域命名 | 5 种范式 | 统一前缀规范 + 前端分组 + 回填脚本 |
| >800 行页面 | 6 个 | 0 个 |
| 全量 pytest / typecheck / build | 基线 | 无新增失败；CI 双端全绿 |

## 3. 用户故事与验收标准

### US-1（P1-06）执行状态唯一词表
> 作为统计/追溯消费者，我希望所有执行表使用同一状态词表，这样聚合层无需逐表映射、口径不会漂移。

- **Given** 5 张执行表各有历史状态值（pass/fail/skip/block、success、done、completed）
- **When** 迁移执行后
- **Then** 全部行映射到 `pending/running/passed/failed/skipped/cancelled/blocked`，新写入只产生新值
- **And** 统计/追溯/报告/前端按新词表工作，旧前端值仍可展示（兼容映射）
- **And** CI 回写端点（POST /api/v1/open/results）继续接受旧值（向后兼容）

### US-2（C181-1）路由层零 ORM
> 作为后端开发者，我希望 api/v1 全部文件不直连 ORM，分层边界可静态校验。

- **Given** 剩余 ~25 个路由文件含 `from app.models`/`select(`/`db.query(`
- **When** 本批收敛后
- **Then** 全 api/v1 静态守卫（模型 import/select/db.query 计数=0）通过，`SessionLocal` 仅限 BackgroundTasks 豁免模式

### US-3（P3-03/04/09）打磨项
> 作为产品用户，我希望追溯轴标签统一中文、域命名成体系、大页面加载不卡顿。

- **Given** 追溯页轴标签混排 / 域标签五种范式 / 6 个大页面
- **When** 打磨后
- **Then** 轴标签全中文统一；域命名按「用户端/运营后台/接口测试」前缀分组展示 + 存量数据可回填；大页面拆分为独立组件文件（行为不变）

## 4. 非目标

| 项 | 说明 |
|----|------|
| 双写「物理删除」 | 计划执行同时写 test_execution 与 api_execution_task_item 是为双 UI（计划页/接口任务页）服务，本批**保留双写、统一词表**；单一事实源改造需 UI 合并决策 → 登记 C182-1 |
| AiTask/DshTask 词表（done） | 任务队列生命周期非执行记录，保持现状（Batch 181 TaskQueue 原语不依赖词表） |
| 执行记录表结构合并 | 不合并表、不改 FK；仅词表统一 |
| 生产数据回填自动执行 | 域命名回填脚本交付但不自动跑（需人工核对后执行） |
| 前端大页面重写 | 仅按组件拆分，不重构业务逻辑 |
| 其余 Open C 条件（C172/C167/C111 等） | 外部阻塞项，与本批无关 |

## 5. C 条件承接

- C75-1 mode:full ✅；C75-3 audit-cconditions ✅；C76-2 scan-common-bugs ✅；C78-1 模块 pytest ✅；C86-1 双 404 ✅；C104-5 worktree 核验 ✅
- **C181-2**：本批承接 ✅；**C181-1**：本批承接 ✅；**C181-3**：本批承接 ✅
- 完成后在 C-CONDITIONS.md 关闭 C181-1/2/3（附合入 commit），新增 C182-1（双写单一事实源）

## 6. 风险与缓解

| 风险 | 等级 | 缓解 |
|------|:----:|------|
| 状态值迁移破坏统计/报告口径 | 高 | 迁移映射表逐项核对；statistics/trace/report 读站点全量转换 + 专项测试；open_api 回写双值兼容 |
| 前端状态展示回归 | 中 | 共享状态映射组件（新旧值兼容），vitest 覆盖 |
| 路由 ORM 收敛行为漂移 | 中 | 薄函数沿用调用方会话；全量 pytest + 路径集守卫 |
| 页面拆分 TS 编译风险 | 中 | 纯组件抽取；typecheck + build + vitest |
| 域命名回填影响统计 | 中 | 脚本 dry-run 模式 + 前端仅展示层归一，不自动改库 |

## 7. 交付物

- P1-06：迁移 `20260816_b182_status_unify` + 写/读站点转换 + open_api 兼容 + 共享前端映射
- C181-1：剩余路由文件 ORM 收敛 + 静态守卫收紧（api/v1 全量）
- P3-03：追溯轴标签统一
- P3-04：域命名规范 + 前端分组 + 回填脚本
- P3-09：6 页面拆分
- 工件六件 + 看板 + ADR 更新（如需）
