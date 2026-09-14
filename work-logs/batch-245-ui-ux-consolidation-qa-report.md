# Batch 245 — QA 报告

> **QA (🔍)** | Date: 2026-09-14 | Verdict: PASS（本地；最终由 PR required checks + 用户总确认封口）

## 测试总览

| 条件数 | 通过 | 失败 | 阻塞 |
|--------|------|------|------|
| 1（C243-3） | 1 | 0 | 0 |

## 可执行门禁

| 检查 | 命令 | 退出码 | 结果 |
|------|------|:------:|------|
| 前端全量 | `npm test` | 0 | 164 files / 710 tests passed |
| 前端类型 | `npm run typecheck` | 0 | PASS |
| 前端 lint | `npm run lint` | 0 | PASS（`--max-warnings=0`） |
| 前端构建 | `npm run build` | 0 | PASS，Vite 产物生成 |
| 后端全量 | `python -m pytest -q` | 0 | 2677 passed / 51 skipped / 1 xfailed |
| 后端 F821 | `ruff check app/ --select F821` | 0 | PASS |
| 密码恢复定向回归 | `pytest tests/test_password_recovery_delivery.py tests/test_auth_reset_security.py -q` | 0 | 6 passed |
| G0–G2 | `pwsh scripts/git/dev-gate.ps1 -RepositoryPath (Get-Location).Path` | 2 | `PASS_WITH_WARN`；HARD=0，WARN=330；G1/G2 全绿 |
| C 条件一致性 | pwsh scripts/git/audit-cconditions.ps1 | 0 | hard errors=0，warnings=0；C243-2 Closed evidence 完整 |
| 多视口 Playwright + axe | `npx playwright test e2e/batch245-auth-home-visual.spec.ts --config=playwright.a11y.config.ts --project=chromium` | 0 | 6 passed（desktop/tablet/mobile × 首页/恢复路径） |

> WARN 330 为当前仓库既有机械扫描基线，未发现本批次新增 HARD；Phase 4 将建立 ratchet/required checks，不在本批用放宽规则掩盖。

## 逐条件验证

### C243-3：收敛 UI 入口、任务化首页、登录恢复与视觉回归

**变更文件**:
- `test-platform-v2/frontend/src/ui/index.ts`
- `test-platform-v2/frontend/src/ui/primitives/{Button,Badge,Input}.tsx`
- `test-platform-v2/frontend/src/layouts/GuestPlatformHome.tsx`
- `test-platform-v2/frontend/src/components/auth/LoginForm.tsx`
- `test-platform-v2/frontend/src/pages/{forgot-password,reset-password}/index.tsx`
- `test-platform-v2/backend/app/api/v1/auth.py`
- `test-platform-v2/backend/app/services/notify_service.py`

| 检查项 | 结果 | 说明 |
|--------|:----:|------|
| 唯一 UI 公共入口 | ✅ | 业务/测试代码直接 `@/components/ui` 导入为 0；仅 `src/ui/**` canonical 适配层保留引用 |
| 双轨回潮阻断 | ✅ | ESLint `no-restricted-imports` + `batch245-ui-entry-governance.test.ts` |
| 历史 API 兼容 | ✅ | `primary/danger/tone` 仍工作；既有 primitive 测试通过 |
| 任务优先首页 | ✅ | 4 个任务入口；模块目录默认折叠，`aria-expanded/aria-controls` 完整 |
| 登录恢复路径 | ✅ | `/forgot-password` → `/reset-password?token=` → 登录，防枚举提示通过 |
| 密码辅助 | ✅ | 显隐按钮、`aria-pressed`、Caps Lock `role=status` 通过 |
| SMTP 诚实提示 | ✅ | 未配置时不显示“已发送”；公开字段仅暴露布尔值 |
| 响应式/触控 | ✅ | 375/768/1440 无水平溢出，CTA/图标按钮达到 44px 命中区 |
| WCAG AA/axe | ✅ | 新首页和恢复路径无 wcag2a/2aa/21a/21aa violations |
| 视觉证据 | ✅ | `work-logs/evidence/batch-245/*.png` 6 张，覆盖三视口 |

## 代码实现逻辑审计

- `@/ui` 是唯一公共 barrel；canonical shadcn 实现仍在 `components/ui`，避免同时维护两套真实实现。
- `ForgotPasswordPage` 的 SMTP 状态来自 `/auth/public-access` 布尔字段，不读取或展示任何 SMTP 凭据。
- 后端只在 `frontend_url` 和用户邮箱都存在时构造完整重置链接；邮件投递进入通知线程池，不阻塞请求。
- `send_password_reset_email` 在配置不完整时返回 `False`；UI 对应显示管理员兜底，不伪造成功。
- Playwright 使用 API route stub，不依赖真实 SMTP 或生产数据；三种视口均检查横向溢出和 axe。

## 缺陷列表

| # | 严重级 | 描述 | 证据 | 状态 |
|---|:------:|------|------|------|
| 1 | P3 | 生产邮件可用性仍取决于运维配置 `SMTP_*` 与 `FRONTEND_URL` | `/auth/public-access` 返回布尔状态；页面显示管理员兜底 | 可接受（运维配置项） |
| 2 | P3 | 像素截图作为人工复核证据，不是 CI 像素基线 | `batch245-auth-home-visual.spec.ts` 目前断言 DOM/溢出/axe + 留图 | Deferred 到 Phase 4 评估 |
| 3 | P3 | `dev-gate` 仍有 330 个历史 WARN | `dev-gate.log`；HARD=0 | Phase 4 ratchet |

## 发布建议

状态: READY（本地门禁通过）
必修复: 0
建议修复: 0（P3 为后续工程治理项）

## 复盘卡（Batch 75 起强制）

| 计划耗时 | 缺陷(P0/P1/P2/P3) | 返工次数 | 根因分类 | 下次避免 |
|----------|-------------------|----------|----------|----------|
| 8h 计划 / 约 6h 实际 | 0/0/0/3 | 2 | 批量 codemod 的 EOF 格式；OpenAPI 默认字段 optional 类型 | 批量改写必须同时规范化 EOF；生成契约手工审计 `default` 字段是否导致 optional |

**技能使用**:
- `cameltv-agent-team` → Product/PM/Design/Dev/QA 工件和看板
- `cameltv-ui-conventions` → 双入口、响应式、触控和 token 走查
- `cameltv-bug-guard` → effect cleanup、错误链、无循环请求自检
- `playwright-cli` → 6 条多视口 + axe 证据
