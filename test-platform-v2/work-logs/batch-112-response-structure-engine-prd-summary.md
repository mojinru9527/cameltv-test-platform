# Batch 112 — PRD（response_structure 断言引擎 + 4 端点用例校准 + 批量执行全绿 + C111-3 UI 定时回归）

> **Product (🟦)** | Date: 2026-08-07 | Status: Review

```markdown
mode: full
豁免理由: 无（含后端断言引擎新增行为 + 生产批量执行重跑 + UI 定时任务触发验证，走完整六部门流水线）。
非目标:
- 用例生成规范/覆盖度再扩量（C103-1 已达标，本期不扩）
- 知识中心「模块-接口-功能」关联梳理与用例生成基座重构（用户 2026-08-07 反馈方向，登记 C112-1，下一批次执行）
- UI 交互点击跳转类用例补充（用户 2026-08-07 反馈，登记 C112-2，下一批次执行）
- Test5 konfi/admin 契约补拉（C111-4 继续 Deferred：内网/凭据未就绪）
- api-regression runner 验证（C111-1 继续外部依赖：internal-network runner 未启动）
- 运营后台生产账号深度操作（只读口径维持）
```

## 1. 问题陈述

Batch 111 已交付平台批量执行回填（C110-3）并创建 run-batch-execution.py / setup-ui-schedule.py，
但合入部署后的验证暴露 4 个明确缺口：

1. **平台断言引擎不支持 `response_structure` 断言类型（102/170 失败根因）**：
   `api_execution_service._run_assertions` 只支持 status_code/response_time/jsonpath/regex/header/
   json_schema/type/array_length；Batch 107/110 生成的接口用例带 `response_structure` 断言
   （envelope/data 键/records 长度/首条记录核心字段），平台批量执行一律按「未知断言类型」判失败。
   Batch 111 生产批量执行 task#2 实测：170 条仅 68 过 / 102 失败，全部为含结构断言的用例。
   脚本侧 execute-interface-cases.py 已有同语义实现且 97/97 通过，平台引擎缺失。
2. **4 个端点用例基线失效（生产实测证据，2026-08-07）**：
   - `/account-service/login/anonymous/web`：契约要求 formData `appCode` + 必填 `clientip` 请求头，
     用例只发 JSON body 无头 → 业务 400、信封从 `{code,msg,detail,success}` 漂移到 `{timestamp,status,msg}`；
     补齐 form+头后恢复 code=0/success=true。
   - `/account-service/ee/ads/activity/get`：契约要求必填 `Accept-Language`/`deviceId`/`X-Real-IP`，
     用例无头 → 业务 400 data 缺失；带头后恢复 200+data。
   - `/camel-service/ee/search/query`：契约要求必填 `Accept-Language`，用例无头 → 业务 400 data 缺失
     （B110-5 动态数据同类根因）；带头后恢复 200+data。
   - `/camel-service/ee/news/get`：生产全 id 业务 400（含登录态/必填头），`news/get_visible` 同 id 200 正常；
     属服务端缺陷 + 用例端点基线错误（用户端实际走 get_visible）。
3. **C111-2/C111-3 未闭环**：批量执行重跑与 UI 定时回归依赖部署后验证，本批完成。
4. **用户 2026-08-07 方向反馈**：用例生成应以「用户端+运营端需求为主、接口为辅、真实体育平台落地补充调整」，
   先理清知识中心里模块/接口/功能关联，再输出用例；当前用例缺 UI 交互（点击跳转）维度。本批登记为
   C112-1/C112-2 下一批次条件，不在本批实现（避免与断言引擎/执行验证混批）。

## 2. 成功指标

| 指标 | 基线 | 目标 |
|------|------|------|
| response_structure 引擎 | 平台不支持（102 失败） | 平台 `_run_assertions` 支持 exists/not_empty/is_object_or_array/len_lte + 动态数据豁免，单测全绿 |
| 4 端点用例校准 | 基线失效（业务 400/信封漂移/错误端点） | 按生产契约+实测请求头校准，实跑恢复成功响应 |
| 批量执行 | 68/170（task#2） | 重跑 170 条全绿（passed=170，failed=0），按端点输出明细证据 |
| C111-3 UI 定时 | job+schedule 未触发 | P0 UI job + 每日 schedule 触发 ≥1 次，运行报告 10/10 |
| C111-2 回填 | 已回填 170 | 重跑后 last_response_json/last_run_status 一致、has_response=170 |

## 3. 用户故事 + 验收标准

- As a **接口测试工程师**, I want 平台能执行生成器产出的 response_structure 断言，so that 批量执行不再因
  「未知断言类型」误失败。
  - Given 170 条含结构断言的接口用例，When 平台批量执行，Then 断言按 exists/not_empty/is_object_or_array/
    len_lte + 动态数据豁免语义求值，无未知类型失败。
- As a **体育平台承接负责人**, I want 4 个失效端点用例按真实契约校准，so that 用例基线 = 真实业务请求参数与真实响应。
  - Given login/ads/search/news 4 端点，When 补齐契约必填头/表单/正确端点并重跑，Then 生产实跑恢复成功响应，
    用例断言与实测一致。
- As a **QA**, I want P0 UI 自动化每日定时生产只读回归触发并核对报告，so that 关键路径持续受控（C111-3 闭环）。
  - Given P0 UI job 与每日 schedule，When 触发一次并轮询运行报告，Then 10/10 通过且证据落盘。

## 4. 技术考量

- **断言引擎**：`api_execution_service._run_assertions` 增加 `response_structure` 分支，语义与
  `scripts/sports/execute-interface-cases.py::_assert_structure` 对齐（已验证 97/97）：
  envelope 键缺失判失败；`data.*` 缺失在 200 信封下记为 warning（passed=True，不判失败）；
  `records[0].*` 记录字段以键存在为准；len_lte 超界判失败；`hint` 型断言为信息提示不参与判定。
  路径解析复用 `_split_path`/`_resolve_segment`，兼容 `data.records[0].id` 与 `data[0]` 写法。
  TDD：新增 `tests/test_api_execution_response_structure.py`。
- **用例校准**：新增 `scripts/sports/calibrate-interface-cases.py`，直连生产库更新 4 端点模块用例：
  login 改 formData + clientip 头；ads/search 补必填头；news/get 重指向用户可见 `news/get_visible`
  （生产 news/get 缺陷登记 B112-1）。校准基线与证据 JSON 落盘。
- **批量执行重跑**：`run-batch-execution.py` 增加 `--label`（证据目录/任务名），并输出按端点聚合的
  passed/failed 明细；重跑 170 条目标全绿。
- **UI 定时（C111-3）**：`setup-ui-schedule.py` 增加 `--label` + 触发后轮询
  `GET /ui-tests/runs/{run_id}`，把运行状态/结果写入证据 JSON，核对 10/10。
- **风险**：生产执行依赖 sportsadmin 密码/DB URL（外部凭据）；UI 定时依赖平台 Playwright 执行器在线。
  凭据缺失时登记 Deferred，不以文档代替执行证据。

## 5. 范围

**纳入**：response_structure 断言引擎（后端 + 单测）、4 端点用例校准脚本与生产校准、批量执行重跑全绿证据、
C111-2 回填核对、C111-3 UI 定时触发与报告核对、B112-1 news/get 缺陷登记、C 条件更新、C112-1/C112-2 下一批登记。

**非目标**（见头部）。

## 6. 上线计划

| 阶段 | 内容 | 出口标准 |
|------|------|---------|
| S1 | 批次工件 + 看板 + response_structure 引擎（TDD） | 单测通过 + 代码提交 |
| S2 | 4 端点校准脚本 + 生产校准 + 证据 | 校准后实跑恢复成功；证据 JSON |
| S3 | 批量执行重跑（170 条）全绿 + 回填核对 | task passed=170；按端点明细证据 |
| S4 | C111-3 UI 定时触发 + 报告核对 | run 10/10 证据 |
| S5 | QA 硬门禁 + QA 报告 + Leader + 一次总确认 | 工件齐全 + 审计 0 硬错 |

## 7. 技能使用

- `cameltv-agent-team` → 六部门流水线（本 PRD）
- `cameltv-bug-guard` → 后端断言引擎避坑（envelope 码 vs HTTP 码约定）
- `test-case-design` / `cameltv-api-test` → 接口用例校准与断言核对
- `playwright-cli` / `playwright-skill` → UI 定时回归验证
