# Batch 46 — Remaining C-Conditions — PM Plan

> **PM (🟨)** | Date: 2026-07-26

## 规格摘要

**原始需求**: 关闭 12 个 Open C-conditions 中所有非设备/非人工阻塞项（8 项）
**目标时间**: 3 Slices，预计 4-6h

## 开发任务 — Slice 1: 前端门禁恢复 + 设计修复

### [ ] Task 1: C45-C1 — 前端 CI 门禁恢复
**描述**: 在新 worktree 中安装 node_modules 并确保 `npm run typecheck && npm run build` 通过
**验收标准**:
- `npm ci` 成功（或 `npm install` 如 lock 过期）
- `npm run typecheck` exit 0
- `npm run build` exit 0
- 若 TS 错误需修复，记录修复内容
**涉及文件**:
- `test-platform-v2/frontend/package.json` — 依赖
- `test-platform-v2/frontend/src/` — 可能的 TS 错误
**参考**: PRD §4 Story 1, C-CONDITIONS.md C45-C1

### [ ] Task 2: TPv2-B19-C2 — 修复 5 项组件测试契约漂移
**描述**: vitest 中预存组件测试与当前实现不一致的修复
**验收标准**:
- `npx vitest run` 全部通过（无失败）
- 记录修复的具体测试和变更
**涉及文件**:
- `test-platform-v2/frontend/src/` — 组件实现或测试文件
- `test-platform-v2/frontend/src/**/*.test.ts` — 测试文件
**参考**: PRD §4 Story 1, C-CONDITIONS.md TPv2-B19-C2

### [ ] Task 3: C45-C4 — WikiImportDialog max-h 修复
**描述**: Wiki 导入弹窗添加 `max-h-[85vh] overflow-y-auto` 防止溢出
**验收标准**:
- WikiImportDialog 含 `max-h-[85vh] overflow-y-auto` class
- 内容溢出时可滚动
**涉及文件**:
- `test-platform-v2/frontend/src/` — WikiImportDialog 组件
**参考**: PRD §4 Story 3, C-CONDITIONS.md C45-C4

## 开发任务 — Slice 2: Playground 编译链路

### [ ] Task 4: C45-C3 — POST /api/v1/playground/compile 端点
**描述**: 实现 Playground 编译 API：接收功能用例（Markdown/Gherkin），生成可执行 .spec.ts
**验收标准**:
- `POST /api/v1/playground/compile` 可接受测试用例内容
- 返回编译后的 Playwright spec 代码
- 编译结果可被 `npx playwright test` 执行（headless chromium）
**涉及文件**:
- `test-platform-v2/backend/app/api/v1/playground.py` — 新路由
- `test-platform-v2/backend/app/services/playground_service.py` — 编译逻辑
- `test-platform-v2/backend/app/schemas/playground.py` — Schema
- 注册路由到 `test-platform-v2/backend/app/main.py`
**参考**: PRD §4 Story 2, batch-45-c22-playground-assessment.md, C-CONDITIONS.md C45-C3

### [ ] Task 5: C45-C3 — Playground execute 端点
**描述**: 实现 Playground 执行 API：接收 .spec.ts，在 headless Chromium 中运行并返回结果/截图
**验收标准**:
- `POST /api/v1/playground/execute` 接受 spec 代码
- 返回执行结果（pass/fail + 截图 base64/URL）
**涉及文件**: 同上 Task 4 文件
**参考**: PRD §4 Story 2, C22-C2

## 开发任务 — Slice 3: Docker Staging 验证

### [ ] Task 6: C43-1 + C45-C2 — Alembic 迁移验证
**描述**: Docker 启动后执行 `alembic upgrade head` + `alembic check` + downgrade 双向演练
**验收标准**:
- `alembic upgrade head` exit 0
- `alembic check` 返回单头确认
- `alembic downgrade -1` + `alembic upgrade head` 双向通过
**涉及文件**:
- `test-platform-v2/backend/alembic/` — 迁移脚本
**参考**: PRD §4 Story 4+5, C-CONDITIONS.md C43-1/C45-C2

### [ ] Task 7: C43-2 — Tier 1 核心链路浏览器验收
**描述**: 浏览器逐页验收核心页面（登录/仪表盘/用例库/测试计划/报告）
**验收标准**:
- 5 个核心页面均正常加载无 console 错误
- 截图记录
**涉及文件**: 无代码变更，纯验收
**参考**: PRD §4 Story 4, C-CONDITIONS.md C43-2

### [ ] Task 8: C44-C1 — 模块树提取准确率实测
**描述**: 人工标注 ground truth + 运行 module_extractor 评估准确率
**验收标准**:
- 准确率 ≥70% 或记录偏差原因
**涉及文件**:
- `test-platform-v2/backend/app/services/module_extractor.py`
**参考**: PRD §4 Story 4, C-CONDITIONS.md C44-C1

### [ ] Task 9: C44-C4 — release_bundle 全链路 staging 实测
**描述**: Docker staging 中测试 create→diff→confirm→sync→regression 全链路
**验收标准**:
- 全链路无报错
- 各步骤输出符合预期
**涉及文件**: 无代码变更，纯验收
**参考**: PRD §4 Story 4, C-CONDITIONS.md C44-C4

## 质量要求

- [x] 响应式（Desktop + Tablet） — N/A（本次无新 UI）
- [ ] OpenAPI 同步 — C45-C3 新端点
- [ ] 单元测试覆盖 — C45-C3 新代码
- [ ] 无 console 报错/告警 — 前端门禁
