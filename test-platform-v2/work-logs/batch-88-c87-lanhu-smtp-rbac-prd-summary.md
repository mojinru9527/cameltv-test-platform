# Batch 88 — PRD Summary（C87-1 蓝湖设计源 / C87-2 SMTP 真实收发 / C87-3 项目级 RBAC）

> **Product (🟦)** | Date: 2026-08-05 | Status: Review

## 0. 批次模式判定（C75-1 强制）

```markdown
mode: full
判定理由: 本批包含新行为（证据包管线支持项目级蓝湖链接）、配置变更（SMTP 配置落地与示例同步）与行为修复（tester 角色权限矩阵扩充），按 pipeline-modes.md 属「配置/新行为」档 → 完整批次（PRD + PM + Design + Dev + QA + Leader 六件）。
```

## 1. 问题陈述

### C87-1 — 蓝湖设计源真实 ingest 缺口（J06 / G56-011 / C55-3 的 Wiki ingest 分支）

Batch 87 用真实 docx + 真实 AI 已闭环需求→用例→RAG→Trace 主链，但 Wiki 的「蓝湖设计源」分支仍缺真实证据：证据包管线 `get_lanhu_pages_for_evidence` 要求 URL 必须带 `docId`，而用户提供的链接是**项目级链接**（`/web/#/item/project/stage?tid=...&pid=...`，无 `docId`），当前直接报「缺少 docId」。需求提取链路 `_extract_lanhu_content` 已有「项目 URL → 自动发现首个文档」的能力，证据包链路未复用，导致同一能力两套行为。

用户关心点：设计稿是需求真源；设计源不进 Wiki/RAG，追溯链就断在「设计稿 ↔ 需求 ↔ 用例」。用户已提供 Web UI 与 APP UI 两个真实项目链接，本批应打通真实采集→OCR→导入闭环，而非继续等链接或伪证。

### C87-2 — SMTP 真实收件验证缺口（J11 / C55-4 / G56-012 通知分支）

定时任务完成/失败与缺陷指派通知的真实邮件收发从未验证（J11 缺口）。用户已提供 SMTP 账号（`smtp.qq.com:587`，发件 `2602997810@qq.com`，deploy/.env 中已登记），但运行中的后端 `backend/.env` 无 SMTP 配置块，发送链路实际未启用（`notify_service._dispatch_email` 在 `smtp_host` 为空时直接跳过）。「地址已提供」≠「已配置已验证」。

用户关心点：通知是异步协作闭环的最后一段；定时任务失败/缺陷指派必须真实触达责任人，不能只有平台内角标。

### C87-3 — 项目级角色权限缺口（B87-Q1）

Batch 87 QA 发现：项目 B 的 tester 成员在自己的项目里建用例返回 403「缺少权限：testcase:create」。根因定位为 **seed 权限矩阵缺口**：`seed.py::_TESTER_ACTIONS` 只给了 apitest/schedule:list/knowledge/wiki/lanhu_evidence/perftest 等少量权限，**没有** `testcase:list/detail/create/update/delete/export`、`testplan:*`、`report:*`、`defect:*`、`schedule:create/update/delete/trigger`、`requirement:*`、`dataset:*`、`review:*`、`mission:*`、`notify:*` 等 tester 日常工作所需权限。菜单可见但按钮全 403，tester 在项目内实际上干不了核心活。

用户关心点：RBAC 是项目隔离与协作的基石；权限矩阵缺项会让「成员已加入项目」成为空壳。用户要求**全部项目**核验/修复，不止项目 B。

## 2. 成功指标

| 指标 | 基线 | 目标 | 测量窗口 |
|------|------|------|---------|
| C87-1 蓝湖证据包链路 | 项目级链接直接失败（缺 docId） | Web UI 与 APP UI 两个链接均完成：页面发现→截图→OCR→质量门禁→导入需求/RAG/Wiki，Wiki Raw Source 可查询 | 本批 |
| C87-2 SMTP 真实收发 | smtp_host 为空，邮件通道跳过 | QQ SMTP 587 STARTTLS 发送 250；`plan_done` 与 `defect_assigned` 两事件真实收件（IMAP/收件箱证据），NotificationLog 记 sent | 本批 |
| C87-3 项目级 RBAC | tester 缺 `testcase:create` 等核心权限（B87-Q1） | 全项目核验矩阵完成；tester 权限矩阵补齐；各项目 tester 成员在自己项目建用例 200；跨项目仍 403 | 本批 |
| 门禁 | — | 前端 typecheck/build、后端 F821/受影响 pytest 全绿、scan-common-bugs 无新增 HARD、audit-cconditions 0 硬错 | push 前 |

## 3. 非目标（本次不做）

- **不新增依赖**：蓝湖证据包复用 lanhu-mcp + 本地 PaddleOCR；邮件复用标准库 smtplib/imaplib；无新 pip/npm 包。
- **不改 RBAC Schema**：`sys_role`/`sys_permission`/`sys_user_role`/`sys_role_permission`/`ProjectMember` 表结构与 rbac_service 计算逻辑保持稳定，只修 seed 权限矩阵与核验。管理员（admin，含 `*`）语义不变；`data_scope` 模型不变。
- **不做前端 UI 新页面**：通知配置页、角色管理页已存在；本批无前端改动（按钮权限由后端 permission_codes 下发，前端自动显示）。
- **不处理 C55-5-P2**（tablet/mobile 响应式回归）：独立 P2 验收项，非本批。
- **不处理外部阻塞项**：真机（C74-3/CP-C1/C2）、Test5 契约（C74-2/C63-2/C65-3）、AI/OCR 之外的 Test5 窗口均维持 Deferred。
- **不扩大 tester 到平台管理域**：不授予 system:*（用户/角色/审计）、project:*（项目管理）、token:manage、knowledge:approve、agent:admin、integration:sync_prod、apitest:execute_prod、uitest:trigger_prod 等管理/生产操作权限。

### C 条件纳入/豁免清单（Product 开工强制）

| C 条件 | 处理 |
|--------|------|
| C87-1 / C87-2 / C87-3 | **纳入**本批，成功指标见上 |
| C75-1 | 本 PRD 已记录 `mode: full`（§0） |
| C75-2 | Leader 判决必须含「流程回写」；SKILL 改动须同步 CHANGELOG |
| C75-3 | push 前运行 `audit-cconditions.ps1 -RequireLatestBatch`，0 硬错 |
| C76-2 / C77-1 / C79-1 / C80-1 | 本批遵守：scan-common-bugs 无新增 HARD；新增代码不引入新 WARN 类别；`SMTP 密码`等敏感值仅入 gitignore 的 .env，不入库 |
| C78-1 | 受影响模块 pytest 必须本地执行并记录退出码 |
| C81-1 | 周审计由 `run-warn-audit.ps1` 节奏负责，非本批范围（豁免） |
| C55-3 / C55-4 / G56-011 / G56-012 / G56-014 | 通过 C87-1/C87-2 部分闭环（Wiki ingest / 邮件通知）；其余分支（真机、Test5）保持 Open |
| C74-3 / CP-C1 / CP-C2 / C63-2 / C65-3 / C58-* | 外部项，豁免（Deferred） |

## 4. 用户故事 + 验收标准

- As a **测试人员（tester）**, I want to create/update test cases, plans, reports, defects and schedules inside my project, so that 我在项目内的日常测试工作不因权限矩阵缺项被 403 阻断。
  - Given 我是某项目 tester 成员（ProjectMember.role_id=tester），When 我在该项目 X-Project-Id 下 POST /test-cases，Then 返回 200 且用例落库。
  - Given 我同时是项目 A 与项目 B 成员，When 我用项目 A 的令牌访问项目 B 的用例，Then 仍返回 403（隔离不被放宽）。
  - Given 全部项目已核验，When 我列出每个项目的成员角色与有效权限，Then 每个非超管成员至少有一个项目内角色且该角色权限集非空。

- As a **平台使用者**, I want 蓝湖 Web/APP 设计源走真实证据包（截图+OCR）进入需求/RAG/Wiki，so that 设计稿与需求用例可溯源（J06/Wiki ingest 闭环）。
  - Given 我提交项目级蓝湖链接（仅 tid+pid），When 创建证据包任务，Then 系统自动发现项目内设计文档并完成页面发现（不再报「缺少 docId」）。
  - Given 证据包质量门禁通过（import_ready=true），When 执行导入，Then 生成需求文档、RAG 知识源（含 chunk）与 Wiki Raw Source，且均带 evidence_job_id/doc_id/page_id 溯源。
  - Given 任一环节失败（截图 0 页/OCR 全空/下载受限），When 任务结束，Then 状态为 failed/success_with_warnings 且禁止导入（质量门禁不被绕过）。

- As a **测试负责人/运维**, I want 定时任务完成与缺陷指派通知真实到达邮箱，so that 不依赖平台内才能获知结果（J11 闭环）。
  - Given SMTP 已配置（qq 587 STARTTLS），When 项目下配置 email 渠道并触发 `plan_done`/`defect_assigned` 通知，Then SMTP 250 接受、NotificationLog=sent、收件箱实际收到两封邮件。
  - Given SMTP 未配置或凭证错误，When 触发通知，Then 邮件渠道记录 failed 且不影响 webhook 渠道与其他主链路。

## 5. 技术考量

1. **C87-1 复用而非另造**：把 `_extract_lanhu_content` 已有的「项目 URL → `/api/project/images` 自动发现首个 docId → 追加 docId」逻辑抽成共享 helper，供 `get_lanhu_pages_for_evidence` 复用；两个入口行为一致。若项目含多份设计稿，按发现的文档逐个创建证据包任务（先发现、后建任务），不自动 fan-out。
2. **C87-2 配置落地**：`config.py` 已支持 `smtp_host/port/user/password/from/use_tls/verify_cert`；本批把 deploy/.env 的真实值同步到运行后端 `backend/.env`（gitignore，不入库），并同步 `.env.example`（tracked）作为模板。`SMTP_FROM` 使用发件邮箱（QQ 要求 From=登录邮箱），修正 deploy/.env 中疑似误填的 `pop.qq.com`。证书校验保持开启（`smtp_verify_cert=true`）。
3. **C87-3 seed 幂等补齐**：`run_seed()` 启动时执行且 `_get_or_create` 幂等 → 扩充 `_TESTER_ACTIONS` 后，存量库重启即自动补权限，无需 Alembic（无 Schema 变更）。同时提供核验手段：按项目×成员×角色汇总有效权限，输出矩阵供 QA 复核。
4. **风险**：蓝湖链接可达性依赖 Cookie/登录态（C67-3 曾实测有效，本次开工前复测）；OCR 依赖本机 PaddleOCR（LANHU_OCR_COMMAND 指向控制仓库 venv，worktree 需调整路径或复用）；QQ 邮箱 IMAP 读取依赖同一授权码（若不可用则退化为 SMTP 250 + 发送成功日志，并在 QA 报告如实标注）。

## 6. 上线计划

| 阶段 | 受众 | 成功门槛 |
|------|------|---------|
| 本批 worktree 验收（六部门） | 平台用户 | C87-1/2/3 成功指标达成 + 门禁全绿 |
| Draft PR → checks | CI | required checks 全绿 + 审计通过 |
| 合入 main 后 | 全平台 | C87 条件按证据关闭并同步 C-CONDITIONS.md |

## 7. 技能使用

- `cameltv-agent-team` → 本流水线六部门工件与看板
- `cameltv-bug-guard` → Dev 编码前避坑清单（RBAC/导入/网络调用/测试相关历史 Bug）
- `karpathy-guidelines` → Dev 编码纪律（最小改动、明确验收）
- `test-case-design` → QA 用例设计（RBAC 核验矩阵与通知事件用例）
- `cameltv-api-test` / `playwright-cli` → QA 真实 API/浏览器验证（通知发送、蓝湖证据包 UI/API）
