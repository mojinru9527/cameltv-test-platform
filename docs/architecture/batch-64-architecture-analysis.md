---
title: "Batch 64 架构解析报告 — 测试平台现状与三仓拆分基线"
owner: "arch-team"
created: "2026-08-02"
last_reviewed: "2026-08-02"
status: "active"
expires: "2027-02-02"
tags: ["architecture", "analysis", "repo-split", "v1-retirement", "ops-platform", "batch-64"]
related:
  - "../../docs/adr/0016-three-repository-separation.md"
  - "../../docs/adr/0015-operations-release-control-plane.md"
  - "../../docs/adr/0003-frontend-backend-physical-separation.md"
  - "../../docs/production-delivery/生产环境交付清单.md"
  - "../../repo-boundaries.json"
---

# Batch 64 架构解析报告 —— 测试平台现状与三仓拆分基线

> 编制：Agent Team（Codex 执行器）| 日期：2026-08-02 | 视角：资深架构师
> 定位：这是 batch-64「基础开发」前的事实基线；后续拆仓、V1 退役、运维平台建设均以此为准绳。

## 1. 执行摘要

**结论 1 — V2 已是主力，V1 是待退役遗留。** `test-platform-v2/`（FastAPI + React）已覆盖
「需求 → AI 用例 → 用例库 → 计划 → 执行 → 报告/缺陷」主闭环及专项测试（API/UI/音视频/性能），
32 个 API 路由域、24 个前端页面域（证据：`test-platform-v2/backend/app/api/v1/`、
`test-platform-v2/frontend/src/pages/`）。`test-platform/`（V1）是 Python 单体 + 11 件 CLI 工具，
仓库地图已将其标为「维护模式」（`docs/repo-map.md` §2.2）。

**结论 2 — V1 目前不能整体移除。** 11 件 CLI 工具中，仅 api_tester / av_checker / report_dashboard /
project_init / env_check（部分）在 V2 有等价实现；**mock_server、traffic_monitor(capture)、api_diff、
data_factory、log_aggregator(部分)、load_tester(部分) 在 V2 无等价物**（详见 §4 矩阵）。
因此「V2 全量覆盖 V1」的退役条件尚未满足；web-ui/ 与 server/ 已确认被 V2 覆盖，可先退役（仍走独立审计批次）。

**结论 3 — 单仓三项目结构已到天花板。** ADR-0003 实现了「目录级物理分离」，但 `backend/` 与 `frontend/`
仍共享同一仓库、同一版本、同一 PR/CI 生命周期；无法支撑用户「某些版本只做前端、某些版本只做后端、
通过运维平台发布」的管理模型。必须升级为**三仓分离**：`cameltv-test-frontend` / `cameltv-test-backend` /
`cameltv-ops-platform`（ADR-0016）。

**结论 4 — 运维平台已有事实层，缺仓库与 Phase 2 面。** Batch 62 交付了 `deploy/release-control/`
（不可变 manifest、哈希事件链、test 环境锁）与只读 `/operations-release` 页面（ADR-0015 §7.1/7.2），
但发布 API/UI、审批、回滚编排属于 Phase 2，且 production 基础设施未就绪（DEFERRED）。

**结论 5 — 生产交付信息已基本齐备但分散。** 业务平台生产域名/网关、测试平台自身生产基础设施
（Vercel + Supabase，Batch 58）均有记录；DB/Redis/MQ 真实内网地址仍为 `10.x.x.x` 占位待运维提供。
本批已收敛为单份交付清单（见 `docs/production-delivery/生产环境交付清单.md`）。

## 2. 现状盘点

### 2.1 仓库拓扑

| 路径 | 角色 | 技术栈 | 状态 | 边界归属 |
|------|------|--------|------|---------|
| `test-platform-v2/` | 测试平台 v2 主力 | FastAPI 3.12 / React 19 + Vite 7 + shadcn/ui | 活跃 | frontend / backend 子仓 |
| `test-platform/` | 测试平台 v1 遗留 | FastAPI + Click CLI + React(AntD) | 维护模式，已弃用 | deprecated-v1 |
| `lanhu-mcp/` | 蓝湖 MCP 集成 | FastMCP + Playwright | 稳定 | backend 子仓 |
| `deploy/` | CI/CD + 运维发布控制面 | Jenkins / GitHub Actions / release-control | 稳定+演进 | ops-platform |
| `tests/` | 测试资产中心 | Markdown / Playwright / pytest | 持续积累 | shared |
| `docs/` + `work-logs/` | 架构文档 + 批次工件 | Markdown | 持续 | shared |

### 2.2 V2 架构要点

- **后端**：FastAPI + SQLAlchemy 2.0 + Alembic（SQLite WAL → PostgreSQL 升级路径，ADR-0001/0002）；
  JWT + BCrypt + RBAC 三级数据范围（ADR-0004）；API 前缀 `/api/v1`，OpenAPI 运行时契约。
- **前端**：React 19 + Vite 7 + shadcn/ui + Zustand + React Router（ADR-0005/0006）；
  httpOnly Cookie 主会话 + `X-Project-Id` 项目隔离。
- **模块面**：工作台/用例/计划/报告/缺陷/定时/追溯/需求/脑图/API 测试/UI 自动化/音视频/环境/数据集/
  通知/集成/知识/Agent/发布包/性能/主题实验室/运维发布展示（成熟度表见 `test-platform-v2/CLAUDE.md`）。
- **CI/CD**：GitHub Actions（PR 门禁 + 主干质量 + 生产冒烟 + AI 交付策略）+ Jenkins 11 阶段
  （ADR-0008）；`ai-delivery-policy.yml` 做范围分类与密钥检查。
- **生产基础设施（Batch 58）**：Vercel（前端托管）+ Supabase PostgreSQL 16（新加坡）；
  Cloudflare 延后；`production.env` gitignored。

### 2.3 生产环境事实（详见交付清单）

- 业务平台生产：`https://www.camel1.tv/`（主站）+ 5 个镜像域名 + API 网关 `https://api.cameltv.live`；
  访问需 vpn07 tun 模式；产品版本用户端 14.1.0 / 运营后台 8.2.0（蓝湖手写口径）。
- 业务平台测试：`*.elelive.cn` 内网节点（g3-test5 等 6 节点 ↔ 生产 6 域名映射）。
- 测试平台自身：Vercel 部署域名、Supabase Project Ref `myhwdpjmxdsodqgeecpn`（凭据仅存 production.env）。
- 未就绪：DB/Redis/MQ 内网地址、运营后台生产地址/只读账号（C31-3 确认不公开）、production 发布门禁。

### 2.4 质量基线

- Batch 63 证据：后端 996/3 skip、前端 315/315、release-control 22/22、pip-audit 0 漏洞、
  F821/Alembic 单头全绿（`test-platform-v2/work-logs/batch-63-regression-57-62-summary.md`）。
- 硬门禁约定：后端 `ruff check app --select F821`；前端 `npm run typecheck && npm run build`；
  全量回归按 CI 范围分类执行（AGENTS.md §3/§4）。

### 2.5 已知外部阻塞

| 阻塞 | 影响 | 状态 |
|------|------|------|
| Test5/VPN 六契约真实执行 | 生产级 API 验收 | 无授权 |
| AI/OCR/蓝湖凭据 | 需求/证据链路真实验收 | 无凭据 |
| 旧 PostgreSQL 快照 | A10 迁移证据 | 无 DBA 提供 |
| 真机性能 | 端到端性能验收 | 无设备 |
| DevOps 基础设施 | test release 真实执行 | 未就绪 |

## 3. 架构评估

### 3.1 优势（已验证）

1. **前后端契约纪律**：OpenAPI 运行时契约 + `npm run gen:api`，契约漂移可编译期拦截。
2. **数据层可演进**：SQLAlchemy + Alembic，SQLite→PostgreSQL 仅改连接串（ADR-0002 已落地）。
3. **安全基线**：JWT/BCrypt/RBAC、生产保护矩阵、无明文 Secret 入库、AI 交付策略检查。
4. **运维发布有事实层**：release manifest + 哈希事件链 + 环境锁（Batch 62），为运维平台打底。
5. **文档/ADR 体系成熟**：15 份 ADR + 仓库地图 + 六部门工件，可追溯。

### 3.2 风险与债务（附证据）

| 风险/债务 | 证据 | 影响 | 缓解（本批/后续） |
|----------|------|------|------|
| 单仓版本耦合 | `backend/` 与 `frontend/` 同仓同版本（ADR-0003 只到目录级） | 无法按前端/后端独立排期发布 | ADR-0016 三仓拆分路线 |
| V1 体积与维护负担 | `test-platform/` 112 个跟踪文件仍占仓库 | 注意力分散、端口冲突（common-pitfalls §4.3） | 覆盖矩阵 + 三档处置（§4） |
| 7 件 CLI 工具无 V2 等价 | §4 矩阵「缺失」行 | 直接删 V1 = 功能缺失（违反用户红线） | 逐项迁移/废弃决策排期 |
| API-only 能力无 UI | `docs/能力产品化决策清单.md`（Token/Playground/导入导出/追溯下钻） | 文档能力≠用户可操作能力 | C64-4 排期 batch-65+ |
| 生产发布未就绪 | ADR-0015 §4（DEFERRED） | 无法交付 production | 交付清单 + C63-2 门禁 |
| 意外跟踪垃圾文件 | 根目录 `pective pipeline — ...` 两文件 | 仓库卫生 | C64-2 独立审计删除 |
| 文档/信息分散 | 生产地址散落 5+ 文档 | 交付核对成本 | 本批收敛交付清单 |

### 3.3 架构健康度评分（5 分制）

| 维度 | 评分 | 说明 |
|------|:----:|------|
| 模块化 | 4 | 路由/服务分层清晰；V1 遗留拉低 |
| 可测试性 | 4 | 三套测试体系齐全；外部阻塞项未闭环 |
| 可部署性 | 3 | 本地/容器可部署；production 未就绪 |
| 可维护性 | 3 | 文档强；单仓耦合 + V1 债务 |
| 安全 | 4 | 基线强；Secret 管理待正式化 |
| **总体** | **3.6** | 可支撑继续开发；拆仓是下一个结构性改善 |

## 4. V1 → V2 功能覆盖矩阵与 V1 处置

### 4.1 CLI 工具矩阵（`test-platform/tools/` + `cli/tp.py`）

| # | V1 工具 | V2 等价物 | 覆盖 | 处置 |
|---|---------|-----------|:----:|------|
| 1 | env_check | `environment` 模块（环境目标/健康） | 部分 | 保留 v1 CLI 或迁移为环境探活服务（排期） |
| 2 | api_tester | `apitest`（OpenAPI 导入 + httpx 执行） | ✅ | 已迁移 |
| 3 | av_checker | `av_check`（ffprobe 真实指标） | ✅ | 已迁移 |
| 4 | report_dashboard | `report` + `dashboard` | ✅ | 已迁移 |
| 5 | project_init | `project`（多项目管理） | ✅ | 已迁移 |
| 6 | mock_server | 无（V2 无 WireMock 等价） | ❌ | 迁移候选（batch-65+）或用户批准废弃 |
| 7 | traffic_monitor(capture) | 无 | ❌ | 迁移候选或废弃（需用户决策） |
| 8 | api_diff（双环境逐字段对比） | 无（`diff_service` 是知识/版本 diff，非 API 双环境对比） | ❌ | 迁移候选（batch-65+） |
| 9 | data_factory（合成数据） | `dataset`（数据集管理，非合成器） | ❌ | 迁移候选或废弃 |
| 10 | log_aggregator | `trace` + `elk_service`（traceId 聚合） | 部分 | 保留 v1 CLI 或补齐 V2 导出 |
| 11 | load_tester | `perf`（性能采集） | 部分 | 保留或迁移 |

### 4.2 server 路由矩阵（`test-platform/server/routes/`）

| V1 路由 | V2 等价 | 覆盖 |
|---------|---------|:----:|
| api_test / ui_auto / test_cases / test_plans / report / envcheck / config / workspace / task_history / datafactory | apitest / uitest / test_case / test_plan / report / environment / project / trace / schedule / dataset | ✅ 主链路已迁移（datafactory 仅部分） |

### 4.3 web-ui 页面

V1 web-ui（AntD）功能已由 V2 的 24 个页面域覆盖（工作台/用例/计划/报告/系统/需求/API/UI/音视频等），
仓库地图已声明「Web 端功能已迁移至 v2」→ **覆盖 ✅**。

### 4.4 V1 处置决策（三档）

| 档位 | 范围 | 动作 | 触发条件 |
|------|------|------|---------|
| **A 可退役** | `test-platform/web-ui/`、`test-platform/server/` | 独立审计批次删除 | 本批矩阵确认覆盖 ✅（已满足） |
| **B 迁移候选** | mock_server / traffic_monitor / api_diff / data_factory / log_aggregator / load_tester / env_check | 每项先出 V2 方案或废弃申请 | 用户批准方案；batch-65+ 排期 |
| **C 保留** | `test-platform/cli/` + 未迁移 tools | 维持维护模式，只修不扩 | B 档全部迁移完成前不得整体删除 |

> **红线**：任何 V1 整体移除，必须以「矩阵全绿 + 用户明确批准」为前提；本批只做决策，不删代码。

## 5. 目标架构：三仓分离（ADR-0016）

### 5.1 仓库职责

| 仓库 | 内容 | 技术栈 | 发布物 |
|------|------|--------|--------|
| `cameltv-test-frontend` | 测试平台 Web UI（24 页面域 + 组件库） | React/Vite/shadcn/ui | Nginx/Vercel 静态站点 |
| `cameltv-test-backend` | FastAPI 后端 + 执行引擎 + lanhu-mcp | FastAPI/SQLAlchemy/Alembic | 后端镜像 |
| `cameltv-ops-platform` | release-control 事实层 + 发布 API/UI + Jenkins 适配 | Python/React（Phase 2 定） | 运维平台镜像 |
| `shared`（共享资产，可不独立成仓） | docs / tests / work-logs / CI 模板 | Markdown | 文档/资产 |

### 5.2 版本与发布模型

- 三仓各自 SemVer；对外产品版本仍以蓝湖「更新日志」手写版本为准（`CLAUDE.md` 关键约定）。
- 发布单元 = release manifest（前端 digest + 后端 digest + Alembic revision + QA 证据），
  一次构建只产生一个 `release_id`（ADR-0015 §4）。
- 每个版本批次可声明「前端版 / 后端版 / 运维版」组合，发布经运维平台执行，禁止手工 SSH/Compose。

### 5.3 契约与依赖

- 契约事实源 = 后端仓 `/openapi.json` → 前端仓 `npm run gen:api`。
- `lanhu-mcp`（git submodule）随后端仓；`tests/` 测试资产跨仓共享（保留在当前仓库或独立资产仓）。
- 拆分后不得出现跨仓 import；共享能力（如类型、工具脚本）进各自仓的公共包或共享目录。

### 5.4 拆分阶段路线（P0–P4）

| 阶段 | 目标 | 退出条件 |
|------|------|---------|
| **P0 边界基线（本批）** | `repo-boundaries.json` + 校验器 + 交付清单 + ADR-0016 | 校验器 `--check` 全绿；ADR 落库 |
| **P1 后端仓** | 以 `test-platform-v2/backend` + `lanhu-mcp` 切出 `cameltv-test-backend` | 后端独立构建/测试/发布；前端仍用当前仓库 |
| **P2 前端仓** | 以 `test-platform-v2/frontend` 切出 `cameltv-test-frontend` | 前后端双仓独立 PR/CI/发布；OpenAPI 契约链路验证 |
| **P3 运维平台** | `deploy/release-control` 升级为 `cameltv-ops-platform`（API + UI + 审批） | ADR-0015 Phase 2 退出条件满足；test 环境经平台发布 |
| **P4 V1 退役** | 按 §4.4 三档矩阵逐项执行 | V1 全部移除且无功能缺失 |

> 每阶段均为独立批次，走完整六部门流水线与用户 push/合入授权，禁止一次性大爆炸迁移。

## 6. 运维平台衔接（ADR-0015 Phase 2）

- 现状：release-control 事实层（manifest 校验、哈希事件链、test 锁）+ 只读 `/operations-release`。
- 目标：发布 API/UI、环境看板、审批、迁移预览、回滚、通知（`test-platform-v2/docs/operations/运维发布平台-架构与交付要求.md`）。
- 本批动作：将 `deploy/`、`ops_releases.py`、`ops_release_reader.py`、`opsReleases.ts`、
  `pages/operations-release` 在边界清单中划归 ops-platform，为拆仓预置归属。

## 7. 生产交付清单框架

单份客户交付清单见 `docs/production-delivery/生产环境交付清单.md`，覆盖：
业务平台生产域名/测试节点、测试平台自身生产基础设施（Vercel/Supabase）、服务器/数据库/中间件地址
（含待运维回填项）、账号与凭证槽位（无明文）、网络访问条件（vpn07/内网）、发布前检查清单。

## 8. 决策与 C 条件

### 本批决策（已批准）

1. **边界事实源**：`repo-boundaries.json` + `scripts/repo-split/validate_repo_boundaries.py`
   成为拆仓与 CI 分类的唯一路径归属事实源（P0 基线）。
2. **三仓目标架构**：ADR-0016 记录（替代 ADR-0003 作为交付目标，ADR-0003 保留历史语义）。
3. **V1 三档处置**：A 可退役（web-ui/server）/ B 迁移候选（7 件工具）/ C 保留——整体移除受矩阵门禁。
4. **生产交付清单**：收敛分散信息，禁止明文 Secret 入库。

### Leader 条件（详见 C-CONDITIONS.md）

- C64-1：V1 整体移除受覆盖矩阵门禁；B 档工具逐项决策后才能删。
- C64-2：独立审计删除 `pective pipeline ...` 两个误提交文件。
- C64-3：生产交付清单待运维回填真实内网地址后更新；不得伪造 production 发布证据。
- C64-4：C63-1 四项 API-only UI（Token/Playground/导入导出/追溯下钻）排期 batch-65+。

## 9. 附录：核查记录

- 历史缺陷/知识检索：本环境无知识库 MCP 工具，采用仓库内替代核查——`docs/common-pitfalls.md`
  （v1/v2 端口冲突、演示态红线、依赖同步）、`C-CONDITIONS.md`（Open 32 项）、
  `test-platform-v2/work-logs/kanbans/DEV-batch-63-legacy-issue-closure.md`（外部阻塞台账）。
- 证据锚点：模块清单 `test-platform-v2/backend/app/api/v1/router.py`；页面清单
  `test-platform-v2/frontend/src/pages/`；生产基础设施 `docs/测试平台全功能验收文档-环境链接与账号汇总.md` §5.7/5.8；
  运维控制面 ADR-0015 §7.1/7.2。
