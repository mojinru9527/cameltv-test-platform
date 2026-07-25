# DEV Kanban — Batch 46: Remaining C-Conditions

> **Dev (💻)** | Started: 2026-07-26 | Executor: claude

## 当前位置

Slice 1 → 🔄 编码 → C45-C1 前端门禁

## 批次记录

| Slice | 内容 | 状态 | 耗时 |
|-------|------|------|------|
| Slice 1 | C45-C1 + TPv2-B19-C2 + C45-C4 | 🔄 | — |
| Slice 2 | C45-C3 Playground API | ⏳ | — |
| Slice 3 | Docker staging 验收 | ⏳ | — |

## Slice 1: 前端门禁 + 测试修复 + 设计修复

### 📝 方案
- C45-C1: 安装 node_modules，跑 typecheck + build，修复 TS 错误
- TPv2-B19-C2: 跑 vitest，修复失败的组件测试
- C45-C4: WikiImportDialog 加 max-h 样式

### 💻 编码
- [ ] C45-C1: node_modules 安装 + typecheck/build
- [ ] TPv2-B19-C2: vitest 修复
- [ ] C45-C4: WikiImportDialog 样式

### 🔍 自测
- [ ] `npm run typecheck` PASS
- [ ] `npm run build` PASS
- [ ] `npx vitest run` PASS

### ✅ 审批
- [ ] Slice commit + push

## Slice 2: Playground API

### 📝 方案
- 新建 `playground.py` router + service + schema
- compile: Gherkin → Playwright .spec.ts（正则模板拼接）
- execute: 运行 spec 在 headless Chromium

### 💻 编码
- [ ] Backend: model/schema/service/router
- [ ] Frontend: 无（Phase 1 API only）

### 🔍 自测
- [ ] pytest for compile + execute
- [ ] ruff check PASS

### ✅ 审批
- [ ] Slice commit + push

## Slice 3: Docker Staging 验收

### 📝 方案
- Docker 启动 → Alembic 迁移 → 浏览器逐页验收
- 模块树准确率 + release_bundle 全链路

### 验收清单
- [ ] C43-1: Alembic upgrade head + check
- [ ] C45-C2: upgrade/downgrade 双向演练
- [ ] C43-2: 5 核心页面截图
- [ ] C44-C1: 模块树准确率 ≥70%
- [ ] C44-C4: release_bundle create→diff→confirm→sync→regression

## 审批历史

| 日期 | 审批人 | 内容 | 结论 |
|------|--------|------|------|
| — | — | — | — |
