# Batch 146 — 视角 3：资深架构师对抗性审查报告

> **审查人**：架构师视角（batch-146 四视角审查）| 日期：2026-08-11
> **方法**：代码层静态扫描（前端 API 层 24 处重复拉取点 + 后端 38 模块关联矩阵 + 服务层依赖）+ 生产运行时 Network 捕获（Playwright CLI 14 页巡检 59 请求）+ 空白机搭建流程梳理（Windows/mac）

---

## 1. 架构总览

```
Vercel (SPA)                    Railway (FastAPI)                 外部依赖
┌─────────────────┐   /api/v1   ┌──────────────────────────┐   ┌────────────────┐
│ React 19 + Vite  │  ────────► │ app/api/v1 (38 routers)  │──►│ PostgreSQL     │
│ shadcn/Radix     │  反代      │ app/services (30+ 服务)  │   │ (Supabase 17.6)│
│ 31 路由/24 页面域 │            │ app/models (26 模型文件)  │   │ SQLite (本地)  │
└─────────────────┘            └──────────────────────────┘   ├────────────────┤
  无状态管理库                      5 套后台 Worker:              │ LLM (DeepSeek) │
  无请求缓存层                      APScheduler + ai_tasks      │ 蓝湖 (MCP)     │
  fetch hook 手写                  + api_task_worker + agent   │ Playwright     │
                                  + ui_runner + lanhu worker   │ 向量: SQLite   │
                                                              └────────────────┘
```

**技术栈判断**：整体选型合理（React 19/Vite/FastAPI/PG/SQLite 降级），无框架性错误。问题集中在**横切关注点缺失**：无统一请求缓存/去重层、无统一统计口径、后台 Worker 重复、配置来源散落。

## 2. 前后端请求冗余专项（用户点名重点，代码 + 运行时双重证据）

### 2.1 运行时证据（Playwright CLI 14 页巡检，`evidence/batch-146/architect/network-capture.json`）

| 端点 | 会话内请求数 | 触发页面 | 问题 |
|------|:---:|---------|------|
| `GET /api/v1/system/menus` | **15** | 登录+全部 14 页 | **每次路由切换全量重拉菜单**（静态权限数据，应会话级缓存） |
| `GET /api/v1/environments` | **4** | apitest×2/uitest/integration | 7 处调用点（代码）跨页重复，低频数据无缓存 |
| `GET /api/v1/dashboard/stats` | **2** | login 重定向 + workbench 挂载 | 登录跳转预拉一次、工作台再拉一次 |
| `GET /api/v1/test-cases/domains` | **2** | requirement + testcase | 元数据跨页重复 |

另：`mindmap` 单请求 `GET /test-cases?page_size=10000` 全量拉取 7879 条（最重单请求）；`integration` 挂载即拉**无分页** `/requirements` 全量 + `/test-cases?page_size=1` 计数探针。

### 2.2 代码层问题模式（扫描统计，锚点见 `pages.jsonl` 附注与前端源码）

| 模式 | 数量 | 代表锚点 | 修复方向 |
|------|:---:|---------|----------|
| A. 同端点多组件重复拉取 | 6 组/24 处 | environments×7、test-cases×6、requirements×3 | 引入 SWR/React Query 或 domain store |
| B. Tab 切换重挂载全量重拉 | 4 页/约 20 tab | apitest(4tab)、knowledge(12tab)、workbench、system | 保留 Tab 状态或 forceMount + 条件加载 |
| C. 轮询无退避 | 5 处 | usePerfWebSocket 500ms、uitest 3s、WikiDiff 2s×150、WikiTab 1.5s×60、special 1s×60 | 指数退避 + 失败上限 |
| D. 搜索逐键请求无防抖 | 2 处 | defect:37、uitest:412 | 300ms 防抖（requirement 已有先例） |
| E. 页面内重复拉取 | 4 处 | WikiTab 编译后连发两发、requirement 详情无缓存 | 合并/缓存 |
| G. 基础设施无缓存/去重 | 4 项 | `client.ts:13-63` 无 GET 缓存/无 dedup/无重试；`useApi.ts` 无 SWR；**`usePaginatedList.ts` 全项目 0 引用死代码** | 请求层统一加缓存+去重 |
| H. 跨页面数据零复用 | 系统性 | 30+ 列表页每页挂载全量重拉，无 context/store 复用 | 按域缓存（environments/menus/domains） |

**根因**：前端请求层 `client.ts` 只做了「401 跳登录」，把去重/缓存/复用全部压在调用方——每个页面手写 fetch 逻辑（`usePaginatedList` 写了但无人用），导致同一数据 N 处拉取。

## 3. 后端架构问题

| # | 问题 | 证据 | 建议 |
|---|------|------|------|
| B-1 | **5 套通过率/趋势统计实现，口径不一**（工作台 7879 vs 追溯 9424 的直接根因） | dashboard_service / report_aggregator / trace_service / test_plan_service / report_service 各写一套 | 收敛为单一统计服务 + 单一口径（计划覆盖率为锚） |
| B-2 | **API 批量任务双 Worker 竞态**：`task_worker.py:41` 无锁轮询 pending + `api_task_worker.py:35` 事务认领，同时轮询同一表 | 两文件并存，`ensure_processor_running()` 双入口 | 下线无锁旧实现，统一认领式 worker |
| B-3 | **覆盖率 3+ 口径**（需求级/模块级/计划级/项目级分散 4 处实现） | trace_service:125 / test_case_linker / report_service:447 | 统一 coverage 服务 |
| B-4 | **AI 用例生成 4 条路径**（需求 AI / 接口规则 / OpenAPI / 产物导入）无统一编排 | ai_service / api_case_generation / case_generation / artifact_service | 抽统一生成管线 |
| B-5 | **服务层环依赖**：requirement_service ↔ test_case_service 靠延迟 import 破环，任一端改顶层即崩 | requirement_service.py:16 | 抽公共 domain 层 |
| B-6 | **5 套后台 Worker 堆叠**（APScheduler + ai_tasks + api_task_worker + agent_queue + ui_runner + lanhu）无统一调度面 | main.py / scheduler.py | 统一任务队列（DB 队列已在 ai_tasks 试点） |
| B-7 | 前端 `project/my-projects` 裸 axios 绕过类型化 api 层 | project/index.tsx:6 | 归入 api 层 |
| B-8 | 执行链路双轨：计划执行（test_execution）与 API 任务（api_execution_task）互不可见，325 失败原因无处查（TP-01 P0 的架构根因） | 两套执行模型 | 统一执行模型或双向关联 |

## 4. 模块关联矩阵（前端域 ↔ 后端 ↔ 数据）

主链路（追溯主线）：`requirement_document → test_case(source_doc_id) → test_plan_case → test_execution → defect → test_report`——设计清晰，但**旁路依赖多**：defect↔integration 同步、knowledge↔test_case 图谱双向、release_bundles↔requirement_modules↔knowledge version_differ。

耦合 Hub：`notify_service`（9 router）、`audit_service`（10 router）、`production_operation_guard`（4 router）、`knowledge.ingest_service`（4 router）——审计/通知横切合理；**knowledge.ingest 反向依赖核心域**（artifact_service 延迟 import test_case_service）是演进风险点。

外部单点：PG（硬依赖）、LLM（无 key 有本地 fallback，✅）、蓝湖（旁路，✅）、Playwright（前置检查，✅）、本地 embedding（首次下载模型挂 volume，✅ 有 health 上报）。

## 5. 空白机搭建流程（Windows/mac，新人视角）

### 5.1 现状：**仓库无「全新机器搭建指南」**（最大缺口）

| 项 | 现状 |
|---|------|
| 文档 | onboarding.md 是「使用向导」非搭建指南；根 README 不存在 |
| 唯一自动化 | `start-platform-environment.ps1` **仅 Windows**、只自动化「配置生成+启动」两步 |
| 依赖冲突 | requirements.lock vs requirements.txt 两处；`npm ci` vs `npm install` 两处；**env 配置 5–6 份来源**（config/runtime/local.env / backend/.env / deploy/.env / frontend/.env.local / jenkins/.env / 根 .env） |
| 冗余 | pnpm-workspace.yaml 无锁文件配套；根 package-lock.json 空壳；`restart_services.bat`/`restart_vite.py` 孤儿脚本（硬编码 F:\CamelTv + taskkill 杀所有 node）；**tracked 空文件 `backend/=3.10`**；PostgreSQL迁移指南引用已废分支 `feature/p1-batch-a-security` |
| 可脚本化未脚本化 | submodule init、npm ci、pip install、Node 安装全手工 |

### 5.2 最小路径（推荐）vs 完整路径

| 维度 | 推荐最小路径 | 当前完整路径 |
|------|------------|-------------|
| 步骤 | **7 步 / 30–60 min** | 11+ 步 / 本地 1.5–3h、含生产数天 |
| 外部账号 | **0**（SQLite + AI 关闭） | 最多 8–9 类（DeepSeek/蓝湖/SMTP/Vercel/Railway/Supabase/Cloudflare/VPN） |
| mac 支持 | 无脚本（仅手工等价步骤） | 同左 |

### 5.3 优化建议

1. 写 `docs/local-setup.md` 固定唯一命令序列（submodule → pip install requirements.lock → npm ci → launcher -InitializeLocal），注明 Windows-only/mac 手工等价 + Node ≥22.22/Python 3.12 硬要求 + **密码存放位置**
2. launcher 加 `-InstallDeps`（自动 submodule + npm ci + venv pip）→ 最小路径压缩到 3 步
3. 删除/归档孤儿：根 package-lock.json、restart_*.bat/py、b2/diag/final-check.js、walkthrough 脚本、`backend/=3.10`、pnpm-workspace.yaml
4. env 入口统一为 `config/runtime/*.env`，backend README 与迁移指南指向它

## 6. 架构优化优先级（建议后续批次）

| 优先级 | 项 | 预期收益 |
|:---:|-----|---------|
| P0 | 前端请求层加缓存+去重（menus/environments/domains 会话缓存 + 防抖 + 轮询退避） | 请求量降 50%+（menus 15→1） |
| P0 | 统一统计口径（5 套→1 套）+ 修复工作台/追溯数字不一致 | 数据可信 |
| P0 | 双 Worker 竞态收敛 + 执行模型统一（计划执行可见失败原因） | TP-01 根因解决 |
| P1 | `usePaginatedList` 死代码清理或启用；Tab 状态保留 | 代码债下降 |
| P1 | 本地搭建引导文档 + 孤儿清理 | 新人 onboarding 30min 达标 |
| P2 | 覆盖率统一服务、AI 生成管线统一、knowledge 反向依赖治理 | 架构收敛 |

---
*配套证据：`evidence/batch-146/architect/network-capture.json`（运行时 59 请求全录）、三份 Explore 扫描输出摘要于本文*
