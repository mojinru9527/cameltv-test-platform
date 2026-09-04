# Batch 229 — Worker Token Onboarding PM Plan
> **PM** | Date: 2026-09-04 | Status: Approved

## 规格摘要

**原始需求**：修复黑盒管理员不知道如何获得 `runner_key`/Worker Token，导致真实 Worker 注册 401。
**目标时间**：单批次完成开发、本地 QA、Draft PR 与 required checks 合入。

## 开发任务

### [x] Task 1：Worker Token 鉴权契约（45 分钟）

**描述**：先用集成测试固定正确 scope 成功、错误 scope 403、成功使用时间更新，再让 heartbeat 复用现有 API Token 哈希鉴权。
**验收标准**：无需网页登录 Cookie 或 `X-Project-Id` 即可用专用 Token 注册；普通 CI Token 不可注册。
**涉及文件**：
- `test-platform-v2/backend/tests/aitde/v34/test_worker_token_auth.py`
- `test-platform-v2/backend/app/api/v2/workflows.py`
- `test-platform-v2/backend/app/services/token_service.py`

### [x] Task 2：前端可发现生成链路（60 分钟）

**描述**：Runtime 提供按权限显示的入口；系统管理支持 Token 深链；Token 创建表单增加用途选择并生成最小 scope。
**验收标准**：管理员从 Runtime 两步内进入预选 Worker 用途的创建表单；无权限用户看见可行动说明但无创建按钮。
**涉及文件**：
- `test-platform-v2/frontend/src/pages/runtime/index.tsx`
- `test-platform-v2/frontend/src/pages/runtime/__tests__/RuntimeAdminPage.test.tsx`
- `test-platform-v2/frontend/src/pages/system/index.tsx`
- `test-platform-v2/frontend/src/pages/system/TokensTab.tsx`
- `test-platform-v2/frontend/src/pages/system/__tests__/TokensTab.test.tsx`
- `test-platform-v2/frontend/src/pages/system/tokenPurposes.ts`
- `test-platform-v2/frontend/src/pages/system/tokenPurposes.test.ts`

### [x] Task 3：一次性 Worker 配置与撤销入口（45 分钟）

**描述**：创建成功弹窗针对 Worker 用途展示可复制配置和启动命令，关闭后清空；列表把 scope 映射为中文，并明确停用/删除即撤销。
**验收标准**：秘密不持久化；复制失败有反馈；配置含当前 origin `/api/v2`；Token 管理入口可停用/删除。
**涉及文件**：
- `test-platform-v2/frontend/src/pages/system/TokensTab.tsx`
- `test-platform-v2/frontend/src/pages/system/tokenScopes.ts`
- `test-platform-v2/frontend/src/pages/system/tokenScopes.test.ts`

### [x] Task 4：Runbook 与启动器 fail-fast（30 分钟）

**描述**：Runbook 写明前端获取路径、轮换顺序和最小权限；启动器拒绝空 Token 后再拉起子进程。
**验收标准**：无 Token 退出码非零且不启动 heartbeat/gateway；文档不含任何真实凭据。
**涉及文件**：
- `test-platform-v2/deploy/aitde-runtime/README.md`
- `test-platform-v2/deploy/aitde-runtime/scripts/start-worker.sh`
- `test-platform-v2/backend/tests/aitde/v34/test_worker_heartbeat.py`

### [x] Task 5：QA、浏览器与交付（90 分钟）

**描述**：执行定向测试、双端硬门禁、全量回归、三视口浏览器关键路径、秘密扫描和 PR 审计。
**验收标准**：首轮 QA 有命令/退出码/截图证据；文件范围固定后请求一次总确认。
**涉及文件**：
- `work-logs/evidence/batch-229-worker-token-onboarding/`
- `work-logs/batch-229-worker-token-onboarding-qa-report.md`
- `work-logs/batch-229-worker-token-onboarding-leader-verdict.md`
- `work-logs/kanbans/DEV-batch-229-worker-token-onboarding.md`

## 质量要求

- [x] 后端定向 Pytest + F821 + app 导入 + Alembic 单头/revision
- [x] 前端相关 Vitest + typecheck + lint + build
- [x] 后端/前端全量回归无新增失败
- [x] `scan-common-bugs.ps1` 与 `dev-gate.ps1` 无 HARD
- [x] 1440x900、768x1024、390x844 三视口关键路径
- [x] Network 中相关 GET 每轮一次，控制台无错误
- [x] 仓库、工件、截图无真实 Token/Cookie/密码
