# Batch 147 — Agent-B 架构师视角汇总（全平台深度对抗审查）

> 审查人：Agent-B（资深架构师）| 日期：2026-08-11 | 环境：生产 https://cameltv-test-platform1.vercel.app（sportsadmin / CamelTv 体育平台）
> 方法：27 页全页加载 Network 捕获（148 请求/46 唯一端点）+ 24 页响应体量化（合计 10.58MB）+ SPA 点击导航实测（26 页/73 请求）+ 前端/后端源码静态分析（文件:行号锚点）+ 写路径 CRUD 实测（临时数据 B147TMP- 前缀，全部清理）
> 交付物：`findings-agent-b.jsonl`（25 项）、`network-agent-b.jsonl`（148 条）、`146-recheck.md`（38 项复测 + C146-1~6）

## 1. 发现清单与评分

| 维度 | 评分 | 结论 |
|------|:---:|------|
| 架构合理性（选型） | 4/5 | React19/Vite + FastAPI/SQLAlchemy + PG/SQLite 降级选型无框架性错误 |
| 横切关注点（缓存/去重/统计口径/Worker） | **1.5/5** | 无请求缓存层、5 套统计、双 Worker 竞态、执行双轨——146 架构问题全部仍在 |
| 数据可信度 | **1.5/5** | 工作台 7879/0 vs 追溯 9429/325 vs 计划 325；dashboard 执行计数 0 是新增矛盾 |
| 请求冗余 | **1.5/5** | menus×53、environments×6、domains×4、defect 搜索 14 键 14 请求、mindmap 10.1MB |
| 空白机可搭建性 | 2/5 | 无完整新机指南；7 份 env 来源；launcher 仅 Windows 且无 -InstallDeps |
| 安全/审计 | 4/5 | CSRF/CSP/生产守卫/审计日志（1877 条）完备 |

发现统计：**P0×2、P1×4、P2×13、P3×6 = 25 项**（详见 findings JSONL）

## 2. 前后端请求冗余专项（量化）

### 2.1 运行时量化（本批实测）

| 端点 | 会话请求数 | 触发场景 | 状态 |
|------|:---:|---------|------|
| `GET /system/menus` | **53**（27 页全页加载） | 每次全页加载/刷新重拉 3.6KB；SPA 点击导航 26 页仅 1 次 | 无会话缓存 |
| `GET /environments` | **6** | environment/integration/uitest 跨页重复 | 无跨页缓存 |
| `GET /test-cases/domains` | **4** | requirement/testcase 跨页 + 每次全页加载 | 无跨页缓存 |
| `GET /dashboard/stats` | **2**（+knowledge 页偶发 1） | workbench + knowledge 页异常重挂载 | 跨页重复 |
| `GET /trace/coverage` | 2 | 追溯页每次加载 | 单页重复（全页加载） |
| `GET /requirements` | **4** | integration 全量(无分页) + requirement page_size=20/50 两份 + 刷新 | 同源 3 种拉法 |
| `GET /test-cases` | **5 变体** | page_size=10000(10.1MB)/page_size=1 探针/page_size=20/taxonomy/stats | 探针与全量并存 |
| `POST /interaction-coverage/gaps` | 1×294KB | 需求页挂载即拉 | 重接口无分页 |
| `GET /defects?keyword=` | **14 键 14 请求** | 缺陷搜索逐键请求无防抖 | 无防抖 |

会话总量：全页加载 148 请求 / 46 唯一端点；响应体合计 10.58MB（其中 mindmap 10.1MB 占 95%）。

### 2.2 代码层问题模式（锚点）

| 模式 | 数量/位置 | 锚点 |
|------|----------|------|
| 请求层无缓存/去重/重试 | client.ts 仅 401 跳转 | `frontend/src/api/client.ts:18-63` |
| useApi 无 SWR；usePaginatedList 死代码 | 0 引用 | `hooks/usePaginatedList.ts` |
| Tab 切换全量重挂载 | 55 处 TabsContent 无 forceMount | apitest/knowledge/system/workbench |
| 轮询无退避 | 5 处 | `usePerfWebSocket.ts:91`(500ms)、`uitest/index.tsx:274`(3s)、`WikiDiffTab.tsx:75-94`(2s×150)、`WikiTab.tsx:98`(1.5s×60)、`special/index.tsx:128`(1s) |
| 搜索无防抖 | 2 处（defect 实测 14/14；uitest 代码） | `defect/index.tsx:37,92`、`uitest/index.tsx:412,554` |
| 写路径级联刷新 | 用例编辑 4 请求 | 保存后 stats+domains+taxonomy+list |

## 3. 模块关联性与数据流转（架构视角）

```
主链路（设计清晰）：requirement_document → test_case(source_doc_id) → test_plan_case → test_execution → defect → test_report
实测断点：
  ① 计划只装接口用例（325），功能用例 7845 零入计划 → 主链路空转
  ② 执行结果不回流功能用例（review_status 恒 draft）
  ③ 执行→缺陷/报告/通知 无自动下游（0 缺陷/0 报告/0 渠道）
  ④ 统计口径 5 套互不相认（dashboard/trace/test_plan/report_aggregator/report_service）
  ⑤ 执行双轨（test_execution vs api_execution_task）互不可见
耦合 Hub：notify_service(9 router)、audit_service(16 router)、production_operation_guard(4 router)
反向依赖风险：knowledge/artifact_service → test_case_service（:126,:168）；requirement_service ↔ test_case_service 环依赖（requirement_service.py:16 / test_case_service.py:106）
外部依赖单点：PG（硬依赖）、LLM（本地 fallback ✅）、蓝湖（旁路 ✅）、SoloX（未部署 ⛔）、发布控制数据源（未配置 ⛔）
```

## 4. 空白机搭建流程（Windows / mac，新人视角）

### 4.1 现状缺口（C146-6 未修复）

- **无全新机器搭建指南**：`docs/` 无 local-setup.md；README 仅 quick start，submodule init、Node/Python/venv、seed 密码、PG 迁移未串联。
- **env 来源 7 份**：`backend/.env(.example)`、`config/runtime/local|production.env.example`、`deploy/.env.example`、`frontend/.env.example|.env.local`。
- **依赖双份**：`requirements.lock` vs `requirements.txt`；根 `package-lock.json` 空壳；`frontend/pnpm-workspace.yaml` 无锁文件配套。
- **孤儿文件**：`restart_services.bat`、`restart_vite.py`、`b2-check.js`、`diag-check.js`、`final-check.js`、`playwright-walkthrough*.js`、`walkthrough-v3.js`、`backend/=3.10`。
- **文档陈旧引用**：PostgreSQL迁移指南:9 引用已废分支 `feature/p1-batch-a-security`。

### 4.2 推荐最小路径（Windows，约 7 步 / 30–60min）

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
# 5. 启动后端 + 前端（launcher 会起 8000/5173，AUTO_CREATE_TABLES=true 自动建表 + run_seed 种子账号）
# 6. 浏览器 http://localhost:5173 登录（密码首次生成后只显示一次，需先设置 ADMIN_PASSWORD/TESTER_PASSWORD/SECRET_KEY）
# 7. （可选）PostgreSQL：AUTO_CREATE_TABLES=false + alembic upgrade head（见 backend/README）
```

### 4.3 Windows vs mac 差异

| 项 | Windows | mac |
|----|---------|-----|
| 启动脚本 | `start-platform-environment.ps1`（唯一自动化，只覆盖配置生成+启动） | 无脚本，手工等价：uvicorn + npm run dev + env 复制 |
| venv 激活 | `.venv\Scripts\activate` | `source .venv/bin/activate` |
| 外部账号 | 0（SQLite + AI 关闭）~ 最多 8-9 类（DeepSeek/蓝湖/SMTP/Vercel/Railway/Supabase） | 同左 |
| 已知坑 | taskkill 类孤儿脚本硬编码 F:\CamelTv；端口冲突 8000/5173 | 无 launcher 等价物，最缺文档 |

### 4.4 优化建议

1. 新增 `docs/local-setup.md`：唯一命令序列 + Node/Python 硬版本 + 密码存放位置 + Windows/mac 双路径。
2. launcher 增加 `-InstallDeps`（submodule + npm ci + venv pip），最小路径压缩到 3 步。
3. 删除/归档孤儿文件与空壳 `package-lock.json`、`backend/=3.10`、`pnpm-workspace.yaml`。
4. env 统一入口 `config/runtime/*.env`，README/迁移指南同步指向；修复 PostgreSQL 指南废弃分支引用。

## 5. 架构优化优先级（下一修复批次建议）

| 优先级 | 项 | 预期收益 |
|:---:|-----|---------|
| P0 | 缺陷新建 422 修复（assignee_id 契约） | 缺陷模块主写路径恢复 |
| P0 | 执行失败根因可见 + 环境预检（C146-1） | 325 失败可归因，TP-01 关闭 |
| P1 | 统计口径收敛（5→1）+ 修复 dashboard 执行计数 0 | 数据可信（7879/9429 对账） |
| P1 | 请求层缓存/去重 + 搜索防抖 + 轮询退避 + mindmap 服务端聚合 | 请求量降 50%+，10.1MB→KB 级 |
| P1 | PlanOut 补 stats（计划列表 0/0） | 列表/详情一致 |
| P2 | 双 Worker 收敛、执行双轨关联、服务层环依赖治理 | 架构收敛 |
| P2 | 本地搭建引导 + 孤儿清理（C146-6） | 新人 onboarding 30min |

## 6. 交付文件

- `evidence/batch-147/architect/findings-agent-b.jsonl`（25 项）
- `evidence/batch-147/architect/network-agent-b.jsonl`（148 条 API 请求全录）
- `evidence/batch-147/architect/146-recheck.md`（38 项 + C146-1~6）
- 本汇总 `evidence/batch-147/architect/agent-b-summary.md`
- 截图：审查过程关键页快照存 `_review_tools/agent-b/`（临时，收尾清理）
