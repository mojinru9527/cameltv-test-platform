# Batch 128 — QA 报告（公开访问、普通注册与用例分类体系）

> **QA (🔍)** | Date: 2026-08-09 | Verdict: PASS（首轮 Draft PR lint 基线失败已本地闭环，待重新确认推送）

## 1. 验收结论

- 未登录访客可打开平台壳、侧栏和模块目录；点击侧栏/目录模块或直接访问 `/testcase` 均打开登录 Dialog，访客态不挂载业务 `<Outlet>`。
- 普通用户无需平台邀请码完成注册、自动登录、创建个人项目和添加测试用例；显式开启邀请码策略、项目邀请 token、主动填写邀请码的撤销/过期校验均保持兼容。
- 用例服务默认功能用例，显式提供功能、接口、UI 自动化、全部四类入口；分类树以“用户端 / 运营后台 / 接口测试 / 其他”为一级，并继续下钻业务域和多级模块路径。
- 用例脑图按“产品界面 → 业务域 → 子模块 → 用例”组织，默认功能用例，可切换类型、界面和业务域。
- 本批无 DB migration；API schema 已重新生成到前端 OpenAPI 类型。

## 2. 最终门禁证据

| 门禁 | 命令/范围 | 结果 |
|------|-----------|------|
| 后端运行时硬门禁 | `python -m ruff check app/ --select F821` | exit 0，All checks passed |
| 后端全量 | `python -m pytest -q` | exit 0，`1238 passed, 3 skipped, 21 warnings`，289.41s |
| 注册/公开访问定向 | `pytest tests/test_register.py tests/test_public_access.py -q` | exit 0，13 passed |
| 用例分类定向 | `pytest tests/test_testcase.py -q` | exit 0，15 passed |
| 前端 lint | `npm run lint` | exit 0；`MainLayout.tsx` 历史 unused-vars 抑制计数已由 6 收敛为 4，无实际 lint 违规 |
| 前端全量 | `npm test` | exit 0，103 files / 397 tests |
| 前端类型 | `npm run typecheck` | exit 0 |
| 前端构建 | `npm run build` | exit 0，3442 modules transformed |
| OpenAPI | `openapi-typescript http://127.0.0.1:8021/openapi.json -o src/types/api.d.ts` | exit 0；公开入口和 taxonomy schema 已同步 |
| 迁移拓扑 | `python -m alembic heads` | exit 0；唯一 head `20260808_batch121_topo_edges` |
| Worktree | `verify-ai-worktree.ps1 -RequireMetadata -ExpectedWorkflow agent-team -ExpectedExecutor codex` | exit 0；分支、执行器、scope、端口匹配 |
| C 条件 | `audit-cconditions.ps1 -RequireLatestBatch` | exit 0；hard 0 / warning 0 / closed missing evidence 0 |
| 常见 Bug | `scan-common-bugs.ps1` | HARD 0；WARN 249，与 Batch 127 最终基线相同，无新增类别 |
| 差异格式 | `git diff --check` | exit 0 |

3 个 skip 为仅在 PostgreSQL 环境执行的并发场景；本批没有新增 skip 或失败。

## 3. 浏览器与视觉证据

Playwright 使用本批隔离服务 `frontend:5191 / backend:8021`，可见 Chromium 执行：

| 场景 | 结果 |
|------|------|
| 1440×900 桌面访客 | 模块目录、免费注册、登录 Dialog、直达门禁、无横向溢出 PASS |
| 768×1024 平板访客 | 同上 PASS |
| 390×844 手机访客 | 单列模块卡、登录 Dialog 可操作、无横向溢出 PASS |
| 访客 Network | 仅 `/auth/public-access`；0 个受保护业务 API 请求 |
| 普通注册 | 无邀请码注册并自动登录 PASS |
| 普通用户项目 | 创建“Batch 128 分类验收项目”并成为可见项目 PASS |
| 用例分类 | 创建用户端/运营后台/API 样例；默认功能、四类型入口、端别分组 PASS |
| 脑图 | 产品界面筛选与新层级标题可见，用户端/运营后台形成一级分叉 PASS |
| Dialog 登录闭环 | 未登录直达 `/testcase`，在 Dialog 登录后恢复 `/testcase` PASS |
| 控制台/网络 | 0 console error、0 非取消失败请求、无重复有效 GET |

证据目录：`work-logs/evidence/batch-128-public-access-case-taxonomy/`，包含桌面/平板/手机访客、用例分类和脑图截图。

## 4. 对抗性返工闭环

| 首轮发现 | 根因 | 闭环 |
|----------|------|------|
| 公开访问/注册定向测试 2 项失败 | 默认配置仍是关闭注册/强制邀请码，公开入口不存在 | 默认改为开放普通注册；新增安全公开目录；13/13 通过 |
| 用例 taxonomy 测试被 `/{case_id}` 抢匹配并返回 422 | 新静态路由尚不存在，FastAPI 落入动态路由 | `/taxonomy` 注册在动态路由前；15/15 通过 |
| 前端验收测试缺少访客首页/邀请码仍必填 | 根路由整体 `RequireAuth`，注册 schema 强制邀请码 | 访客壳阻止 Outlet；共享 LoginForm/Dialog；注册策略从公开入口读取 |
| 后端首轮全量 3 个蓝湖失败 | 独立 worktree 未初始化 `lanhu-mcp` 子模块 | `git submodule update --init --recursive lanhu-mcp`；失败集和全量均通过 |
| 后端首轮全量 1 个邀请码管理失败 | 普通注册模式静默忽略用户主动填写的已停用邀请码 | 可选但“填写即校验”，保留邀请码撤销语义；相关 17/17 通过 |
| Draft PR #179 前端 required check 在 Lint 步骤失败 | 本批移除 `MainLayout.tsx` 两个未使用变量后，`eslint-suppressions.json` 仍保留旧计数 6；ESLint 将未使用抑制视为 exit 2 | 用 `--prune-suppressions` 将计数最小更新为 4；`npm run lint`、397 项测试、typecheck、build 全部 exit 0；没有通过放宽 lint 参数绕过门禁 |

## 5. 安全与兼容性抽检

- 公开接口只返回 `registration_enabled`、`invite_code_required` 和安全菜单树，不返回用户、项目、角色或权限点。
- 访客态不调用 `/system/menus`，不挂载业务页，不依赖客户端隐藏保护数据。
- 注册仍保留独立限流、httpOnly cookie、默认角色、个人组织、项目配额和项目邀请加入逻辑。
- taxonomy 从现有 `domain/module/case_type` 推导，不改写存量 7,559 条用例，不增加迁移风险。
- `functional` 继续 canonical 为 `manual`；旧 `/test-cases/domains` 与分类管理接口保持兼容。

## 6. 受控限制

- 本批只修改代码与仓库生产配置示例，未变更 Railway/test/prod 的外部环境变量；若生产仍显式设置旧值，必须在发布流程中把 `REGISTRATION_ENABLED=true`、`INVITE_CODE_REQUIRED=false` 纳入受控配置变更。
- 合入 main 不等于发布；生产访客与注册效果需进入发布火车后复验。
- `npm ci` 报告锁文件现有 4 个 high severity 依赖告警；本批未新增依赖，该基线不由本批扩张，继续由依赖治理处理。

## 7. 发布建议

状态：**READY FOR RECONFIRMATION**。首轮 Draft PR 已创建；CI lint 基线修复会新增提交，因此原总确认按门禁失效。用户重新确认新增范围后，可再次推送 `feature/batch-128-public-access-case-taxonomy`，由新一轮 required checks 与最终 `audit-ai-pr.ps1 -RequireSuccessfulChecks` 决定是否转 Ready 和 squash merge。

**技能使用**：`cameltv-agent-team`、`cameltv-bug-guard`、`cameltv-ui-conventions`、`impeccable`、`karpathy-guidelines`、`writing-plans`、`playwright-skill`；技能判断均由上述命令和浏览器证据独立验证。
