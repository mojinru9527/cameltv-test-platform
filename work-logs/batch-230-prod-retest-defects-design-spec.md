# Batch 230 — Design Spec

> **Design (🎨)** | Date: 2026-09-05 | Status: 有条件通过（条件见 §6）
>
> 覆盖 DEF-20260905-001 / -002 / -003 / -004 / -005 / -006 / -007 / -009（-008 已撤回）。
> 上游：[PRD](batch-230-prod-retest-defects-prd-summary.md) · [PM Plan](batch-230-prod-retest-defects-pm-plan.md) · [复测台账](evidence/sports-e2e-20260904/复测结论-20260905.md)
> 全部行号锚点基于 worktree `feature/batch-230-prod-retest-defects`（base `origin/main` = `9c721bc6`），路径相对 `test-platform-v2/`。

---

## 0. 技术体系确认

**shadcn/ui（Radix primitives + Tailwind CSS + CVA）**，非 Ant Design（ADR-0006）。颜色/尺寸走 Tailwind 语义类（`bg-card` `text-muted-foreground` `border` `text-destructive` + Badge/Button `variant`），主题由 `data-theme-id` + `.dark` 驱动，改色改 `src/globals.css` 变量。反馈用 `sonner` toast，图标用 Lucide `size-4`。

本批复用的既有组件（**不新造轮子**）：

| 用途 | 组件 | 位置 | 备注 |
|------|------|------|------|
| 列表四态（Loading/Error/Empty） | `useApi` + `ErrorState` + `DataTable` | `hooks/useApi.ts:35-49`、`components/state/ErrorState.tsx:23-37`、`components/DataTable.tsx:61-81` | ⚠️ `DataTable` **无** `isError` prop（只有 `loading`/`emptyState`），错误态必须由外层承担 |
| 严重级 / 状态徽标（**本批主力**） | `StatusBadge` | `ui/components/StatusBadge.tsx`，由 `@/ui` 导出（`ui/index.ts:55`） | 已内建 `severityMap`（P0-致命/P1-严重/P2-一般/P3-建议 → danger/warning/info/neutral）与 `statusMap`（通过/失败/运行中/待执行/阻断/跳过）；既有消费方 ≥8 处（`pages/defect/DefectTable.tsx`、`pages/executions/*`、`components/data/FixtureStatusBadge.tsx`） |
| 自定义语义徽标 | `Badge` 的 **`tone`** prop | `ui/primitives/Badge.tsx:4,17,22-28` | `tone: 'success'\|'warning'\|'danger'\|'info'\|'neutral'`；⚠️ `variant` 已标注 `@deprecated`（`:19`），新代码一律用 `tone` |
| 搜索框 | `SearchInput` | `components/SearchInput.tsx:6-15` | props: `value/onChange/onSearch/placeholder/clearable/inputClassName` |
| 页头 | `PageHeader` / `PageShell` | `@/ui` | |
| 路由 | `react-router` `^8.3.0` | `package.json:62` | `Link` / `useMatches` / `useLocation` 均由 `react-router` 导出 |

**Token 架构（本批硬性约束，修正 RECIPES §2 在本仓的适用性）**：状态色不是裸色阶，而是 `ui/tokens/semantics.css:27-45` 的派生 Token——

```css
--status-warning-base: oklch(0.68 0.15 75);
--color-status-warning:        color-mix(in srgb, var(--status-warning-base) 35%, var(--foreground));
--color-status-warning-bg:     color-mix(in srgb, var(--status-warning-base) 10%, transparent);
--color-status-warning-border: color-mix(in srgb, var(--status-warning-base) 24%, transparent);
```

文字色混入 `--foreground`（深浅色下自动翻转），底色/边框混入 `transparent`（任意背景成立）→ **Token 层已完成深色适配，组件层不得再写 `dark:` 变体**。因此本批：

- ❌ 禁止 `border-orange-400 text-orange-600 dark:border-orange-500 dark:text-orange-400` 这类手写裸色阶——它绕过 Token 系统，且与 `data-theme-id`（crystal/xlab/column/clay/liquid/obsidian-flow）的主题覆盖机制冲突（对照 `ui/themes/obsidian-flow.css:278` 是按 `.ui-badge-warning` 类名覆盖的，裸类名覆盖不到）。
- ✅ 一律用 `StatusBadge` 或 `<Badge tone="...">`。RECIPES §2 的「补 `dark:` 变体」仅适用于**不得不**用裸色阶的遗留代码，本批不产生新的此类代码。

**本批不新增依赖，不改数据库 Schema，不动响应信封语义**（`R.ok` 包 `ok:false` 是全仓系统性模式，见 §1 D4-2）。

---

## 1. 关键设计决议（PM 显式下放的两项 + 三项派生）

### D1 — S3 阻塞原因承载方式：**复用 `failures`，不新增顶层 `reason` 字段**

PM Plan Task 3.1 下放此项。决议：**复用既有 `failures` 数组，新增 `kind: "plan"` 分类。**

| 判据 | 复用 failures | 新增顶层 reason |
|------|:---:|:---:|
| 是否需要 Alembic 迁移 | 否 | **是**（`models/version_task_run.py:20-38` 无 reason 列） |
| 与 PRD 非目标「本批不做 DB Schema 变更」一致 | ✅ | ❌ |
| 语义是否自洽 | ✅ `failures` 现有形状已带 `kind` 分类，「无可执行目标」本就由它表达（`services/version_task_service.py:373-381` 的 `not_run` 分支） | ⚠️ 顶层 reason 与 per-item failures 双轨 |
| 前端是否需新增渲染路径 | **否**（`pages/version-tasks/[taskId].tsx:146-161` 已渲染 `failures[].message`） | 是 |
| 历史 run 记录兼容性 | ✅ 旧记录 `failures=[]`，读出来就是空 | ⚠️ 旧记录 reason 为 NULL，需前端兜底 |

零采纳项导致的整体阻塞与单项环境阻塞是**同一类事实**（「有条目该跑但没跑成」），用同一结构表达是正确的建模，不是妥协。

### D2 — S7 404 横幅修法：**选 (b) splat 抑制，不做 (a) 前缀段边界改造**

PM Plan Task 7.2 下放此项。决议：**(b)**。

我对 `router/index.tsx` 的**全量路由表**与 `components/legacy/LegacyNoticeBanner.tsx:8-20` 的 `LEGACY_PREFIXES` 做了逐一比对：

```
真实路由（去重）：* /login /register acceptance action-plan agent-workbench ai-config apitest
builds changes contract data dataset defect defect/:id dsh-tasks environment executions gaps
hybrid-run impact integration knowledge lanhu-evidence lanhu-evidence/:id manual metrics mindmap
my-projects notify observe onboarding organizations overview playground project release-bundles
release-bundles/:id release-bundles/:id/panorama report requirement requirement/:id/review
scenarios schedule scope sources system testcase testplan testplan/:id trace uitest
version-mission version-tasks workbench
```

结论：**没有任何真实路由构成前缀越界误命中**——`version-tasks` 不以 `version-mission` 开头；`scenarios` 不以 `schedule` 开头；`testplan` 不以 `testcase` 开头；`defect/:id` 是 `/defect` 的合法子路径（横幅本应显示）。

因此 (a) 想消除的「真实路由被误判为历史入口」今天**不存在**。越界命中只发生在**未匹配路径**上（`/defects`、`/environments`、`/knowledge/xyz`），而它们的成因是：

- `router/index.tsx:503` 的 `{ path: '*', element: <NotFound /> }` 是 MainLayout 路由（`:231-238`）的**子路由**
- → 404 页被 MainLayout 包裹
- → `layouts/MainLayout.tsx:460` 的 `<LegacyNoticeBanner />` 照常渲染在 `<Outlet/>` 之上
- → 用户在「页面不存在」上读到「此页面属于历史入口」

(b) 是结构性判定（**404 页永远不是历史入口**），且能覆盖 (a) 覆盖不了的 `/knowledge/anything`（前缀 + 段边界成立、但仍是 404）；也不依赖前缀表与路由表长期同步。在 (b) 生效后再加 (a)，是为不可能发生的场景加防御代码 → 拒绝。

### D3 — S2 路由形状：`/version-tasks` 变列表页，向导迁到 `/version-tasks/new`

侧栏与 seed 菜单 `menu:versiontask`（`backend/app/seed.py:24`）指向 `/version-tasks`，其语义是「版本验收任务」这个**集合**，不是「创建向导」这个**动作**。当前 `pages/version-tasks/index.tsx:21-208` 只有 3 步向导，`task`/`plan`/`step` 全是裸 `useState`（`:23-30`），刷新即回到第 1 步、已建任务彻底失联——这就是 DEF-20260905-002「创建后界面不可达」的本体。

| 路径 | 现状 | 决议 |
|------|------|------|
| `/version-tasks` | 向导（`VersionTasksPage`） | **列表页**（新 `VersionTaskListPage`） |
| `/version-tasks/new` | 不存在 | **向导**（`VersionTasksPage` 原样迁入，内部逻辑不动） |
| `/version-tasks/:taskId` | 运行页 | 不变（`router/index.tsx:272`） |

React Router v8 按段类型排序（静态 > 动态），`new` 不会被 `:taskId` 吞掉；仍按可读性把 `new` 声明在 `:taskId` 之前。形状与仓库既有习惯一致（对照 `release-bundles` + `release-bundles/:id`）。

全仓仅 2 处硬引用需同步：`pages/workbench/index.tsx:137`（`创建版本任务` → 改指 `/version-tasks/new`）、`pages/version-tasks/index.tsx:198`（step 3 → `/version-tasks/${task.id}`，不变）。

### D4 — S1 快照传输形态：**后端回传已解析对象 `snapshot`，不回传原始 `snapshot_json` 字符串**

| 判据 | `snapshot: ContractSnapshot \| null` | `snapshot_json: str` |
|------|:---:|:---:|
| 前端是否已具备类型 | ✅ `api/contract.ts:3-24` 已定义 `ContractSnapshot`/`ContractRule`/`ContractOutcome`，**当前零引用** | 需新增解析层 |
| RECIPES §5「原始 JSON 裸展示」红旗 | ✅ 规避 | ❌ 需要在组件里 `JSON.parse` + `prettyJson` 兜底 |
| 渲染成结构化表格 | ✅ 直接 map | ⚠️ 解析失败态与空态混淆 |

派生决议 **D4-2**：`modules/aitde/contract/schemas.py:46-54` 的 `ContractVersionRead` 声明了 `snapshot_json: str`，但**全仓（含前端）零引用**——是死 schema。本批把它改成与真实响应一致（`snapshot: ContractSnapshot | None = None`）并挂到版本列表端点作 `response_model`，消除「schema 说有、响应说无」的漂移。**不新增第二个 wire 字段**（不同时回传 `snapshot` 和 `snapshot_json`）。

### D5 — S6 操作人解析位置：**在 `_audit` 内部按 `user_id` 反查稳定登录名，不改任何服务函数签名**

`modules/aitde/scope/service.py:136-157` 的 `_audit` 在 `:150` 硬编码 `username=""`。两条修法：

| 方案 | 改动面 |
|------|--------|
| 透传 username | 改 `_audit` + `analyze_scope`(`:70`) + `review_scope`(`:111-113`) 三个签名 → 连带 `api/v2/mission_scope.py:31-32,64-65` 与既有测试 |
| **内部反查（选定）** | 只改 `_audit` 函数体；`_audit` 已持有 `db` 与 `user_id`，一次 `db.get(User, user_id)` |

选定内部反查并记录 `User.username`。调用频率极低（仅范围分析/评审两个动作），且 `_audit` 既有 `except Exception: pass`（`:156-157`）会让反查失败自动降级为今天的 `username=""`——**不引入新失败模式**。

---

## 2. 组件规格表（逐 Slice）

### S1 · 契约快照可读 + 空契约不可冻结（DEF-20260905-001，P1）

**API 契约变更**（须同步 OpenAPI，AGENTS.md §3.2）：

| 端点 | 变更 |
|------|------|
| `GET /api/v2/missions/{id}/contract` | `data.version` 增加 `snapshot: ContractSnapshot \| null` |
| `GET /api/v2/contracts/{id}/versions` | 每个元素增加 `snapshot`；挂 `response_model=R[list[ContractVersionRead]]`（D4-2） |
| `POST /api/v2/contracts/{id}/freeze` | 新增 **400** 失败分支（见下） |

**后端**：

1. `modules/aitde/contract/service.py:230-241` `_version_to_dict` 增加 `"snapshot": _parse_snapshot(v.snapshot_json)`。
2. 新增模块级私有函数 `_parse_snapshot(raw: str | None) -> dict | None`：`json.loads` + `try/except (TypeError, ValueError)` 返回 `None`。这是**系统边界**（`snapshot_json` 是 `models.py:26-44` 的 Text 列，历史数据可能畸形），防御解析是必要的，不属于「为不可能的场景加处理」。
   ⚠️ `service.py:177,180` 的 `diff()` 已在裸 `json.loads`；本批**不重构 diff**（无对应缺陷），但 `_parse_snapshot` 的写法应可直接被后续批次复用。
3. `service.freeze`（`:140-166`）在 `repository.get_version`（`:153-155`）之后、`repository.freeze_version`（`:157`）之前插入空规则拦截：

```python
snapshot = _parse_snapshot(version.snapshot_json) or {}
if not snapshot.get("rules"):
    raise APIException(
        code=400,
        msg="CONTRACT_FREEZE_EMPTY: 契约快照无有效规则（rules 为空），不可冻结；请先完成 Scope 评审后重新生成",
        http_status=400,
    )
```

**为什么是 400 而不是 409**（关键，Dev 不得自行改成 409）：`frontend/src/lib/conflict.ts` 把 409 绑定为乐观锁/状态冲突语义，`pages/missions/contract.tsx:136-139` 命中 `isConflictError` 时渲染 `StaleConflictBanner`，其文案是「并发冻结/评审状态已变更，请刷新」——对「契约本身是空壳」给出**错误指引**（刷新不会让它变非空）。用 400 则走既有 `toast.error(err.message)` 路径（`:141`），前端**零分支**即可显示真实原因。

> `_freeze_precondition`（`:31-45`）的 409 保持不变——那是真正的状态前置冲突。

**前端** `pages/missions/contract.tsx`：

- `api/contract.ts:26-34` `ContractVersion` 增加 `snapshot?: ContractSnapshot | null`。
- 在 Test Contract 卡（`:218-258`）的版本徽标行（`:225-237`）之后、按钮行（`:238-247`）之前插入**契约内容区**。

**契约规则表**（`snapshot.rules`）：

| 列 | 内容 | 规格 |
|----|------|------|
| 规则 | `title`（主）+ `rule_key`（副，`font-mono text-[11px] text-muted-foreground`，`truncate` + `title` 属性） | `width: '28%'` |
| 类型 | `kind` 中文映射 → `<Badge tone="neutral">`（`variant` 已废弃，见 §0） | `CONTRACT_RULE_KIND_LABEL`（见下） |
| 风险 | `risk_level` → **`<StatusBadge variant={risk_level} />`**（`StatusBadge.tsx:16-21` 已内建 `P0-致命`/`P1-严重`/`P2-一般`/`P3-建议` 与 danger/warning/info/neutral tone） | 四级天然可辨，无需自定义 className |
| 来源 | `source_type` 中文映射，`text-xs text-muted-foreground` | `CONTRACT_SOURCE_TYPE_LABEL` |
| 陈述 | `statement`，`text-sm`，为空时显 `—` | |

```ts
// 与 pages/version-tasks/statusLabels.ts 同风格（RECIPES §3）
export const CONTRACT_RULE_KIND_LABEL: Record<string, string> = {
  BUSINESS_RULE: '业务规则',
  // Dev 须 grep provider.py:210-238 与 enums 补全实际取值，未命中的 fallback 到原值
}
export const CONTRACT_SOURCE_TYPE_LABEL: Record<string, string> = {
  REQUIREMENT_EXPLICIT: '需求明示',
  TESTER_APPROVED: '测试确认',
}
// 渲染一律 {MAP[v] ?? v}，禁止裸英文（Red Flag #3）
```

**必需产出**（`snapshot.required_outcomes`）：轻量列表（非表格），每行 `outcome_key`（mono）+ `statement`，`space-y-1`，`text-sm`。

**四态**（详见 §4）——其中 Error 态是**新增要求**：当前 `:70-71` 的 `.catch(() => [] as Ambiguity[])` / `.catch(() => null)` 把接口失败静默降级为空态，正是 Red Flag #4，也是「空壳无法自证」的原因之一。本批必须改为保留 error 并渲染 `ErrorState` + 重试。

**同文件顺带修（走查发现 P2-4）**：`:188` 的歧义严重级 `<Badge variant="secondary">{a.severity}</Badge>` 未走四级梯度（P0/P1 同色，Red Flag #1）。改为 `<StatusBadge variant={a.severity} />`——与上面 `risk_level` 用的是同一个组件、同一份 `severityMap`，零新增代码即可同时获得四级可辨色与 `P0-致命` 这类中文标签。S1 本就在此文件引入 `StatusBadge`，属同一处决断，一并改。

### S2 · 版本任务列表可达（DEF-20260905-002，P1）

**路由**（按 D3）：`router/index.tsx:271` 拆为三条，`VersionTaskListPage` 与 `VersionTasksPage` 各自 lazy import（`:44-45` 同风格）。

**新页面** `pages/version-tasks/list.tsx`：

```
PageShell title="版本验收任务"
└── Card > CardContent
    ├── toolbar（DataTable 的 toolbar slot）
    │   flex flex-wrap items-center gap-2
    │   ├── Select 状态筛选（h-9 w-[130px]，aria-label="按状态筛选"，选项来自 TASK_STATUS_LABEL）
    │   ├── SearchInput（placeholder="搜索标题或版本"，inputClassName="w-[220px]"，clearable）
    │   └── Button primary ml-auto「新建版本任务」→ Link /version-tasks/new
    └── DataTable
        columns / data / rowKey / loading / emptyState / onRowClick / ariaLabel
```

| 列 | 内容 | 规格 |
|----|------|------|
| 标题 | `title`，`truncate` + `title` 属性 | `sortable` 关 |
| 版本 | `version` → `<Badge tone="neutral">` | `width: '110px'` |
| 状态 | `TASK_STATUS_LABEL[status] ?? status` → `<Badge tone={TASK_STATUS_TONE[status] ?? 'neutral'}>` | ⚠️ `task.status` 取值是 `draft/plan_review/approved/executing/executed/verdict/released/blocked/cancelled`，**不在 `StatusVariant` 内**，不得直接塞给 `StatusBadge`（TS 会报错）；须用 `TASK_STATUS_LABEL` + `TASK_STATUS_TONE` 两个字典，同放 `statusLabels.ts` |
| 结论 | `verdict` 中文映射，空显 `—` | `width: '100px'` |
| 覆盖 | `coverage.pass / (pass+fail+skip+blocked)`，无数据显 `—` | `width: '90px'` |
| 更新时间 | `updated_at` 本地化短格式 | `width: '140px'` |
| 操作 | `Link` 到 `/version-tasks/${id}`，`Button size="sm" variant="ghost"` + `ArrowRight size-4` | `ml-auto` |

- `onRowClick={(row) => navigate(\`/version-tasks/${row.id}\`)}`；行高由 `DataTable` 既有样式保证 ≥36px（Red Flag #7）；操作列按钮 `h-8`。
- `emptyState={{ title: '暂无版本验收任务', description: '创建任务后可在此跟踪方案评审、执行与放行结论。', action: { label: '新建版本任务', onClick: () => navigate('/version-tasks/new') } }}`
- `ariaLabel="版本验收任务列表"`。
- 数据获取：`useApi((signal) => listVersionTasks(status, keyword, signal), [status, debouncedKeyword])`，配 `useDebouncedValue`（`hooks/useDebouncedValue.ts` 已存在）避免逐字符请求（AGENTS.md §3.4 无 N+1 / 重复请求）。
- 错误态：`if (isError) return <ErrorState error={error} onRetry={refetch} secondaryAction={{ label: '返回工作台', onClick: () => navigate('/workbench') }} />`。**不用 `AsyncState` 包 `DataTable`**——两者各有 skeleton，会叠加；`DataTable` 自带 `loading`，错误态由外层显式分支承担（§0 已注明 `DataTable` 无 `isError`）。

**状态字典决议（消除 Red Flag #3 复发根源）**：`TASK_STATUS_LABEL` 当前是 `pages/version-tasks/[taskId].tsx:7-17` 的**局部常量**。新建 `pages/version-tasks/statusLabels.ts`，集中导出：

| 导出 | 用途 | 消费方 |
|------|------|--------|
| `TASK_STATUS_LABEL` | 任务状态中文（从 `[taskId].tsx:7-17` 迁出） | `list.tsx`、`[taskId].tsx:128` |
| `TASK_STATUS_TONE` | 任务状态 → `BadgeTone` | `list.tsx` |
| `VERDICT_LABEL` | 放行结论中文（`''/pass/blocked/conditional`，对照 `version_task_service.py:37` `VALID_VERDICTS`） | `list.tsx` |
| `FAILURE_KIND_LABEL` | 失败分类中文（`business/environment/plan`） | `[taskId].tsx:152` |
| `FAILURE_KIND_TONE` | 失败分类 → `BadgeTone` | `[taskId].tsx:152` |
| `RUN_STATUS_TO_VARIANT` | `run.status` → `StatusVariant`（`done→pass`、`failed→fail`，其余同名） | `[taskId].tsx` 运行状态徽标 |

**判定规则**：取值落在 `StatusVariant`（`pass/fail/running/pending/blocked/skipped`）或 `SeverityVariant`（`P0-P3`）内的 → **直接用 `StatusBadge`**，它自带中文标签与 tone（证据状态 `e.status`、契约 `risk_level`、歧义 `severity` 都属此类，无需字典）。取值超出这两个联合类型的（`task.status`、`run.status`、`verdict`、`failure.kind`）→ 走本文件字典。

**禁止两处各写一份字典**——历史上裸英文状态标签反复返工正是因为字典分散（RECIPES §3）。放页面域内而非 `api/versionTask.ts`，避免展示层词汇污染 API 层。

**API 签名扩展**：`api/versionTask.ts:81-89` `listVersionTasks(status, keyword)` 增加第三形参 `signal?: AbortSignal`，透传给 `v1.get(url, { signal })`。没有它，列表页无法在卸载/依赖变更时取消请求 → 违反 AGENTS.md §3.4 useEffect cleanup 铁律。

**侧栏锚点（D2 同批，两处 bare `<a>`）**：

`components/ui/sidebar.tsx:660` 的 `const Comp = asChild ? Slot : "a"` → 未传 `asChild`/`href` 时渲染**无 href 的 `<a>`**：无隐式 link role、不可 Tab 聚焦、不能中键/Ctrl 点击、不能复制链接。

| 文件:行 | 现状 | 改法 |
|---------|------|------|
| `layouts/MainNavRows.tsx:62-69` | `SidebarMenuSubButton onClick={() => onNavigate(child.path, child.name)}` | `asChild` + `<Link to={child.path}>`，**移除 onClick** |
| `layouts/NavigationMenuItems.tsx:107-114` | `SidebarMenuSubButton onClick={() => goTo(child.path, child.name)}` | `asChild` + `<Link to={child.path} onClick={closeMobile}>` |

两处改法**不同**，原因必须理解后再动手：

- `MainNavRows` 的 `onNavigate` 实参是 `MainLayout.tsx:138-140` 的 `navigateMenu`，函数体只有 `navigate(path || '/')`——**纯导航，无副作用**。Link 化后必须删掉 onClick，否则 `<Link>` 与 `navigate()` 双重导航。
- `NavigationMenuItems` 的 `goTo`（`:76-79`）= `onNavigate(path, label)` **+ `if (isMobile) setOpenMobile(false)`**——**有移动端关闭抽屉的副作用**。直接删 onClick 会导致移动端点击后抽屉不收起（回归）。故新增 `const closeMobile = () => { if (isMobile) setOpenMobile(false) }`，Link 只挂这个纯副作用处理器，导航交给 `<Link>`。
- `NavigationMenuItems` 的 `SidebarMenuButton` 行（`:89-98`、`:125-129`）**保持 `goTo` 不动**——它们渲染为 `<button>`（`sidebar.tsx:503`），可键盘操作，只是没有 href。

**与 DEF-20260904-001 的边界（QA 报告须原样写明）**：

- DEF-20260904-001 测得「5 个锚点 `href=null role=null`」= `layouts/nav-config.ts:25-30` 的 5 个分组子项（`menu:versiontask` / `missions` / `versionmission` / `report` / `defect`），与 `MainNavRows.tsx:62` 一一对应。
- 本批修复后这 **5 个锚点即消除**（获得真实 href + link role + 键盘可达）。
- `NavigationMenuItems.tsx:107`（资产与更多分桶的子项）是**同一根因的额外实例**，一并修复——否则下一轮复测必然以同一措辞重新立案。
- DEF-20260904-001 的**剩余部分**（`SidebarMenuButton` 渲染为 `<button>`、无 href、不可中键打开）不在本批范围，留待后续批次。

### S3 · 一键运行阻塞可见（DEF-20260905-003，P1）

**后端** `services/version_task_service.py:328-427`：

1. **合成阻塞项**（按 D1）。在 `:396` 的判定处，`adopted_items` 为空时向 `failures` 追加一条：

```python
if not adopted_items:
    failures.append({
        "item_id": 0,
        "title": "整体运行",
        "kind": "plan",
        "evidence": "",
        "message": "本任务方案中没有已采纳/已修订的条目（adopted/modified），因此没有可执行目标；"
                   "请先在建任务向导中采纳至少一条方案条目。",
        "http_status": None,
    })
```

新 `kind="plan"` 与既有 `business`（`:368`）/ `environment`（`:377,385`）并列，语义为「方案侧无可执行项」，区别于「环境侧无可执行 URL」。

2. **计数不改算术**。`run.total` 仍为 `len(adopted_items)`（`:345,414`），`run.blocked` 仍为逐项累加值（`:356,375,408`）。零采纳项时 `total=0, blocked=0` 是**事实正确**的——没有任何条目被阻塞，是整个运行没有标的。把 `blocked` 伪造成 1 会造成 `blocked > total` 的自相矛盾。阻塞事实由 `run.status="blocked"`（`:396-397`，已存在）+ 合成失败项承载。

3. **`task.status` 去无条件化**（`:424`）：

```python
task.status = "executed" if run_status in ("done", "failed") else "blocked"
```

状态机 `executing → blocked` 已被 `service.py:29` 允许；`TASK_STATUS_LABEL.blocked = '已阻塞'` 已存在（`[taskId].tsx:15`）。

> ⚠️ **回归面（Dev 必须跑全量版本任务 pytest，QA 必须记录退出码）**：`:418-423` 的 coverage 回写（C217-1）、`releaseTask` / `buildReleasePackage` / `transitionVersionTask` 对 `task.status` 的合法输入集合。放行判定 `isPassVerdictAllowed`（`[taskId].tsx:19-21`）要求 `passed>0 && failed===0 && skipped===0 && blocked===0`，零采纳项场景 `passed=0` → 放行按钮仍禁用，符合预期。

**前端** `pages/version-tasks/[taskId].tsx`：

| # | 位置 | 改动 |
|---|------|------|
| 1 | `:58-69` `handleRun` | 按 `run.status` 分支：`done` → `toast.success`；`failed` / `blocked` → `toast.error`。**禁止无条件 success**（这是缺陷本体）。`blocked` 文案：`运行被阻塞：没有可执行的方案条目`；`failed` 文案：`运行完成：${passed} 通过 / ${failed} 失败` |
| 2 | `:152` | `<Badge variant="destructive">{f.kind}</Badge>` → 中文映射 + 按 kind 分级 tone（见下方决议） |
| 3 | `:133` | `total === 0` 时 `覆盖 —`，不显 `覆盖 0/0`（「0/0」会被读成「跑了 0 个且通过 0 个」） |
| 4 | `:148` | 标题「失败分类」→ 含 `plan`/`environment` 项时改「未通过 / 阻塞明细」（把阻塞叫失败会误导分诊） |
| 5 | `:168` | `<Badge variant={e.status === 'pass' ? 'secondary' : 'destructive'}>{e.status}</Badge>` 裸英文（走查 P2-3）→ **直接换 `<StatusBadge variant={e.status} />`**。`StatusBadge` 的 `statusMap`（`StatusBadge.tsx:7-14`）已覆盖 `pass/fail/running/pending/blocked/skipped` 的中文标签与 tone，**不需要新造 `EVIDENCE_STATUS_LABEL` 字典**。当前写法把非 pass 一律染红（`skipped` 也显示为失败色），换组件后自动纠正 |
| 6 | `:140-143` | 四个计数 Badge 用的是已废弃的 `variant`；本行只在**已触碰的**行内改为 `tone`，不做全文件迁移（避免扩大 diff） |

**toast 色调决议**：`blocked` 用 `toast.error` 而非 `toast.warning`。仓库既有反馈词汇只有 success/error（`[taskId].tsx:62,65,75,77,86,88,113,115,120`；`missions/contract.tsx:89,92,101,104,113,120,132,141`），引入第三种色调会破坏一致性，且阻塞对用户而言就是「这次运行没产出结果」的失败体验。

**kind 分级 tone（Red Flag #1 同类：不可辨）**：当前 `business` / `environment` 全用 `destructive`，把「没东西可跑」渲染成「跑挂了」。

```ts
// pages/version-tasks/statusLabels.ts（S2 决议新建的共享字典文件）
export const FAILURE_KIND_LABEL: Record<string, string> = {
  business: '业务失败',
  environment: '环境阻塞',
  plan: '方案无可执行项',
}
export const FAILURE_KIND_TONE: Record<string, BadgeTone> = {
  business: 'danger',     // 质量问题 → 红
  environment: 'warning', // 环境阻塞 → 橙，非质量问题
  plan: 'warning',        // 方案无可执行项 → 橙，同上
}
// 渲染：<Badge tone={FAILURE_KIND_TONE[f.kind] ?? 'neutral'}>{FAILURE_KIND_LABEL[f.kind] ?? f.kind}</Badge>
```

**不写裸色阶、不写 `dark:` 变体**——`tone="warning"` 落到 `ui-badge-warning bg-status-warning-muted text-status-warning`（`Badge.tsx:24`），其色值由 `--color-status-warning*` 派生 Token 提供，已在 Token 层完成深浅色适配（见 §0 Token 架构）。主题包（如 `ui/themes/obsidian-flow.css:278`）按 `.ui-badge-warning` 类名覆盖，用 tone 才能吃到主题；手写 `border-orange-400` 会绕过整套机制。

**`run.status` 徽标同理**：`:141` 的失败计数与新增的阻塞提示统一走 tone。注意 `run.status` 的取值是 `done|failed|blocked|running|pending`（`version_task_service.py:396-403`），与 `StatusVariant`（`pass|fail|running|pending|blocked|skipped`）**不完全对齐**——`done`/`failed` 不在其中。故 run.status 不得直接塞给 `StatusBadge`，须先经一层显式映射：

```ts
const RUN_STATUS_TO_VARIANT: Record<string, StatusVariant> = {
  done: 'pass', failed: 'fail', blocked: 'blocked', running: 'running', pending: 'pending',
}
// <StatusBadge variant={RUN_STATUS_TO_VARIANT[run.status] ?? 'pending'} />
```

`StatusBadge` 的 `variant` prop 是必填且类型受限（`StatusVariant | SeverityVariant`），传未映射的 `done` 会 TS 报错——这层映射是类型系统强制的，不是过度设计。

**Schema 同步**：

- `backend/app/schemas/version_task.py:199-214` `VersionTaskRunOut` 不变（`failures` 已是 `list[dict]`）。
- `frontend/src/api/versionTask.ts:144` `failures` 元素类型补 `http_status?: number | null`（后端 `:371,380,388` 已在写，前端未声明），`kind` 收窄为 `'business' | 'environment' | 'plan' | (string & {})` 以保留字典 fallback 能力。

### S4 · AI 自动发现假成功（DEF-20260905-004，P2）

**类型** `api/aiConfig.ts:75-79`：

```ts
export async function discoverAiModels(
  body: { api_base_url: string; api_key: string },
): Promise<{
  ok: boolean
  models?: string[]
  count?: number
  /** 可执行中文提示，见 services/ai_config_service.py:272-312 */
  error?: string
  /** 错误类别，决定是否属于 Key 问题 */
  kind?: string
}>
```

⚠️ **不声明 `detail`**：`ai_config_service.py:272-312` 的 discover 分支从不返回 `detail`（只有 `:262-270` 的 test-connection 返回）。声明一个后端永不发送的字段就是假契约——这正是本缺陷的成因类型。对照 `testAiProviderConnection`（`:57-69`）是**正确**写法，可直接照抄其注释风格。

**逻辑** `pages/ai-config/index.tsx:242-270` `handleDiscoverModels`：

1. `res.ok === false` → `toast.error(res.error || '模型发现失败', { duration: 10_000 })` 后 **`return`**，不得落入 `:254` 的合并分支。当前代码 `res?.models ?? []` 在失败时得到 `[]`，与既有模板模型合并后 `merged.length === 5`，于是走到 `:263` 的 `toast.success` ——**这就是假成功**。
2. **不给 action 按钮**。`:207-215` 的「更新密钥」action 是打开*已存在*提供方的编辑抽屉；discover 发生在新建/编辑抽屉**内部**，再开一次会嵌套。只给 10s 长时错误提示（`duration: 10_000` 与 `:205` 一致）。
3. **成功文案改用后端 `res.count`**。当前 `:263`「已拉取厂商全量模型（共 ${merged.length} 个）」里的数字是既有模板模型数，实际可能拉取 0 个——假成功的残留。改为：`已拉取 ${res.count} 个模型，合并后共 ${merged.length} 个`。
4. `:255-257` 的 `merged.length === 0 → toast.error('未发现可用模型')` **保留不动**。在 `res.ok === true` 之后，后端保证 `count ≥ 1`（`:304-306`），此分支实际不可达；但它是既有代码，删除属无关清理。

**后端不改**（见 §0 / D4-2 同族理由）：`api/v1/ai_config.py:106-116` 用 `R.ok(...)` 无条件包裹业务失败是全仓系统性模式（同构点：`services/ffmpeg_service.py:98-142`、`services/test_plan_service.py:711-787`、`api/v1/lanhu_evidence_jobs.py:100-114`、`modules/aitde/.../cleanup_service.py`）。改信封语义会波及所有消费端，PRD 已列为非目标。本批只在消费端补 `ok` 判定。

**走查确认（无需改动）**：`discoverAiModels` 是**唯一**的假成功点。其余内层 `ok` 消费端均已正确判定：`pages/ai-config/index.tsx:198-200`（test-connection）、`pages/lanhu-evidence/components/LanhuReloginDialog.tsx:73-81`、`components/data/DataSourceConnectionBadge.tsx`。

### S5 · 缺陷搜索支持编号（DEF-20260905-005，P2）

**后端** `services/defect_service.py:87-88`：

```python
if keyword:
    base = base.where(
        or_(Defect.title.contains(keyword), Defect.defect_id.contains(keyword))
    )
```

`or_` 从 `sqlalchemy` 导入。

> 🔴 **唯一正确性风险点**：`project_id` 过滤（`:80`）必须留在 `or_` **之外**。`base` 是 `.where()` 累加（AND 语义），当前写法天然满足；但若 Dev 把 project_id 也塞进 `or_` 就会跨项目泄漏数据。**必须写一条测试：keyword 命中另一项目的 `defect_id` 时返回空。**

**不含 `external_id`**（`models/defect.py:28`，禅道/Jira 编号）：DEF-20260905-005 的「编号」= 界面展示的 `DEF-YYYYMMDD-NNN`（`_generate_defect_id`，`:33-42`），`external_id` 不在列表作为编号展示，纳入会无谓扩大匹配面。已考虑并否决。

**文案**：

- `pages/defect/DefectFilterBar.tsx:71` placeholder「搜索缺陷标题」→「**搜索标题或缺陷编号**」。
- `api/v1/defect.py:69` 的 `keyword: str = Query("")` 补 description（OpenAPI 文案同步），**不新增查询参数**——前端 `pages/defect/index.tsx:26-40` 的单一 debounce keyword 结构保持不变。

### S6 · 范围评审审计操作人（DEF-20260905-006，P2）

按 D5，只改 `modules/aitde/scope/service.py:136-157` 的 `_audit` 函数体：

```python
from app.models.user import User  # 模块顶部既有导入区

user = db.get(User, user_id) if user_id else None
username = user.username if user else ""
write_audit(
    db,
    user_id=user_id,
    username=username,   # ← 原为硬编码 ""
    project_id=project_id,
    action=action,
    target=f"mission:{mission_id}",
    detail=detail,
)
```

**命名口径最终决议**：用稳定登录名 `username`。初版设计曾选择 `nickname or username`；QA 通过跨模块列表对比和真实浏览器复测发现，同一管理员会在不同审计来源显示为“超级管理员”和 `admin`，不利于检索与追责，因此收紧为不可由用户随时修改的登录名。

| 口径 | 模块 |
|------|------|
| `cu.user.username or ""` | `api/v1/defect.py:25`、`integration.py:30`、`notify.py:20`、`project.py:33`、`report.py:24`、`auth.py` 多处 |
| `(cu.user.nickname or cu.user.username)` | `convergence.py:18`、`knowledge_artifacts.py:48`、`knowledge_core.py:47`、`knowledge_graph.py:51`、`onboarding.py:28`、`release_bundles_core.py:40` |

选择 `username`：审计字段的首要目标是稳定身份识别，而非展示友好度；这也与缺陷、集成、通知、项目、报告和认证等审计来源保持一致。测试必须覆盖“用户同时有昵称”时仍写入登录名，并覆盖未知用户时沿用既有空串降级行为。

⚠️ **口径统一属 DEF-20260904-015（未修复，本批不覆盖）**。本批只让范围评审审计**有**操作人，不统一全仓口径。QA 报告须显式记录这一点，避免被读成 -015 已修。

**`ip` 缺失不改**：`_audit` 的 `write_audit` 调用（`:147-155`）**根本没有传 `ip` 参数**（对照 `api/v1/defect.py:32` 传了 `ip=req.client.host`）。补 IP 需要 `Request` 对象，而 `_audit` 位于 service 层、拿不到请求上下文——补齐就得改签名，与 D5 决议冲突。记为遗留，归入 -015 同批处理。

**走查发现（本批不修，建议 Leader 开 C 条件）**：全仓另有两处 `write_audit` **完全无用户归属**：

| 位置 | action | 问题 |
|------|--------|------|
| `services/production_operation_guard.py:65` | `production_operation:allowed` | **生产环境操作审计无操作人** |
| `services/api_execution_service.py:1409` | `apitest:execute_prod` | **生产环境执行审计无操作人** |

两处调用点上下文均无 user 对象（前者只有 `user_permissions`，后者无用户上下文），修复需把用户身份透传进服务层 = 独立批次工作量。**严重度高于 DEF-20260905-006**（生产操作可追溯性是合规项，不只是显示问题），建议 Leader 单开 C 条件而非并入本批。

### S7 · 拼写 + 404 横幅边界（DEF-20260905-007 / -009，P3）

**拼写**：`pages/missions/contract.tsx:175`「歧义（Ambiguitity）」→「歧义（**Ambiguity**）」。Dev 须 `grep -rn "Ambiguitity"` 全仓确认无其他实例（后端 `/ambiguities` 路由拼写正确）。

**横幅**（按 D2 选 (b)）：`components/legacy/LegacyNoticeBanner.tsx`

```tsx
import { Link, useLocation, useMatches } from 'react-router'

export function LegacyNoticeBanner() {
  const { pathname } = useLocation()
  const matches = useMatches()
  const aitdeEnabled = useAitdeV3Enabled()
  if (!aitdeEnabled) return null
  // 404 splat 叶子（router/index.tsx:503）不是历史入口，不显示收敛提示。
  if (matches[matches.length - 1]?.params?.['*'] !== undefined) return null
  if (!LEGACY_PREFIXES.some((p) => pathname.startsWith(p))) return null
  ...
}
```

- `useMatches()` 返回当前 URL 的**完整匹配分支**（含 `<Outlet/>` 渲染的叶子），与调用点在树中的位置无关——横幅虽在 `MainLayout.tsx:460`，仍能读到 splat 叶子。
- 判据用 `params['*'] !== undefined` 而非 pathname 字符串比较，避免与未来嵌套 splat 冲突。
- `LEGACY_PREFIXES`（`:8-20`）与 `:26` 的前缀匹配**保持原样**（D2 已论证无需改造）。
- 早退顺序：`aitdeEnabled` → splat → 前缀。splat 判定放在前缀判定**之前**，因为它是更强的结论。

⚠️ **Dev 必须实测四条路径**（这是本条唯一的验证手段，单测覆盖不到 `useMatches` 的真实分支）：

| 路径 | 预期 |
|------|------|
| `/defects`（未知，前缀越界） | 横幅**隐藏** |
| `/defect`（真实路由） | 横幅**显示** |
| `/knowledge`（真实路由） | 横幅**显示** |
| `/nonexistent`（未知，无前缀关系） | 横幅**隐藏** |

**404 页相似模块推荐不做**：`pages/NotFound.tsx:5-16` 为纯静态，`components/CommandPalette.tsx:67-71` 有关键词索引但未与 NotFound 接线。DEF-20260904-004 的「无相似模块建议」属该批遗留，PRD 已列为非目标。

---

## 3. 布局与响应式

| Slice | <768px（单列） | md 768–1023 | lg 1024+ |
|-------|---------------|-------------|----------|
| S1 契约内容区 | 规则表横向滚动（`DataTable` 自带 `overflow` 容器 + `ariaLabel`）；`statement` 列 `hidden md:table-cell` | 全列显示 | 全列显示 |
| S2 列表页 | toolbar `flex-wrap`，Select 与 SearchInput 换行；主按钮 `w-full` | toolbar 单行，按钮 `ml-auto` | 同 md |
| S3 明细卡 | badge 行 `flex flex-wrap items-center gap-2` 防溢出；行内按钮组换行 | 单行 | 单行 |
| S7 横幅 | 既有 `flex items-start gap-3 px-4 py-3` 不变 | 不变 | 不变 |

触控目标（Red Flag #7）：列表主点击区 ≥36px；所有行内动作按钮 `size="sm"` + `h-8`；禁止 `h-6`/`h-7` 行内动作。

---

## 4. 状态设计核对（四态）

| 组件 | Loading | Empty | Error | 未启用(503) |
|------|---------|-------|-------|-------------|
| S1 契约内容区 | 既有 `Skeleton`（`contract.tsx:148-155`），扩展为含内容区骨架 | **三种空须可区分**：① `contract === null` →「尚未生成 Test Contract」+ 生成按钮（既有 `:250-255`）② `snapshot === null` →「契约快照解析失败或为空，请重新生成」③ `rules.length === 0` →「快照无有效规则：请确认 Scope 已批准，或配置可用 AI 提供方后重新生成」（此态下**冻结按钮必须禁用**并给出 `title` 说明） | 🆕 **必须新增**：`:70-71` 的 `.catch(() => [])` / `.catch(() => null)` 改为保留 error，渲染 `ErrorState` + `onRetry={reload}`（Red Flag #4） | N/A（AITDE 开关由 `useAitdeV3Enabled` 在路由层处理） |
| S2 版本任务列表 | `DataTable loading` + `loadingRows={5}` | `emptyState`（标题 + 描述 + 「新建版本任务」action） | `ErrorState` + `onRetry={refetch}` + `secondaryAction` 返回工作台 | N/A |
| S3 运行明细 | `handleRun` 期间 `Button disabled={loading}`（既有 `:132`） | `latest` 为空 → 不渲染明细区（既有 `:136`）；`failures.length === 0` → 不渲染明细（既有 `:146`） | `toast.error`（既有 `:65`）+ 🆕 `blocked` 分支必须给可见原因（合成失败项），**不得静默** | N/A |
| S4 模型发现 | `discovering` → 按钮 disabled（既有） | N/A | 🆕 `res.ok === false` → `toast.error(res.error, {duration: 10_000})` | N/A |
| S5 缺陷搜索 | 既有列表 loading | 「未找到匹配的缺陷」（文案须同时覆盖标题与编号） | 既有 | N/A |
| S7 横幅 | N/A | N/A | N/A | `aitdeEnabled === false` → `return null`（既有 `:25`） |

---

## 5. 设计 QA 走查发现（均附文件:行号）

> 走查范围＝本批触碰的文件及其直接邻居。P0/P1 为本批**必须**处理项，P2 为同文件顺带项，P3 为记录不处理。

### 🔴 P1-1 静默吞错把「加载失败」伪装成「没有数据」
`pages/missions/contract.tsx:70-71` — `.catch(() => [] as Ambiguity[])` 与 `.catch(() => null)` 丢弃错误对象。
→ **建议**：改为保留 error 状态并渲染 `ErrorState` + 重试。**本批必须修**（S1 四态要求），属 Red Flag #4。

### 🔴 P1-2 无条件成功反馈（DEF-20260905-003 本体）
`pages/version-tasks/[taskId].tsx:62` — `toast.success(\`运行完成：${run.passed} 通过 / ${run.failed} 失败\`)` 不判 `run.status`。
→ **建议**：按 `done`/`failed`/`blocked` 三分支。**本批必须修**（S3）。

### 🔴 P1-3 空契约可被冻结，且冻结后 Mission 直接跳到 CONTRACT_FROZEN
`modules/aitde/contract/service.py:140-166` — `freeze` 校验了 `confirm`(`:149`)、Scope/歧义前置(`:151`)、版本存在(`:153-155`)，**唯独不校验快照非空**；`:158-159` 随后把 `mission.current_contract_version_id` 与 `mission.status = "CONTRACT_FROZEN"` 一起写死。空壳契约一旦冻结，主链会带着「已有标准答案」的假状态推进到场景阶段。
→ **建议**：按 §2 S1 加 400 拦截。**本批必须修**，这是三条 P1 中影响最深远的一条。

### 🟠 P2-1 失败分类 badge 裸英文
`pages/version-tasks/[taskId].tsx:152` — `<Badge variant="destructive">{f.kind}</Badge>` 直接渲染 `business`/`environment`，与全中文界面割裂。
→ **建议**：`FAILURE_KIND_LABEL` + `tone`。**本批顺带修**（S3 同文件同行）。

### 🟠 P2-2 阻塞与失败同色，不可辨
同上 `:152` — `environment`（环境阻塞，非质量问题）与 `business`（业务失败）都用 `destructive`，分诊时无法区分「跑挂了」和「没东西可跑」。
→ **建议**：按 §2 S3 的 `FAILURE_KIND_TONE`（danger vs warning）。**本批顺带修**。Red Flag #1；深色适配由 Token 层负责，无需手写 `dark:`（§0）。

### 🟠 P2-3 证据状态 badge 裸英文且非 pass 一律染红
`pages/version-tasks/[taskId].tsx:168` — `<Badge variant={e.status === 'pass' ? 'secondary' : 'destructive'}>{e.status}</Badge>`：裸英文，且把 `skipped` 也渲染成失败红。
→ **建议**：换 `<StatusBadge variant={e.status} />`，仓库既有 `statusMap` 直接覆盖，无需新字典。**本批顺带修**（1 行替换，同时纠正染色错误）。

### 🟠 P2-4 歧义严重级未走四级梯度
`pages/missions/contract.tsx:188` — `<Badge variant="secondary">{a.severity}</Badge>`，P0 与 P1 同色。
→ **建议**：换 `<StatusBadge variant={a.severity} />`。**本批顺带修**（S1 已在同文件为 `risk_level` 引入该组件）。Red Flag #1。

### 🟡 P3-1 content_hash 截断无提示
`pages/missions/contract.tsx:232-236` — `content_hash.slice(0, 12)` 无 `title` 也无 `aria-label`，用户无法得知完整值或这是哈希前缀。
→ **建议**：加 `title={contract.version.content_hash}` 与 `aria-label={\`内容哈希 ${...}\`}`。**本批不修**（无对应缺陷，记录待后续）。

### 🟡 P3-2 原生 `window.prompt` 与设计语言割裂
`pages/version-tasks/[taskId].tsx:110`（风险点输入）、`pages/version-tasks/index.tsx:172,177`（修改/追问说明）——三处用浏览器原生 prompt，无法主题化、无校验、无多行、移动端体验差，且**阻塞主线程**。
→ **建议**：换 `Dialog` + `Textarea`。**本批不修**（无对应缺陷；D3 把向导迁到 `/new` 时**不得顺手重构**，避免扩大回归面）。

### 🟡 P3-3 死 schema 与真实响应漂移
`modules/aitde/contract/schemas.py:46-54` — `ContractVersionRead` 声明 `snapshot_json: str`，全仓零引用。
→ **建议**：按 D4-2 改为 `snapshot` 并挂 `response_model`。**本批顺带修**（S1 已在改同一响应形状）。

---

## 6. 设计签核

**结论：有条件通过。**

S1–S7 的实现路径均已落到 file:line，两项 PM 下放决议（D1 复用 failures、D2 splat 抑制）已给出可验证的论证，Dev 可直接编码。放行条件（不满足则 QA 应判 NEEDS WORK）：

| # | 条件 | 理由 |
|---|------|------|
| 1 | S1 必须落地 Error 态（P1-1），不得只加内容渲染 | 否则「契约页空白」的成因仍不可自证，等于把缺陷从「看不到内容」改成「看不到错误」 |
| 2 | S1 空契约拦截必须用 **400**，不得用 409 | 409 会触发 `StaleConflictBanner` 给出「请刷新」的错误指引（`lib/conflict.ts` + `contract.tsx:136-139`） |
| 3 | S3 必须同时落地 `FAILURE_KIND_LABEL` 中文映射与 danger/warning 的 tone 分级（P2-1、P2-2），且**不得手写裸色阶或 `dark:` 变体**（§0 Token 架构） | 否则只是把「假成功」换成「假阻塞」——用户看到 `blocked` 但读不懂 `kind: plan` |
| 4 | S2 侧栏两处改法**不得互换**：`MainNavRows` 删 onClick，`NavigationMenuItems` 保留 `closeMobile` | 前者双导航，后者移动端抽屉不收起 |
| 5 | S5 的 `project_id` 过滤必须在 `or_` 之外，并有跨项目隔离测试 | 唯一的数据泄漏风险点 |
| 6 | S7 必须实测四条路径（`/defects` 隐藏、`/defect` 显示、`/knowledge` 显示、`/nonexistent` 隐藏） | `useMatches` 的分支无法靠单测覆盖 |
| 7 | 后端响应形状变更（`snapshot`）必须同步 OpenAPI | AGENTS.md §3.2 |

**移交 Leader 的走查产出（本批不做，建议开 C 条件）**：

1. **生产操作审计无操作人**（严重度高于 DEF-20260905-006）：`services/production_operation_guard.py:65`、`services/api_execution_service.py:1409`。需把用户身份透传进服务层，属独立批次。
2. **`SidebarMenuButton` 无 href**：DEF-20260904-001 的剩余部分，`layouts/MainNavRows.tsx:36-44`、`layouts/NavigationMenuItems.tsx:89-98,125-129` 渲染为 `<button>`，不可中键/新标签打开。
3. **原生 `window.prompt` 三处**（P3-2）。
4. **审计操作人命名口径不统一**：DEF-20260904-015，两种口径各 6–7 个模块。

**技能使用**：`cameltv-ui-conventions`（SKILL.md + RECIPES.md §1/§2/§3/§4/§5/§6/§8）→ 用于 §0 组件选型、§2 字典与 badge 分级决议、§3 响应式与触控目标、§4 四态核对、§5 走查红旗定级。非测试证据。
