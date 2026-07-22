# Batch 31 — PRD Summary：平台全面审查、Agent Team 与远端交付闭环

> **Product (🟦)** | Date: 2026-07-22 | Status: Approved

## 1. 问题陈述

最新 `origin/develop` 中的测试平台无法在全新检出后完成前端构建；部分已实现页面没有可用导航入口，后端存在运行时未定义符号和未注册路由。上一个 PR #55 在创建后约 66 秒即合并，无 Review、无 status check，QA 结论主要来自文件存在和静态检查，导致“已经修过”的问题再次进入 develop。

用户同时要求：

1. 拉取最新代码，做代码、功能和 UI 全面审查；
2. 核验 GitHub push/PR 方案是否真正可用；
3. 审查 Agent Team 为什么重复返工；
4. 用蓝湖需求与生产站点验收，并把修复推到远端。

## 2. 成功指标

| 指标 | 基线 | 目标 |
|---|---:|---:|
| 后端全量测试 | 37 failed | 0 failed |
| 前端全量测试 | 5 failed | 0 failed |
| 全新前端类型检查/构建 | 失败 | 通过 |
| 后端 F821 | 4+ 运行时风险 | 0 |
| develop PR 硬门禁 | 仅导入/迁移冒烟 | 后端 F821/迁移 + 前端 typecheck/build |
| 知识中心移动端横向溢出 | 424px / 375px | 375px / 375px |
| 本次修改远端交付 | 无 | 功能分支 + Draft PR → develop |

## 3. 非目标

- 不在本批次进行前端依赖大版本升级；`npm audit` 风险单独治理。
- 不一次性清理 201 条非运行时 Ruff 债务，避免无关的大规模格式改写。
- 不替用户合并 PR；远端 required checks/审批规则尚未完整配置。
- 未提供运营后台生产地址，因此不宣称后台运行态验收通过。

## 4. 用户故事与验收标准

- As a 开发者, I want 从最新 develop 的隔离 worktree 开发并提交 PR, so that 本地变更可追踪且不覆盖现有工作区。
  - Given 主工作区存在未提交修改 / When 开始审查 / Then 使用独立 worktree 和 feature 分支，主工作区保持不变。
- As a QA, I want QA 结论包含实际执行证据, so that 文件存在不能再冒充功能通过。
  - Given 变更完成 / When Leader 审批 / Then 必须有构建、测试、关键路径、响应式和 CI 证据。
- As a 测试平台用户, I want 从“版本测试任务”进入真实发布包页面, so that 已开发功能不是隐藏状态。
  - Given 点击旧菜单 / When 路由仍为 `/version-mission` / Then 自动跳转 `/release-bundles`；后端启动会修正旧菜单数据。

## 5. 需求与生产验收源

- 用户端蓝湖：文档最新版本 15.0（2026-07-20），新增首页赛事回放入口、回放列表和详情（MB/PC）。
- 运营后台蓝湖：文档最新版本 9.0（2026-07-20），新增赛事回放管理页面。
- 生产站点：`https://www.camel1.tv/`。

## 6. 上线计划

| 阶段 | 门槛 |
|---|---|
| Draft PR | 本地硬门禁、全量回归、页面验收通过 |
| Ready PR | GitHub checks 通过，审查者确认范围 |
| 合并 develop | 人工确认 required checks 与未解决风险 |
