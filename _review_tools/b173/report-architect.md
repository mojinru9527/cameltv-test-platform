# CamelTv 测试平台 v2 — 架构师视角审查报告（Batch 173）

> **审查对象**：CamelTv 测试平台 v2（生产 https://cameltv-test-platform1.vercel.app，Vercel 前端 + Railway 后端 v2.1.0 + Supabase PostgreSQL）
> **审查日期**：2026-08-14 | **审查人**：架构师（综合 batch-173 后端/前端两份子代理深度报告 + 独立复核）
> **方法**：① 通读 `_review_tools/b173/` 下的 00-evidence-master.md（第一手实测）、report-arch-backend.md、report-arch-frontend.md；② 独立复核关键结论：87 张表实测、双 Worker 竞态（`task_worker.py:81-83` 僵尸守卫）、长事务（`test_plan_service.py:1119` 单点 commit）、cachedGet 被 signal 绕过（`client.ts:101` 约定）、裸线程入口（`open_api.py:300-304`）、同步长任务端点（`knowledge.py:623/917/935`）；③ 读本地搭建脚本（`scripts/start-platform-environment.ps1`，831 行）、onboarding、配置与依赖文件。
> **范围**：总体架构 / 模块关联矩阵 / 请求层冗余（重点）/ 本地搭建（重点）/ 部署与运行 / 技术债 / 演进路线。
> **证据约定**：`文件:行号` 均指 `test-platform-v2/` 下相对路径；实测数据引用 `00-evidence-master.md` §5/§6 与 `evidence/*.json`。

---

## 0. 执行摘要

**总体判断**：这是一套**功能覆盖面大、域内建模认真、但跨域集成失控**的"演示态→真实引擎"快速迭代系统。单体内聚度足够（FastAPI 单体合理），问题不在"要不要拆服务"，而在**内部边界从未被执行**：执行引擎 9 套调度入口、6 套认领队列、4 张执行记录表 4 套状态值、权限码双份、软删除三套——这些是"同一个事实被多处各写一份"的典型架构债务，已直接造成生产可观测的后果（通过率 9.1% vs 22.1% 口径分裂、API 批量任务僵尸卡死、计划执行长事务撞锁）。前端请求层问题本质是一个**设计约定错误**（`client.ts:101`"传 signal 绕过缓存"），修复成本极低、收益可直接量化。

| 维度 | 评级 | 一句话结论 |
|------|------|-----------|
| 前后端分离 + 三云部署 | ✅ 合理 | Vercel 静态托管 + /api 反代 + Railway + Supabase 是标准 SPA 拓扑；短板是反代超时与长任务错配 |
| 单体 FastAPI vs 微服务 | ✅ 单体正确 | 26 模块高度互相引用，拆服务成本 >> 收益；缺的是模块内部边界与公共 API 治理 |
| 数据模型（实测 87 张表） | ⚠️ 域内好、跨域烂 | 核心业务链有 FK；跨域关联（用例↔需求↔接口资产↔UI 脚本↔计划）几乎全为无约束整数列/JSON 数组 |
| 执行引擎一致性 | 🔴 失控 | 9 套调度机制、6 套认领队列、4 张执行表 4 套状态取值 → 统计分裂、僵尸任务、重复执行 |
| 事务与并发 | 🔴 高危 | 计划执行单长事务、认领 TOCTOU、无 statement_timeout，生产 PG 下已构成故障源 |
| 请求层冗余 | 🟠 可快速修复 | 根因是单一设计约定（signal 绕过缓存），修复后全站重复 GET 可降 30~40% |
| 本地搭建 | 🟡 功能强、文档缺 | 831 行 PowerShell 极健壮但 Windows 专属；`docs/local-setup.md` 被手册引用两次却不存在 |
| 文档保鲜 | 🔴 多份漂移 | 完整PRD 技术栈过时、手册引用了不存在的文件、隐藏路由未同步 |

---

## 1. 总体架构评估

### 1.1 部署拓扑与合理性

```
┌────────────── 用户浏览器 ──────────────┐
│  React 19 SPA (146 个页面文件, 1.6MB)  │
└──────────────┬────────────────────────┘
               │ https://cameltv-test-platform1.vercel.app
       ┌───────▼────────┐   vercel.json:8-12  /api/:path* 反代
       │     Vercel     │──────────────────────────────┐
       │ 静态托管+边缘反代│                              │
       └────────────────┘   https://test-platform.up.railway.app/api/*
                              ┌─────────▼─────────┐
                              │  Railway FastAPI   │ 单实例单进程
                              │  uvicorn + APScheduler + 9 类线程/线程池
                              └─────────┬─────────┘
                                        │ DATABASE_URL=postgresql://...
                              ┌─────────▼─────────┐
                              │ Supabase PG16      │ PgBouncer :6543 事务池
                              │ PgBouncer 连接池    │ pool_size=10/max_overflow=20
                              └───────────────────┘
```

**评估**：这是成本最低且合理的三云组合——Vercel 免费静态托管 + 边缘 /api 反代（`frontend/vercel.json:8-12`）消除 CORS/Cookie 跨域问题（前端始终走同源 `/api/v1`，`.env.example` 注释明确此设计）；Railway 托管有状态的后端进程；Supabase 提供托管 PG。**合理性成立**，但有三处结构性短板（详见 §5）：

1. **反代超时错配**：Vercel 对外部目标 rewrite 有平台级限制（长请求在 Vercel 社区与官方错误码 `ROUTER_EXTERNAL_TARGET_ERROR` 中均有 502 报告）；而前端 axios timeout 设为 **600 秒**（`client.ts:15`），后端无任何 statement/transaction timeout（`db.py:21-30`，全仓 grep `statement_timeout` 0 命中）。三层超时互不知情，长任务必然先撞网关 502，前端却等到 600s 才报错。
2. **同步长任务端点残留**：知识图谱 extract/evolve/auto-build、计划 execute-all（默认同步）、接口批量生成仍是同步阻塞（§5.2 清单），与反代超时直接冲突。
3. **单实例假设**：所有 Worker（APScheduler、守护线程、线程池、裸线程）都在一个 uvicorn 进程内（`main.py:110-164`）。Railway 一旦水平扩容到 2 副本，双 Worker 竞态（ARCH-01/02）会被放大成跨进程重复执行——当前架构对多副本是**不安全的**。

### 1.2 单体 FastAPI vs 模块化服务

**结论：保持单体，治理内部边界。** 理由（架构师判断）：

- 26 个功能模块的服务层相互引用密度极高（`report-arch-backend.md` §2 的 147 条顶层引用、`requirement_service ⇄ test_case_service` 双向环），按域拆微服务会让 80% 的调用变成跨服务 RPC，事务边界被撕碎（当前计划执行就是单事务跨 8 个服务调用）。
- 团队规模与迭代节奏（批次制、单人仓库）不支持微服务运维成本。
- **真正的债在服务层内部**：65+ 服务文件无统一分层接口（`core/base_service.py` 只提供纯函数工具）、8 处跨服务直接引用私有符号（`_row_to_dict`/`_call_llm_sync`/`_execute_schedule` 等，`report-arch-backend.md` §2.4）、路由层直连 ORM（`knowledge.py:675-693` 直接 `select(KnowledgeEntity)`）。这些是"微服务化之前必须先解决的模块化问题"。

### 1.3 数据模型设计质量（87 张表——修正子报告口径）

**独立复核修正**：后端子报告称"约 55 张表"，实际递归扫描 `app/models/`（40 个模型文件）提取 `__tablename__` 得 **87 张唯一表**。子报告口径低估了 50%+，说明 schema 复杂度被系统性低估。

**域内质量（好的方面）**：
- 核心测试域建模完整：`test_plan → test_plan_case → test_execution` 有 FK 链；`defect → transition/comment/attachment`、`av_check`、`perf`、`api_asset(service/endpoint/import_batch/execution_task/item)` 结构完整。
- 权限/审计域严谨：`rbac` 五表 + `sys_audit_log` + 双份邀请码体系（`sys_invite_code`/`sys_project_invite`）都有 FK。
- 知识域表量大质参差：`knowledge_*` 10 张、`wiki_*` 13 张、`lanhu_evidence_*` 5 张——域内表设计尚可，但跨域引用几乎全为软引用。

**跨域质量（坏的方面）**：

| 问题 | 证据 | 后果 |
|------|------|------|
| 跨域关联无 FK | `TestCase.source_doc_id`（test_case.py:75）、`TestPlanCase.case_id`（test_plan.py:53）、`ApiExecutionTaskItem.case_id`（api_asset.py:102）均无 FK；`RequirementDocument.linked_swagger_id/linked_api_endpoint_ids` 是 JSON 数组存 id（requirement.py:51-52） | 删除时无 DB 级保护，全凭服务层手写级联（`defect_service.delete_defect:244 _cascade_knowledge`）；用例软删后计划内成孤儿 |
| 多态外键 | `TestSchedule.job_id`（test_schedule.py:24）"job_type=ui 时指向 ui_test_job.id" | 无 FK 约束、无 UNION 校验，删 UI 任务不级联调度 |
| 反范式缓存字段 6 处 | `TestCase.last_run_status/last_response_json`（test_case.py:64-65）3 处写入口口径不一；`ApiExecutionTask.passed/failed/skipped` 由两份 worker 逻辑各自汇总 | 同一"执行结果"概念在 schema 层无统一形状，统计必然分裂（§2.2 实测） |
| 软删除三套语义 | `is_deleted` 布尔（test_case）、`status=deprecated`（knowledge_source/chunk）、`db.delete` 硬删 36 处（需求/缺陷/计划/UI 任务等） | "删了能不能恢复"取决于模块，查询过滤写法 `is_(False)`/`== False`/`is False` 三种并存，易漏过滤 |
| 87 张表无统一命名域 | 26 张系统表前缀 `sys_`，其余裸命名 | 演进期改名成本高 |

**架构师判断**：数据层最该先动的是**执行记录事实源单一化**（§6 P1-1）而非表结构大改——4 张执行表互指、4 套状态值（`pass/fail/skip` vs `passed/failed/skipped` vs `done/fail` vs `completed/failed`，`report-arch-backend.md` §3.1）才是生产数据分裂的直接根因（通过率 9.1% vs 22.1%）。

### 1.4 "如果重新设计会怎样"（架构师视角，务实对照）

若从零开始（不迁移存量），我会做四个不同的决策：

1. **执行引擎用一张任务表 + 一个队列抽象**：`tasks(id, kind, status, locked_by, heartbeat_at, payload_json, retry_count)`，所有执行（API/AI/DSH/UI/证据包/Agent）共用；worker 用 `UPDATE ... WHERE status='pending' FOR UPDATE SKIP LOCKED RETURNING` 认领（生产 PG 方言），一条 stale 回收任务兜底。现状是 6 套各自为政的队列（ARCH-07），每条都要单独写认领/恢复/状态机。
2. **执行记录单一事实源**：机器可读明细（`api_execution_task_item`/`ui_test_run`）为唯一事实源，`test_execution` 降级为计划维度的轻量索引视图，前端/聚合层只读一个聚合口径。现状是双轨互指（ARCH-04），统计口径三处三个数。
3. **前端用 React Query 而非手写缓存**：`cachedGet` + `useApi` + `useAbortableEffect` 三套自定义机制解决的是 React Query 十年前就解决的问题。现状 36 个 api 模块约定不统一，signal 语义与缓存语义打架。
4. **跨域引用一律显式 FK + 服务级 API 边界**：用例↔接口资产↔UI 脚本↔计划之间建真实关联表，删除走 DB 级联；服务间只允许公共函数调用（`__all__` 强制）。现状 8 处私有符号跨模块引用（ARCH-05）是环依赖长期存在的土壤。

**但务实结论**：存量 87 张表、146 个页面、65+ 服务文件已经成型且功能可用，"推倒重来"不成立；上述四条恰好就是 Phase 1/2 的最小成本改造路径（§7），只是顺序与力度不同。

---

## 2. 模块关联矩阵（26 模块耦合/断裂分析）

### 2.1 全景矩阵

| # | 功能模块 | 路由文件 | 主服务 | 核心表 | 强耦合对象 | 关联断裂点 |
|---|---------|---------|--------|--------|-----------|-----------|
| 1 | 工作台 | dashboard.py | dashboard_service → statistics/test_case_service | 读 4 张执行表 | test_case_service（顶层引用） | 统计口径与 trace/report 分裂（§2.2） |
| 2 | 质量追溯 | trace.py | trace_service → statistics/test_case_service | 读 test_execution | 同工作台 | 通过率 22.1% vs dashboard 9.1% |
| 3 | 需求文档 | requirement.py (45KB) | requirement_service | requirement_document | **test_case_service（环）**、test_plan_service、api_case_generation | 需求覆盖率三处三个数（0%/33.3%/67%）；`source_doc_id` 无 FK |
| 4 | 版本测试任务 | version_mission.py | version_mission_service | version_mission/generated_artifact | case_generation_service（顶层） | — |
| 5 | 用例脑图 | （前端页） | 读 taxonomy/domains | — | test_case 域 | — |
| 6 | 用例服务 | test_case.py (26KB) | test_case_service | test_case + 域/模块/评审/版本 | **6 个服务引用它（statistics/dashboard/trace/review/artifact/requirement）** | `case_type=api` 用例与接口资产无 FK（§2.3-b）；`is_deleted` 过滤 20+ 处写法不一 |
| 7 | 测试计划 | test_plan.py (20.7KB) | test_plan_service | test_plan/test_plan_case/test_execution | 8 个 lazy 引用（api_execution/environment/case_compiler/playground/defect/notify/report/triage） | `test_plan_case.case_id` 无 FK；执行端点三套重叠 |
| 8 | 接口测试 | apitest.py (37KB) | api_execution_service + api_task_worker | api_asset 四表 | environment_service（顶层）、dataset_service | 与用例/UI 脚本无资产链关联（§2.3-b） |
| 9 | UI 自动化 | ui_test.py (16.5KB) | ui_test_service + ui_runner_queue + playwright_executor | ui_test_job/run/script | playwright_executor（私有符号引用） | 三入口并存（ui_runner_queue/task_worker 轮询/open_api 裸线程） |
| 10 | Playground | playground.py | playground_service | — | playwright_executor、ui_test_service | LLM 编译与 case_compiler_service 双路径重复（§2.4-a） |
| 11 | 定时任务 | schedule.py | schedule_service | test_schedule/run | **core.scheduler._execute_schedule（私有）** | `job_id` 多态外键；cron 线程阻塞时整个调度排队 |
| 12 | 报告中心 | report.py (12KB) | report_service + report_aggregator | test_report | **读 api_execution_task/ui_test_run（口径 B）** | 与 trace/dashboard 口径分裂；gate 双端点 |
| 13 | 系统管理 | system.py (10.8KB) | rbac/role/user_service | rbac 五表 + audit | seed.py 权限目录 | 权限码双份（344+ 处内联字符串 vs seed.py:16-192） |
| 14 | 我的项目 | project.py (10.5KB) | project_service | sys_project(+member/invite) | organization_service（顶层） | 前端 `/project` 重定向；`fetchProjects` 死代码 |
| 15 | 缺陷管理 | defect.py (14KB) | defect_service | defect + transition/comment/attachment | **knowledge.knowledge_cleanup（硬耦合）** | 前端无删除入口（API 有）；删除后知识切片残留 |
| 16 | 测试数据集 | dataset.py | dataset_service | dataset | 无 FK 表 | — |
| 17 | 集成配置 | integration.py | integration_service → sync.engine → jira/tapd | integration_config/sync_log | defect 模型（同步回写） | 外部 0 配置（生产实测） |
| 18 | 通知配置 | notify.py | notify_service | notification_channel/log | 被 api_task_worker/test_plan/defect 引用 | — |
| 19 | 目标环境 | environment.py | environment_service | environment(+variable) | **被 api_execution/test_plan/ui/apitest 广泛引用** | 前端 7 处调用点各自拉取（§3） |
| 20 | Agent 工作台 | agent.py | knowledge/agent_queue | agent_run/agent_queue_item | knowledge 域 | 6 套队列之一，SQLite 专用锁处理 |
| 21 | DSH 任务 | dsh_tasks.py | dsh/dsh_task_service | dsh_task | dsh_runner | 6 套队列之一；生产实测"DSH 服务未启用" |
| 22 | 蓝湖证据包 | lanhu_evidence.py (22KB) | lanhu_evidence/*（13 文件） | lanhu_evidence 5 表 | **import_service → requirement/knowledge/wiki** | 失败任务无删除入口；存储无持久卷 |
| 23 | 知识中心 | knowledge.py (**68KB/1668 行**) | knowledge/*（25 文件） | knowledge 10 表 | **wiki 借用 `_call_llm_sync` 私有符号** | 路由直连 ORM；8 域混一文件 |
| 24 | 运维发布控制 | ops_releases.py | ops_release_reader | release-control 独立 store | — | 生产"未启用"占位 |
| 25 | 主题实验室 | （前端） | — | — | — | 生产门禁关闭（router/index.tsx:240-244） |
| 26 | 音视频/性能（隐藏） | av_check.py / perf.py / perf_ws.py | av_check/perf_service | av_check_*/perf_* | ffmpeg_service（私有符号） | 路由已注释隐藏（router/index.tsx:214-215/234-235）但仍在维护 |

### 2.2 耦合过紧的模块对（a 项）

按耦合强度排序（证据均出自 `report-arch-backend.md` §2，架构师已抽查关键项）：

1. **需求 ⇄ 用例（设计级环）**：`test_case_service.py:106` 函数内 `from app.services import requirement_service`；`requirement_service.py:789` 注释自认"懒加载：避免 requirement_service ↔ test_case_service 环依赖"。不崩但**任一方向签名变更都穿透到对方**，是后续域拆分的最硬障碍。
2. **计划 → 执行链（4 层 + 2 条同层路径）**：`test_plan_service` → `playground_service`（:625,721）→ `ui_test_service`（:418）→ `playwright_executor`；同时 `test_plan_service` 又直连 `case_compiler_service`（:616）与 `playwright_executor`（:715）。**"把用例编译成 Playwright spec 再执行"的能力被 4 个服务各自接线**。
3. **test_case_service 全局中心**：statistics/dashboard/trace/review/artifact/requirement 6 个服务引用它（4 个顶层引用），任何改动波及面最大——这本身是"模块化不足"的信号（应抽公共 case 查询/写入 API）。
4. **缺陷 → 知识（业务删除与知识清理硬耦合）**：`defect_service.py:239` 调 `knowledge.knowledge_cleanup`，删除缺陷的副作用横跨两个域；生产实测缺陷删除后知识切片确实残留（evidence-master §3），说明该耦合不可靠。
5. **wiki → knowledge（借私有符号）**：`wiki/contract_extractor.py:15`、`wiki/ingest_service.py:18` 顶层 import `knowledge.agent_orchestrator._call_llm_sync`——LLM 调用能力不是公共 API，而是私有入口被借用。

### 2.3 本应关联却断裂的链（b 项）——用例↔接口资产↔UI脚本↔计划

这是架构师认为**最值得补的领域模型缺口**：

| 断裂链 | 现状 | 证据 | 生产后果 |
|--------|------|------|----------|
| 用例 ↔ 接口资产 | `case_type='api'` 的用例把 `api_method`/`api_endpoint` 存成**文本冗余列**，不指向 `api_endpoint` 表 | test_case.py（model 字段）vs api_asset.py；`ApiExecutionTaskItem.case_id` 无 FK | 接口资产更新后用例不同步；接口用例通过率 1.1%（4/363）历史失败残留无法溯源到具体资产 |
| 用例 ↔ UI 脚本 | `ui_test_script` 与 `test_case` 无关联表 | ui_test.py:13 模型 | UI 任务"关联用例"（evidence-master §3）是手动选择而非资产链 |
| 用例 ↔ 计划 | `TestPlanCase.case_id` 无 FK（test_plan.py:53） | 同上 | 用例软删后计划内成孤儿，统计口径再分裂 |
| 需求 ↔ 接口资产 | `RequirementDocument.linked_swagger_id/linked_api_endpoint_ids` 是 JSON 数组存 id（requirement.py:51-52） | 无 FK 无校验 | 需求覆盖率 0%/33.3%/67% 三处三个数（UI-04），AI 导入 1157 条用例与需求无可靠锚点 |
| 用例 ↔ 知识 | `TestCase.source_doc_id` 无 FK（test_case.py:75） | 同上 | 需求软删后历史用例失去来源锚点 |

**架构师判断**：这是"管理闭环（需求→用例→计划→执行→报告）"产品叙事的**领域模型缺环**。最小成本修补不是建 5 张关联表，而是：a) 先给 `ApiExecutionTaskItem.case_id`/`TestPlanCase.case_id` 补 FK 并做孤儿清理脚本（1-2 天）；b) 中间态用"资产关联表"（`case_asset_link`：case_id + asset_type + asset_id）承接接口资产/UI 脚本两个方向的关联（3-5 天）；c) 统计口径统一（§6 P1-1）后需求覆盖率三处数字自然归一。

### 2.4 重复实现的能力清单（c 项）

| 能力 | 重复路径 | 证据 | 收敛建议 |
|------|---------|------|----------|
| **LLM 编译双路径** | `case_compiler_service`（test_plan_service.py:613-628 先 LLM 后规则）vs `playground_service.compile_spec`（:176-190 同样双路径） | report-arch-backend.md §2.3 链 1 | 抽唯一 `compile_ui_case(case) -> spec` 公共函数，两者都调用 |
| **执行三入口** | `ui_runner_queue` 线程池（ui_test_service.py:334-375）+ `task_worker._process_ui_runs`（task_worker.py:168-229）+ `open_api.py:300-304` 裸线程 | 已独立核实 open_api.py:300-304 | 全部收敛到 `ui_runner_queue.enqueue_run` |
| **认领 6 套队列** | api_task_worker / ai_tasks / dsh / lanhu_evidence / agent_queue / playwright_executor 各写一套 claim+状态机 | report-arch-backend.md §3.4 | Phase 2 统一 TaskQueue 抽象 |
| **批量删除用例双端点** | `DELETE /test-cases/batch`（test_case.py:267）+ `POST /test-cases/batch-delete`（:287）函数体逐行相同 | 同上 §5.1 | 保留一个，另一个 410 |
| **计划执行三端点** | `execute-all`（test_plan.py:309）/`auto-execute`（:370）/`batch-execute`（:513）语义重叠 | 同上 | 收敛为 execute-all + 参数开关 |
| **报告门禁双端点** | `GET /reports/{id}/gate`（report.py:130）+ `/gate/check`（:144） | 同上 | 收敛 |
| **权限码双份** | seed.py `_MENUS`/`_ACTIONS`（:16-192）vs 路由内联 ~344+ 处 `require_permission("...")` | 已独立核实 394 处命中 | 单点常量 + CI 校验 |

---

## 3. 请求层冗余深度分析与优化方案（重点）

### 3.1 实测数据（第一手）

**apitest 模块切 tab 实测**（`evidence/15-apitest-log.json`，10 条请求）：

```
GET /system/menus          ← 会话级 1 次（cachedGet 生效 ✅）
GET /apitest/services
GET /apitest/endpoints
GET /environments          ← tab1 挂载
GET /datasets              ← tab1 挂载
GET /environments          ← tab 切换重复！×2
GET /datasets              ← tab 切换重复！×2
GET /test-cases
GET /test-cases/domains
GET /apitest/tasks
```

**testcase 页首载实测**（`evidence/09-testcase-load-requests.json`，5 条）：menus/test-cases/stats/domains/taxonomy，**无重复**——说明会话级缓存对不传 signal 的路径有效，问题集中在 signal 路径。

**25 页全站走查**：初始加载 0 重复 GET（cachedGet 生效），加载耗时 2.4~4.1s/页（evidence-master §1）。

**结论**：重复请求不是全站性灾难，而是**集中在"低频静态数据 × 多页面/多 tab 各自挂载"的交叉点**——`/environments` 在 apitest 3 个 tab 组件 + integration + release-bundles + testplan + uitest 共 7 处调用点各自拉取（report-arch-frontend.md §A.2 P1-1 表）；`/test-cases/domains` 4 处。batch-147 的"domains×4、environments×6"在 60s 窗口内依然复现。

### 3.2 根因链（单一设计约定错误）

```
client.ts:101 约定「传 signal 时请直接使用 client.get，保持 abort 语义」
  → api 层函数写成 if (signal) return api.get(...)  else return cachedGet(...)
    （environment.ts:8-11 为模板，全仓同构）
  → 页面几乎全部经 useApi/useAbortableEffect 传 signal
  → cachedGet 仅剩 3 个真实调用点（auth.ts:40 / environment.ts:10 / testcase.ts:60，已独立核实）
  → 静态低频数据（environments/domains/menus）随每次页面/tab 挂载重新请求
```

注意：**缓存失效路径是健全的**——所有 mutation 都调用 `clearApiCache(BASE)`（environment.ts:16/23/29），401 时 `clearApiCache()` 全清（client.ts:72）。**坏的只是读路径**。

### 3.3 优化方案（按成本递增排序，全部可落地）

#### 方案 A（P0，1-2 人日）：修正 cachedGet 的 signal 语义——缓存命中优先，abort 只退订不取消共享请求

改动集中在 `frontend/src/api/client.ts`（约 40 行）：

```
cachedGet(url, params, { ttl, signal, force })
  1. key = url + params；命中未过期缓存 → 直接 resolve（signal 已 abort 也无所谓，值已就绪）
  2. 未命中 → 查 inflightGets：
     - 有 in-flight：把当前 signal 登记到该请求的订阅集合，请求完成时统一分发；
       signal abort 只从订阅集合移除，不取消底层 axios 请求
     - 无 in-flight：发起 axios.get，并把「取消」改为「仅当所有订阅者都 abort 时才真正 cancel」
  3. 缓存写入/失效逻辑不变（force 参数已存在，mutation 侧继续用 clearApiCache）
```

同时把 15+ 处调用点改为 `cachedGet(url, undefined, { ttl: 60_000, signal })`（机械替换，`useApi` 的 AbortController 语义保留：**组件卸载只退订，不打断其他页面的共享请求**）。`useAbortableEffect` 保持原样。

**为什么这是正解**：共享静态数据本来就是幂等、可并发的；"页面 A 卸载就取消请求"会连带取消"页面 B 正在等的同一个请求"——这正是当前设计把 abort 和缓存对立起来的根本矛盾。React Query 的 `staleTime` + 共享 query 订阅就是同一语义。

#### 方案 B（P1，3-5 人日）：补 4 处 useEffect cleanup + 修 environment 页竞态

- `pages/defect/DefectFormDialog.tsx:61-81`、`pages/knowledge/components/SearchTab.tsx:63-67/70-86`、`pages/testcase/CaseDrawer.tsx:125-154`：加 `cancelled` 标志或 AbortController（违反 engineering-standards §4.1 铁律，Block PR 级问题）。
- `pages/environment/index.tsx:106-108`：环境切换竞态，加请求序号守卫（`let seq = 0; const mySeq = ++seq; if (mySeq !== seq) return`）。

#### 方案 C（P1，3-5 人日）：轮询加指数退避 + 条件暂停

| 位置 | 现状 | 改法 |
|------|------|------|
| `pages/dsh-tasks/index.tsx:81-85` | 3s 固定（仅 hasRunning） | 指数退避 2s→4s→8s→16s→封顶 30s；状态变化（pending→running→done）时重置为 2s；done 后立即停 |
| `pages/uitest/index.tsx:297-323` | 3s 固定（运行详情打开且 running/pending 时） | 同上 |

收益量化：一次 3 分钟 UI 任务，固定 3s = 60 次请求；退避后 ≈ 25 次（省 ~58%）。已确认 cleanup 齐全（report-arch-frontend.md §A.2 P2-2），无泄漏风险。

#### 方案 D（P2，2-3 人日）：页面级合并——聚合端点试点

`pages/testcase/index.tsx` 挂载 5 请求（:118-147）：`test-cases`（page_size=20）+ `stats` + `domains` + `taxonomy` + `menus`。其中 `stats` 与 `taxonomy` 同为用例域聚合数据，可合并为 `GET /test-cases/bootstrap?case_type=manual` 返回 `{cases, stats, domains, taxonomy}`（后端一个 service 函数，4 个 SQL 复用现有 service）。

**不建议**把 domains/environments 这类跨模块共享数据塞进 bootstrap——会破坏其"全局共享缓存"性质。合并只针对**同页面同域**的聚合。

#### 方案 E（P2，评估后决定）：React Query 引入评估（§3.5）

### 3.4 量化预期收益

| 场景 | 现状 | 优化后（A+C+D） | 降幅 |
|------|------|----------------|------|
| apitest 进入 + 切 4 tab | 10 请求（15-apitest-log.json 实测） | 8 请求（environments/datasets 各 1） | **-20%** |
| 60s 窗口内跨页访问 testcase→apitest→uitest→integration→testplan | environments ×5+、domains ×3-4 | 各 1 次（共享缓存） | **-60~70%**（静态数据部分） |
| 全站 25 页一次会话走查 | ~80 GET（每页 ~3.2，含静态重复） | ~50-55 GET | **-30~40%** |
| 单次 3 分钟 UI 任务轮询 | 60 次 | ~25 次 | **-58%** |
| 首屏加载（重复请求被缓存命中） | 2.4~4.1s/页 | 静态数据秒回，预计整体 -0.3~0.8s/页 | 取决于后端查询耗时（domains 实测 2005ms、taxonomy 2094ms 首载） |

后端侧收益：Railway 单实例上每次冗余 GET = 一次 PG 查询 + JSON 序列化 + 往返；消除重复后对 PG 的读压力直接下降 30-40%（生产当前用例 8984、接口资产 899，列表接口都是重型查询）。

### 3.5 React Query / SWR 引入评估

| 维度 | 结论 |
|------|------|
| 问题匹配度 | 高：缓存/去重/轮询/失效正是 React Query 核心能力，现状三套手写机制（cachedGet/useApi/useAbortableEffect）都是它的子集 |
| 成本 | 依赖 `@tanstack/react-query`（核心 ~13KB gzip）；但**迁移要动 36 个 api 模块 + 146 页面文件**，且 zustand（已用于 auth 等全局状态）与 React Query 的职责需要划清（服务端状态 vs 客户端状态） |
| 风险 | 全量重写风险 > 收益；当前页面已能工作，重写引入回归面 |
| **建议** | **分两步走**：Phase 1 只做方案 A（修正现有缓存语义，2 人日，不动架构）；Phase 2 以 3 个轮询点 + 2 个重型列表页（uitest/testcase）为试点引入 React Query（`useQuery` + `refetchInterval` 退避），验证后再决定是否全量迁移。**不建议现在就全量引入**——先用最便宜的方案止血，用 React Query 解决"轮询与列表缓存"两个真正痛点 |

---

## 4. 本地搭建流程梳理（重点）

### 4.1 现状盘点

- 一键脚本：`scripts/start-platform-environment.ps1`（831 行）——Target 分 `local`（uvicorn + vite 裸进程）与 `production`（docker compose）；支持 `-InitializeLocal`（安全生成受 Git 忽略的 `config/runtime/local.env` 与随机凭据）、`-InstallDeps`（`pip install -r requirements.txt` + `npm ci`）、`-Action start/status`。
- 健康检查完备：后端 `/health`、前端 `/login`、代理 `/api/v1/open/health` 三重探测 + 60s 超时（:579-595, 729-732）。
- 进程所有权校验严谨：`Get-NetTCPConnection`/`Get-CimInstance` 反查监听进程属于当前 worktree，防止端口被外部进程占用（:345-502）。
- 运行时清单：`%TEMP%/cameltv-platform-local/runtime-manifest.json` 记录 URL/端口/DB/PID/Git SHA（:312-343）。
- 种子数据：启动时 `run_seed()`（main.py:106-108）幂等写入权限目录 + admin/tester/viewer 账号（ADMIN_PASSWORD 由 `-InitializeLocal` 生成，dev 下未配置则自动生成并打日志，config.py:234-247）。

### 4.2 空白机完整步骤清单（Windows/macOS 通用，含缺口标注）

| 步骤 | 操作 | 说明 | 现状 |
|------|------|------|------|
| 1 | 安装 Git + PowerShell 7（macOS 用 pwsh） | 脚本是 .ps1，macOS 需 `brew install powershell` | ✅ 脚本运行前提 |
| 2 | 安装 Python 3.10+（含 pip） | 手册 1.2 声明 3.10+；README 无版本下限声明 | ✅ |
| 3 | 安装 Node 22+（**需 ≥22.22.0**） | `frontend/package.json:7` engines 字段；README:51 说 Node 22+ | ⚠️ 两处口径不一致（22+ vs 22.22+） |
| 4 | 克隆仓库（含 lanhu-mcp 子模块，`git submodule update --init`） | lanhu-mcp 是后端蓝湖 Provider 的运行依赖（requirements.txt:14-15 注释） | ⚠️ AGENTS.md §4.3 声明但本地步骤未写进手册 |
| 5 | `pwsh scripts/start-platform-environment.ps1 -Target local -Action start -InitializeLocal -InstallDeps` | 一条命令完成：生成 local.env（随机 SECRET_KEY/ADMIN_PASSWORD）→ pip install → npm ci → 起 uvicorn+vite → 三重健康检查 | ✅ 手册 1.2 已写（但"详见 docs/local-setup.md"指向不存在的文件） |
| 6 | 登录：从 `config/runtime/local.env` 取 ADMIN_PASSWORD | 平台无默认密码 | ✅ |
| 7 | （可选）`npm run gen:api` | 前端类型由后端 OpenAPI 生成（README:141），需后端先起在 8000 端口 | ⚠️ 本地流程未文档化 |
| 8 | （可选）停服/查状态：`-Action status` / 手动杀进程 | manifest 记录 PID | ✅ |

**架构师修正**：README"快速启动"（:84-97）给了**第二套手工路径**（`python -m venv` + `pip install -r requirements.lock` + `npm ci` + `npm run dev`），与脚本路径并存且依赖文件口径不同（`requirements.lock` vs 脚本用的 `requirements.txt`）——这就是文档漂移的第一处源头（§4.4）。

### 4.3 冗余步骤与可优化项

| # | 问题 | 证据 | 类型 | 建议 |
|---|------|------|------|------|
| 1 | **docs/local-setup.md 不存在**，手册:11/:51 两次引用 | `Test-Path docs/local-setup.md` = False；手册:11"Windows/macOS 完整步骤见 docs/local-setup.md"、:51"详见" | 🔴 文档缺口 | 补写（内容即 §4.2 步骤表 + 常见问题：端口占用/子模块/密码找回），预计 0.5 人日 |
| 2 | **macOS 兼容性名不副实** | 手册声称 Windows/macOS；脚本用 `Get-NetTCPConnection`（:349）与 `Get-CimInstance Win32_Process`（:353）——`icacls` 有 `$IsWindows` 守卫（:79-80）但 `Get-NetTCPConnection` 无，macOS 上该函数在部分 PS7 版本不可用；`.env.example` 注释（:9-11）也仅示例 Windows worktree | 🟡 冗余/风险 | 脚本平台差异抽一层（`Test-NetConnection`/`Get-Process` 兜底），或文档明确"macOS 请用手工路径" |
| 3 | 依赖安装路径双份 | 脚本 `Install-Dependencies` 用 `requirements.txt`（:779）与 `npm ci`（:787）；README 手工路径用 `requirements.lock`（:88）；`npm ci` 又要求 package-lock 存在 | 🟡 冗余 | 统一为 `requirements.lock`（有锁文件就该用它），脚本与 README 对齐 |
| 4 | 无 Docker 一键本地 | docker compose 只有 `production` Target（`Invoke-SharedCompose`，:743-775）；`deploy/docker-compose.yml` 是整栈（含 postgres/nginx） | 🟡 可优化 | 增加 `local` 的 compose profile（backend+frontend，DB 仍用 SQLite）或独立 `compose.dev.yml`，让"不装 Python/Node 也能跑"成为可能（配合 `-Target docker-local`） |
| 5 | 种子数据只有账号无业务数据 | `run_seed()` 建权限+账号；无演示用例/计划/环境数据，新用户首屏空 | 🟡 可优化 | 可选 `-SeedDemoData`：按模板导入 1 项目 + 20 用例 + 1 计划 + 4 环境（仅 local），方便验收/培训 |
| 6 | 本地用 `AUTO_CREATE_TABLES=true` 建表，与 alembic 58 个迁移并存 | config.py:90 默认 true、脚本强制 local 为 true（:208-210）；`alembic/versions` 实测 58 个文件 | 🟡 架构风险 | `create_all` 不做增量迁移，本地 schema 会与生产漂移（生产 `AUTO_CREATE_TABLES=false` + alembic upgrade）；建议 local 也切到 alembic（`uvicorn` 前跑 `alembic upgrade head`），并在脚本里加 migrate 步骤 |
| 7 | gen:api 未纳入本地流程 | README:141 说明存在但步骤缺失；gen:api 依赖后端 8000 端口已启动，与脚本端口可配置（FRONTEND_PORT/BACKEND_PORT）冲突 | 🟡 文档缺口 | 脚本 `-Action genapi` 或在 local-setup.md 写明 `npm run gen:api` 前提 |
| 8 | 端口占用/多 worktree 冲突处理强但文档弱 | 脚本抛错信息完整（:415/:487/:547）但用户手册无故障排查章节 | 🟡 文档缺口 | local-setup.md 加 FAQ：端口被占→查 manifest/杀进程；Git SHA 不匹配→rebase |

### 4.4 文档缺口汇总（本地搭建视角）

| 缺口 | 引用处 | 严重度 |
|------|--------|--------|
| `docs/local-setup.md` 不存在 | 手册:11、:51 | 🔴 |
| 手册称支持 macOS 但脚本/示例 Windows 专属 | 手册:11 | 🟡 |
| README 手工路径（requirements.lock）与脚本路径（requirements.txt）口径不一 | README:88 vs ps1:779 | 🟡 |
| Node 版本下限口径不一（22+ vs ≥22.22.0） | 手册:44 vs package.json:7 | 🟡 |
| onboarding.md 仍是 v1 时代"http://localhost:8000 + Bearer"接口示例 | onboarding.md:38-42（v2 是 Cookie 会话 + /api/v1 前缀） | 🟡 |
| 完整PRD 技术栈过时（React 18.3/Router 6 vs 实际 19.2.8/8.3.0） | 完整PRD:71,100 vs package.json:56,61 | 🟡 |

---

## 5. 部署与运行架构问题

### 5.1 Vercel 反代与长任务 502

**现状**：`frontend/vercel.json:8-12` 把 `/api/:path*` rewrite 到 `https://test-platform.up.railway.app/api/:path*`。Vercel 对外部目标 rewrite 存在平台级时长限制，社区与官方错误码 `ROUTER_EXTERNAL_TARGET_ERROR`（[Vercel 官方错误文档](https://examples.vercel.com/docs/errors/router_external_target_error) / [vercel/vercel Discussion #7721](https://github.com/vercel/vercel/discussions/7721)）均指向慢上游触发 502。

**当前错配**：
- 前端 axios timeout = **600s**（client.ts:15）；
- 后端代码注释自认"避免多 UI 用例超过网关 300s"（test_plan.py:320，batch-169）；
- 后端无任何 statement/transaction timeout（db.py:21-30，grep 0 命中）；
- 同步长任务端点仍可被直接调用（§5.2）。

**架构师判断**：三层超时（网关 ~300s / axios 600s / DB 无上限）互不知情，结果是"网关先 502、前端继续等、后端线程继续跑、DB 锁继续挂"。**修法不是调大超时，而是让长任务全部退出请求-响应路径**（§5.2 异步化），请求线程只创建任务并返回 task_id，前端轮询任务状态（配合 §3.3 方案 C 的退避轮询）。

### 5.2 异步化改造清单（哪些端点必须 async 化）

| 端点 | 位置 | 现状 | 改造 |
|------|------|------|------|
| 知识图谱提取 | `POST /knowledge/graph/extract`（knowledge.py:623，:643 调 `extract_and_build_graph_in_new_session`） | 同步 def，LLM 180s 超时（config.py:139） | 走 `ai_task` 队列或 `BackgroundTasks`，返回 task_id + `GET /ai-task/{id}` 轮询（复用需求链路现成模式 requirement.py:1100/1132） |
| 图谱演化/自动构建 | `graph/evolve`（:917）、`graph/auto-build`（:935） | 同步 def | 同上 |
| 回归预测 | `predict/regression-scope`（:1652） | 同步 def | 同上 |
| 计划执行（默认） | `POST /test-plans/{id}/execute-all`（test_plan.py:310，默认 async_mode=False:306/322） | 同步阻塞，batch-169 已留 async_mode 开关 | **默认改为 async_mode=true**；auto-execute（:371）、batch-execute（:514）加同一开关 |
| 接口批量生成 | `apitest` cases/batch-generate（apitest.py:604，:644 挂 BackgroundTasks） | 同步 def + BackgroundTasks，HTTP 仍同步等主流程 | 主流程改任务表 |
| 命名误导 | `*_in_new_session` 系列（knowledge.py:66-67、:304、:462、:1292） | 是"新 DB session"不是"后台执行"，阻塞请求线程 | 改名 + docstring 明确（P2，防后续误用） |

### 5.3 PostgreSQL 连接池 / 超时配置缺失

| 项 | 现状 | 证据 | 建议 |
|----|------|------|------|
| statement_timeout | **全仓 0 配置** | grep 0 命中；db.py:21-30 仅 pool_pre_ping/pool_size/max_overflow/pool_recycle | 连接串加 `options=-c statement_timeout=30000`（或 connect_args）；长事务端点单独放宽 |
| connect/transaction timeout | 无 | 同上 | `connect_timeout=10` 防 Supabase 抖动拖垮请求线程 |
| 连接池 | pool_size=10 / max_overflow=20 / pool_recycle=3600 | db.py:28-30 | 与 Supabase PgBouncer 事务池（:6543）匹配尚可；但**长事务占着连接不放**（§P0-3），10+20 个连接会被单计划执行耗尽 |
| 长事务与池的冲突 | `execute_all_cases` 单事务末尾 commit（test_plan_service.py:1119），期间锁 test_plan_case/test_execution 行 | 已独立复核 :1050-1119 | 见 Phase 1-3（逐用例小事务 + 任务化） |
| 无锁认领 | `api_task_worker.claim_next_task`（api_task_worker.py:46-58）SELECT→UPDATE→commit 无 FOR UPDATE | 已独立复核 :35-71，docstring 自认"依赖单 worker"（实际双 worker） | Phase 1-1（UPDATE...RETURNING 原子认领） |

### 5.4 运行时架构问题（可观测性与单实例）

- **单进程承载 9 类调度/执行机制**（main.py:110-164 + 各 ensure_*_running）：APScheduler / 轮询线程 / 守护线程 / 线程池 / 裸线程 / BackgroundTasks 并存（report-arch-backend.md §3.2）。问题：a) 任一机制崩溃无隔离；b) 调度线程被长任务阻塞时，cron 与 task_worker_poll 全部排队（report-arch-backend.md §6.2）；c) **水平扩容不安全**（双 worker 竞态跨进程放大）。
- **无结构化可观测性**：日志是 `logging` 平铺，无 request-id 贯穿、无指标端点（/metrics）、无任务心跳监控（仅 evidence 包与调度 run 有 stale 回收，`api_execution_task` 无——僵尸任务直接漏检）。
- **存储无持久卷**：`main.py:90` 注释"生产请用持久卷挂载，否则 Railway 重建会清空截图"；蓝湖证据、DSH 会话目录、嵌入缓存都是容器内文件，Railway 重建即丢。
- **依赖外部条件的功能大量 fail-closed**：DSH（config.py:273-281）、Wiki/知识入库（:183-208）、外部集成、OpenVPN——生产实测多数处于关闭态，这是安全默认，但**前端入口未随开关禁用**（DSH 任务页菜单/新建按钮可见，提交必失败，UI-11）。

---

## 6. 技术债清单（按优先级）

### P0（生产正在受伤，1-2 周内必修）

| # | 债 | 证据 | 修法（文件） |
|---|----|------|-------------|
| T1 | 双 Worker 竞态 + 僵尸任务：APScheduler 轮询（5s）与 api_task_worker 守护线程（2s）并行认领；task_worker.py:82 认领后重查 `status not in ("pending",)` 必 return → 任务永久卡 running 且无 stale 回收 | task_worker.py:53-62,81-83；api_task_worker.py:290-316；scheduler.py:364-376（已独立复核） | 删除 `task_worker._process_api_tasks` 的 API 分支（保留 UI+证据包）或删 api_task_worker 之一；修复 :82 守卫；为 api_execution_task 加 stale 回收 |
| T2 | 认领 TOCTOU：SELECT→UPDATE→commit 无锁，PG 下双线程可重复认领 | api_task_worker.py:46-58（对照 scheduler.py:34 已用 with_for_update） | `UPDATE ... SET status='running', locked_by=:wid WHERE id=(SELECT id FROM ... WHERE status='pending' ORDER BY id LIMIT 1 FOR UPDATE SKIP LOCKED) RETURNING id` |
| T3 | 计划执行单长事务：整个计划一个事务末尾 commit，数百条用例挂数分钟锁行；且在 APScheduler 线程中阻塞 cron | test_plan_service.py:924-1119（commit :1119）；scheduler.py:127 | 逐用例独立短事务（result 落库立即 commit）或整体走任务队列；从调度线程挪出 |
| T4 | 无 statement_timeout / 无 DB 超时 | db.py:21-30；全仓 grep 0 | PG 连接串加 statement_timeout/connect_timeout |
| T5 | 执行记录双轨：同一条 API 用例写 test_execution + api_execution_task_item 双向互指 → 统计分裂（通过率 9.1% vs 22.1% 实测） | test_plan_service.py:506-544,1046-1079；report_aggregator.py:38-159 | 确定唯一事实源，聚合层统一口径（§2.3-b） |

### P1（3 个月内收敛）

| # | 债 | 证据 |
|---|----|------|
| T6 | 9 套调度/执行机制并存、6 套认领队列各自为政 | report-arch-backend.md §3.2/§3.4 |
| T7 | 环依赖仅靠 lazy import 压制 + 8 处跨服务私有符号引用 | requirement_service.py:789、test_case_service.py:106、review_service.py:140 等 |
| T8 | 路由层直连 ORM + 超大路由文件（knowledge.py 68KB/1668 行；9 个 >20KB，已实测） | knowledge.py:675-693 |
| T9 | 同步长任务端点残留（知识图谱/计划执行默认/接口批量生成） | §5.2 清单 |
| T10 | 前端 cachedGet 被 signal 系统性绕过（15+ 调用点）+ 4 处 useEffect 无 cleanup | client.ts:101、environment.ts:8-11；DefectFormDialog.tsx:61-81 等 |
| T11 | 权限码双份（seed.py 目录 vs 344+ 处路由内联）无 CI 校验 | seed.py:16-192；路由 394 处命中 |
| T12 | 文档/承诺 vs 实现漂移（local-setup.md 缺失、隐藏路由、完整PRD 过时） | §4.4、report-arch-frontend.md B.1 |

### P2（6 个月内清理）

| # | 债 | 证据 |
|---|----|------|
| T13 | 软删除三套语义并存 + `is_deleted` 过滤写法三种 | report-arch-backend.md §4.4 |
| T14 | 重复端点（batch-delete×2、计划执行×3、gate×2、API 执行×2、AI 提取/生成×2） | report-arch-backend.md §5.1 |
| T15 | 反范式缓存字段 6 处多写入口 | report-arch-backend.md §4.2 |
| T16 | 死代码：`soft_delete_status`（base_service.py:107-117 零引用）、`fetchProjects`/`fetchMe`（api/auth.ts:43-44 零调用）、project/organization 页面（路由已重定向）、special/perftest 页面（路由已隐藏但维护中） | report-arch-frontend.md §A.2 P3-1 |
| T17 | 前端 5 个 >800 行超大页面（最大 AiResultModal 1424 行）+ 146 页面文件 1.6MB | report-arch-frontend.md §A.1 |
| T18 | 用例内容数据质量问题（"2、0"数字拆行，大量用例受影响） | evidence-master §4 UI-02 |
| T19 | 多态外键 `TestSchedule.job_id`、外键孤岛 8+ 处 | report-arch-backend.md §4.3 |
| T20 | 统计口径多套并存（需求覆盖率 0%/33.3%/67%、通过率两套） | evidence-master §2（与 T5 同源） |

---

## 7. 演进路线图（Phase 1/2/3）

> 原则：**先用最小成本止血（Phase 1），再收敛重复实现（Phase 2），最后才谈架构演进（Phase 3）**。每项都给出文件级落点与工作量量级。

### Phase 1 — 短期止血（0~2 个月，目标：生产数据可信、任务不再卡死）

| # | 动作 | 落点 | 量级 |
|---|------|------|------|
| 1 | 修复双 Worker 竞态 + 僵尸任务 + 认领 TOCTOU + API 任务 stale 回收 | `api_task_worker.py:35-71`（原子认领）、`task_worker.py:41-68`（删 API 分支）、`core/scheduler.py`（新增 reap_stale_api_tasks，仿 :292） | 3-5 人日 |
| 2 | 计划执行拆"逐用例小事务"，`execute-all` 默认 async_mode=true | `test_plan_service.py:924-1119`、`test_plan.py:306-337` | 3-5 人日 |
| 3 | PG 连接串加 statement_timeout/connect_timeout | `config.py` + `db.py:21-30` | 0.5 人日 |
| 4 | 统一执行记录事实源（先统一状态取值与聚合口径，双轨表合并放 Phase 2） | `report_aggregator.py`/`trace_service.py`/`dashboard_service.py` 收敛到同一聚合函数；`statistics_service` 为唯一入口 | 3-5 人日 |
| 5 | 前端请求层：修正 cachedGet signal 语义 + 4 处 useEffect cleanup + environment 竞态 | `frontend/src/api/client.ts`、DefectFormDialog/SearchTab/CaseDrawer/environment 页 | 3-5 人日 |
| 6 | 补 `docs/local-setup.md`（§4.2 步骤表 + FAQ），修正 README/手册依赖口径 | `docs/local-setup.md`、`README.md:84-97`、`测试平台使用手册.md:11,51` | 0.5-1 人日 |
| 7 | 轮询退避（dsh-tasks/uitest） | `frontend/src/pages/dsh-tasks/index.tsx:81-85`、`uitest/index.tsx:297-323` | 1-2 人日 |

**Phase 1 完成标志**：API 批量任务不再卡 running；计划批量执行不再长时间锁库；工作台/追溯/报告三处通过率一致；apitest 切 tab 无重复请求；新装机照 local-setup.md 15 分钟内跑通。

### Phase 2 — 中期收敛（3~6 个月，目标：执行引擎单轨、模块边界清晰）

| # | 动作 | 落点 | 量级 |
|---|------|------|------|
| 1 | 统一 `TaskQueue` 抽象，替换 6 套认领队列；APScheduler 只留一个 2s 分发 job | 新建 `app/core/task_queue.py`；`ai_tasks.py`/`api_task_worker.py`/`agent_queue.py`/`dsh_task_service.py`/`lanhu_evidence/worker.py` 改为继承 | 10-15 人日 |
| 2 | 执行记录双轨合并：`test_execution` 收敛为计划维度轻量索引（或反之），废弃双向互指一方；统一 4 表状态值为 `pending/running/passed/failed/skipped/cancelled` | `test_plan_service.py:506-544,1046-1079`、`api_asset.py:80-109`、`ui_test.py:27` | 5-8 人日（需迁移脚本） |
| 3 | 服务边界治理：8 处私有符号提公共 API + ruff 规则禁跨服务私有 import + 断 requirement⇄test_case 环（`validate_source_doc` 下沉独立 validator） | `test_case_service.py:106`、`review_service.py:140`、`ai_service.py:32`、`wiki/contract_extractor.py:15`、`schedule_service.py:15` 等 | 5-8 人日 |
| 4 | 同步长任务端点全部异步化（§5.2 清单 6 处） | `knowledge.py:623/917/935/1652`、`test_plan.py:306-337`、`apitest.py:604` | 5-8 人日 |
| 5 | 路由按域拆分（knowledge.py 拆 3 个、requirement/requirement_modules/wiki/apitest 各拆 2 个）+ 路由层禁 ORM | `app/api/v1/knowledge*.py` 等 | 5-10 人日 |
| 6 | 权限码单点常量 + CI 漂移校验（pytest 比对 seed 目录与路由引用集合） | 新建 `app/core/permissions.py`；`seed.py` 与 36 个路由文件机械替换 | 2-3 人日 |
| 7 | 前端 React Query 试点（轮询 3 点 + uitest/testcase 列表）→ 评估全量 | 新增依赖 `@tanstack/react-query`；`frontend/src/pages/uitest`、`dsh-tasks` | 5-8 人日 |
| 8 | 本地 Docker 一键（dev compose profile）+ local 切 alembic 迁移 + `-SeedDemoData` | `deploy/docker-compose.yml`、`start-platform-environment.ps1` | 3-5 人日 |

### Phase 3 — 长期目标（6~24 个月，目标：可水平扩容、可观测、可运营）

| # | 方向 | 具体建议 |
|---|------|---------|
| 1 | **多副本安全**：任务表加 `locked_by/heartbeat_at` 心跳；认领全部原子化；worker 数量成为配置项 | 前置是 Phase 2-1 的 TaskQueue 抽象；完成后 Railway 可横向扩到 2-3 副本 |
| 2 | **事件驱动**：任务完成事件（DB 轮询 → 进程内事件总线 → webhook/SSE 推前端），替代固定间隔轮询 | 与 Phase 2-7 React Query 的 `refetchInterval` 配合；前端轮询请求数可再降一个量级 |
| 3 | **可观测性三件套**：结构化日志（request-id 贯穿，`middleware/request_id.py`）、`/metrics`（Prometheus：任务队列深度/执行时长/DB 连接/锁等待）、慢查询日志（statement_timeout 后的 log_min_duration） | 建议引入 `structlog` + `prometheus-fastapi-instrumentator`（各 ~0 运行时成本） |
| 4 | **域拆分评估**：仅当 Phase 2 完成且团队扩容到 3+ 后端后，才评估把 `knowledge/wiki/lanhu_evidence`（25+13+13 服务文件，LLM/OCR 重）拆为独立服务 | 拆之前必须先完成 Phase 2-3 的公共 API 边界，否则拆服务 = 把环依赖变成跨服务 RPC |
| 5 | **前端架构收敛**：146 页面/1.6MB 的页面层按域整理；`AiResultModal.tsx`（1424 行）等 5 个超大型页面拆组件；删除死代码页面（project/organization/special/perftest 或恢复路由） | 与后端路由拆分同步进行，保持模块清单一致 |
| 6 | **数据治理**：87 张表补跨域 FK（`TestCase.source_doc_id`、`ApiExecutionTaskItem.case_id`、`TestPlanCase.case_id`、拆 `TestSchedule.job_id` 多态外键）；统一软删除为 `is_deleted` 全量；孤儿数据清理脚本 | 每次 release 一个域，先加 FK 校验再改删除逻辑 |

---

## 8. 结论

1. **平台的技术骨架（FastAPI 单体 + React SPA + 三云托管）是正确的**，不需要推倒重来；真正的问题是"迭代速度远超架构治理速度"——执行引擎从 1 套长成 9 套、执行记录从 1 张表长成 4 张互指表、权限码从 1 份长成 2 份，都是"能跑就行"的增量演进产物。

2. **四个最痛的架构问题按序处理**：① 任务执行可信度（P0 双 Worker/僵尸/长事务）→ ② 数据口径可信度（执行双轨 → 统计分裂）→ ③ 请求层效率（cachedGet 语义，1 个文件 2 人日）→ ④ 本地搭建/文档可复制性（local-setup.md 缺失，0.5 人日）。①②合计约 2-4 周即可让生产数据可信、任务不再卡死。

3. **对"如果重新设计"的回答是：架构决策不重做，但四个决策必须用低成本方式补回来**——单任务表队列、单一执行事实源、缓存/轮询交给成熟库、跨域引用显式化。这些不是新系统才有资格做的事，Phase 1/2 的每个条目都是对存量代码做同样的收敛，且每条都给出了文件级落点。

4. **最大的隐性风险不是技术债本身，而是文档与实现的持续漂移**：手册引用了不存在的文档（DOC-01）、声称可用已隐藏的路由（DOC-02）、完整PRD 停留在 React 18.3（DOC-03）。架构演进的前提是"文档与代码同源"——建议把"文档保鲜"纳入每个批次的 Definition of Done（AGENTS.md §3.3 已有此要求，缺的是执行）。

5. **总体评价**：从"演示态 → 真实引擎"的蜕变过程中，平台的**能力密度**已经很高（26 模块、87 张表、真实 httpx/Playwright/ffprobe 引擎、双通道 CI/CD），当前处于"能力过剩、治理不足"的阶段；按本报告 Phase 1（2 个月）执行后，可以进入可信任、可验收、可交接的状态。

---

## 附录：本报告与子报告的关系及独立修正

| 项 | 子报告口径 | 本报告独立复核结果 |
|----|-----------|-------------------|
| 数据表数 | "约 55 张" | **87 张唯一表**（递归扫描 40 个模型文件 `__tablename__` 实测），子报告低估 50%+ |
| 路由聚合 | "43 个 include_router" | **35 个** include_router 调用（router.py:9-43） |
| require_permission | "~344 处" | 394 处命中（含 import 行，量级一致） |
| 双 Worker 僵尸 | task_worker.py:82 守卫必 return | **独立确认**，且进一步指出：由于 claim 先于 _run_api_task，该路径认领的任务**必然**僵尸（非偶发） |
| 长事务 | execute_all_cases 单事务 :1119 commit | **独立确认**（读 :1050-1119，循环内 flush + 末尾 commit，含 API 双写快照） |
| cachedGet 绕过 | 3 个调用点 | **独立确认**（auth.ts:40 / environment.ts:10 / testcase.ts:60） |
| 超大型路由文件 | 9 个 >20KB | **独立确认**（实测 knowledge.py 66.8KB / requirement.py 44.1KB / requirement_modules.py 42.6KB / wiki.py 38.6KB / apitest.py 36.4KB 等 9 个） |
| 文档缺口 | local-setup.md 不存在 | **独立确认**（Test-Path=False；手册:11/:51 引用） |
