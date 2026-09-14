# Batch 245 — Leader Verdict

> **Leader (🎯)** | Date: 2026-09-14 | Decision: 有条件通过

## 评审摘要

| 维度 | 评分 | 备注 |
|------|:----:|------|
| 实现质量 | A- | 唯一 UI 入口落地，canonical 实现未分叉；刷新/恢复链路完整 |
| 风险控制 | A- | 防枚举、SMTP 未配置兜底、token 一次性复用既有安全机制 |
| 回归覆盖 | A | 前后端全量、G0–G2、三视口 axe/溢出、截图证据 |
| 可维护性 | A- | ESLint + governance test 阻止双轨回归；README/skill 已回写 |

## 关键决策（已批准）

1. **`@/ui` 作为业务唯一入口，`components/ui` 保留 canonical 实现**：避免把 169 个文件一次性改造成另一套实现，先通过聚合与兼容适配削掉双轨。
2. **公开首页改为任务优先**：需求、接口、UI、报告四类入口先于模块目录；模块目录保留可展开浏览，不丢访客能力。
3. **登录恢复复用现有后端 token 机制**：新增前端 forgot/reset 页面；邮件发送使用 `FRONTEND_URL + /reset-password?token=`，不把 token 返回给浏览器响应。
4. **SMTP 状态公开为布尔值**：只暴露“是否具备完整发送配置”，不泄露 SMTP 主机、账号或密码；未配置时 UI 明确管理员兜底。

## 抽检通过

- ✅ `test-platform-v2/frontend/src/ui/index.ts` — canonical 聚合 + legacy adapter 边界清楚。
- ✅ `test-platform-v2/frontend/eslint.config.js` — 业务代码禁止 `@/components/ui/*` 与 `@radix-ui/*`。
- ✅ `test-platform-v2/frontend/src/layouts/GuestPlatformHome.tsx` — 4 任务入口、模块可展开、触控目标与响应式规格。
- ✅ `test-platform-v2/frontend/src/components/auth/LoginForm.tsx` — 密码显隐、Caps Lock、找回入口。
- ✅ `test-platform-v2/backend/app/api/v1/auth.py` + `notify_service.py` — 防枚举响应与异步邮件投递。
- ✅ `npm test` — 164 files / 710 tests passed，exit 0。
- ✅ `python -m pytest -q` — 2677 passed / 51 skipped / 1 xfailed，exit 0。
- ✅ `npx playwright test ...` — 6 passed（三视口 × 首页/恢复），axe/零溢出，exit 0。
- ✅ `dev-gate.ps1` — HARD=0、G1/G2 全绿；WARN=330 为既有 ratchet 基线，本批不新增阻断。
- ✅ 视觉证据 — `work-logs/evidence/batch-245/` 6 张 PNG。

## CI 首轮修复

首轮前端 required check 暴露治理测试的跨平台路径判断缺陷：Linux 下 ignore 目录使用 `/`，测试仅按 `\` 比较。已改用 `node:path.sep`，本地全量 710/710 通过；修复提交后必须重新等待 required checks，禁止复用首轮结果。

## 判决

本批实现与本地 QA 已满足 C243-3；在**用户一次总确认**后推送分支、创建 Draft PR，并等待 required checks。required checks 全绿且 `audit-ai-pr.ps1 -RequireSuccessfulChecks` 通过后，可转为 Ready 并 squash 合入 `main`。在最终审计前不得把 `C243-3` 标为 Closed。

## 下一批次 Leader 条件

本批未新增 C 条件。Phase 4 必须继续处理：

- `C243-4`：完整 Ruff/mypy、axe/Lighthouse、依赖审计纳入 required checks，禁止 `|| echo` 吞错。
- `C244-1`：Dashboard per-project 统计彻底改为 GROUP BY/一次性聚合。
- `C243-1`：Runner 单任务容器隔离、只读 rootfs 与更严格 egress policy。

## 流程回写（Batch 75 起强制）

| 发现 | 处理 | 落点 |
|------|------|------|
| 双 UI 入口没有机械门禁，文档声明与真实代码不一致 | 更新 UI 规范并加入 ESLint/治理测试 | `.claude/skills/cameltv-ui-conventions/SKILL.md`；`batch245-ui-entry-governance.test.ts` |
| 批量 import 迁移因 `Set-Content` 引入 EOF 空白行 | 统一以 UTF-8 无 BOM + 单尾换行规范重写，`git diff --check` 纳入复核 | 本批 QA 复盘卡；后续 codemod 规则 |
| OpenAPI 全量生成造成 36k 行无意义 diff | 保留原生成文件，只对新增 default 字段做最小契约 patch，再用 typecheck 验证 | `src/types/api.d.ts`；QA 复盘卡 |
| 登录恢复依赖邮件配置但原实现静默吞异常 | 改为公开 `password_reset_email_enabled`，未配置时 UI 明确管理员兜底 | PRD US-3；`test_password_recovery_delivery.py` |

## 复盘卡

| 计划耗时 | 缺陷(P0/P1/P2/P3) | 返工次数 | 根因分类 | 下次避免 |
|----------|-------------------|----------|----------|----------|
| 8h 计划 / 约 6h 实际 | 0/0/0/3 | 2 | 机械迁移与契约生成边界 | 先确认生成器幂等性；批量改写后立即跑 `git diff --check` 与全量类型检查 |

**技能使用**:
- `cameltv-agent-team` → 六部门交付与看板
- `cameltv-ui-conventions` → 组件入口、响应式和触控规范
- `cameltv-bug-guard` → React effect、错误链与测试夹具自检
- `playwright-cli` → 三视口截图、axe 与溢出证据
