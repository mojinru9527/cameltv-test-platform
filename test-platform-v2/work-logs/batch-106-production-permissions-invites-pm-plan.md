# Batch 106 — PM Plan（生产启用 + 组织权限映射 + 项目邀请链接）

> **PM (🟨)** | Date: 2026-08-06

## 规格摘要

**原始需求**: 生产启用（C104-2/C105-2）+ 组织权限映射（C105-1）+ 项目邀请链接（C104-4）
（PRD US-01~04）。
**目标时间**: 5–7 小时（单窗口 Codex 执行）

## 开发任务

### [ ] Task 1: 批次工件与看板
**描述**: PRD/PM/Design 落盘 + 看板 + 三条件纳入/豁免记录。
**验收标准**: 工件无占位符；看板含切片。

### [ ] Task 2: 后端组织权限映射
**描述**: `rbac_service.permission_codes` 在按项目计算权限时，若项目有
`organization_id` 且当前用户是组织 owner/admin，追加 `project:manage/project:update/
project:delete/project:detail` 权限码；保持全局/项目角色原逻辑与超管 `*` 不变。
**验收标准**:
- `pytest tests/test_org_permission_mapping.py`：组织负责人/管理员在组织项目内
  成员管理/质量门禁 200；普通组织成员 403；项目级角色优先逻辑不回归；
- 既有 rbac/viewer/project_owner 测试不回归。
**涉及文件**:
- `backend/app/services/rbac_service.py` — org 推导权限
- `backend/tests/test_org_permission_mapping.py` — 新测试
**参考**: PRD US-02。

### [ ] Task 3: 后端项目邀请链接
**描述**: 新表 `sys_project_invite` + 迁移；`POST /projects/{id}/invites`（负责人生成，
限次/有效期）；`RegisterIn.project_invite_token`：注册时校验并消耗 token（有效 token
免除平台邀请码），事务内自动加入项目与项目所属组织（原子化）。
**验收标准**:
- `pytest tests/test_project_invite.py`：生成/列表/停用、权限 403、无效/过期/用尽 400、
  注册自动入项目+组织、重复 token 消耗拒绝；
- Alembic 单头；迁移幂等。
**涉及文件**:
- `backend/app/models/project_invite.py` — 新模型
- `backend/alembic/versions/20260806_batch106_project_invite.py` — 迁移
- `backend/app/services/invite_service.py` 或新 `project_invite_service.py` — 服务
- `backend/app/api/v1/project.py` — 邀请链接端点
- `backend/app/schemas/auth.py` / `api/v1/auth.py` — 注册集成
- `backend/app/schemas/project.py` — InviteOut
- `backend/tests/test_project_invite.py` — 新测试
**参考**: PRD US-03；Batch 104 邀请码模式。

### [ ] Task 4: 前端项目邀请链接
**描述**: 项目成员 Sheet 增加「生成邀请链接」（负责人可见）→ Dialog（次数/有效期）→
链接展示+复制；注册页支持 `?invite=TOKEN`（提示 + 自动携带 token，注册成功跳转
「我的项目」）。
**验收标准**:
- vitest 新增测试；typecheck/lint/build 全绿；
- 非负责人不显示生成按钮。
**涉及文件**:
- `frontend/src/pages/my-projects/index.tsx` — 邀请链接 UI
- `frontend/src/pages/register/index.tsx` — URL 参数处理
- `frontend/src/api/project.ts` 或现有 api — 新接口
- `frontend/src/pages/my-projects/__tests__/MyProjectsPage.test.tsx` — 扩展
- `frontend/src/pages/register/__tests__/RegisterPage.test.tsx` — 扩展
**参考**: PRD US-03；Design 规范。

### [ ] Task 5: 生产启用检查清单 + 演练证据
**描述**: 产出/更新生产启用检查清单（环境变量、迁移、配额、密钥、cookie、验证命令）；
执行 SQLite + PostgreSQL 契约演练（复用迁移测试 + PG 契约测试）并落盘证据；在凭据
可用时执行生产切换并登记，否则标记人工步骤。
**验收标准**:
- 清单文档更新；演练命令与退出码记录；
- C104-2/C105-2 关闭或转 C106 人工步骤（证据驱动）。
**涉及文件**:
- `test-platform-v2/deploy/production-enablement-checklist.md` — 新文档（或并入交付清单）
- `test-platform-v2/work-logs/evidence/batch-106/` — 证据
**参考**: PRD US-01。

### [ ] Task 6: QA 硬门禁 + 回归 + 总确认
**描述**: 全量 pytest/vitest/lint/build/ruff/迁移单头；QA 报告 + Leader 判决 +
C 条件登记；展示变更摘要做一次总确认。
**验收标准**: 硬门禁全绿；QA 含命令与退出码；Leader APPROVED。

## 质量要求

- [ ] 响应式（注册页/成员 Sheet）  - [ ] OpenAPI 契约同步（新端点）
- [ ] 单元测试覆盖（pytest/vitest）  - [ ] 无障碍（ARIA/键盘）
- [ ] 无 console 报错/告警  - [ ] 双 404 约定（C86-1）
- [ ] Token 不落日志/不硬编码；邀请链接含 secrets 随机
