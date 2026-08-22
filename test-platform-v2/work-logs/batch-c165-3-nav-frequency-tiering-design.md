# Batch c165-3-nav-frequency-tiering — 设计文档（PRD-lite + 设计合一）

> **Product (📦)** | Date: 2026-08-20 | Status: Approved（用户已在会话中确认设计 v2）
> **mode: light**
> **豁免理由**：本批为 UI 入口收敛延续批次（隐藏 4 个与页内 Tab 同源的菜单子项 + 侧边栏按频率分层展示），不新增接口/配置/依赖（`ui/collapsible.tsx`、`localStorage`、`HIDDEN_MENU_CODES` 机制均为现有能力）；按「轻量批次」执行，先例 `batch-c165-2-entry-consolidation`。
> **Executor**: DeepSeek Harness（direct 任务，worktree `DeepSeek_Harness-nav-frequency-tiering`）

## 1. 问题陈述

入口收敛批次（#293 / #295–#299）上线生产后，侧边栏仍有 18 个一级入口，且知识中心 4 个子项（项目知识/平台研发/知识图谱/AI审核台）与知识中心页内 Tab 完全同源（路径均为 `/knowledge?tab=xxx`），高低频入口混排、视觉负担大。

用户（产品负责人）确认的高频入口仅 9 个：工作台、需求文档、知识中心、用例服务、接口测试、UI 自动化、定时任务、DSH 任务、AI 配置；其余 9 个（版本发布包/测试计划/报告中心/系统管理/我的项目/缺陷管理/测试数据集/目标环境/蓝湖证据包）为低频。

## 2. 成功指标

| 指标 | 基线 | 目标 | 测量窗口 |
|------|------|------|---------|
| 侧边栏默认可见行数 | 18 平铺 + 知识 4 子项 | 9 高频 + 1 个「更多功能」折叠行 = 10 行 | 合入部署后走查 |
| 低频入口可达性 | 平铺可见 | 「更多功能」一键展开可见；路由/命令面板/书签全部保留 | 组件测试 + 走查 |
| 活跃低频路由 | — | 当前页在「更多」内时该组自动展开，活跃项高亮可见 | 组件测试 |
| 知识子项 | 侧边栏 4 行 | 侧边栏消失，页内 Tab 与 `?tab=` 书签不受影响 | 后端单测 + 走查 |

## 3. 非目标（本次不做）

- 不做 per-user 个性化（「我的常用」置顶/隐藏）——记入 backlog 后续排期。
- 不删除任何路由、页面、权限行或后端 API；`?tab=` 深链全部保留。
- 不改命令面板（Ctrl+K）条目；不改 `guestModuleCatalog` 访客目录。
- 不做图标折叠模式（`collapsible="icon"`）下的弹层——该模式下低频项仍以图标平铺。

## 4. 用户故事 + 验收标准

- As 平台日常用户，I want 侧边栏默认只呈现 9 个高频入口，so that 导航一眼可达、无视觉噪音。
  - 验收：登录后侧边栏默认可见 = 工作台/需求文档/知识中心/用例服务/接口测试/UI 自动化/定时任务/DSH 任务/AI 配置 + 「更多功能(9)」一行；知识中心无子项展开。
- As 偶用低频功能的用户，I want 点击「更多功能」展开低频入口且状态被记住，so that 低频功能一键可达且不每次重复操作。
  - 验收：点击展开后 9 个低频项可见；`localStorage` 持久化，刷新后保持展开/收起状态。
- As 正在低频页面工作的用户，I want 当前页属于「更多」时该组自动展开，so that 活跃导航项不被折叠隐藏。
  - 验收：直接打开 `/report`（等低频路由）时「更多功能」自动展开且对应项高亮。
- As 管理员，I want 知识中心子项从菜单消失但权限与深链保留，so that 既有授权与书签不受影响。
  - 验收：`/api/v1/system/menus` 与 `/api/v1/auth/public-access` 均不再返回 `menu:knowledge:project/platform/graph/artifacts`；直接访问 `/knowledge?tab=graph` 正常打开对应 Tab。

## 5. 技术设计

### 5.1 后端（1 处机制改动 + seed 同步）

- `backend/app/services/menu_service.py`：`HIDDEN_MENU_CODES` 增加 `menu:knowledge:project`、`menu:knowledge:platform`、`menu:knowledge:graph`、`menu:knowledge:artifacts`（附注释：子项与知识中心页内 Tab 同源，入口收敛 c165-3）。与 #296–#299 完全同模式：`menu_tree` 对存量库即时生效，权限行保留在库，**无需 Alembic 迁移**。
- `backend/app/seed.py`：注释 4 个菜单行（新库不再生成）；tester/viewer 角色菜单列表同步移除该 4 个 code（与 c165-2 处理 `menu:organization` 同模式）。
- 已确认除 seed.py 外无任何代码引用这 4 个 menu code（`git grep menu:knowledge:` 全仓仅 seed.py 命中）。

### 5.2 前端（1 新增 + 1 重写）

- 新增 `frontend/src/layouts/nav-config.ts`：
  - `PRIMARY_MENU_CODES: ReadonlySet<string>` = `{menu:workbench, menu:requirement, menu:knowledge, menu:testcase, menu:apitest, menu:uitest, menu:schedule, menu:dsh_tasks, menu:ai_config}`
  - `splitMenusByFrequency(menus)` 纯函数：返回 `{ primary, more }`；**fail-safe**：未识别的新 code 一律落入 `more`（以后新增功能不污染高频区）。
- 重写 `MainLayout.tsx` 分组逻辑：
  - 删除现有 knowledge/system/main 三段拆分（注：`systemMenus` 过滤用 `'system'` 对比 `menu:system` code，从未命中，属死逻辑，本次自然清除）。
  - 「更多功能」组：`SidebarGroup` + 现有 `components/ui/collapsible.tsx`；组头行展示 `更多功能` + 数量徽标 + chevron；默认收起。
  - 展开状态持久化：`localStorage` key `sidebar:more-menus-open`（`"1"/"0"`），初始化读取。
  - 活跃自动展开：`location.pathname` 命中 `more` 组任一项的 path 时，该组强制展开（`open || containsActive`）。
  - 图标折叠模式（`group-data-[collapsible=icon]`）下：低频项仍以图标平铺，不做弹层（YAGNI）。
- 数据源 `/system/menus` 不变；命令面板不联动（其 `menuBacked` 仅跟随后端隐藏项，本次分层属展示层）。

### 5.3 部署

合入 main 后 Vercel（前端）与 Railway（后端）均自动部署，无手动窗口；无环境变量/迁移依赖。

## 6. 测试计划

- 后端单测（`test_menu_service*.py` 增补）：构造含 4 个知识子项的权限集 → `menu_tree` 输出不含子项、`menu:knowledge` 保留为叶子节点；`effective_hidden_menu_codes` 包含新 4 项。
- 前端单测（`nav-config.test.ts`）：18 项输入 → primary=9（按 PRIMARY_MENU_CODES）、more=9；未知 code 落 more；空输入安全。
- 组件测试（MainLayout 级）：mock 菜单渲染 → 默认仅见 9 高频 + 更多功能行；点击展开/收起；localStorage 持久化（mock）；`/report` 路由下自动展开且 report 项高亮。
- 硬门禁：后端 `ruff check app/ --select F821` + 受影响 pytest；前端 `npm run typecheck && npm run build` + 受影响 Vitest；PR 前双端全量回归记录基线。

## 7. 上线计划与风险

| 阶段 | 受众 | 成功门槛 |
|------|------|---------|
| 合入 main | 全团队 | required checks 全绿 + audit-ai-pr 通过 |
| 自动部署后走查 | 产品负责人 | 生产侧边栏 10 行默认视图；「更多」展开/持久化/活跃自动展开正常；知识中心 Tab 与旧书签正常 |

风险：低——纯展示层收敛，数据/权限/路由不动；缓解 = 活跃自动展开 + 命令面板兜底 + `?tab=` 深链保留。
