# CamelTv 测试平台 v2 后端深度架构审查报告

> **审查对象**：`F:\CamelTv-batch173-review\test-platform-v2\backend\`
> **技术栈**：FastAPI + SQLAlchemy 2.0 + APScheduler + httpx（生产：Vercel 前端 + Railway 后端 + Supabase PostgreSQL）
> **审查时间**：2026-08（batch-173）
> **审查方法**：全量 import 依赖扫描（147 条 service 间引用）、路由/服务函数清单枚举、执行链路逐文件通读、模型字段与外键核对、事务/锁/权限点系统比对。所有结论均附 `文件:行号` 证据。
> **范围说明**：本报告独立于 batch-147 已有报告，未重复罗列其内容；对 batch-147 指出的问题给出更深的机制证据，并新发现多项问题。

---

## 0. 审查结论速览（TL;DR）

| 严重度 | 问题 | 位置 |
|--------|------|------|
| 🔴 P0 | **API 批量任务双 Worker 竞态 + 认领后放弃的僵尸任务 bug**：APScheduler 轮询与 api_task_worker 守护线程并行认领同一任务；`task_worker._run_api_task` 在认领后重查 `status not in ("pending")` 直接 return，任务永久卡在 running | `task_worker.py:53-62,81-82`、`api_task_worker.py:35-71,290-316`、`scheduler.py:364-376` |
| 🔴 P0 | **认领非原子（TOCTOU）**：`claim_next_task` 先 SELECT 后 UPDATE+commit，无 `FOR UPDATE`/`SKIP LOCKED`；双线程在 PostgreSQL 下可同时认领同一任务导致重复执行 | `api_task_worker.py:46-58` |
| 🔴 P0 | **计划执行单长事务**：`execute_all_cases`/`auto_execute_api_cases` 在整个计划执行期间（每条 API 用例含 HTTP 调用、每条 UI 用例起 Playwright 子进程）只开一个事务、末尾一次性 commit | `test_plan_service.py:924-1119`、`465-610` |
| 🟠 P1 | **执行记录多表冗余/双轨**：同一计划 API 执行同时写 `test_execution` 与 `api_execution_task_item` 两张表，双向 `api_task_id`/`test_execution_id` 互指；汇总统计口径分裂（`report_aggregator` 只读 task/run 表，`trace/dashboard` 读 `test_execution`） | `test_plan_service.py:506-602,1066-1079`、`report_aggregator.py:38-159` |
| 🟠 P1 | **环依赖仅靠懒加载压制**：`requirement_service ↔ test_case_service` 双向 import（函数内 lazy），`review_service → test_case_service._row_to_dict` 直接引用私有函数 | `requirement_service.py:789`、`test_case_service.py:106`、`review_service.py:140` |
| 🟠 P1 | **UI 执行三套入口并存**：`ui_runner_queue`（线程池）+ `task_worker._process_ui_runs`（APScheduler 轮询）+ `open_api.py` 裸线程调 `execute_playwright_async`；并发闸门依赖 `playwright_executor` 内 `_claim_pending_run` 兜底，但调度冗余与重复入队风险仍在 | `ui_test_service.py:334-335,340-375`、`task_worker.py:168-229`、`open_api.py:300-304` |
| 🟠 P1 | **6 套各自为政的"认领式任务队列"**：API/AI/DSH/证据包/Agent 队列/UI run，各有独立 claim 实现与状态机，无统一抽象 | 见 §3.4 |
| 🟡 P2 | **权限字符串双份维护**：seed.py 目录（`_ACTIONS`/`_MENUS`）与路由内联字符串（~344 处）不共享常量，已核对当前无漂移，但改动即引入静默不可授权的风险 | `seed.py:16-192`、各路由 `require_permission("...")` |
| 🟡 P2 | **软删除三套语义并存**：`is_deleted` 布尔（用例/域/模块）、`status=deprecated`（知识源/切片）、硬删除（需求/缺陷/计划/UI 任务等），无统一约定 | 见 §4.3 |
| 🟡 P2 | **路由层直连 ORM / 大文件聚集**：knowledge.py 68KB/1668 行直接 `select(KnowledgeEntity)`；9 个路由文件 >20KB；`DELETE /batch` 与 `POST /batch-delete` 完全重复 | `knowledge.py:675-693`、`test_case.py:267-304` |

---

## 1. 模块清单与职责

### 1.1 路由层（`backend/app/api/v1/`，36 个文件）

| 文件 | 大小 | 职责一句话 |
|------|------|-----------|
| `auth.py` | 9.6KB | 登录/注册/登出/改密/忘记密码/SSO 配置 |
| `router.py` | 2KB | v1 路由聚合（43 个 include_router） |
| `dashboard.py` | 3.3KB | 工作台统计、跨项目统计、API+UI 测试全景摘要 |
| `defect.py` | 14KB | 缺陷 CRUD、状态流转、评论、附件、外部同步（sync-push/pull） |
| `environment.py` | 4.6KB | 目标环境与变量 CRUD、变量解析 |
| `ops_releases.py` | 2.6KB | 运维发布记录只读查询 |
| `project.py` | 10.5KB | 项目 CRUD、成员、质量门禁、项目邀请 |
| `organization.py` | 5.3KB | 团队组织 CRUD、成员管理 |
| `system.py` | 10.8KB | 用户/角色/权限点/审计日志/邀请码管理 |
| `test_case.py` | 26KB | 用例 CRUD、域树/分类、评审、Xmind/Excel 导入导出、版本历史、单用例执行 |
| `report.py` | 12KB | 报告 CRUD、趋势、门禁、导出 |
| `schedule.py` | 4.8KB | 调度 CRUD、手动触发、运行记录 |
| `test_plan.py` | 20.7KB | 计划 CRUD、计划内用例、四类执行端点、triage/缺陷草稿 |
| `av_check.py` | 9KB | 音视频质量检测任务/测量/指标 |
| `ui_test.py` | 16.5KB | UI 任务 CRUD、脚本资产、运行详情/取消/产物、XHR 采集、Runner 健康 |
| `requirement.py` | 45KB | 需求文档上传/解析、AI 提取（同步+异步）、AI 生成用例（同步+异步）、API 匹配、评审、导入 |
| `trace.py` | 2.2KB | 质量追溯：覆盖率/趋势/用例追溯/需求覆盖 |
| `notify.py` | 3.4KB | 通知渠道 CRUD、测试通知 |
| `open_api.py` | 13.4KB | 外部 CI Token 鉴权、计划触发/结果回写、UI 触发、门禁检查 |
| `token.py` | 4.5KB | API Token CRUD |
| `apitest.py` | 37KB | 接口资产（服务/端点/导入）、即时执行、用例生成、批量执行任务 CRUD/取消/重试/curl/失败分析 |
| `dataset.py` | 5.8KB | 数据集 CRUD、上传/预览 |
| `integration.py` | 7KB | 外部集成配置 CRUD、连接测试、同步触发、同步日志 |
| `version_mission.py` | 7.3KB | 版本测试任务 CRUD、日志、OpenAPI/流量/UI 草稿生成、质量门禁 |
| `knowledge.py` | 68KB | 知识中心：检索/源/切片/产物审核/AI 产物导入/图谱/设计稿/技能/迭代/回归预测 |
| `agent.py` | 9KB | Agent 执行记录、手动触发、变更检测、队列管理 |
| `dsh_tasks.py` | 3.2KB | DSH 任务提交/列表/取消/健康 |
| `wiki.py` | 39KB | Wiki：导入/编译任务/页面/差异对比/外部连接/健康体检/同步 |
| `release_bundles.py` | 23KB | 发布包 CRUD、版本链、差异对比、回归范围/触发 |
| `requirement_modules.py` | 43KB | 模块树、提取/直建、用例关联、交互提取、全局导航、配置关联、附件、生产差异 |
| `interaction_coverage.py` | 2.5KB | 交互拓扑边、覆盖缺口、导入 |
| `lanhu_evidence.py` | 22KB | 蓝湖证据包：Cookie/登录/任务/页面/资产/审核/取消/重试/导入/删除 |
| `perf.py` | 7.9KB | 性能监控会话/设备/指标/报告/对比 |
| `perf_ws.py` | 9.9KB | 性能采集 WebSocket 流 |
| `playground.py` | 3KB | Playwright 编译/批量编译/执行/批量执行 |
| `template.py` | 3.4KB | 报告模板 CRUD |
| `ui_test.py` | — | 同上 |

### 1.2 服务层（`backend/app/services/`，65 个顶层文件 + 子包）

**核心业务服务**（与路由 1:1 主服务）：`test_case_service`、`test_plan_service`、`requirement_service`、`defect_service`、`report_service`、`api_execution_service`、`ui_test_service`、`schedule_service`、`environment_service`、`dataset_service`、`project_service`、`organization_service`、`auth_service`、`rbac_service`、`role_service`、`user_service`、`version_mission_service`、`av_check_service`、`perf_service`、`integration_service`、`notify_service`、`knowledge/*`（约 25 文件）、`wiki/*`（约 13 文件）、`lanhu_evidence/*`（约 13 文件）。

**执行/任务类服务**：`api_execution_service`（1464 行，HTTP 执行引擎）、`api_task_worker`（批量任务线程）、`task_worker`（APScheduler 轮询）、`ui_runner_queue`（UI 线程池）、`playwright_executor`（Playwright 子进程执行器）、`ai_tasks`（AI 任务线程）、`dsh/*`（DSH 任务线程）、`knowledge/agent_queue`（Agent 队列线程）、`lanhu_evidence/worker`+`job_runner`（证据包执行）。

**支撑服务**：`audit_service`、`elk_service`、`excel_service`、`file_parser_service`、`xmind_service`、`case_compiler_service`、`playground_service`、`triage_service`、`failure_analyzer`、`statistics_service`、`trace_service`、`dashboard_service`、`coverage_report`、`report_aggregator`、`version_service`、`version_coverage_service`、`case_generation_service`、`api_case_generation_service`、`openapi_import_service`、`requirement_source_service`、`template_service`、`menu_service`、`invite_service`、`project_invite_service`、`production_operation_guard`、`openvpn_service`、`ffmpeg_service`、`perf_collector_service`、`xhr_capture_service`、`association_baseline`、`test_case_taxonomy`、`ops_release_reader`、`sync/*`（Jira/TAPD）。

**问题观察**：服务层 65+ 文件无统一分层接口（无 Service 基类约束，`core/base_service.py` 仅提供纯函数工具）；存在一个已定义但**从未被调用**的 `soft_delete_status`（`base_service.py:107-117`，全仓 grep 无引用）——死代码。

---

## 2. 依赖关系与环依赖

### 2.1 服务间 import 全图（顶层引用，`app/services` 内）

grep 证据（`from app.services...` / `import app.services...`，共 147 条命中）：

```
auth_service ──→ project_service, rbac_service, organization_service, project_invite_service, invite_service      (auth_service.py:22-25)
project_service ──→ organization_service                                                                          (project_service.py:14)
production_operation_guard ──→ audit_service                                                                      (production_operation_guard.py:11)
api_execution_service ──→ environment_service（顶层 :19）、audit_service、dataset_service（lazy）
test_plan_service ──→ elk_service（顶层 :23）、api_execution_service / environment_service / case_compiler_service /
                      playground_service / defect_service / notify_service / report_service / triage_service（全部 lazy）
playground_service ──→ playwright_executor、ui_test_service（lazy :416-418）
ui_test_service ──→ playwright_executor、ui_runner_queue（lazy :283,334,347,438）
ui_runner_queue ──→ playwright_executor（顶层 :13）
task_worker ──→ lanhu_evidence.worker / api_task_worker / api_execution_service / playwright_executor / knowledge（lazy）
api_task_worker ──→ api_execution_service（lazy :80）、notify_service、knowledge.ingest_service
requirement_service ──→ test_case_service（lazy :789）、test_plan_service（lazy :919）、api_case_generation_service（lazy :1205）
test_case_service ──→ requirement_service（lazy :106）、version_service（lazy :258）
dashboard_service ──→ statistics_service、test_case_service（顶层 :12-13）、project_service（lazy :164）
statistics_service ──→ test_case_service（顶层 :20）
trace_service ──→ statistics_service、test_case_service（顶层 :13-14）
case_generation_service ──→ version_mission_service（顶层 :14）
review_service ──→ test_case_service._row_to_dict（lazy :140，引用私有函数）
knowledge/artifact_service ──→ test_case_service（lazy :126）
ai_service ──→ external.lanhu_provider._extract_lanhu_content（顶层 :32）、association_baseline、dsh.dsh_runner（lazy）
ai_tasks ──→ requirement_service、ai_service、coverage_report（lazy）
report_service ──→ elk_service（顶层 :17）
excel_service ──→ file_parser_service（顶层 :10）
perf_service ──→ perf_collector_service（顶层 :23）
av_check_service ──→ ffmpeg_service、notify_service（lazy）
integration_service ──→ sync.engine（lazy :121）
defect_service ──→ knowledge.knowledge_cleanup（lazy :239）
lanhu_evidence/import_service ──→ requirement_service、knowledge、wiki（顶层 :20-22）
wiki/* ──→ knowledge/*（大量顶层引用，如 contract_extractor.py:15 引用 agent_orchestrator._call_llm_sync）
```

### 2.2 循环依赖（a 项结论）

**确认的环：`requirement_service ⇄ test_case_service`**（设计级环，运行时靠函数内 lazy import 拆解）：

- `test_case_service.py:106` → `from app.services import requirement_service`（在 `validate_source_doc` 函数体内）
- `requirement_service.py:789` → `from app.services import test_case_service`（注释自认："懒加载：避免 requirement_service ↔ test_case_service 环依赖（Batch 155 / P2-12）"）

**分析**：模块加载期不会失败（双向均 lazy），因此不是 import-time 崩溃，但这是**设计级环依赖**：`requirement_service.import_cases`（函数 `sync_imported_cases`，789 行起）依赖 `test_case_service.create_case`，而 `test_case_service.validate_source_doc`（106 行）依赖 `requirement_service.get_requirement`。任一方向的函数签名变更都会穿透到对方，重构/单测时必须同时维护两处，且这是后续"按域拆分"的最硬障碍。

**未形成环但值得注意**：`test_case_service` 是全局被依赖中心（`statistics`/`dashboard`/`trace`/`review`/`artifact`/`requirement` 共 6 个服务引用它，其中 4 个是顶层引用），任何对 `test_case_service` 的改动波及面最大。

### 2.3 单向过深依赖链（b 项结论）

**链 1（计划执行 → UI 编译 → UI 执行，4 层 + 2 个同层调用）**：
`test_plan_service` → `playground_service`（:625,721）→ `ui_test_service`（playground_service.py:418）→ `playwright_executor`（ui_test_service.py:347）；同时 `test_plan_service` 又直接 → `case_compiler_service`（:616）与 `playwright_executor`（经 `_execute_ui_case_sync`，:715）→ `playwright_executor`。同一"把用例编译成 Playwright spec 再执行"的能力被 4 个服务各自接线，LLM 编译与规则回退逻辑在 `case_compiler_service` 与 `playground_service.compile_spec` 中重复实现（`_compile_ui_case` 于 test_plan_service.py:613-628 先 LLM 后规则，playground_service.py:176-190 也做同样双路径）。

**链 2（AI 任务 → 需求 → 用例）**：`ai_tasks` → `requirement_service` → `test_case_service` → （反向）`requirement_service`。链长 3 且闭环，任何一层改动都会触发环。

**链 3（外部同步）**：`integration_service` → `sync.engine` → `sync.jira/tapd`（→ `defect`/`IntegrationConfig` 模型）→ 深度 3，尚可，但 `defect_service` → `knowledge.knowledge_cleanup`（:239）把业务删除与知识清理硬耦合。

### 2.4 跨服务直接引用私有函数/内部符号（c 项结论，应走依赖注入/公共 API）

| 引用方 | 被引用符号 | 位置 | 问题 |
|--------|-----------|------|------|
| `review_service.py:140` | `test_case_service._row_to_dict`（**私有**，test_case_service.py:417） | `from app.services.test_case_service import _row_to_dict` | 直接 import 私有序列化函数，绕过公共 `get_case`；`_row_to_dict` 签名/字段变更会无声破坏评审模块 |
| `ui_test_service.py:283,438` | `playwright_executor._check_playwright_installed` / `_list_available_specs`（**私有**） | 函数内 import | 两个下划线私有符号被跨模块使用 |
| `ai_service.py:32` | `external.lanhu_provider._extract_lanhu_content`（**私有**） | 顶层 import，注释自认"委托调用" | 私有 async 函数被 1308/1093 行调用，改名即断 |
| `wiki/contract_extractor.py:15`、`wiki/ingest_service.py:18` | `knowledge.agent_orchestrator._call_llm_sync`（**私有**） | 顶层 import | LLM 调用能力被 wiki 子包直接借用私有入口 |
| `schedule_service.py:15,363` | `core.scheduler._execute_schedule`（**私有**） | 顶层 + 函数内 import | 路由手动触发复用调度内部回调，`_execute_schedule` 承担"建 run + 执行 + 通知"三职责，被服务层当公共 API 用 |
| `av_check_service.py:314` | `ffmpeg_service._check_ffmpeg_installed`（**私有**） | 函数内 import | 同上模式 |

**模式总结**：服务层之间**没有依赖注入容器或服务定位器**，全部是模块级函数 + 直接 import；私有符号（`_`/`__` 前缀）被跨模块使用共 8 处，说明"公共 API 边界"从未被严格执行——这比环依赖更普遍，是 `requirement_service ⇄ test_case_service` 环能长期存在的原因（大家习惯了 lazy import + 直接调函数）。

---

## 3. 执行引擎双轨/多轨

### 3.1 执行记录表全景（4 张"任务/执行"主表 + 2 张快照表）

| 表 | 模型 | 用途 | 状态值 |
|----|------|------|--------|
| `test_execution` | `test_plan.py:68` | 计划内单条用例执行记录（manual/api/ui 统一落账） | pending/pass/fail/skip/block |
| `api_execution_task` + `api_execution_task_item` | `api_asset.py:68,96` | 接口批量执行任务 + 明细快照 | pending/running/success/failed/cancelled；item: pending/passed/failed/skipped |
| `ui_test_job` + `ui_test_run` | `ui_test.py:13,41` | UI 任务 + 运行记录 | job: idle/running/done/fail；run: pending/running/done/fail/cancelled |
| `test_schedule` + `test_schedule_run` | `test_schedule.py:14,44` | 定时调度 + 调度运行 | running/completed/failed |

**双轨确认（batch-147 所指的 test_execution vs api_execution_task 双写）**：计划内 API 用例执行时，**同一条用例同时写两张表**：
- `test_plan_service.auto_execute_api_cases`：每条 API 用例 `db.add(TestExecution)`（:521-533）+ `_ensure_plan_api_task`（:536-543）创建 `api_execution_task`（trigger_type=plan）+ `_register_plan_api_snapshot`（:544）创建 `api_execution_task_item`；
- `execute_all_cases` 同样双写（:1046-1075），并双向互指：`TestExecution.api_task_id`（test_plan.py:85）+ `ApiExecutionTaskItem.test_execution_id`（api_asset.py:109）。

**状态机不一致**：`test_execution.status` 是 `pass/fail/skip`，而 `api_execution_task_item.status` 是 `passed/failed/skipped`（过去式）；`ui_test_run.status` 是 `done/fail`，`test_schedule_run` 是 `completed/failed`。同一执行事实在 4 张表中 4 套取值，前端/聚合层必须做映射（如 `ui_test_service.writeback_case_result` :388 的 status_map）。

### 3.2 执行驱动机制全景（至少 9 套并发调度入口）

| # | 机制 | 载体 | 启动方式 | 处理内容 |
|---|------|------|----------|----------|
| 1 | APScheduler 定时 | `core/scheduler.py:13` BackgroundScheduler | main.py:112 启动 | cron 调度执行、**task_worker_poll（每 5s）**、stale 回收（5min）、保鲜退化、图谱演化 |
| 2 | 任务轮询线程 | `task_worker.py:26 poll_and_execute` | 由 #1 每 5s 调用 | **API 批量任务** + **UI pending run** + 蓝湖证据包 |
| 3 | API 任务守护线程 | `api_task_worker.py:290 _processor_loop`（2s 轮询） | apitest.py:761/902 懒启动 `ensure_processor_running` | **API 批量任务**（与 #2 重叠！） |
| 4 | AI 任务守护线程 | `ai_tasks.py:203 _worker_loop` | main.py:146-148 `ensure_ai_worker` | AiTask 提取/生成 |
| 5 | DSH 任务守护线程 | `dsh/dsh_task_service.py:168 _worker_loop` | dsh_tasks.py 提交时 `ensure_worker_running` | DshTask |
| 6 | Agent 队列守护线程 | `knowledge/agent_queue.py:314 _queue_loop` | agent.py:146 `ensure_processor_running` | AgentQueueItem |
| 7 | UI 线程池 | `ui_runner_queue.py:22` ThreadPoolExecutor(max=2) | ui_test.py:318 懒初始化 + 重启恢复 | UI run（enqueue_run） |
| 8 | 裸线程 | `open_api.py:300-304` `threading.Thread(target=execute_playwright_async)`；`schedule_service.py:400-408` trigger_schedule 裸线程 | 路由内直接起线程 | UI run（CI 触发）、调度执行 |
| 9 | FastAPI BackgroundTasks | 各路由 `background_tasks.add_task` | 请求返回后 | 通知、失败自动链、异步计划执行（run_async_execute_all）、知识向量化等 |

### 3.3 双 Worker 竞态与僵尸任务（本次审查最重要的新发现）

**竞态链路**（API 批量任务）：

```
创建任务（apitest.py:761-762 ensure_processor_running + kick）
  ├─ 线程 A：api_task_worker._processor_loop（每 2s）─→ claim_next_task
  └─ 线程 B：APScheduler → task_worker.poll_and_execute（每 5s）─→ _process_api_tasks ─→ claim_next_task（task_worker.py:53-57）
```

**Bug 1 — 认领后放弃（僵尸任务）**：`claim_next_task`（api_task_worker.py:46-58）把任务 `status=pending → running` 并 `db.commit()`；随后 `task_worker._run_api_task`（task_worker.py:71-144）在新线程里**重查** `task.status not in ("pending",)`（:82）——此时 status 已是 running，条件成立，**函数直接 return**，任务永远停留在 running，无任何 stale 回收覆盖 `api_execution_task`（scheduler.py 的 `reap_stale_schedule_runs` 只回收 `test_schedule_run`）。Batch 155 把"认领"从 `_run_api_task` 上移到 `_process_api_tasks` 时漏改了 :82 的守卫，属不完整合并。

**Bug 2 — 认领非原子（TOCTOU）**：`claim_next_task` 是 `SELECT ... status=='pending'` → 内存改状态 → `UPDATE` + `commit`（api_task_worker.py:46-58），**没有 `FOR UPDATE`/`SKIP LOCKED`**（注释自认"SQLite 不支持 SKIP LOCKED，依赖单 worker"——但实际是双 worker）。在 PostgreSQL（生产）下，两个线程可同时读到同一 pending 任务并都成功 UPDATE，导致**同任务被两个 worker 重复执行**；SQLite 下靠写锁串行化侥幸规避。

**对比**：`core/scheduler.py:31-35` 的调度认领用了 `select(...).with_for_update()`（Batch 163），是正确范式；`requirement_modules.py:363`、`requirement_service.py:769` 也用了 `with_for_update`——只有 API 任务认领漏了。

### 3.4 六套"认领式队列"各自为政

`api_task_worker.claim_next_task`（API 任务）、`ai_tasks.claim_next_task`（AI 任务）、`dsh/dsh_task_service.claim_next_task`（DSH）、`lanhu_evidence/worker.claim_next_job`（证据包，带 `recover_stale_jobs`）、`knowledge/agent_queue`（带 SQLite busy 处理 `QueueWriteBusy`）、`playwright_executor._claim_pending_run`（UI run）。六者状态值、认领方式（有些 UPDATE rowcount=1、有些 SELECT-then-update）、恢复机制（只有证据包和调度 run 有 stale 回收）各不相同，是"执行引擎多轨"的根源。

### 3.5 状态机一致性结论

**不一致**。同一批用例：
- 手动批量执行 → `api_execution_task`（success/failed/cancelled）+ 回写 `TestCase.last_run_status`（api_task_worker.py:152）；
- 计划自动执行 → `test_execution`（pass/fail/skip）+ `api_execution_task_item`（passed/failed/skipped）+ `TestPlanCase.last_status` + `TestCase.last_run_status`（部分路径）；
- UI 执行 → `ui_test_run`（done/fail）+ `UiTestJob.last_result` + `TestCase.last_run_status`（writeback_case_result）。

`TestCase.last_run_status` 的取值来源有 3 处（api_task_worker.py:152、ui_test_service.py:388、test_plan 各路径），写入值 `success/fail/skipped` vs `pass/fail/skip` 混用（:388 status_map 明确做了 `done→pass` 映射，但 api_task_worker:152 写的是 item 的 `passed/failed`），**同一字段写入口径不统一**。

---

## 4. 模型层设计

### 4.1 模型清单（`backend/app/models/`，46 个文件，约 55 张表）

用户组织：`user`、`organization`(+`organization_member`)、`project`(+`project_member`)、`project_invite`、`invite_code`、`rbac`(role/permission/user_role/role_permission)。
核心测试：`test_case`(+`test_case_category` domain/module、`test_case_review`、`test_case_version`)、`test_plan`(+`test_plan_case`、`test_execution`)、`test_report`、`report_template`、`quality_gate`、`test_schedule`(+`test_schedule_run`)、`api_asset`(service/endpoint/import_batch/execution_task/item)、`ui_test`(job/run/script)、`defect`(+transition/comment/attachment)、`dataset`、`environment`(+`environment_variable`)、`av_check`、`perf`、`interaction_edge`。
需求/发布：`requirement`、`requirement_review`、`requirement_module`(+`module_admin_link`)、`release_bundle`、`version_mission`(+`agent_work_log`、`generated_artifact`)。
AI/知识：`ai_task`、`dsh_task`、`knowledge`(source/chunk/vector/entity/relation/artifact/agent_run/agent_queue_item/iteration/snapshot)、`wiki`(raw_source/page/link/ingest_job/diff_task/diff_item/review_item/review_contradiction/external_connection/lint_report/lint_issue)、`lanhu_evidence`(job/page/asset/ocr_block)。
系统：`audit`、`notification`(channel/log)、`integration`、`sync_log`、`api_token`。

### 4.2 冗余字段 / 反范式缓存（未同步风险）

| 缓存字段 | 主数据源 | 写入口 | 风险 |
|----------|----------|--------|------|
| `TestCase.last_run_status` / `last_response_json`（test_case.py:64-65） | test_execution / api_task_item / ui_run | api_task_worker.py:152、ui_test_service.py:389、test_plan 各路径 | 3 处写入、口径不一（见 §3.5） |
| `TestPlanCase.last_status` / `last_executed_at`（test_plan.py:55-56） | test_execution | test_plan_service.py:584-586 等 | 计划外执行不更新 |
| `UiTestJob.last_result`（ui_test.py:27） | ui_test_run.result | ui_test_service.py:309,326 | 与 run.result 双份 JSON |
| `ApiExecutionTask.passed/failed/skipped`（api_asset.py:80-82） | api_execution_task_item | api_task_worker.py:176-178 / test_plan_service.py:1113-1117 | 两份 worker 逻辑各自汇总，可能不一致 |
| `TestSchedule.last_run`（test_schedule.py:29） | test_schedule_run | scheduler.py:150 | 仅 cron 触发路径更新 |

**状态/结果语义三套并存**：`result` JSON 文本列（`ui_test_run.result`、`test_schedule_run.result`、`UiTestJob.last_result`）、结构化列（`test_execution.status_code/error_type/error_message`、`api_execution_task_item.request_snapshot/response_snapshot/assertion_results`）、聚合计数（`ApiExecutionTask.passed/failed`）。同一"执行结果"概念在 schema 层无统一形状，`report_aggregator` 只能各自解析（`_ui_summary` 里 `json.loads(r.result)`）。

### 4.3 外键孤岛（无 FK 或弱关联的表）

- **`ApiExecutionTaskItem.case_id`**（api_asset.py:102）无 FK（用例可软删，可接受，但 task 删除时 item 无级联，`apitest.delete_task` 需手删）；
- **`TestExecution.plan_case_id`** 有 FK（test_plan.py:72）但 `TestPlanCase.case_id`（:53）无 FK——用例软删后计划内成孤儿；
- **`TestCase.source_doc_id`**（test_case.py:75）无 FK（软删需求后历史用例失去来源锚点）；
- **`RequirementDocument.linked_swagger_id` / `linked_api_endpoint_ids`**（requirement.py:51-52）无 FK、JSON 数组存 id；
- **`TestSchedule.job_id`**（test_schedule.py:24）"job_type=ui 时指向 ui_test_job.id"——**多态外键**，无 FK 约束、无 UNION 校验；
- **`TestScheduleRun`** 只有 schedule FK，无 plan/job 引用；
- **完全无外键的表**：`Dataset`、`AiTask`、`DshTask`、`TestReport`（plan_id 有 FK，但 template_id 有）、`KnowledgeEntity/Relation`（from/to_entity_id 无 FK，business_ref 无 FK）、`WikiLink` 等——知识图谱/嵌入类表基本是软引用。

**外键孤岛结论**：核心业务链（test_plan→test_plan_case→test_execution、defect→*、av_check→*、perf→*）有 FK；但跨域关联（用例↔需求、用例↔接口资产、调度↔UI任务、知识↔业务）几乎全部是无约束整数列或 JSON 数组，删除时无数据库级保护，全凭服务层手写级联（如 defect_service.delete_defect:244 的 `_cascade_knowledge`）。

### 4.4 软删除一致性

**三套机制并存**：

| 机制 | 表 | 证据 |
|------|----|------|
| `is_deleted` 布尔（**软删**） | `test_case`(:39)、`test_case_domain`(:20)、`test_case_module`(:39) | test_case_service.py:279,292 置 True |
| `status=deprecated`（**软删**） | `knowledge_source`(:40)、`knowledge_chunk`(:66) | source_service.py:247,251 |
| **硬删除** `db.delete` | requirement_document(requirement_service.py:577)、defect(defect_service.py:248)、test_plan(test_plan_service.py:137)、ui_test_job/run(ui_test_service.py:198,528)、dataset、environment、integration、schedule、report、template、role、user 等 | grep `db.delete(` 36 处 |

**影响**：用例/域/模块删了可恢复（is_deleted 反转，test_case_service.py:478-479），但需求/缺陷/计划/UI 任务删了不可恢复；查询层对 `TestCase` 的过滤散落在 20+ 处 `is_deleted.is_(False)` / `== False` / `is False` 三种写法（grep 见 test_case_service.py:136,137 用 `== False`，:303,330 用 `.is_(False)`，knowledge/test_case_linker.py:317 用 `== False  # noqa: E712`），**风格不一且易漏**（如 dashboard_service.py:86 与 statistics_service.py:29 各自维护过滤）。

---

## 5. API 设计问题

### 5.1 明显重复/重叠的端点

| 重复组 | 证据 | 说明 |
|--------|------|------|
| **批量删除用例** | `DELETE /api/v1/test-cases/batch`（test_case.py:267）+ `POST /api/v1/test-cases/batch-delete`（:287） | 函数体逐行相同（同为 `transaction(db)` 循环 `delete_case`），注释承认"POST 入口避免兼容性问题"——应收敛为一个 |
| **计划批量执行 ×3** | `POST /{plan_id}/execute-all`（test_plan.py:309）+ `POST /{plan_id}/auto-execute`（:370，仅 API 子集）+ `POST /{plan_id}/batch-execute`（:513） | 三端点都执行"计划内用例"，语义重叠；execute-all 含 auto_ui 分支已覆盖 auto-execute 的 API 子集 |
| **报告门禁 ×2** | `GET /reports/{report_id}/gate`（report.py:130）+ `GET /reports/{report_id}/gate/check`（:144） | 同一门禁评估两个端点，gate/check 走 `report_service`，gate 走路由内联逻辑 |
| **接口执行 ×2** | `POST /apitest/api-execute`（apitest.py:116）+ `POST /test-cases/{case_id}/execute`（test_case.py:349） | 前者即时调试、后者执行已保存用例，底层都调 `api_execution_service`，前端可绕过其一 |
| **AI 提取/生成 ×2** | `requirement.py` extract(:268)/generate(:577) 与 extract-async(:1100)/generate-async(:1116) | 同步 async 版 + 异步任务版并存（历史兼容），同一能力双 API |

### 5.2 过大路由文件（>20KB，违反单一职责）

| 文件 | 大小 | 端点/函数 | 主要问题 |
|------|------|-----------|----------|
| `knowledge.py` | 68KB/1668 行 | ~40 端点 | 检索/源/产物/图谱/设计稿/技能/迭代/回归预测 8 个域混在一个文件；**路由内直连 ORM**：`select(KnowledgeEntity)...`（:675-693）、`select(TestCase)`（:688-691） |
| `requirement.py` | 45KB/1148 行 | ~20 端点 | 上传/提取/生成/API匹配/评审/导入 6 域 |
| `requirement_modules.py` | 43KB/1149 行 | ~20 端点 | 模块树/提取/交互/导航/配置/附件/差异 7 域，:363 路由内 `with_for_update()` 事务 |
| `wiki.py` | 39KB/984 行 | ~30 端点 | 导入/编译/页面/差异/外部连接/体检/同步 7 域 |
| `apitest.py` | 37KB/977 行 | ~20 端点 | 资产/导入/生成/任务 4 域 |
| `test_case.py` | 26.6KB/730 行 | ~20 端点 | CRUD/域树/评审/导入导出/版本 5 域 |
| `release_bundles.py` | 23KB/592 行 | ~12 端点 | 发布包/差异/回归 3 域 |
| `lanhu_evidence.py` | 22KB/558 行 | ~15 端点 | 任务/页面/审核/资产 4 域 |
| `test_plan.py` | 20.7KB/587 行 | ~17 端点 | CRUD/执行/triage/缺陷草稿 4 域 |

### 5.3 同步长任务端点（AI 生成/执行类）async 覆盖情况

- **需求提取/生成**：`extract_features`（:268）、`generate_test_cases`（:577）为 `async def`；异步任务版 `extract-async`（:1100）、`generate-async`（:1116）走 `ai_tasks` 后台线程 + `GET /ai-task/{task_id}` 轮询（:1132）——**覆盖完整**。
- **接口批量生成**：`apitest.py` 的 `import/confirm`（:356）、`cases/generate`（:552）、`cases/batch-generate`（:604）是**同步 def + BackgroundTasks**（:381,593,644 挂后台），HTTP 仍同步等待生成主流程，大 OpenAPI 或大批量时仍会超网关。
- **计划执行**：`execute-all` 默认**同步阻塞**（test_plan.py:337），仅 `async_mode=true` 才后台（:322-334）；`auto-execute`、`batch-execute` 无 async 分支——batch-169 注释自认"避免多 UI 用例超过网关 300s"。
- **知识图谱提取/演化/回归预测**：`knowledge.py` `graph/extract`（:623）、`graph/evolve`（:917）、`auto-build`（:935）、`predict/regression-scope`（:1652）全部同步 def，内部调 `extract_and_build_graph_in_new_session`（:643）等**同步函数名却以 `_in_new_session` 后缀伪装异步**，实际阻塞请求线程直到 LLM/嵌入完成。
- **UI/发布差异**：`release_bundles.py diff_bundle`（:307）、`confirm_diff`（:369）为 async；`wiki.py` 差异任务走任务表轮询——覆盖较好。

**结论**：AI 需求链路有 async 双轨，但**知识图谱、计划执行（默认）、接口批量生成、回归预测**仍是同步长任务，且 `_in_new_session` 命名误导（是"新 DB session"而非"后台执行"）。

### 5.4 权限点一致性

- **集中定义**：seed.py `_MENUS`（:16-55）+ `_ACTIONS`（:58-192）是唯一权威目录，启动时幂等写入 `permission` 表。
- **路由使用**：~344 处 `require_permission("...")` 内联字符串，**与 seed 目录完全独立、无共享常量模块**。
- **本次核对结果**：路由用到的 96 个权限码 100% 存在于 seed 目录（无缺失授权）；seed 中 12 个码未在 `require_permission` 出现（`apitest:execute_prod`/`uitest:trigger_prod`/`integration:sync_prod`/`project:create` 等走路由内 `in current.permissions` 手检，如 apitest.py:717；`agent:list` 已弃用保留）。
- **风险点**：字符串双份维护，改名/新增码若只改一边，会出现"路由引用一个 seed 从未创建的权限码"→ 任何人 `has_permission` 恒为 False，**权限静默失效**（本次核对未发现现网漂移，但无 CI 校验，属定时炸弹）；`defect.py:368,382` 的 sync 端点直接用 `integration:sync` 权限（缺陷域借用集成域权限码），权限语义跨域。

---

## 6. 事务与并发

### 6.1 事务边界盘点

- **显式事务工具**：`core/base_service.py:126 transaction(db)` contextmanager（commit-on-success / rollback-on-exception），仅 test_case.py 批量端点（:250,275,295,574,660）使用；全仓 **无** `with db.begin()` 用法（grep 0 命中）。
- **提交纪律混乱**：服务函数对"谁负责 commit"无统一约定——
  - 自 commit：`test_case_service.update_case`(:264)、`create_case`(commit=True 默认,:239-240)、`batch_delete`(:293)、`defect_service` 多数函数、`dataset_service.create_dataset` 等；
  - 只 flush 交调用方：`artifact_service.import_to_test_case`（:166,172 flush，但 :168 调用的 `create_case` **默认 commit=True**——注释"create_case 只 db.flush()"与实际行为矛盾，`review_status=imported` 的中间态会被提前提交，破坏"未审核不得进正式库"的原子性声明）；
  - 混合：`execute_all_cases` 末尾单次 commit（:1119），内部 `_ensure_plan_api_task` 等函数却各自 flush。

### 6.2 长事务风险点（🔴 高）

1. **`test_plan_service.execute_all_cases`**（:924-1119）：整个计划所有用例在一个事务中，`db.commit()` 仅在 :1119。每 API 用例同步 httpx 调用（`DEFAULT_TIMEOUT=30s`，api_execution_service.py:25），每 UI 用例起 Playwright 子进程（`DEFAULT_TIMEOUT=300s`，playwright_executor.py:27）并 join 等待（:297-313）。数百条用例 → **单事务挂数分钟**，期间锁住 `test_plan_case`/`test_execution` 相关行，阻塞同一计划的并发查询/更新；该函数既被请求线程调用（test_plan.py:337）也被 APScheduler 线程调用（scheduler.py:127）——调度线程阻塞时，其他 cron 触发与 task_worker_poll 全部排队。
2. **`auto_execute_api_cases`**（:465-610）：同样单事务（:602 commit），N 条 API 用例全量 HTTP 后统一提交；若中途异常，`except` 分支（:551-581）继续追加失败行，最终仍 commit——**部分成功被强制落库**，与"事务原子性"预期相反。
3. **`requirement_service` 批量导入**（:770-850 附近，`sync_imported_cases` 循环 `create_case`）：`create_case` 默认逐条 commit（:239-240），导入几百条用例 = 几百个小事务（无原子性但可接受）；与第 2 点形成"同域不同事务策略"对照。
4. **`knowledge/entity_service.extract_and_build_graph_in_new_session`**（:362）：`SessionLocal()` 新会话 + LLM 调用（`ai_timeout_seconds=180`，config.py:139）期间持有写事务。

### 6.3 超时与连接池

- **无 `statement_timeout`**：全仓 grep `statement_timeout` 0 命中；PostgreSQL 分支仅配 `pool_pre_ping`、`pool_size=10`、`max_overflow`、`pool_recycle=3600`（db.py:21-30），**未设 connect/statement/transaction 超时**——长事务失控时只能靠网关 300s 兜底。
- **SQLite 分支**：`busy_timeout=30000` + `synchronous=NORMAL` + WAL（db.py:35-45），对并发写做了较好缓解（证据包 worker 的 `QueueWriteBusy` 处理即为此）。

### 6.4 互斥锁/认领实现

| 位置 | 机制 | 安全性 |
|------|------|--------|
| `scheduler.py:34` | `select(...).with_for_update()` 认领调度 run | ✅ 行锁原子（PG）；SQLite 退化 |
| `requirement_service.py:769`、`requirement_modules.py:363` | `with_for_update()` | ✅ |
| `api_task_worker.py:46-58` | SELECT→UPDATE→commit，**无锁** | ❌ TOCTOU，PG 双 worker 重复执行（§3.3 Bug 2） |
| `playwright_executor.py:35-53` | `UPDATE ... WHERE status='pending'` + `rowcount==1` | ✅ 原子（但依赖行锁粒度，SQLite 可接受） |
| `knowledge/agent_queue.py:54` | 捕获 `OperationalError` 判 `_is_sqlite_locked` 重试 | ⚠️ SQLite 专用，PG 下无意义 |
| `ai_tasks.py:81`、`dsh/dsh_task_service.py:107` | SELECT→UPDATE→commit | ❌ 同 TOCTOU（单线程场景暂安全） |
| `lanhu_evidence/worker.py:48` + `recover_stale_jobs`(:22) | SELECT→UPDATE + stale 回收 | ⚠️ 有回收兜底，竞态后果轻 |

---

## 7. 架构级建议（按优先级排序）

1. **【P0】统一任务队列抽象，替换 9 套调度入口（§3.2/§3.4）**。以 `ai_tasks`/`api_task_worker`/`agent_queue` 三者的共性（claim/execute/finish + 状态表）收敛为单一 `TaskQueue` 基类（DB 表 `status`+`locked_by`+`heartbeat_at`+`retry`），APScheduler 只保留一个 2s 轮询 job 分发到各 handler；**删除 `task_worker._process_api_tasks` 与 `api_task_worker._processor_loop` 之一**（建议保留 `api_task_worker` 并让其唯一负责 API 任务，`task_worker` 改回只做 UI+证据包）。具体文件：`task_worker.py`、`api_task_worker.py`、`core/scheduler.py:364-376`。

2. **【P0】修复认领竞态与僵尸任务（§3.3）**。a) `api_task_worker.claim_next_task` 改用 `UPDATE api_execution_task SET status='running', locked_by=:wid WHERE id=(SELECT id ... WHERE status='pending' ORDER BY id LIMIT 1 FOR UPDATE SKIP LOCKED) RETURNING id`（PG 方言分支）或 SQLite 下退化为单线程 + `BEGIN IMMEDIATE`；b) 删除 `task_worker.py:82` 的 `status not in ("pending",)` 守卫或改为 `in ("running",)` 且校验 `locked_by`；c) 为 `api_execution_task` 增加 stale 回收（仿 `core/scheduler.py:292 reap_stale_schedule_runs`，心跳超时置 failed）。

3. **【P0】计划执行拆分为"逐用例小事务 + 任务化"（§6.2）**。`execute_all_cases`/`auto_execute_api_cases` 改为每条用例独立 `SessionLocal()` 短事务（result 落 `test_execution` 后立即 commit），或整体改走 `api_execution_task` 队列（trigger_type=plan 已有雏形，test_plan_service.py:856-890），请求线程只创建任务并返回；同时把 `execute_all_cases` 从 APScheduler 线程（scheduler.py:127）挪到独立执行线程，避免阻塞 cron。

4. **【P1】确定唯一"执行记录"事实源，消除双轨（§3.1/§4.2）**。选择 `api_execution_task_item`/`ui_test_run` 作为机器可读执行明细的事实源、`test_execution` 收敛为计划维度的轻量索引（或反之，但必须单一），废弃 `ApiExecutionTaskItem.test_execution_id`/`TestExecution.api_task_id` 双向互指中非必要的一方；统一四表状态值（建议 `pending/running/passed/failed/skipped/cancelled`），`report_aggregator`/`trace`/`dashboard` 全部基于同一聚合视图（可建 SQL VIEW 或 `statistics_service` 为唯一入口——trace_service.py:24 已有"统一口径"注释，扩大该口径到 report_aggregator）。

5. **【P1】服务层引入依赖边界与公共 API 治理（§2.4）**。a) 把 8 处跨服务私有符号引用（`_row_to_dict`、`_check_playwright_installed`、`_extract_lanhu_content`、`_call_llm_sync`、`_execute_schedule` 等）提升为公共函数（去掉下划线 + 加入模块 `__all__`）；b) 用 `requirements.txt` 级 lint 规则（如 ruff `TID252`/自定义 F401 检查）禁止服务间 `import` 私有符号；c) 对 `requirement_service ⇄ test_case_service` 环，将 `validate_source_doc`（test_case_service.py:106）下沉为独立 `source_link_validator` 或改由路由层组装，彻底断环而非靠 lazy import 压制。

6. **【P1】路由文件按域拆分 + 路由层禁止 ORM（§5.2）**。`knowledge.py`(68KB)、`requirement.py`(45KB)、`requirement_modules.py`(43KB)、`wiki.py`(39KB)、`apitest.py`(37KB) 各拆 2-3 个 `APIRouter(prefix=...)` 文件（如 `knowledge_sources.py`/`knowledge_graph.py`/`knowledge_artifacts.py`），并禁止路由内出现 `select(...)`/模型 import（`knowledge.py:675-693` 直查 ORM 为反例），统一收敛到 services。

7. **【P1】权限码改为单点常量 + CI 校验（§5.4）**。新建 `app/core/permissions.py` 导出全部权限码常量，`seed.py` 与各路由 `require_permission(PERM.CASE_LIST)` 引用同一常量；CI 增加一个 pytest 用例：比对路由引用的权限码集合与 seed 目录集合，漂移即红（本次核对 96 个码无漂移，但应固化为回归）。

8. **【P2】模型层规范化（§4.2/§4.3/§4.4）**。a) 全库统一软删除语义：要么全 `is_deleted`（建议，与 TestCase 一致），要么全 `status`，废弃"需求硬删 + 用例软删 + 知识 deprecated"三分天下；b) 为跨域引用补约束：`TestCase.source_doc_id`、`ApiExecutionTaskItem.case_id`、`TestSchedule.job_id`（拆为 `job_type`+`job_id` 两列或加 CHECK），删除时由 DB 级联或显式清理，替代服务层手写级联（defect_service.py:244）；c) 统一 `TestCase.is_deleted` 过滤写法（`is_(False)` 唯一化，grep 出 `== False` 3 处并修正）。

9. **【P2】长事务与超时治理（§6.2/§6.3）**。a) PostgreSQL 连接串加 `statement_timeout=30000`（或 `connect_args`），并为 `execute_api_case` 的 httpx 调用加每用例超时（已有 `DEFAULT_TIMEOUT=30`，但计划循环无整体超时上限）；b) `execute_all_cases` 循环内按用例/批次 commit（与建议 3 合并）；c) 移除或修正 `base_service.py:107 soft_delete_status` 死代码；d) 统一 `_in_new_session` 系列函数命名（`*_in_new_session` 是"新 DB session"，与异步无关，改名 `*_in_new_session_sync` 或在 docstring 明确）。

10. **【P2】删除重复端点与死路径（§5.1）**。a) 收敛 `DELETE /test-cases/batch` 与 `POST /test-cases/batch-delete`（保留一个，另一个 410 或重定向）；b) 收敛 `test_plan` 三个执行端点为 `execute-all`（含 async_mode 与 auto-ui 开关），`auto-execute`/`batch-execute` 移入同一端点参数或标记 deprecated；c) `ui_test_service.execute_playwright_async`（:340）与 `open_api.py:300-304` 裸线程路径统一走 `ui_runner_queue.enqueue_run`；d) 收敛 report 两个 gate 端点。

---

## 附录 A：证据索引（关键 grep 结果）

```
# 环依赖
requirement_service.py:789   from app.services import test_case_service  # 懒加载：避免环依赖
test_case_service.py:106     from app.services import requirement_service
# 私有符号跨模块
review_service.py:140        from app.services.test_case_service import _row_to_dict
ui_test_service.py:283,438   playwright_executor._check_playwright_installed / _list_available_specs
ai_service.py:32             from app.services.external.lanhu_provider import _extract_lanhu_content
wiki/contract_extractor.py:15  from app.services.knowledge.agent_orchestrator import _call_llm_sync
schedule_service.py:15,363   from app.core.scheduler import _execute_schedule
# 双 worker
scheduler.py:364-376         注册 task_worker_poll（每 5s）
task_worker.py:53,57,62      共用 claim_next_task 认领后转 _run_api_task
task_worker.py:81-82         if not task or task.status not in ("pending",): return  ← 僵尸任务
api_task_worker.py:46-58     SELECT→UPDATE→commit 无锁认领
api_task_worker.py:290-316   _processor_loop 每 2s
# 双轨
test_plan_service.py:521-544 / 1046-1079  TestExecution + ApiExecutionTaskItem 双写
report_aggregator.py:40,94   只读 api_execution_task / ui_test_run
# 长事务
test_plan_service.py:924-1119  execute_all_cases 单事务（:1119 commit）
test_plan_service.py:465-610   auto_execute_api_cases 单事务（:602 commit）
# 重复端点
test_case.py:267 vs :287       DELETE /batch vs POST /batch-delete
test_plan.py:309 vs :370 vs :513  execute-all / auto-execute / batch-execute
# 权限
seed.py:16-192                _MENUS + _ACTIONS 权威目录；路由 96 码全部在目录内
```

## 附录 B：与 batch-147 报告的关系

- **batch-147 已指出**：requirement_service↔test_case_service 环、artifact_service→test_case_service、双 Worker 竞态、执行双轨。本报告全部复核并补充了机制级证据：环仅靠 lazy import 压制（§2.2）、artifact_service 引用为 `:126` 且伴随 `create_case` commit 语义矛盾（§6.1）、双 Worker 竞态具体到 `task_worker.py:82` 的僵尸任务 bug 与 `claim_next_task` 的 TOCTOU（§3.3）、双轨的字段级证据 `test_execution.api_task_id` ↔ `api_execution_task_item.test_execution_id`（§3.1）。
- **本报告新增发现**：① 认领后放弃的僵尸任务（P0，§3.3 Bug 1）；② 计划执行单长事务在调度线程中阻塞 cron（P0，§6.2）；③ 六套认领队列各自为政（P1，§3.4）；④ 权限码双份维护与 96 码核对结论（P2，§5.4）；⑤ 软删除三套语义并存（P2，§4.4）；⑥ `DELETE /batch` 与 `POST /batch-delete` 完全重复端点（P2，§5.1）；⑦ 8 处跨服务私有符号引用清单（P2，§2.4）；⑧ 路由层直连 ORM（knowledge.py:675-693，P1，§5.2）；⑨ 无 statement_timeout、`soft_delete_status` 死代码（P2，§6.3/§4.1）。
