# Batch 115 — Design Spec（Part 2 全部解决）

> **Design (🎨)** | Date: 2026-08-07 | Status: 就绪

## 0. 技术体系确认

后端：FastAPI + SQLAlchemy + APScheduler + Playwright；前端：shadcn/ui + Tailwind（minimal 入口）。
知识中心：标准 capture + RAG。

## 1. UI job 定时（B112-3）

UiTestJob 新增 `cron_expression`（可空）+ `schedule_enabled`（bool 默认 false）。
TestSchedule 新增 `job_type`（plan|ui，默认 plan）+ `job_id`（可空，job_type=ui 时必填）。
`_execute_schedule` 按 job_type 分发：plan → 原逻辑；ui → `ui_test_service.trigger_job`。
迁移：`alembic` 新增 revision（schedule job_type/job_id + ui_job cron 字段）。
前端：UI job 管理页「定时设置」：cron 输入 + 启用开关（minimal，复用 schedule 组件）。

## 2. 接口依赖链（C107-2）

TestCase 新增 `depends_on_ids`（JSON 数组：前置用例 id）。
执行链（`api_execution_service.execute_api_case` 增强）：
1. 解析 depends_on_ids → 先执行前置用例（同环境、同 confirm_prod 口径）。
2. 前置响应 `last_response_json` 注册为变量 `$prev.{case_key}.{jsonpath}`（case_key=前置用例 id）。
3. 后置请求 body/url 中 `$prev.*` 占位替换（resolve_variables 前处理）。
4. 环检测（DFS）+ 拓扑顺序；失败短路。
单测：`test_api_dependency_chain.py`（前置执行/变量注入/环检测/失败短路）。

## 3. XHR 采集工具（B10）

新增「采集任务」类型（复用 UiTestJob 表，`job_type=capture` 或独立 service）：
`xhr_capture_service.py`：playwright 只读打开页面列表，拦截 `page.on('request')`（含 method/url/headers/body）
+ `page.on('response')`（状态/body 前 250KB）→ 样本 JSON 落库/导出。
只读口径复用 B112-4（GET/HEAD + 查询型 POST）。
证据：`evidence/batch-115/xhr-capture-sample.json`。

## 4. 生成链路消费关联基座

`case_generation_service`/`api_case_generation_service` 生成入口注入：
- 知识检索（RAG query=模块名）→ 命中接口/功能清单拼接进提示词；
- 关联基座本地 JSON 兜底（RAG 不可用时读 `docs/体育平台-关联基座.json`）。
单测：断言生成提示/结果含模块对应接口路径。

## 5. Runner 加固（B114-2）

chromium launch args 增 `--disable-dev-shm-usage --no-sandbox --disable-gpu`；
spec retries=1 保留；连续 2 次平台 10/10 证据。

## 6. 设计签核

结论：通过（P0/P1 无阻断）。