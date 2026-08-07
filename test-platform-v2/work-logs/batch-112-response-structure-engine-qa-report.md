# Batch 112 — QA 报告（response_structure 断言引擎 + 4 端点校准 + 批量全绿 + C111-3）

> **QA (🔍)** | Date: 2026-08-07 | Verdict: 有条件通过（C111-2/C111-3 生产验证待合入部署）

## 1. 交付与证据

| 资产 | 结果 | 证据 |
|------|------|------|
| response_structure 断言引擎 | `api_execution_service._run_assertions` 支持 exists/not_empty/is_object_or_array/len_lte + `data.*` 动态豁免 warning + hint 提示；新增单测 **14/14 通过** | `backend/app/services/api_execution_service.py` + `backend/tests/test_api_execution_response_structure.py` |
| 引擎回归 | `test_apitest_generation` + `test_api_task_worker` + `test_apitest_tasks` + `test_api_execution_snapshots` **74/74 通过**；后端全量 **1167 passed / 3 skipped / 0 failed**（退出码 0） | pytest 运行日志 |
| 4 端点校准脚本 | `scripts/sports/calibrate-interface-cases.py`（login→form+clientip；ads/search→必填头；news/get→get_visible）；干跑验证 **36/36 通过**（login 9、ads 21、search 3、news 3） | 干跑日志 + 本报告 §2 |
| 批量执行脚本增强 | `run-batch-execution.py` 新增 `--label` + 按端点聚合 passed/failed 明细输出 | 代码 + py_compile |
| UI 定时脚本增强 | `setup-ui-schedule.py` 新增 `--label` + 触发后轮询 `GET /ui-tests/runs/{run_id}` 写运行报告证据 | 代码 + py_compile |
| 生产缺陷登记 | **B112-1**：news/get 生产全 id 业务 400（含登录态/必填头），`news/get_visible` 同 id 200 正常 → 用户端用例重指向 get_visible | 生产实测（2026-08-07，多 id/头组合探测） |

## 2. 4 端点校准实测证据（2026-08-07 生产实跑）

| 端点 | 校准前（Batch 110 用例） | 校准后（契约实参） | 干跑验证 |
|------|-------------------------|---------------------|---------|
| login/anonymous/web | JSON body 无 clientip → 业务 400、信封漂移 `{timestamp,status,msg}` | formData appCode + `clientip` 头 → `code=0/success=true`，信封 `{code,msg,detail,success}` | 9/9 |
| ads/activity/get | 无 Accept-Language/deviceId/X-Real-IP → 业务 400 data 缺失 | 补三头 + 真实 matchId → 200 + data | 21/21 |
| search/query | 无 Accept-Language → 业务 400 data 缺失 | 补 `Accept-Language: en` → 200 + data | 3/3 |
| news/get | 样本 id 已失效（样本本身业务 400） | 重指向 `news/get_visible`（同真实 id，用户可见端点）→ 200 + data | 3/3 |

> 根因共性：Batch 110 XHR 样本未采集请求头，生成用例缺少契约必填头（C103-3/4 真实业务参数口径未覆盖请求头）。

## 3. 可执行门禁（命令 + 退出码）

| 门禁 | 结果 | 退出码 |
|------|------|--------|
| 后端全量 pytest（tests，`-q -x`） | ✅ 1167 passed / 3 skipped / 0 failed（265.39s） | 0 |
| ruff `check app/services/api_execution_service.py --select F821` | ✅ All checks passed | 0 |
| 脚本 py_compile（3 个） | ✅ 0 错误 | 0 |
| Alembic 单头 | ✅ `20260806_batch106_project_invite (batch27) (head)`（本批无迁移） | 0 |
| scan-common-bugs（C76-2） | ✅ HARD=0 / WARN=209（与 batch-89 基线 209 持平，无新增类别） | 0（HARD） |
| validate_repo_boundaries --check | ✅ RESULT: PASS（1408 shared / 445 backend / 386 frontend / 35 ops） | 0 |
| 前端 typecheck/build | ⏸ 本批无前端 React 改动（仅断言结果 warning 字段为后端新增，前端兼容未知字段） | N/A |
| audit-cconditions | 🔄 Leader 阶段运行（0 硬错目标） | — |

## 4. 缺陷/障碍

| # | 级别 | 问题 | 证据 | 处理 |
|---|:----:|------|------|------|
| B112-1 | P1 | news/get 生产业务 400（全 id/带登录态均复现）；get_visible 同 id 200 正常 | 2026-08-07 多参数探测日志 | 用户端用例重指向 get_visible；服务端缺陷登记 `改进任务backlog.md` SPORT-INT 追加 |
| B112-2 | P2 | Batch 110 XHR 样本未采集请求头 → 4 端点用例漏必填头 | 契约对比 + 实跑 400 | 本批校准脚本补头；后续采集工具（B10）补请求头捕获 |

## 5. 诚实性说明

- 断言引擎语义与脚本侧 `execute-interface-cases.py` 完全对齐（envelope 严格 / `data.*` 动态豁免 warning），
  平台与脚本不再双口径；97/97 的既有结论由引擎单测 + 全量回归承接。
- 4 端点校准为**干跑验证 36/36**（未写生产库）；生产库替换在校准脚本就绪后执行，证据为
  `evidence/batch-112/calibration-summary.json`（含 before/after/verify）。
- 生产批量执行重跑（170 全绿）与 UI 定时触发（10/10）依赖本批引擎合入部署（Railway），
  按 Batch 111 既定模式登记 C111-2/C111-3 为 In-Progress，部署后执行并回填证据；不以文档代替执行证据。
- 用户 2026-08-07 方向反馈（知识中心模块关联优先 / UI 交互用例）登记 C112-1/C112-2，本批不混入。

## 6. 发布建议

状态: **有条件通过**
必修复: 0 ｜ 条件: C111-2（部署后 170 全绿 + 回填核对）、C111-3（UI 定时 10/10 核对）

## 7. 复盘卡

| 计划耗时 | 缺陷(P0/P1/P2/P3) | 返工次数 | 根因分类 | 下次避免 |
|----------|-------------------|----------|----------|----------|
| 计划 1d / 实际 0.5d | 0/1/1/0 | 1 | 工具链 + 外部依赖 | 用例生成必须按契约补请求头后再落库；生产执行前置确认部署与凭据 |

**技能使用**：`cameltv-agent-team`（流水线）、`cameltv-bug-guard`（envelope 码 vs HTTP 码约定）、
`test-case-design`/`cameltv-api-test`（接口断言与校准）、`playwright-cli`（UI 定时核对，部署后）。
