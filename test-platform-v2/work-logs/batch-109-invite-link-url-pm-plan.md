# Batch 109 — PM Plan（邀请链接正式域名 + 生产种子演示用户开关 + 生产启用回填）

> **PM (🟨)** | Date: 2026-08-06

## 规格摘要

**原始需求**: PRD US-01/02/03。**目标时间**: 4h（含门禁与文档回填）。

## 开发任务

### [ ] Task 1: FRONTEND_URL 配置项 + 邀请链接 URL 修复
**描述**: 后端新增 `frontend_url` 配置；`create_project_invite` 用 `settings.frontend_url or req.base_url` 拼链接；补 URL 单测。
**验收标准**:
- `FRONTEND_URL` 配置时返回链接以该域名开头；
- 未配置时回退请求域名（原行为）；
- `test_project_invite.py` 新增用例通过。
**涉及文件**:
- `backend/app/core/config.py` — 新增 `frontend_url` 字段
- `backend/app/api/v1/project.py` — 链接 base 取配置优先
- `backend/tests/test_project_invite.py` — 新增 URL 用例

### [ ] Task 2: SEED_DEMO_USERS 配置项 + 种子演示账号开关
**描述**: 后端新增 `seed_demo_users` 配置；`run_seed()` 在 false 时跳过 tester/viewer 创建及其角色/成员关系；生产校验联动。
**验收标准**:
- `SEED_DEMO_USERS=false` 时启动不创建 tester/viewer；
- `true`（默认）行为与历史一致；
- `validate_security` 在 false 时不再要求 `TESTER_PASSWORD`；
- `test_seed_credentials.py` 新增用例通过。
**涉及文件**:
- `backend/app/core/config.py` — 新增 `seed_demo_users` + 校验联动
- `backend/app/seed.py` — 条件化演示账号创建
- `backend/tests/test_seed_credentials.py` — 新增用例

### [ ] Task 3: 环境模板 + 生产启用清单回填
**描述**: env 模板补两个新变量；checklist §1/§2/§6 回填本批验证与清理结果。
**验收标准**: 三个 env 模板含新变量；checklist 登记完整、无占位。
**涉及文件**:
- `config/runtime/production.env.example`
- `deploy/.env.example`
- `backend/.env.example`
- `deploy/production-enablement-checklist.md`

### [ ] Task 4: QA 硬门禁 + 回归 + 证据 + C 条件
**描述**: ruff F821、app 导入、Alembic 单头、相关 pytest、全量 pytest；evidence README；C-CONDITIONS 关闭 C104-2/C105-2/C106-1 并新增 C109-1。
**验收标准**: 门禁退出码 0；QA 报告与 Leader 判决落盘；C-CONDITIONS 关闭证据齐备。

## 质量要求

- [x] 无前端改动（响应式/无障碍不适用）
- [ ] OpenAPI 同步（本批无 API 契约变化，仅 URL 字段值语义）
- [x] 单元测试覆盖（两条新分支）
- [x] 无 console/日志泄露（不打印凭据）
