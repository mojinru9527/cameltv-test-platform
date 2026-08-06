# Batch 109 — QA 报告（邀请链接正式域名 + 生产种子演示用户开关 + 生产启用收尾）

> **QA (🔍)** | Date: 2026-08-06 | Verdict: PASS

## 测试总览

| 条件数 | 通过 | 失败 | 阻塞 |
|--------|------|------|------|
| 8（3 US + 5 门禁） | 8 | 0 | 0 |

## 可执行门禁（命令、退出码与结果）

| 门禁 | 命令 | 退出码 | 结果 |
|------|------|--------|------|
| 后端未定义符号 | `ruff check app --select F821` | 0 | All checks passed |
| 后端应用导入 | `python -c "import app.main"` | 0 | import OK |
| Alembic 单头 | `python -m alembic heads` | 0 | `20260806_batch106_project_invite (head)` 唯一 |
| 新功能测试 | `pytest test_project_invite.py test_seed_credentials.py -q` | 0 | **18 passed** |
| 后端全量回归 | `pytest -q --tb=short --ignore=tests/playwright` | 0 | **1146 passed, 3 skipped**（263.4s） |
| 批次门禁 | `scan-common-bugs.ps1` | 1* | HARD 0 / WARN 209（*既有基线持平，Batch 106 同为 209） |
| 批次门禁 | `audit-cconditions.ps1 -RequireLatestBatch` | 0 | hard errors 0 / warnings 0 |
| 前端 | 本批无前端改动 | N/A | CI 按 backend+docs 分类，前端重测试跳过（记录分类） |

## 逐条件验证

### C1: US-01 邀请链接使用前端正式域名
**变更文件**: `backend/app/core/config.py`、`backend/app/api/v1/project.py`、`backend/tests/test_project_invite.py`

| 检查项 | 结果 | 说明 |
|--------|------|------|
| `FRONTEND_URL` 配置时链接以该域名开头 | ✅ | 新用例 `test_invite_url_uses_configured_frontend_url`（https 前缀断言） |
| 未配置时回退请求域名 | ✅ | 既有 `test_owner_generates_invite` 保持 `url.startswith("http")` 通过 |
| 生产真实缺陷复现路径关闭 | ✅ | B109-1：后端 `req.base_url` 拼链接（http+404）→ 配置优先 |

### C2: US-02 生产种子演示账号开关
**变更文件**: `backend/app/core/config.py`、`backend/app/seed.py`、`backend/tests/test_seed_credentials.py`

| 检查项 | 结果 | 说明 |
|--------|------|------|
| `SEED_DEMO_USERS=false` 不创建 tester/viewer | ✅ | 新用例 `test_seed_demo_users_disabled_skips_tester_and_viewer`（admin/默认项目仍创建） |
| 默认 true 行为不变 | ✅ | 既有 seed 用例 8/8 全部通过（含幂等/生成密码只显示一次） |
| 生产校验联动 | ✅ | 新用例 `test_production_without_demo_users_does_not_require_tester_password` |
| 生产清理不复活 | ✅ | B109-2 关闭：生产库 2026-08-06 已清理并备份，部署后不再重建（待 C109-1 实测） |

### C3: US-03 生产启用回填
**变更文件**: `deploy/production-enablement-checklist.md`、`C-CONDITIONS.md`、`work-logs/evidence/batch-109/README.md`

| 检查项 | 结果 | 说明 |
|--------|------|------|
| checklist §1/§2/§6 回填 | ✅ | 备份/变量/迁移/验证/清理登记完成 |
| C104-2/C105-2/C106-1 关闭 | ✅ | Closed 表带生产实测证据；audit-cconditions 0 硬错 |
| 新条件 C109-1 | ✅ | 部署后配置 FRONTEND_URL/SEED_DEMO_USERS 并复测 |

## 缺陷列表

| # | 严重级 | 描述 | 证据 | 状态 |
|---|--------|------|------|------|
| B109-1 | P1 | 生产实测：项目邀请链接为后端域名 + http + `/register` 404 | `evidence/batch-109/README.md` §上线验证 #6 + 新单测 | ✅ 已修复（FRONTEND_URL 优先） |
| B109-2 | P2 | 生产清理后 seed 会在下次部署重建 tester/viewer 演示账号 | 新单测 + seed.py 开关 | ✅ 已修复（SEED_DEMO_USERS=false） |
| B109-3 | P3 | 运维事项：本地 production.env 密码与线上不一致 | 管理员临时密码重置（用户授权）后登录 200 | ✅ 已处理（建议用户改密并同步） |

## 发布建议

状态: **READY**（需用户一次总确认 + PR required checks 全绿；生产部署后按 C109-1 配置两个新变量）
必修复: 0   建议修复: 0

## 复盘卡

| 计划耗时 | 缺陷(P0/P1/P2/P3) | 返工次数 | 根因分类 | 下次避免 |
|----------|-------------------|----------|----------|----------|
| 4h vs ≈3.5h | 0/1/1/1 | 0 | 技术债（req.base_url 反代失真）+ 外部依赖（凭据不一致） | 生产验收把「可分享链接」完整 URL 纳入断言，不只校验 token 与入项目 |

## 技能使用

- `cameltv-agent-team` → 六部门流程与工件；
- `cameltv-bug-guard` → 编码前避坑核对（本批不涉及新增路由/网络调用/前端副作用铁律）；
- KB：本地 work-logs/PATTERNS 替代运行中知识库核查（与 Batch 106 口径一致）。
