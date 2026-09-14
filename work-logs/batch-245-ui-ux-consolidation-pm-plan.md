# Batch 245 — PM Plan

> **PM (🟨)** | Date: 2026-09-14 | Batch mode: full

## 规格摘要

**原始需求**: 收敛两套 UI 组件体系；按任务入口重做公开首页；补齐登录恢复路径；保留视觉回归。
**目标时间**: 1 个完整批次，优先完成可合并的最小闭环。

## 开发任务

### [ ] Task 1: 建立唯一 `@/ui` 公共出口
**描述**: 扩展 `src/ui/index.ts`，聚合 canonical `components/ui` 导出；将历史 primitive 改为兼容适配；批量把业务/测试文件的 `@/components/ui/*` 导入迁移到 `@/ui`。
**验收标准**:
- 迁移后源码仅 `src/ui/**` 可导入 canonical 实现。
- 现有 `primary/danger/tone` 调用不破坏。
- ESLint 禁止新增 `@/components/ui/*` 和直接 Radix 导入。
**涉及文件**:
- `test-platform-v2/frontend/src/ui/index.ts` — 公共 barrel
- `test-platform-v2/frontend/src/ui/primitives/*` — canonical 适配
- `test-platform-v2/frontend/src/pages/**`、`layouts/**`、`components/**` — 导入入口迁移
- `test-platform-v2/frontend/eslint.config.js` — 阻止双轨回潮
**参考**: PRD §4 US-2

### [ ] Task 2: 任务优先公开首页
**描述**: 在首页加入 4 个任务入口；完整模块树收进“浏览全部模块”展开区；保留访客模块预览能力。
**验收标准**:
- 4 个入口对未登录用户触发登录门禁。
- 展开区有 `aria-expanded` 和键盘操作。
- 375/768/1440 无水平溢出。
**涉及文件**:
- `test-platform-v2/frontend/src/layouts/GuestPlatformHome.tsx`
- `test-platform-v2/frontend/src/layouts/__tests__/GuestPlatformHome.test.tsx`
**参考**: PRD §4 US-1、US-5

### [ ] Task 3: 登录辅助与密码恢复页面
**描述**: 增加密码显隐/Caps Lock；新增 forgot/reset 页面、路由和 typed API；后端发送重置邮件并公开布尔配置。
**验收标准**:
- 登录页可进入 `/forgot-password`；重置页可消费 `?token=`。
- 未配置 SMTP 不伪造“邮件已发送”的事实。
- 重置成功后回登录页。
**涉及文件**:
- `frontend/src/components/auth/LoginForm.tsx`
- `frontend/src/pages/forgot-password/index.tsx`
- `frontend/src/pages/reset-password/index.tsx`
- `frontend/src/api/auth.ts`、`router/index.tsx`
- `backend/app/api/v1/auth.py`、`schemas/auth.py`、`services/notify_service.py`
**参考**: PRD §4 US-3、US-4

### [ ] Task 4: 视觉/可访问性/治理测试
**描述**: 补充组件入口治理测试、登录恢复单测、Playwright 多视口截图和 axe 检查。
**验收标准**:
- `npm run typecheck`、`npm run lint`、`npm run build` 通过。
- 相关 Vitest 与全量 Vitest 通过。
- Playwright 截图写入 `work-logs/evidence/batch-245/`，无 console error。
**涉及文件**:
- `frontend/src/ui/themes/__tests__/batch245-ui-entry-governance.test.ts`
- `frontend/src/components/auth/__tests__/*`
- `frontend/e2e/batch245-auth-home-visual.spec.ts`
**参考**: PRD §2、§4 US-5

## 质量要求
- [x] 响应式 Desktop + Tablet + Mobile
- [x] OpenAPI 同步并更新 generated types
- [x] 单元测试覆盖关键行为
- [x] 无障碍 ARIA/键盘/axe
- [x] 无 console 报错/告警
- [x] 不夹带批次外文件

## 风险与缓解
- **批量导入迁移 diff 大**：以脚本机械迁移 + typecheck 逐项修复；不改业务逻辑。
- **SMTP 环境未知**：UI 明确显示未配置状态，测试 stub 邮件路径，不在 CI 依赖真实 SMTP。
- **历史 API 变体兼容**：适配层允许旧 `primary/danger/tone`，canonical 变体继续透传。
