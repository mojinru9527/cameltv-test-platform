# Batch 109 证据目录 — 邀请链接正式域名 + 生产种子演示用户开关 + 生产启用收尾

## 生产上线验证（2026-08-06，C106-1 / C104-2 / C105-2）

环境：`https://test-platform.up.railway.app`（后端）/ `https://cameltv-test-platform1.vercel.app`（前端）。

| # | 验证项 | 结果 |
|---|--------|------|
| 1 | health | 200，version 2.3.0 |
| 2 | 管理员登录 | 200（admin 临时密码重置，用户授权），permissions 含 `*`，organizations 返回 |
| 3 | 注册开关 | `/register` 页面 200；无邀请码注册 400「请填写邀请码」 |
| 4 | 邀请码注册 | 成功并自动登录；个人组织自动创建 |
| 5 | 组织 | 个人组织（my_role=1）+ 团队组织创建成功 |
| 6 | 项目邀请链接 | token 注册自动入项目+组织；**发现 B109-1**：URL 为后端 http 404 → 本批修复 |
| 7 | 配额 | 第 6 个项目 / 第 6 个团队组织均 400 |
| 8 | 隔离 | 非成员 GET 他人项目 403；成员越权 PUT 403 |

验证产生的临时数据已清理（保留 admin/sportsadmin/admin1 + cameltv 项目）；清理前快照：
`F:/CamelTv-safe-backup/20260806-prod-cleanup-pre.json`。

## 本批缺陷（生产发现，代码修复）

- B109-1（P1）：项目邀请链接用 `req.base_url` 拼 URL → 后端域名 + http + `/register` 404；
  修复：`FRONTEND_URL` 配置优先，空值回退请求域名（`project.py:create_project_invite`）。
- B109-2（P2）：seed 每次部署重建 tester/viewer 演示账号，使生产验收数据清理失效；
  修复：`SEED_DEMO_USERS=false` 时跳过演示账号创建及其角色/成员关系（`seed.py:run_seed`）。

## 本地门禁（Batch 109 QA）

| 门禁 | 命令 | 退出码 | 结果 |
|------|------|--------|------|
| ruff F821 | `ruff check app --select F821` | 0 | All checks passed |
| app 导入 | `python -c "import app.main"` | 0 | import OK |
| Alembic 单头 | `python -m alembic heads` | 0 | `20260806_batch106_project_invite (head)` 唯一 |
| 模块测试 | `pytest test_project_invite.py test_seed_credentials.py -q` | 0 | 18 passed |
| 后端全量 | `pytest -q --tb=short --ignore=tests/playwright` | 0 | 1146 passed, 3 skipped（263.4s） |
| 前端 | 本批无前端改动 | N/A | CI 按 backend+docs 分类，前端重测试跳过 |
