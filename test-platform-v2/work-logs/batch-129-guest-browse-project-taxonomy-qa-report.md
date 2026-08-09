# Batch 129 — QA 报告（访客功能浏览、项目引导与用例重分类）

> **QA (🔍)** | Date: 2026-08-09 | Verdict: PASS（待用户总确认与 required checks）

## 1. 验收结论

- 未登录访客可以从首页或侧栏进入 26 个公开模块的静态能力说明页；导航本身不再弹登录，只有“登录后使用”动作打开 Login Dialog。
- 访客说明页不挂载任何业务页面，桌面、平板、手机实测受保护业务 API 请求均为 0。
- 普通用户可完成公开注册；无项目时在布局层阻断业务 `<Outlet>`，明确展示“创建第一个项目”，切换到用例服务不会产生缺少 Project ID 的请求。
- 用例列表和 taxonomy 共用后端分类器并输出 `surface`；脑图只消费该字段，不再复制归类规则。
- Batch 110 的 476 条存量功能用例、31 个历史业务域全部重分类：用户端 227、运营后台 249、其他 0。
- 本批无数据库 migration；OpenAPI 类型已用 7.13.0 重新生成。

## 2. 测试先行证据

| 阶段 | 结果 |
|------|------|
| RED（前端） | 6 个目标测试文件按预期失败：模块目录/预览、项目边界与 surface API 尚不存在 |
| RED（后端） | taxonomy 34 项中 31 项按预期失败：31 个旧域仍落入“其他”；3 项原基线通过 |
| GREEN（前端定向） | 6 files / 40 tests passed |
| GREEN（后端定向） | `TestCaseTaxonomy` 34/34 passed |

## 3. 最终门禁

| 门禁 | 命令/范围 | 结果 |
|------|-----------|------|
| 后端运行时硬门禁 | `python -m ruff check app --select F821` | exit 0，All checks passed |
| 后端全量 | `python -m pytest -q` | exit 0，1270 passed / 3 skipped / 22 warnings，264.65s |
| 前端全量 | `npm test -- --run` | exit 0，107 files / 434 tests |
| 前端 lint | `npm run lint` | exit 0 |
| 前端类型 | `npm run typecheck` | exit 0 |
| 前端构建 | `npm run build` | exit 0，3446 modules transformed |
| 应用导入 | `python -c "import app.main"` | exit 0（本机无 adb 为非阻塞提示） |
| 迁移拓扑 | `python -m alembic heads` | exit 0，唯一 head `20260808_batch121_topo_edges` |
| OpenAPI | `openapi-typescript http://127.0.0.1:8022/openapi.json -o src/types/api.d.ts` | exit 0；`TestCaseOut.surface` 已同步 |
| 常见 Bug | `scan-common-bugs.ps1` | HARD 0；WARN 249，与 Batch 128 基线一致 |
| Worktree | `verify-ai-worktree.ps1 -RequireMetadata -ExpectedWorkflow agent-team -ExpectedExecutor codex` | exit 0；分支、执行器、scope、端口匹配 |
| C 条件 | `audit-cconditions.ps1 -RequireLatestBatch` | exit 0；hard 0 / warning 0 / closed missing evidence 0 |
| 调试/凭据增量扫描 | `git diff origin/main...HEAD` | console/debug/print 0；私钥/token/API key 0 |
| 差异格式 | `git diff --check` | exit 0 |

3 个 skip 为仅在 PostgreSQL 环境执行的并发场景，本批没有新增 skip。首次全量因独立 worktree 未初始化锁定的 `lanhu-mcp` 子模块出现 3 个环境失败；执行 `git submodule update --init --recursive` 后，失败集 3/3 通过，随后完整 1273 项重跑为 1270 passed / 3 skipped / 0 failed。

## 4. 浏览器与视觉证据

Playwright 使用批次隔离服务 `frontend:5192 / backend:8022`，可见 Chromium 执行。

| 场景 | 结果 |
|------|------|
| 桌面访客首页 | 公开能力目录可见 PASS |
| 模块导航 | 点击“查看用例服务功能”进入 `/testcase` 说明页，不自动弹登录 PASS |
| 显式使用 | 点击“登录后使用”打开对应 Login Dialog PASS |
| 公开注册 | 无邀请码注册并自动登录，跳转 `/my-projects` PASS |
| 无项目切换 | `/testcase` 显示创建项目引导，业务页面未挂载、业务请求 0 PASS |
| 创建项目入口 | CTA 返回 `/my-projects` PASS |
| 768×1024 / 390×844 | 模块说明页无横向溢出，控制台错误 0、业务请求 0 PASS |
| 390×844 无项目 | 步骤纵向排列、CTA 可操作、无横向溢出、业务请求 0 PASS |
| 浏览器总览 | console errors 0、failed requests 0 |

证据目录：`work-logs/evidence/batch-129-guest-browse-project-taxonomy/`。

## 5. 对抗性审查闭环

| 风险/发现 | 根因 | 闭环 |
|-----------|------|------|
| 浏览模块即要求登录 | 导航与使用共用 `onRequireLogin`，直达路由又自动开 Dialog | 导航只切 URL；静态说明页的主 CTA 才触发登录 |
| 无项目持续缺 Project ID | `ProjectScopeBoundary` 只换 key，仍挂载 `<Outlet>` | 新布局边界在挂载前阻断，仅白名单放行项目/组织起步页 |
| 存量用例落入“其他” | 31 个旧 domain 没有显式端别词 | 以仓库功能地图锁定 19 用户端 + 12 后台域，31 项参数化测试 |
| 两视图可能漂移 | 列表和脑图各自猜测端别 | 后端单一分类器随列表输出 `surface`，脑图直接消费 |
| “其他”空入口长期存在 | 前端固定枚举四个端别 | 筛选只展示当前响应中实际存在的端别；未知数据仍保留信号 |

## 6. 风险与发布边界

- 公开页只含静态产品能力文案，不开放匿名项目、用例、报告或缺陷 API。
- `surface` 是兼容新增响应字段；未改写历史数据、未删除未知分类、无 schema migration。
- `npm ci` 报告锁文件现有 4 个 high severity 依赖告警；本批未新增依赖。
- 本报告证明本地交付就绪，不代表已合入或已部署生产。生产验收仍需进入发布流程后执行。

## 7. QA 判定

**PASS / READY FOR TOTAL CONFIRMATION**。允许展示本批完整待推送范围并请求一次总确认；确认后才可推送、创建 Draft PR，并由 required checks 和最终 PR 审计决定是否合入 `main`。
