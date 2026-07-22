# Batch 31 — Dev 全面代码审查

> **Dev (💻)** | Date: 2026-07-22 | Base: `origin/develop@94a96ae`

## 1. P0/P1 发现与修复

| 发现 | 根因 | 修复 |
|---|---|---|
| 最新 develop 前端无法构建 | PR #55 引用了未提交 UI 组件、依赖和图标；类型契约不一致 | 补齐 Radix 依赖与组件、图标和共享类型 |
| 性能监控 26 条 API 测试全 404 | `perf.py`/`perf_ws.py` 存在但未注册到聚合路由 | 注册 REST 与 WebSocket router |
| 蓝湖告警任务导入抛 500 | API 写成 advisory，service/test 是 hard gate | 统一为 409 拦截，捕获 service ValueError |
| 删除用例后仍可查询 | soft delete 写入但 `get_case` 未过滤 | get/update/delete/batch 全部过滤已删除数据 |
| 版本任务显示“页面建设中” | seed 指向废弃 `/version-mission` | seed 可变字段对账 + 前端兼容重定向 |
| 本地源码修改不生效 | 过期 `vite.config.js` 覆盖 `vite.config.ts` | 删除跟踪生成物，脚本显式指定 TS 配置 |
| 迁移在默认 Alembic 表失败 | revision ID 超过 32 字符 | 缩短 revision 并同步 merge head |
| 后端潜在 NameError | knowledge/requirement/job_runner 缺 logger，test_plan 缺 json | 补齐导入与 logger |

## 2. 前端契约与 UI 修复

- `DiffReviewPanel` 按后端真实 `new/modified/deleted/unchanged` 契约渲染，确认接口发送 `skip_modules`，删除无后端支持的伪“修正/导出”操作。
- DebugTab 正确预填 service/module/path/header/必填参数，显示完整请求地址，错误后停止重复执行。
- CaseDrawer 必填校验覆盖模块、步骤、预期结果；步骤 textarea 可编辑。
- SphereTab 使用正确 vis-network 类型，补齐深度 5 和 metadata 描述。
- Dialog/Sheet 转发 ref；接口用例分组消除 button 嵌套。
- 知识中心和主顶栏在 390px 下无页面级横向溢出。

## 3. Agent Team 根因审查

1. 六部门是文档角色扮演，缺少自动阻断；PR #55 的工件齐全但 clean build 失败。
2. QA 把“文件存在/代码目测”写成 PASS，没有命令、退出码和全量失败集合。
3. develop ruleset 要 PR，但审批数、required checks 都是 0；PR #55 无 review、无 checks。
4. 工作流使用 `git add -A`，容易把别的窗口和生成物夹带进提交。
5. “首个实现必须有 3–5 个问题”制造错误激励；不可用技能被当作硬依赖。
6. 旧流程允许安全策略绕过，且无 staged diff 检查。

本批已逐项修订 `.claude/skills/cameltv-agent-team/`、`AGENTS.md` 和 develop CI。

## 4. Push 方案审查

- ✅ SSH remote 可 fetch/push；`gh` 已登录用户 `mojinru9527`，具备 repo/workflow scope。
- ✅ 使用独立 worktree 和 feature 分支，主工作区脏改动未被触碰。
- ⚠️ 仓库 Git identity 是 `Jenkins CI <ci@cameltv.local>`，不应作为人工 PR 作者；本提交使用一次性的 GitHub 用户身份覆盖，不改共享配置。
- ⚠️ `delete_branch_on_merge=false`，合并后远端分支需人工或仓库设置清理。
- ⚠️ develop 无审批和 required checks，Draft PR 禁止自动合并。

## 5. 未纳入本批的债务

- Ruff 全规则仍有 201 条：113 unused import、23 E712、20 unused variable 等；F821 已为 0。
- `npm audit`：17 个漏洞（2 critical / 7 high / 8 moderate），主要需依赖大版本治理。
- 生产构建有 Wiki API 静态/动态重复导入提示；不影响构建结果。
- React Router v7 future flag 提示待路由升级处理。
