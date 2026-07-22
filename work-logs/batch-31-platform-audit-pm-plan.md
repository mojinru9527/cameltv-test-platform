# Batch 31 — PM Plan：全面审查与交付闭环

> **PM (🟨)** | Date: 2026-07-22

## 开发任务

### Task 1：基线与远端隔离

- 从最新 `origin/develop` 创建 `feature/batch-31-platform-audit` 独立 worktree。
- 记录主工作区脏状态并禁止夹带。
- 核验 GitHub 登录、remote、分支规则、PR #55 检查证据。

### Task 2：代码与功能修复

- 修复前端缺失组件/依赖/图标、API 类型契约和构建失败。
- 修复性能路由未注册、蓝湖质量门禁冲突、用例软删除泄漏、F821 和迁移 revision 长度。
- 修复 Vite 源配置与已跟踪生成文件漂移。
- 修复旧菜单无法进入发布包页面。

### Task 3：UI 与浏览器验收

- 桌面、390px 移动端检查知识中心。
- 清理 Dialog/Sheet ref 和嵌套 button 警告。
- 将知识标签滚动限制在局部，消除页面横向溢出。
- 验证项目球、版本发布包空状态和控制台错误。

### Task 4：流程加固

- 修改 Agent Team：显式暂存、禁止绕过安全策略、无预设缺陷数、QA 可执行门禁、Leader 需 CI 证据。
- 扩展 develop PR CI。
- 更新 PR 模板与常见陷阱。

### Task 5：远端交付

- 执行全量回归，显式暂存，检查 staged diff。
- 使用当前 GitHub 账号的提交身份创建 commit。
- push 功能分支并创建指向 develop 的 Draft PR。

## 质量要求

- 后端：F821、app import、Alembic 单头/revision、653 条全量 Pytest。
- 前端：`npm ci`、typecheck、96 条 Vitest、生产 build。
- UI：桌面/移动、无页面级横向溢出、无新增 console error。
- Git：禁止直接 push develop，禁止 `git add -A`，不触碰主工作区脏改动。
