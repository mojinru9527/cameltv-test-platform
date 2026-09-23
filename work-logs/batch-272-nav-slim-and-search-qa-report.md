# Batch 272 — QA 报告

> **QA (🔍)** | Date: 2026-09-23 | Verdict: **PASS**
> 档位：轻量批次（前端导航展示 + 命令面板覆盖对账）

## 可执行门禁

| 命令 | 结果 |
|------|------|
| `npx vitest run src/layouts/nav-config.test.ts src/layouts/AssetsMoreGroup.test.tsx src/components/__tests__/CommandPalette.test.ts --maxWorkers=2` | **38 passed**（本批新增 8 例） |
| `npx vitest run --maxWorkers=2`（**前端全量**） | **168 文件 / 745 例 passed**（基线 737 + 本批 8） |
| `npm run typecheck`（tsc -b） | ✅ 通过 |
| `npm run lint`（eslint --max-warnings=0） | ✅ 通过 |
| `npm run build` | ✅ `✓ built in 9.59s` |
| `pwsh scripts/git/scan-common-bugs.ps1` | HARD **0** |
| **真实浏览器验证**（Playwright + 真实前后端 + 真登录） | ✅ 见下（tester 瘦身 / admin 全景 / 搜索直达 `/schedule`） |

## 逐条验证（A1–A6）

### A1 tester 侧栏被瘦身 ✅

真实渲染（`evidence/batch-272/nav-b272-render.json` + `nav-b272-tester.png`）：

```
导航菜单 | 工作台 | 版本验收（版本验收任务/版本发布包/需求文档）| 结果与缺陷（缺陷管理/报告中心）| 知识中心
专家区 5 | 其余 7 个模块已收进搜索：按 Ctrl/⌘ + K 输入名称直达
```

对账：4 行（7 个 code）+ 保留 5 + 搜索 7 = **19** = `/system/menus` 返回的 tester 菜单数 ✓

### A2 超管不受影响 ✅

同环境下 `drill-admin`：专家区 **13** 项（资产 5 + 引擎与配置 4 + 个人 4）、**无**搜索提示（`searchOnly = 0`）；
对账：4 行（7）+ 13 = **20** = 该角色的菜单数 ✓

### A3 被瘦身模块可搜并直达 ✅

tester 身份按 `Ctrl+K` → 输入「定时」→ 命中「定时任务」→ 点击后 URL = **`/schedule`**（该模块已不在侧栏）。
截图 `nav-b272-tester-palette.png`；机器可读结果在 `nav-b272-render.json`。

### A4 对账：不丢菜单、不重复 ✅

- 单测：`batch-272 选项 B` 用例断言 `侧栏 ∪ searchOnly = 全部菜单`、`Set(codes).size === menus.length`；
- 浏览器：19/20 两个角色逐条对齐（上文）。

### A5 提示在收起状态可见 ✅

`AssetsMoreGroup.test.tsx` 新增两例：`searchOnlyCount=7` 时提示渲染且**分桶项仍未渲染**（说明提示在折叠内容之外）；`searchOnlyCount=0` 时无提示。

> 设计取舍：提示**没有**放进 `CollapsibleContent` —— 默认收起时用户也要能看到"其余模块去哪了"，否则会被误读成"功能被删了"。

### A6 既有约束不回退 ✅

`nav-config.test.ts` 原有断言（一级入口 `≤ PRIMARY_ENTRY_LIMIT`、分桶顺序、fail-safe「更多」桶、每个可见菜单恰好一次）全部保留并通过；前端全量 745 例通过。

## 缺陷列表

| # | 严重级 | 描述 | 状态 |
|---|:------:|------|------|
| D1 | P2 | 专家区列全量模块 + 当前页命中即强制展开 → 用户视角"左侧还是一长串"（`C271-2`） | ✅ 本批修复（非超管只留 5 项） |
| D2 | P2 | 「被隐藏页面可经搜索直达」长期未验证（`C259-1`） | ✅ 本批闭环：单测 2 例 + 真实浏览器搜到并导航到 `/schedule` |
| D3 | P3 | **验证过程中的坑**：用 `context.request` 注入 cookie 登录时，前端引导不认（渲染 guest 菜单），会得出"两个角色一样"的错误结论 | ✅ 已修正为**真实登录表单**；教训写入 Leader 流程回写（E2E 必须走真实登录） |

## bug-guard「未关闭已知风险」表核对（三问）

1. **本批是否新增清单中任一项？** 否——只改渲染与提示；**未新增 useEffect / 网络请求**（前端四条铁律不适用变更面）。
2. **本批是否修复/关闭任一项？** 关闭 `C271-2`、`C259-1`（搜索直达口径）；`C269-3`（节点自愈）与本批无关，保持 Open。
3. **新增路径是否过铁律？** 无新增"用户输入 → 出网/落盘/执行代码"路径；UI 用既有语义类与组件（`SidebarGroup/Collapsible`），未手改 `components/ui/*`。

## CI 分层核对

本批只改 `test-platform-v2/frontend/**` + `work-logs/**` + `C-CONDITIONS.md` → 分类器应判 `backend:false / frontend:true`，跑前端 required；a11y 与覆盖率由每日 `pr-check.yml` 观察兜底。

## 复盘卡

| 计划耗时 | 缺陷(P0/P1/P2/P3) | 返工次数 | 根因分类 | 下次避免 |
|----------|-------------------|----------|----------|----------|
| 2h / ~2.2h | 0/0/2/1 | 2（cookie 注入验证误导 1 次；重复创建已有测试文件 1 次） | 流程（E2E 登录方式）+ 技术债（C259-1 长期未闭环） | ① 前端 E2E **必须走真实登录表单**（cookie 注入不触发内存态，会得到 guest 渲染）；② 写测试前先 `rg --files` 确认文件不存在，别凭"没看到"就新建 |

**技能使用**: `cameltv-bug-guard`（三问）、`cameltv-ui-conventions`（提示样式与可发现性）、`cameltv-agent-team`（轻量批次）。
