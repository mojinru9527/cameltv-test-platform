# Batch 147 — 视角 3：资深架构师对抗性审查报告（双 AI 交叉验证）

> **审查人**：架构师视角（batch-147 四视角深度对抗审查，Agent-B 独立走查 + 主会话网络/静态双重复核）
> **日期**：2026-08-11 | **环境**：生产 `https://cameltv-test-platform1.vercel.app/`（sportsadmin / CamelTv 体育平台）
> **方法**：27 页全页加载 Network 捕获（148 请求/46 唯一端点）+ SPA 点击导航实测 + 响应体量化（10.58MB）+ 前端/后端源码静态分析（文件:行号）+ 写路径 CRUD 实测
> **证据**：`evidence/batch-147/architect/`（network-main-session.jsonl、network-agent-b.jsonl、findings-agent-b.jsonl、146-recheck.md、agent-b-summary.md）

---

## 1. 架构总览与判断

```
Vercel (SPA)                    Railway (FastAPI)                 外部依赖
┌─────────────────┐   /api/v1   ┌──────────────────────────┐   ┌────────────────┐
│ React 19 + Vite  │  ────────► │ app/api/v1 (38 routers)  │──►│ PostgreSQL     │
│ shadcn/Radix     │  反代      │ app/services (30+ 服务)  │   │ (Supabase 17.6)│
│ 31 路由/27 页面域 │            │ app/models (26 模型文件)  │   │ SQLite (本地)  │
└─────────────────┘            └──────────────────────────┘   ├────────────────┤
  无状态管理库                      5+ 套后台 Worker:              │ LLM (DeepSeek) │
  无请求缓存层                      APScheduler + api_task_worker │ 蓝湖 (MCP)     │
  fetch hook 手写                  + agent_queue + ui_runner_queue│ Playwright     │
                                  + lanhu_evidence.worker         │ 向量: SQLite   │
                                                                  └────────────────┘
```

**技术栈判断**：选型合理（React 19/Vite/FastAPI/PG/SQLite 降级），无框架性错误。**问题集中在横切关注点缺失**：无统一请求缓存/去重层、无统一统计口径、Worker 重复、执行双轨、服务层环依赖——**146 的全部架构问题在本批复测中无一修复**，且出现 2 个新 P0/P1（缺陷 422、计划列表 0/0、dashboard 执行计数 0）。

| 维度 | 评分 | 结论 |
|------|:---:|------|
| 架构合理性（选型） | 4/5 | 无框架性错误 |
| 横切关注点（缓存/去重/统计/Worker） | 1.5/5 | 146 问题全部仍在 |
| 数据可信度 | 1.5/5 | 7879 vs 9429 vs 325 三套数字并存 |
| 请求冗余 | 1.5/5 | menus×53、mindmap 10.1MB、搜索无防抖 |
| 空白机可搭建性 | 2/5 | 无 local-setup.md；launcher 仅 Windows |
| 安全/审计 | 4/5 | CSRF/CSP/生产守卫/审计日志（1877 条）完备 |

## 2. 前后端请求冗余专项（用户点名重点，运行时 + 代码双重证据）

### 2.1 运行时量化（主会话 + Agent-B 双录）

| 端点 | 请求数 | 触发场景 | 状态 |
|------|:---:|---------|------|
| `GET /api/v1/system/menus` | **53**（Agent-B 全页加载）/ **28**（主会话遍历） | 每次全页加载/刷新重拉 3.6KB；SPA 点击导航 26 页仅 1 次（MainLayout 单挂载） | 无会话缓存，146 ×15 → 现 ×53 恶化 |
| `GET /api/v1/environments` | 6 | environment/integration/uitest 跨页重复 | 无跨页缓存 |
| `GET /api/v1/test-cases/domains` | 4 | requirement/testcase 跨页 | 无跨页缓存 |
| `GET /api/v1/dashboard/stats` | 2（+knowledge 页偶发 1） | workbench + knowledge 异常重挂载 | 跨页重复 |
| `GET /api/v1/trace/coverage` | 2 | 追溯页每次加载 | 单页重复 |
| `GET /api/v1/requirements` | 4 | integration 全量(无分页) + requirement 两种 page_size + 刷新 | 同源 3 种拉法 |
| `GET /api/v1/test-cases` | 5 变体 | `page_size=10000`（**10.1MB**）+ `page_size=1` 探针 + 20 + taxonomy + stats | 探针与全量并存 |
| `POST /interaction-coverage/gaps` | 1 × 294KB | 需求页挂载即拉 | 重接口无分页 |
| `GET /defects?keyword=` | **14 键 14 请求** | 缺陷搜索逐键请求无防抖 | 无防抖 |

会话总量：全页加载 148 请求/46 唯一端点；响应体合计 **10.58MB（mindmap 占 95%）**。优化后预计请求量降 50%+、传输降 95%。

### 2.2 代码层问题模式（文件:行号锚点）

| 模式 | 数量/位置 | 锚点 | 修复方向 |
|------|----------|------|----------|
| A. 请求层无缓存/去重/重试 | client.ts 仅 401 跳转 | `frontend/src/api/client.ts:18-63` | 会话级缓存 + 去重（menus/environments/domains）或引入 React Query/SWR |
| B. useApi 无 SWR；usePaginatedList 死代码 | 0 引用 | `hooks/usePaginatedList.ts`（全项目无引用） | 收敛为统一列表 hook 或删除 |
| C. Tab 切换全量重挂载 | 55 处 TabsContent 无 forceMount | apitest/knowledge/system/workbench | forceMount + 条件加载或保留状态 |
| D. 轮询无退避 | 5 处 | `usePerfWebSocket.ts:91`(500ms)、`uitest/index.tsx:274`(3s)、`WikiDiffTab.tsx:75-94`(2s×150)、`WikiTab.tsx:98`(1.5s×60)、`special/index.tsx:128`(1s) | 指数退避 + 失败上限 |
| E. 搜索逐键请求无防抖 | 2 处（defect 实测 14 键 14 请求；uitest 代码） | `defect/index.tsx:37,92`、`uitest/index.tsx:412,554` | 300ms 防抖 |
| F. 写路径级联刷新 | 用例编辑 4 请求 | 保存后 stats+domains+taxonomy+list | 局部更新 + 依赖失效 |
| G. mindmap 全量拉取 | 单请求 10,591,245 字节 | `mindmap/index.tsx:35` page_size=10000 | 服务端 taxonomy 聚合 + 懒加载 |
| H. integration 无分页全量 | `/requirements` 全量 + `page_size=1` 计数探针 | `integration/index.tsx` | 去探针 + 服务端分页 |

## 3. 后端架构问题（146 复测 + 新发现）

| # | 问题 | 证据 | 建议 |
|---|------|------|------|
| B-1 | **统计口径 5+ 套，运行时三处矛盾**：工作台 7879/执行 0 vs 追溯 9429/已执行 325 vs 计划详情 325 全失败；`trace_service.py:15` 未过滤 `is_deleted`（9424→9429 软删累积）；dashboard `execution_total=0` 与 `test_execution` 表 325 条矛盾（新恶化） | dashboard_service.py:59 / trace_service.py:15 / test_plan_service.py:358 / report_service.py:447 / report_aggregator.py:13 | 收敛单一统计服务 + trace 补 is_deleted + 修复 dashboard 执行计数 |
| B-2 | **缺陷新建 422（新 P0）**：前后端契约不一致 | `schemas/defect.py:10-19` assignee_id int 非 Optional vs 前端默认 null | assignee_id 改 Optional[int]=None 或前端 null→0 |
| B-3 | **计划列表进度恒 0/0（新 P1）**：后端已算 stats 但 `PlanOut` schema 未声明被 Pydantic 丢弃 | `test_plan_service.list_plans` + `schemas/test_plan.PlanOut` | PlanOut 补 stats 字段 |
| B-4 | **双 Worker 竞态**：APScheduler `task_worker`（5s 轮询）与 `api_task_worker` 同时认领 ApiExecutionTask pending，无互斥 | scheduler.py:259-265 / api_task_worker.py:244 | 下线无锁旧实现，统一认领式 worker |
| B-5 | **执行链路双轨**：计划执行（test_execution）与 API 任务（api_execution_task）互不可见 | 两套执行模型 | 统一执行模型或双向关联 |
| B-6 | **5+ 套后台 Worker 堆叠**：scheduler + api_task_worker + agent_queue + ui_runner_queue + lanhu_evidence.worker | main.py:154-163 / scheduler.py / api_task_worker.py | 统一任务队列 |
| B-7 | **服务层环依赖**：requirement_service ↔ test_case_service 延迟 import 破环；artifact_service → test_case_service 反向依赖 | requirement_service.py:16 / test_case_service.py:106 / artifact_service.py:126 | 抽公共 domain 层 |
| B-8 | **AI 用例生成 4 条路径无统一编排** | ai_service / api_case_generation / case_generation / artifact_service | 抽统一生成管线 |
| B-9 | **知识图谱 graph_evolve 后端报错**：SQLAlchemy `"Neither 'count' object nor 'Comparator' object has an attribute 'where'"`，功能不可用 | 审计日志 2026-08-09 | 修复查询 + 单测 |

## 4. 模块关联矩阵与数据流转（架构视角）

```
主链路（设计清晰）：requirement_document → test_case(source_doc_id) → test_plan_case → test_execution → defect → test_report
实测断点：
  ① 计划只装接口用例（325），功能用例 7845 零入计划 → 主链路空转
  ② 执行结果不回流功能用例（review_status 恒 draft）
  ③ 执行→缺陷/报告/通知 无自动下游（0 缺陷/0 报告/0 渠道）
  ④ 统计口径 5 套互不相认（dashboard/trace/test_plan/report_aggregator/report_service）
  ⑤ 执行双轨（test_execution vs api_execution_task）互不可见
耦合 Hub：notify_service(9 router)、audit_service(16 router)、production_operation_guard(4 router)
反向依赖风险：knowledge/artifact_service → test_case_service；requirement_service ↔ test_case_service 环
外部依赖单点：PG（硬依赖）、LLM（本地 fallback ✅）、蓝湖（旁路 ✅）、SoloX（未部署 ⛔）、发布控制数据源（未配置 ⛔）
```

## 5. 空白机搭建流程（Windows/mac，用户点名重点）

### 5.1 现状缺口（C146-6 未修复）

- **无 `docs/local-setup.md` 完整新机指南**；README 仅 quick start，submodule init / Node/Python 版本 / venv / seed 密码 / PG 迁移未串联。
- **env 来源 7 份**：`backend/.env(.example)`、`config/runtime/local|production.env.example`、`deploy/.env.example`、`frontend/.env.example|.env.local`——入口混乱。
- **依赖双份**：`requirements.lock` vs `requirements.txt`；根 `package-lock.json` 空壳；`frontend/pnpm-workspace.yaml` 无锁文件配套。
- **孤儿文件**：`restart_services.bat`、`restart_vite.py`、`b2-check.js`、`diag-check.js`、`final-check.js`、`playwright-walkthrough*.js`、`walkthrough-v3.js`、`backend/=3.10`。
- **陈旧引用**：PostgreSQL 迁移指南引用已废分支 `feature/p1-batch-a-security`。

### 5.2 最小路径（Windows，约 7 步 / 30–60min）

```powershell
# 0. 前置：Git + Node.js ≥ 22.22 + Python 3.12（Windows 勾选 PATH；mac 用 brew）
# 1. 克隆 + 子模块（lanhu-mcp 是后端依赖，必须 init）
git clone <repo>; cd CamelTv; git submodule update --init --recursive
# 2. 后端依赖（用 requirements.lock 固定版本）
cd test-platform-v2/backend; python -m venv .venv; .venv\Scripts\activate  # mac: source .venv/bin/activate
pip install -r requirements.lock
# 3. 前端依赖
cd ..\frontend; npm ci
# 4. 本地配置（自动生成受忽略的 config/runtime/local.env + 固定本地凭据）
cd ..\..; pwsh scripts/start-platform-environment.ps1 -Target local -Action start -InitializeLocal
# 5. 启动（launcher 起 8000/5173，AUTO_CREATE_TABLES=true 自动建表 + run_seed 种子账号）
# 6. 浏览器 http://localhost:5173 登录（密码首次生成后只显示一次；建议先设 ADMIN_PASSWORD/TESTER_PASSWORD/SECRET_KEY）
# 7. （可选）PostgreSQL：AUTO_CREATE_TABLES=false + alembic upgrade head
```

### 5.3 Windows vs mac 差异

| 项 | Windows | mac |
|----|---------|-----|
| 启动脚本 | `start-platform-environment.ps1`（唯一自动化） | 无脚本等价物，手工 uvicorn + npm run dev + env 复制 |
| venv 激活 | `.venv\Scripts\activate` | `source .venv/bin/activate` |
| 外部账号 | 0（SQLite+AI 关闭）~ 最多 8-9 类（DeepSeek/蓝湖/SMTP/Vercel/Railway/Supabase） | 同左 |
| 已知坑 | 孤儿脚本硬编码 F:\CamelTv；端口冲突 8000/5173 | 最缺文档 |

### 5.4 优化建议

1. 新增 `docs/local-setup.md`：唯一命令序列 + Node/Python 硬版本 + 密码存放位置 + Windows/mac 双路径。
2. launcher 增加 `-InstallDeps`（submodule + npm ci + venv pip），最小路径压缩到 3 步。
3. 删除/归档孤儿文件与空壳 `package-lock.json`、`backend/=3.10`、`pnpm-workspace.yaml`。
4. env 统一入口 `config/runtime/*.env`，README/迁移指南同步指向；修复废弃分支引用。

## 6. 架构优化优先级（下一修复批次建议）

| 优先级 | 项 | 预期收益 |
|:---:|-----|---------|
| P0 | 缺陷新建 422 修复（assignee_id 契约） | 缺陷模块主写路径恢复 |
| P0 | 执行失败根因可见 + 环境预检（C146-1） | 325 失败可归因，TP-01 关闭 |
| P1 | 统计口径收敛（5→1）+ 修复 dashboard 执行计数 0 + trace is_deleted | 数据可信（7879/9429 对账） |
| P1 | 请求层缓存/去重 + 搜索防抖 + 轮询退避 + mindmap 服务端聚合 | 请求量降 50%+，10.1MB→KB 级 |
| P1 | PlanOut 补 stats（计划列表 0/0） | 列表/详情一致 |
| P2 | 双 Worker 收敛、执行双轨关联、服务层环依赖治理 | 架构收敛 |
| P2 | 本地搭建引导 + 孤儿清理（C146-6） | 新人 onboarding 30min |

## 7. C146-1~6 状态（本批复测结论）

| 条件 | 优先级 | 状态 | 复测说明 |
|------|:---:|:---:|---------|
| C146-1 | P0 | **未修复** | 数据已存 actual_result（error/error_type/status_code），UI 未暴露；无环境预检 |
| C146-2 | P1 | **未修复（恶化）** | 7879/7880/9429 三数字并存；dashboard 执行计数 0 vs 实际 325 |
| C146-3 | P1 | **未修复（恶化）** | menus 全页加载 ×53；defect 搜索 14 键 14 请求；mindmap 10.1MB |
| C146-4 | P1 | **未修复** | 使用手册仍 v2.6/2026-07-15；8+ 模块未入文档 |
| C146-5 | P2 | **未修复** | 三执行按钮仍在；手动录入默认「通过」 |
| C146-6 | P2 | **未修复** | 无 local-setup.md；launcher 无 -InstallDeps；孤儿文件仍在 |

---
*配套证据：`evidence/batch-147/architect/`（network 双录 + findings-agent-b.jsonl 25 项 + 146-recheck.md 38 项逐条）*
