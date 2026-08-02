---
title: "Batch 63 — Batch 57–62 回归汇总与遗留问题台账"
owner: "qa-team"
created: "2026-08-02"
last_reviewed: "2026-08-02"
status: "active"
expires: "2027-02-02"
tags: ["batch-63", "regression", "legacy-debt", "summary", "agent-team"]
related:
  - "../../C-CONDITIONS.md"
  - "batch-59-legacy-debt-issue-register.md"
  - "batch-60-issue-register.md"
  - "batch-61-issue-register.md"
  - "batch-62-operations-control-plane-qa-report.md"
---

# Batch 63 — Batch 57–62 回归汇总与遗留问题台账

> 本文档是 Batch 63「汇总问题遗留解决版本」的需求输入事实源之一。
> 数据来源：各批次 work-logs 工件、issue register、QA 报告、Leader Verdict、
> `C-CONDITIONS.md` 与 `origin/main` 合并记录（PR #84–#91）。

## 1. 版本范围与基线

| 版本 | PR | 合入时间 | 分支 | 主题 |
|---|---|---|---|---|
| Batch 57 | #84 + #85 | 2026-07-30 | `feature/batch-57-environment-targets-and-acceptance` | 固定运行环境 + Batch 56 验收内部收口 |
| Batch 58 | #86 | 2026-07-30 | `feature/batch-58-production-cloud-registration` | 生产基础设施云注册（Cloudflare/Vercel/Supabase） |
| Batch 59 | #87 | 2026-07-30 | `feature/batch-59-legacy-debt-closure` | 50–58 遗留质量问题收敛 |
| Batch 60 | #88 | 2026-08-01 | `feature/batch-60-sports-platform-production-validation` | 体育平台生产级验证与修复 |
| Batch 61 | #89 + #90 | 2026-08-01 | W1 production-safety / W2 sports R2 | 生产安全、测试可信度、体育 R2 验收 |
| Batch 62 | #91 | 2026-08-02 | `feature/batch-62-operations-control-plane` | Operations Release Control Plane MVP |

Batch 63 基线：`origin/main@9c6263f`（Batch 62 squash 合入后）。

## 2. 各版本工作内容与验收结论

### Batch 57 — 固定运行环境 + Batch 56 收口

**做了什么**
- 确立 local / production 两套固定实例模型；`/environment` 页面只管理被测系统目标，不再承担平台自身数据库切换。
- 新增 runtime profile（`config/runtime/*.env.example`）、Compose profile 隔离、fail-closed 启动器与 PID 归属校验。
- 修复环境/变量跨项目 IDOR（B57-SEC-01）；Wiki 同步覆盖率 Badge 去假态（B57-WIKI-01）。
- 知识中心 3 个 placeholder 替换为可验证实现：JSON-only LLM 客户端、附件失败显式化、真实 DOM 属性提取（B57-KNOW-01）。
- 生命周期完整性：计划/缺陷/报告/调度/通知审计显式提交；失败转缺陷真实接通；调度幂等（B57-LIFE-01/02）。
- 依赖升级：React 19.2.8 / React Router 8.3.0 / Node 22.22；`npm audit` 0 漏洞（B57-DEP-01）。
- 双端许可证审计（前端 235 实例 / 后端 Linux 111/111，B57-LIC-01）；J01–J22 原子证据盘点（B57-TRACE-01）；PC 六主题 11/11 矩阵（B57-PC-01）。

**验收结论**：`LOCAL PASS WITH EXTERNAL CONDITIONS`。G56-016 按文档对账关闭（WITH-NOTICE）；
G56-011 / G56-012 / G56-014 仍 OPEN；B56-B01～B10 外部阻塞保留。

### Batch 58 — 生产基础设施云注册

**做了什么**
- 交付云注册的配置与文档：`vercel.json`、Cloudflare DNS 记录、Supabase setup、
  production-architecture、`production.env`、注册操作单、验收文档回填。
- 明确非目标：不执行生产部署、不迁移数据、不购买付费计划、不改后端架构。

**验收结论**：`APPROVED WITH CONDITIONS`。浏览器实际注册由用户在外部完成；
C58-01～06 全部进入 OPEN/PARTIAL/UNVERIFIED 跟踪（P0/P1/P2），截至 Batch 62 仍全部未闭合。

### Batch 59 — 遗留质量收敛

**做了什么**
- 质量门禁 fail-closed：ESLint 锁定依赖 + 135 条既有 unused 显式基线、覆盖率阈值、
  a11y 确定性门禁（36/36）。
- PostgreSQL 16 并发回归从永久 skip 改为 CI 必跑（迁移后 3/3）。
- Jenkins 遗留修复（Node 22、secrets 首次生成并复用、容器内健康检查、F821、fail-fast）。
- 数据安全：Dataset 跨项目更新/参数化读取 IDOR 修复（B59-BE01）；报告 CSV/Excel
  崩溃与公式注入修复（B59-BE02）。
- 前端：AddCasesModal 旧筛选值/竞态（B59-FE01）、12 个 hooks lint（B59-FE02）、
  tablet Theme Lab WCAG 4 项（B59-FE03）、WikiDiff 单请求轮询、CaseDrawer 域选择（B59-FE04）。

**验收结论**：`LOCAL PASS WITH EXTERNAL CONDITIONS`。全量后端 900/3 skip、前端 222 全绿。
G56-014 仍 OPEN；J03/J08/J09/J15（P0）、J16（P1）未关闭；C55-5-P2 缺 E2E 凭据 READY-NOT-RUN。

### Batch 60 — 体育平台生产级验证

**做了什么**
- 建立 53 项问题台账（4 P0 / 43 P1 / 6 P2）并关闭大部分：凭据进入 AI 指令、
  流量脱敏、项目切换陈旧数据、生产保护、失败分诊路由、批量删除确认、历史交互标注、
  a11y、Runner 假健康/编码/管道死锁、审计持久化/CSV、通知假成功、Agent 假可用、
  Wiki/Skills/图谱前置条件、API 数值断言、发布包权限、非法项目 404 等。
- 本地真实闭环：R1 OpenAPI 5 paths → 5 接口资产 → 7 用例 → 计划/执行/缺陷/报告/追溯；
  UI 自动化 Run #5 = 4 pass / 0 fail / 1 skip；音视频真实 MP4 六指标。

**验收结论**：`NEEDS WORK`；production `DEFERRED`。A11 FAIL（体育自动化 7 high）。
关键未关闭：B60-P0-003（隔离复测未扩全模块）、B60-P0-004（多入口 production guard 未统一）、
B60-P1-012/013（弱断言/smoke 假绿）、B60-P1-019（五入口一致性）、B60-P2-001/002/006。

### Batch 61 — 生产安全 + 体育 R2

**做了什么（W1 #89）**
- 统一生产保护（API 直触发、UI 任务双门禁）、强制改密前端流程、项目隔离/RBAC 矩阵、
  a11y 三视口 21/21、PRD/README/CLAUDE 事实对账、仓库卫生防回归、Midscene 1.10.8 +
  `npm audit --omit=dev` 0 漏洞。

**做了什么（W2 #90）**
- 体育 API/UI R2 自动化资产：39 条用例（16 API + 23 UI）、preflight 16/16、
  production-smoke truth contract 6/6、深层脱敏与安全契约 17/17。

**验收结论**：`NOT READY`。20 个 MUST = 5 PASS / 1 FAIL / 6 BLOCKED / 8 NOT RUN。
新增 B61-P1-001：backend `ecdsa 0.19.2` high（CVE-2024-23342，CVSS 7.4）无补丁且未接受。
R2 39 条全部 BLOCKED（Test5/VPN/凭据缺失）；本地 R2 请求数 = 0。

### Batch 62 — Operations Release Control Plane MVP

**做了什么**
- 新独立项目 `deploy/release-control`：不可变 manifest（规范 SHA-256）、SQLite 持久化、
  append-only 事件哈希链、环境锁、幂等重放、test-only 状态机、production fail-closed、
  Compose/Jenkins 输入契约、schema-check CLI。
- Slice 5 只读消费端：`GET /api/v1/ops/deployments[/{id}/events]`（全局 `release:view`），
  前端 `/operations-release` 只读页（loading/error/empty/production-deferred）。

**验收结论**：`CONDITIONAL READY FOR DRAFT PR`（后合入 main）。22 核心测试 + 后端 980/3 skip +
前端 293 全绿。残余：OPS2-CORE-001/002（真实 executor 未配置、写命令 API/UI 未做）PARTIAL；
B61-P1-001 继续 FAIL；B62-C1/C2（DevOps owner、production 禁令）设为下一批条件。

## 3. 遗留问题总台账（Batch 63 输入）

### 3.1 本地可控、应在本批解决（纳入范围）

| ID | 级别 | 摘要 | 来源 |
|---|---|---|---|
| B61-P1-001 | P1 | backend `ecdsa 0.19.2` high 未接受（python-jose 引入） | Batch 61/62 |
| B60-P0-003 | P0 | 项目切换 A→B 陈旧数据/写上下文，需扩全模块复测 | Batch 60/61 |
| B60-P0-004 | P0 | 多执行入口 production guard 未统一（API 五入口/发布包回归/双向集成） | Batch 60/61 |
| B60-P1-002 | P1 | 菜单/命令面板/权限/PRD 对账（隐藏模块恢复或显式状态） | Batch 60/61 |
| B60-P1-006 | P1 | 用例批量删除动态闭环（DB/审计/失败回滚） | Batch 60/61 |
| B60-P1-008 | P1 | 发布包历史交互标注保存→重载→编辑闭环 | Batch 60/61 |
| B60-P1-009 | P1 | 多页面无权限写入口收敛 + 三身份矩阵 | Batch 60/61 |
| B60-P1-010 | P1 | API-only 能力（Excel/XMind、报告模板、Token、改密、playground、追溯下钻）产品化决策 | Batch 60/61 |
| B60-P1-017 | P1 | 全功能点正负面资产矩阵，Mock/真实证据分层 | Batch 60/61 |
| B60-P1-019 | P1 | API 五入口环境/变量/保护/结果 schema 统一 | Batch 60/61 |
| B60-P2-001 | P2 | 搜索提交态浏览器 Network 复核（testplan/report） | Batch 60/61 |
| B60-P2-002 | P2 | 移动/平板触控与小按钮全局审计 | Batch 60/61 |
| B60-P2-006 | P2 | 知识中心桌面标签/卡片密度 | Batch 60/61 |

### 3.2 遗留 C 条件（批量对账，见 PM 计划 Slice 6）

- 早期孤儿（batch-18/19/21/22/24/25v2/26KB/27/31、CP-C1/C2）：逐一复核状态，
  能本地关闭的关闭（含 TPv2-B19-C1、TPv2-B21-C2、C25v2-C2 等），其余显式豁免或升级。
- C55-3/C55-4、G56-011/012/014、C58-01～06：外部依赖，本批豁免，保留 OPEN。

### 3.3 外部阻塞（本批明确豁免，不计数为通过）

| ID | 内容 | 解除条件 |
|---|---|---|
| B60-BLK-001 | Test5 六服务/VPN/契约/账号 | 书面 VPN 窗口 + 六契约 + 最小权限账号 |
| B60-BLK-002 | AI/蓝湖/OCR 凭据 | 独立非生产凭据 + 数据范围 + 费用/隐私授权 |
| B60-BLK-003 | SMTP/Webhook/Jira/TAPD/ELK | 非生产端点 + 最小权限凭据 + 脱敏规则 |
| B60-BLK-004 | 真机性能（SoloX/ADB/tidevice） | 授权设备 + 包名 + 采集窗口 |
| B60-BLK-005 | 旧 PostgreSQL 脱敏快照 | 快照 + 来源版本 + checksum + 升级断言 |
| C58-01～06 | 云注册真实完成 | 浏览器注册 + `production.env` 真实值 + 后端托管 |
| OPS1 / B62-C1/C2 | test release 真实执行 | DevOps/DBA owner + registry/Runner/PG16/备份/Secret 引用 |

## 4. 回归基线（本批自检起点）

| 门禁 | Batch 62 实测基线 |
|---|---|
| 后端 F821 | PASS，0 项 |
| 后端全量 Pytest | 980 passed / 3 skipped / 0 failed（3 skip = PG 并发专用） |
| 前端 typecheck / build | PASS |
| 前端全量 Vitest | 77 files / 293 passed |
| release-control 核心 | 22 passed |
| 供应链 | 前端 0 漏洞；backend `ecdsa` high 未接受（本批 Slice 1 关闭） |

## 5. 结论

Batch 57–62 持续提升了平台的生产级质量、可信度与发布事实源，但存在三类债务：
（1）本地可控但未收口的 P0/P1 修复与复测（本批核心范围）；
（2）供应链与权限/导航事实漂移（本批 Slice 1/Slice 4）；
（3）大量外部阻塞项（Test5、AI/OCR、真机、旧库、云注册、DevOps 基础设施），
必须由用户/外部 owner 提供前置条件，任何本地证据不得冒充通过。
