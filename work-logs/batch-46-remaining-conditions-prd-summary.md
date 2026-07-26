# Batch 46 — Remaining C-Conditions — PRD Summary

> **Product (🟦)** | Date: 2026-07-26 | Status: Draft

## 1. 问题陈述

Batch-45 将 Open C-conditions 从 23 降至 12（关闭 15 项 batch-18/C21/C22/C24/C25v2/C26KB 遗留）。剩余 12 项中：
- 2 项 P0 被物理设备阻塞（CP-C1/CP-C2 Android/iOS 真机）
- 1 项 P1 需人工审查者（C31-2）
- 4 项 P1 此前被 Docker 阻塞（C43-1/C43-2/C44-C1/C44-C4），Docker 现已恢复
- 4 项 P1-P3 为 batch-45 新设条件（C45-C1/C45-C2/C45-C3/C45-C4）
- 1 项 P2 被 node_modules 阻塞（TPv2-B19-C2）

**本次目标**：关闭所有非设备/非人工阻塞的条件，将 Open 数从 12 降至 ≤4。

## 2. 成功指标

| 指标 | 基线 | 目标 | 测量窗口 |
|------|------|------|---------|
| Open C-conditions | 12 | ≤4 | batch-46 结束 |
| 前端 CI 门禁 | C45-C1 blocked | npm typecheck + build PASS | Slice 1 |
| Playground 编译链路 | C45-C3 未实现 | POST /api/v1/playground/compile 端到端可用 | Slice 2 |
| Docker staging 验证 | 4 项 blocked | C43-1/C43-2/C44-C1/C44-C4 全绿 | Slice 3 |
| Staging 迁移演练 | C45-C2 未执行 | upgrade/downgrade 双向通过 | Slice 3 |
| 组件测试契约 | 5+ 项漂移 | 全部修复 + vitest pass | Slice 1 |

## 3. 非目标（本次不做）

- **CP-C1/CP-C2**: Android/iOS 真机采集验证 — 阻塞于物理设备不可用，豁免至设备就绪
- **C31-2**: 人工审查者确认 — 需独立人工审核，不在 Agent Team 自动化范围内
- **新功能开发**: 仅关闭 C-conditions，不加 PRD 外需求
- **C22 Playground Phase 2+**: Phase 1（编译+执行）即可满足 C45-C3；完整编排器 Phase 2 留待 batch-47+

## 4. 用户故事 + 验收标准

### Story 1: 前端 CI 门禁恢复 (C45-C1 + TPv2-B19-C2)
- As a 开发者, I want `npm ci && npm run typecheck && npm run build` 全部通过, so that 前端代码质量门禁有效
- As a 开发者, I want 5+ 项预存组件测试契约漂移被修复, so that vitest 不再有假失败
- 验收：Given 干净 node_modules / When `npm ci && npm run typecheck && npm run build` / Then 三命令均 exit 0；vitest run 全绿

### Story 2: Playground 编译链路 (C45-C3)
- As a 测试工程师, I want `POST /api/v1/playground/compile` 将功能用例编译为可执行 .spec.ts, so that UI 自动化链路可行
- 验收：Given P0 功能用例 / When 调用 compile API / Then 返回可执行 .spec.ts 内容 + 编译成功状态

### Story 3: WikiImportDialog 设计修复 (C45-C4)
- As a 用户, I want Wiki 导入弹窗支持滚动, so that 内容溢出时可完整查看
- 验收：Given 导入内容超过视口 / When 打开 WikiImportDialog / Then 弹窗 `max-h-[85vh] overflow-y-auto` 生效

### Story 4: Docker Staging 验证 (C43-1/C43-2/C44-C1/C44-C4)
- As a QA, I want staging 环境 Docker 恢复后完成核心验收, so that 平台功能在类生产环境已验证
- 验收：Given Docker 已启动 / When 执行 Alembic upgrade head + 浏览器验收 / Then alembic check PASS + Tier 1 核心链路全绿 + 模块树准确率 ≥70% + release_bundle 全链路可用

### Story 5: Staging 迁移双向演练 (C45-C2)
- As a 运维, I want batch-45 迁移在 staging 完成 upgrade/downgrade 双向验证, so that 生产迁移零风险
- 验收：Given staging DB / When 执行 `alembic upgrade head` → `alembic downgrade -1` / Then 两方向均 exit 0 且数据完整

## 5. 技术考量

- **C45-C1/TPv2-B19-C2**: 需要前端 node_modules。若 package-lock 过期可能需 `npm install` 后再修 type 错误
- **C45-C3**: 需要创建 `/api/v1/playground/compile` 端点，涉及 Playwright codegen 模板或正则拼接
- **C43-1/C45-C2**: 依赖 Docker 运行中，需确认 docker compose 状态
- **C43-2/C44-C1/C44-C4**: 需要浏览器人工逐页验收，需启动前后端服务

## 6. 上线计划

| 阶段 | 受众 | 成功门槛 |
|------|------|---------|
| Slice 1 | Dev | C45-C1 + TPv2-B19-C2 + C45-C4 完成 |
| Slice 2 | Dev | C45-C3 Playground compile API 完成 |
| Slice 3 | QA | Docker staging 全链路验收 + 迁移演练 |
| 合入 | All | PR 门禁全绿 + Leader APPROVED |
