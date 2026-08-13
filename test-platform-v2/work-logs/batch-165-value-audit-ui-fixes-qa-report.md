# Batch 165 — QA 报告
> **QA (🔍)** | Date: 2026-08-13 | Verdict: PASS（待用户一次总确认后合入）

## 测试总览
| 条件数 | 通过 | 失败 | 阻塞 |
|--------|------|------|------|
| 8 | 8 | 0 | 0 |

## 可执行门禁（命令 + 退出码）
| 门禁 | 命令 | 结果 |
|------|------|------|
| 前端 typecheck | `npm run typecheck` | ✅ exit 0 |
| 前端 build | `npm run build` | ✅ exit 0（tsc -b && vite build 8.93s） |
| 前端全量单测 | `npm test`（vitest run） | ✅ 113 files / 461 tests passed |
| 前端 lint | `npm run lint`（eslint . --max-warnings=0） | ✅ exit 0（并 prune 6 行过期 suppression） |
| 后端 F821 | `python -m ruff check app --select F821` | ✅ All checks passed |
| 后端导入 | `python -c "from app.main import app"` | ✅ exit 0 |
| Alembic 单头 | `python -m alembic heads` | ✅ 单 head：20260812_b164_sched_heartbeat |
| 后端全量回归 | `python -m pytest -q`（worktree，初始化 lanhu-mcp 子模块后） | ✅ 1389+40 passed / 0 failed / 3 skipped |
| UI/功能（本地 dev 栈 + Playwright headless） | 见证据目录 work-logs/evidence/batch-165/ | ✅ 截图 14 张 |

> 基线说明：首轮全量出现 5 个 lanhu 部署契约失败，根因是 worktree 未初始化 `lanhu-mcp` 子模块（`git submodule status` 为 `-`）。`git submodule update --init --recursive` 后重跑 40/40 通过。非本批回归。

## 逐条件验证
### C1: 专项测试/性能监控入口全部隐藏
**变更文件**: backend/app/services/menu_service.py:10-13; backend/app/seed.py:34-35,48-49,266,268; frontend/src/router/index.tsx; CommandPalette.tsx; guestModuleCatalog.ts
| 检查项 | 结果 |
|--------|------|
| 侧边栏不再出现 专项测试/性能监控 | ✅ Playwright 实测（SIDEBAR_HAS_SPECIAL=false, SIDEBAR_HAS_PERF=false） |
| /special、/perftest 路由返回 404 页面 | ✅ 实测两路由均显示"页面不存在" |
| 命令面板无两入口 | ✅ 单测 CommandPalette.test.ts（batch-165 新增用例） |
| 访客目录无两模块 | ✅ guestModuleCatalog.ts 注释 |
| 存量库菜单也隐藏（服务端过滤） | ✅ menu_service HIDDEN_MENU_CODES 对所有角色生效（含 * 超管） |
| seed 契约测试同步 | ✅ test_batch63_menu_catalog.py 更新 + 新增 hidden 断言，5/5 通过 |

### C2: 知识中心 tab 换行错位/点击不切换修复
**变更文件**: frontend/src/pages/knowledge/index.tsx:93-97
| 检查项 | 结果 |
|--------|------|
| 复现（修复前） | 1280/1024 下 TabsList 固定 h-8，第二行 tab 被裁（知识差异对比/Skills 等 clipped） |
| 修复后 1440/1280/1024/1920 | listH 35/67/67/35，无 clipped，点击 Skills 正常切到 ?tab=skills 且 active=Skills ✅ |
| 12 个 tab 全部可点击切换 | ✅ Playwright 逐 tab 验证 URL 与 active 同步 |

### C3: 接口资产列表 20 行/页 + 参数展示
**变更文件**: AssetTab.tsx（扁平列表）、EndpointDetailPanel.tsx（请求/响应参数区）
| 检查项 | 结果 |
|--------|------|
| 25 个资产 → 第 1 页 20 行（含服务列），分页 第 1/2 页 | ✅ 实测（ASSET_STATE rows=20, pagination=true） |
| 行内容：服务名/方法/路径/说明/操作 | ✅ 实测首行 account-service GET /api/seed/endpoint/1 |
| 端点详情显示 query 参数与请求体 | ✅ 实测 DETAIL_HAS_QUERY=true, DETAIL_HAS_BODY=true |

### C4: 接口用例可编辑参数/断言
**变更文件**: ApiCaseTab.tsx（编辑按钮+CaseDrawer）、CaseDrawer.tsx（断言升级为结构化 AssertionEditor）
| 检查项 | 结果 |
|--------|------|
| 接口用例行出现"编辑"按钮 | ✅ 实测 EDIT_BTN_COUNT=1 |
| 点击打开"编辑用例"抽屉 | ✅ 实测 DRAWER_OPEN=1 |
| 抽屉含 HTTP 方法/接口路径/请求参数（可改） | ✅ 实测 |
| 抽屉含结构化"断言规则"编辑器（status_code/jsonpath/...） | ✅ 实测 DRAWER_HAS_ASSERT_RULES=true |
| 单测 | ✅ ApiCaseTab.test（2 用例）+ CaseDrawer.test 通过 |

### C5: UI 自动化 用例/脚本可见性
**变更文件**: frontend/src/pages/uitest/index.tsx（页面级 Tabs：任务 / 用例·脚本）
| 检查项 | 结果 |
|--------|------|
| 页面新增"用例 / 脚本"页签 | ✅ 实测 |
| 页签含 UI 自动化用例列表 + 脚本资产列表 | ✅ 实测 UITEST_ASSETS_HAS_UI_CASES=true / HAS_SCRIPT_SECTION=true |
| 运行过程入口（原详情抽屉 stdout/产物/轮询）保留 | ✅ 未改动，代码审查确认 |
| 单测 | ✅ UiTestPage.test 5 用例通过（脚本请求次数断言更新为 2） |

### C6: 全平台价值与冗余评估文档
**变更文件**: docs/platform-feature-value-and-redundancy-audit.md
| 检查项 | 结果 |
|--------|------|
| 覆盖 8 个功能逐项解释+效率证据 | ✅ 每项含源码/生产审计证据 |
| 测试计划全跳过解释（TP-SPORTS-1600） | ✅ §3.1（0/405 + 环境预检 C146-1） |
| 系统管理/项目管理/组织管理/我的项目冗余评估 | ✅ §3.3（建议 4→2 入口） |
| 全平台冗余矩阵 | ✅ §4（14 组两两比对） |

### C7: 测试计划环境选择入口（用户反馈补充）
**变更文件**: frontend/src/pages/testplan/PlanDetail.tsx
| 检查项 | 结果 |
|--------|------|
| 根因确认 | 环境选择仅在 `hasApiCases`（含 API 用例）时渲染；纯人工用例计划看不到入口，且批量执行按设计将人工用例标记为跳过 |
| 修复 | 环境选择改为含 API/UI 自动化用例即显示（hasAutomatedCases）；纯人工计划执行弹窗增加明确提示 |
| 实测 | 含 API 用例计划头部显示"执行环境"✅；纯人工计划弹窗显示提示且不显示环境字段 ✅ |
| 单测/门禁 | typecheck/eslint/testplan 6 用例 ✅ |

### C8: 回归无新增失败
| 检查项 | 结果 |
|--------|------|
| 前端全量 461 用例 | ✅ 全绿 |
| 后端全量 1429 用例 | ✅ 全绿（子模块初始化后） |
| lint / typecheck / build / ruff / alembic | ✅ 全绿 |

## 缺陷列表
| # | 严重级 | 描述 | 证据 | 状态 |
|---|--------|------|------|------|
| 1 | P2 | 接口用例分组折叠时"编辑"不可见（需先展开分组） | 交互设计使然 | 已知体验，已加行内编辑按钮 |
| 2 | P3 | 生产凭据过期（production.env 登录 401），无法在线回归 | 审计环境 | 不影响本地验证 |

## 发布建议
状态: **READY（待用户一次总确认）** | 必修复: 0 | 建议修复: 0

## 复盘卡
| 计划耗时 | 缺陷(P0/P1/P2/P3) | 返工次数 | 根因分类 | 下次避免 |
|----------|-------------------|----------|----------|----------|
| 计划 6h vs 实际 4h | 0/0/1/1 | 2 | 需求/测试数据环境 | worktree 首次使用先初始化子模块；生产凭据先验证再排期 |

**技能使用**: cameltv-bug-guard（React 副作用铁律核对）；cameltv-ui-conventions（Tabs 组件基线）；vision（生产审计截图解读）；playwright-skill/playwright-cli（本地复现与回归）
