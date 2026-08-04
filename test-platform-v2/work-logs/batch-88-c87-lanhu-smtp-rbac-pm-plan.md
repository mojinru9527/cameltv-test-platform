# Batch 88 — PM Plan（C87-1/2/3）

> **PM (🟨)** | Date: 2026-08-05

## 规格摘要

**原始需求**: C87-1 蓝湖项目级链接证据包（截图+OCR→RAG/Wiki）；C87-2 SMTP 真实收发验证；C87-3 项目级 RBAC 全项目核验/修复（PRD §1–§2）。
**目标时间**: 3 个工作日（2026-08-05 → 08-07）；切片粒度 ≤60 分钟。
**批次模式**: full（PRD §0）。

## 开发任务

### Slice 0: 环境与凭据核验（前置，非编码）

**描述**: 在 batch-88 worktree 补齐并核验真实链路依赖：蓝湖 Cookie/登录态（C67-3 复测）、OCR 命令路径（LANHU_OCR_COMMAND 指向控制仓库 venv，需改为 worktree 可用的 python + ocr_paddle.py）、SMTP 配置落地到 backend/.env（deploy/.env 同源）、后端启动（独立 SQLite + 8044）与前端可用。
**验收标准**:
- `GET /api/v1/open/health` 200；`wiki/config` 显示 lanhu_mcp_enabled=true
- 蓝湖真实 API 抽查 200（如 `GET https://lanhuapp.com/api/project/images?...`，业务码 00000，账号脱敏记录）
- `LANHU_OCR_COMMAND` 在本 worktree 可执行且 PaddleOCR 正常（对一张截图跑出文本或给出明确错误）
- `backend/.env` 含 SMTP 五件套（host/port/user/password/from），密码不入库
**涉及文件**: `test-platform-v2/backend/.env`（gitignore）、`test-platform-v2/backend/.env.example`、`test-platform-v2/deploy/.env.example`

### Slice 1: C87-3 RBAC 权限矩阵修复（TDD）

**描述**: 扩充 `seed.py::_TESTER_ACTIONS` 为 tester 完整工作矩阵（testcase:*、testplan:*、report:list/detail/create、schedule:create/update/delete/trigger、defect:list/detail/create/update、requirement:upload/generate/import、dataset:*、review:submit/approve、mission:list/detail/create/update/log、notify:list/manage、uitest:*、avcheck:*）；保持管理域权限不授予。先写失败测试（tester 建用例 403），实现后转 200。
**验收标准**:
- 单测：tester 成员在项目内 `POST /test-cases` 200；跨项目 403；`system:user:create` 仍 403
- `run_seed()` 幂等：重复执行不产生重复 RolePermission
- 存量库重启后 tester 自动补齐权限（seed 幂等验证）
**涉及文件**: `test-platform-v2/backend/app/seed.py`、`test-platform-v2/backend/tests/test_rbac_project_roles.py`（新增）
**参考**: PRD §4 C87-3 验收；docs/engineering-standards.md

### Slice 2: C87-1 项目级蓝湖链接支持（TDD）

**描述**: 把 `_extract_lanhu_content` 的项目级 docId 自动发现逻辑抽为共享 helper（如 `resolve_doc_id_for_project_url(url, extractor)`，调 `/api/project/images`），供 `get_lanhu_pages_for_evidence` 复用：无 docId 时自动发现并追加 docId 后继续下载/发现页面。page_discovery 保持纯函数可测。
**验收标准**:
- 单测：项目级 URL（仅 tid+pid）→ mock `/api/project/images` → 返回 docId 追加后的 pages 列表；无 images 时报「项目内未发现设计文档」而非「缺少 docId」
- 原 docId 链接行为不回退（全量现有 lanhu 测试通过）
**涉及文件**: `test-platform-v2/backend/app/services/external/lanhu_provider.py`、`test-platform-v2/backend/app/services/lanhu_evidence/page_discovery.py`、`test-platform-v2/backend/tests/test_lanhu_provider.py`、`test-platform-v2/backend/tests/test_lanhu_page_discovery.py`
**参考**: PRD §5.1

### Slice 3: C87-1 真实证据包执行（Web/APP 两个链接）

**描述**: 用用户提供的 Web UI 与 APP UI 项目链接分别创建证据包任务（先经 Slice 2 能力发现文档，必要时按文档逐个建任务），跑真实截图+OCR，质量门禁通过后导入需求/RAG/Wiki；保存截图与导入结果证据。
**验收标准**:
- 每个链接至少一个成功任务（status=success 且 quality.import_ready=true），页面数>0、OCR 文本非空
- 导入产物存在：需求文档、knowledge_source（含 chunk）、wiki_raw_source；均可查询且带溯源字段
- 失败路径验证一次：无 docId 且项目空时任务 failed 且不可导入
**涉及文件**: `test-platform-v2/backend/storage/lanhu-evidence/*`（运行产物）、`test-platform-v2/work-logs/evidence/batch-88/*`
**参考**: PRD §4 C87-1 验收

### Slice 4: C87-2 SMTP 真实收发验证

**描述**: 在项目中创建 email 通知渠道（收件人=发件邮箱），触发 `plan_done`（/notify/test）与 `defect_assigned`（真实缺陷指派），验证 SMTP 250 + NotificationLog=sent；用 IMAP（同授权码）拉取收件箱确认两封邮件主题/正文，保存证据（敏感信息脱敏）。
**验收标准**:
- `/notify/test` 返回 sent=1；`defect_assigned` 事件邮件送达
- IMAP 或收件箱证据确认两封真实邮件；若 IMAP 不可用，如实标注并保留 SMTP 250 + 日志证据（不伪证）
- 反向：SMTP 关闭时邮件渠道 failed 且 webhook 不受影响（如有单测则记录）
**涉及文件**: `test-platform-v2/backend/.env`（gitignore）、`test-platform-v2/work-logs/evidence/batch-88/*`
**参考**: PRD §4 C87-2 验收；`app/services/notify_service.py`

### Slice 5: 全项目 RBAC 核验矩阵

**描述**: 枚举全部项目×成员×角色，汇总每个成员在项目内的有效权限集；对每个项目抽测 tester 建用例 200、跨项目 403；输出核验矩阵（含项目 B 回归）。如有角色权限为空的成员，标记并修复（补角色或明确豁免）。
**验收标准**:
- 核验矩阵覆盖全部项目；每个非超管成员至少一个非空项目角色
- 每个项目 tester 抽测建用例 200；跨项目 403
- 结果写入 QA 报告，无未解释的权限空洞
**涉及文件**: `test-platform-v2/work-logs/batch-88-c87-lanhu-smtp-rbac-qa-report.md`

### Slice 6: QA 硬门禁 + 回归

**描述**: 前端 `npm ci && npm run typecheck && npm run build`；后端 app 导入、`ruff check app --select F821`、Alembic 单头/revision、受影响 pytest 全绿（lanhu/rbac/smtp/notify 相关 + 全量）；`scan-common-bugs.ps1` HARD=0（无新增）；`audit-cconditions.ps1 -RequireLatestBatch` 0 硬错；WARN 基线无新增类别。
**验收标准**: 全部命令记录退出码与摘要；无新增失败（与 main 基线对比）；C87 条件证据齐备。
**涉及文件**: QA 报告 + evidence

### Slice 7: Leader 判决 + C 条件同步 + 交付

**描述**: Leader 抽检工件、判决（APPROVED 条件：一次总确认 + checks 全绿）；C87-1/2/3 在 C-CONDITIONS.md 标记 In-Progress/Closed（带 PR/commit 证据）；流程回写 + 复盘卡；看板更新；向用户展示变更摘要并执行一次总确认 → push → Draft PR → checks → 合入。
**验收标准**: 六件工件齐备、C 条件状态机正确、总确认后交付。

## 质量要求

- [x] 响应式（Desktop + Tablet）— 本批无前端 UI 改动，不适用
- [x] OpenAPI 同步 — 无新端点（复用现有），不适用
- [x] 单元测试覆盖 — Slice 1/2 强制 TDD；Slice 4 现有 smtp 测试复用
- [x] 无障碍（ARIA/键盘）— 不适用
- [x] 无 console 报错/告警 — 后端日志清理
- [x] 敏感信息（SMTP 密码/蓝湖 Cookie）仅入 gitignore 的 .env，任何工件/commit 不得含明文
