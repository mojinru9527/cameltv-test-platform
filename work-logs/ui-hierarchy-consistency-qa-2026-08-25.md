# UI 层级与一致性修复 — QA 报告（2026-08-25）

> 批次：`fix/ui-hierarchy-consistency`（DeepSeek_Harness 直接任务）
> 依据：`work-logs/ui-design-audit-2026-08-24.md`（H1–H3 高优先级 + M1–M5 中优先级）
> 范围：`test-platform-v2/frontend` 源码与 token 体系

## 0. 结论

| 项 | 状态 | 验证 |
|---|---|---|
| H1 主按钮层级 | ✅ 已修 | 浏览器实测 3 处主 CTA 均为 primary 实心 |
| H2 黑曜壳 token 化 | ✅ 已修 | 60+ 硬编码 hex 下沉 CSS 变量，观察窗内仅剩刻意显示字重 |
| H3 Link 跳转 | ✅ 已修 | Button 原语新增 asChild/Slot，DSH 入口为 `<a>` |
| M1 省略号 | ✅ 已修 | 55 文件 70+ 处 `...` → `…` |
| M2 标题层级 | ✅ 已修 | PageHeader 24px + 黑曜对齐 tracking |
| M3 字重归一 | ✅ 已修 | font-semibold → 580 与 token 一致 |
| M4 URL 状态 | ✅ 已修 | 工作台时间范围/Tab、用例页全部筛选同步 URL |
| M5 刷新按钮原语 | ✅ 已修 | 黑曜壳刷新改 `<Button ghost loading>` |
| 硬门禁 | ✅ | typecheck / build / vitest 通过；console 零错误 |

## 1. H1 — 主按钮层级

- `Button.tsx:41` 默认 `variant='secondary'` **未改**（报告第一推荐方案：显式标注，避免改默认引发全量走查）
- 三处页面级主 CTA 显式 `variant="primary"`：
  - `LoginForm.tsx:97` 登录提交
  - `CaseFilterBar.tsx:217` 新建用例
  - `GuestPlatformHome.tsx:39` hero「登录并开始使用」
- 浏览器实测（playwright chromium）：
  - guest hero 按钮 `data-variant=primary`、class 含 `ui-btn-primary` ✓
  - 登录页提交按钮 `variant=primary` ✓
  - 用例页「新建用例」绿色实心、搜索/重置/导入/导出为次级 ✓（截图 evidence-testcase.png）

## 2. H2 — 黑曜壳 token 化

- `globals.css` 的 `[data-theme="obsidian-flow"]` 新增 `--obsidian-*` 语义层 17 个变量：
  `--obsidian-fg/fg-2/muted-2/muted-3/live/dot/surface/glass/glass-hover/border-soft/border-strong/tone-positive/tone-active/tone-risk/tone-neutral`
- `tailwind.config.cjs` 注册 `obsidian:` 颜色组 + 字阶 token（caption/meta/control/body/section/page）映射 + `fontWeight.semibold: 580`
- 三个壳文件重写：
  - `ObsidianWorkbench.tsx` — 全部颜色换 `text-obsidian-*`/`text-muted-*`/`bg-obsidian-*`；字阶换 `text-caption/meta/body/control`；L3 状态点 `<i>` 补 `aria-hidden`
  - `ObsidianListPage.tsx` — 同上；面板 `#141c17` → `bg-card`、`rounded-[9px]` → `rounded-md`
  - `MetricStrip.tsx` — tone 色板换 token 组
- 观察窗内刻意保留：`font-[650]`（kicker，对应 `--weight-bold: 650`）、`font-[560]`（指标数字显示字重）、`text-[1.75rem]`/`clamp(...)`（黑曜 hero 标题与指标大数字，无对应 token，属设计特征）
- **契约测试守护**：`obsidian-theme-contract.test.ts:40` 禁止 `#718077` 出现在 CSS 文件（历史低对比残留色），本设计因此未引入该色，MetricStrip note 用 `--muted-foreground` 基线

## 3. H3 — navigate → Link

- `CaseTable.tsx:219`「用 DSH 补充用例」改为 `<Button asChild><Link to="/dsh-tasks?...">`
- `Button.tsx` 新增 `asChild?: boolean`（Radix `Slot`，依赖已在 package.json），渲染 `<a>` 继承按钮样式/焦点/按压
- 浏览器实测：元素为 `<a href="/dsh-tasks?scene=functional&hint=...">`，class 含 `ui-btn-icon-xs`，aria-label 保留 ✓（Cmd/Ctrl+click、中键新标签恢复）

## 4. M1 — 省略号归一

- 依据 web-interface-guidelines：placeholders / loading states 以 `…` 结尾
- 55 文件、70+ 处替换（'加载中...'→'加载中…'、'保存中...'→'保存中…'、'搜索...'→'搜索…' 等），含 `searchable-select` 测试断言同步更新
- 刻意保留：URL/密钥格式示例（`https://...`、`sk-...`、`?tid=...&pid=...`）、表格 6 点空值占位 `'......'`、JS spread 语法

## 5. M2 — 标题层级

- `PageHeader.tsx:16` `text-lg(19px)` → `text-page(1.5rem=24px)` 且 `tracking-[-0.03em]`，与黑曜 h1 对齐
- 两视图标题均 ≥24px 起步（黑曜 h1 实测 34.56px、weight 580、tracking -1.0368px）

## 6. M3 — 字重归一

- `tailwind.config.cjs` `fontWeight.semibold: 580`，全应用 `font-semibold` 统一 580
- 与 `typography.css --weight-semibold: 580`、黑曜 `font-[580]` 三方一致；h2–h4 的显式 600 属标题层级基调，非 M3 点名范围

## 7. M4 — URL 状态同步

- 工作台 `workbench/index.tsx`：`?preset=&start=&end=&tab=` 双向同步（setter 内单向写 URL，replace 防历史堆积；URL 初始化带合法性校验）
- 用例页 `testcase/index.tsx`：`?type=&surface=&domain=&module=&direct=&nature=&priority=&keyword=&page=&pageSize=` 统一 `useEffect` 数据流；视图 `tab` 保留且切换不再清空筛选
- 浏览器实测：
  - `?preset=30d&tab=cross` → API 请求 2026-07-26~08-25（30 天区间）✓、「多项目概览」selected ✓
  - `?preset=30d&tab=project` → 「近 30 天」`variant=primary` ✓
  - 点击日期输入 → URL `preset=custom&start=&end=` 更新 ✓

## 8. M5 — 刷新按钮原语

- `ObsidianWorkbench.tsx:110-117` / `ObsidianListPage.tsx:89-96` 自绘 `<button>` 改为 `<Button variant="ghost" loading={loading}>刷新</Button>`
- 浏览器实测：`data-variant=ghost`、class 含 `active:` 按压反馈、`aria-busy` 由原语提供 ✓

## 9. 硬门禁与回归

- `npm run typecheck` ✅
- `npm run build` ✅
- vitest：UI/主题/用例/鉴权/API 相关 102 个用例全过（18 文件）；偶发 `spawn UNKNOWN` 为 Windows worker 启动瞬态，单跑复测通过
- 浏览器 console：零 error / 零 failed request（playwright 实测）
- 截图证据：`work-logs/evidence/ui-hierarchy-2026-08-25/`（guest-home / login / workbench / testcase 四张）

## 10. 变更文件

- `src/ui/primitives/Button.tsx`（+asChild/Slot）
- `src/components/PageHeader.tsx`（M2）
- `src/components/auth/LoginForm.tsx`、`src/pages/testcase/components/CaseFilterBar.tsx`、`src/layouts/GuestPlatformHome.tsx`（H1）
- `src/pages/testcase/components/CaseTable.tsx`（H3）
- `src/ui/patterns/ObsidianWorkbench.tsx`、`src/ui/patterns/ObsidianListPage.tsx`、`src/ui/components/MetricStrip.tsx`（H2/M5/L3）
- `src/globals.css`（--obsidian-* 变量）、`tailwind.config.cjs`（颜色组/字阶/字重）
- `src/pages/workbench/index.tsx`、`src/pages/testcase/index.tsx`（M4）
- 55 个文件省略号替换（M1）
- 本报告 + 截图证据