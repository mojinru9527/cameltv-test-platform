# Batch 18 — LLM-Wiki 知识库差异对比能力 设计规范 + 设计 QA 走查

> **设计部门 (🎨) Design Department** ｜ 日期：2026-07-10 ｜ 状态：**前端已实现，设计规范 + 走查流程回填**
>
> 说明：本能力（VNext-1..3）由 DEV 部门先行落地前端，本文档按团队六部门流水线约定**反向回填**设计规范，并基于真实组件做设计还原度 / 一致性 / 可访问性走查。所有结论以真实代码为准，均给出「文件:行号」锚点。

---

## 0. 评审前置：技术体系确认

本平台前端**不是 Ant Design**，而是 **shadcn/ui（Radix primitives + Tailwind CSS）**，见 [test-platform-v2/CLAUDE.md ADR-0006](../test-platform-v2/CLAUDE.md)。因此：

- **Design Token** 走 Tailwind CSS 变量语义类（`text-muted-foreground` / `bg-muted` / `border` / `bg-background` / `variant` 系统），**不使用** AntD Token。设计部门 memory 里"基于 Ant Design 5"的记录已过时，本次以真实代码为准。
- **组件** 走 Radix primitives 封装：`Tabs` / `Card` / `Badge` / `Select` / `Sheet` / `Dialog` / `Switch` / `Button` / `Input` / `Textarea` / `Skeleton`。
- **无 Markdown 渲染库**：Wiki 正文与 JSON 契约均用 `<pre className="whitespace-pre-wrap">` 直出，见 [WikiTab.tsx:196](../test-platform-v2/frontend/src/pages/knowledge/components/WikiTab.tsx#L196)、[WikiDiffTab.tsx:32](../test-platform-v2/frontend/src/pages/knowledge/components/WikiDiffTab.tsx#L32)。

---

## 1. 设计参考与方向

### 1.1 视觉基线沿用

新增两个 Tab（**Wiki 知识库** / **知识差异对比**）挂载于知识中心九 Tab 体系，见 [knowledge/index.tsx:62-69](../test-platform-v2/frontend/src/pages/knowledge/index.tsx#L62)。设计方向：**与既有成熟 Tab（以 [SearchTab.tsx](../test-platform-v2/frontend/src/pages/knowledge/components/SearchTab.tsx) 为样式基线）完全对齐**，不引入新视觉语言。

| 维度 | 基线约定（沿用 SearchTab / 知识中心） | 新组件是否遵守 |
|------|--------------------------------------|----------------|
| 容器间距 | 外层 `space-y-3 / space-y-4` | ✅ 遵守 |
| 卡片 | `Card > CardContent p-3/p-4` | ✅ 遵守 |
| 工具条 | `flex items-center gap-2`，主按钮右侧 `ml-auto` | ✅ 遵守 |
| 控件高度 | 检索区控件 `h-9`，卡内小控件 `h-7/h-8` | ✅ 遵守 |
| 次要文字 | `text-xs / text-[11px] text-muted-foreground` | ✅ 遵守 |
| 图标 | Lucide，`size-4`，Tab 图标 `size-4 mr-1` | ✅ 遵守 |
| 加载 | `Loader2 animate-spin` + `Skeleton` | ✅ 遵守 |
| 反馈 | `sonner` toast | ✅ 遵守 |

### 1.2 图标语义

- Wiki 知识库：`BookOpen`（[index.tsx:63](../test-platform-v2/frontend/src/pages/knowledge/index.tsx#L63)）
- 知识差异对比：`GitCompare`（[index.tsx:67](../test-platform-v2/frontend/src/pages/knowledge/index.tsx#L67)）
- 左右契约互换指示：`ArrowLeftRight`（[WikiDiffTab.tsx:122](../test-platform-v2/frontend/src/pages/knowledge/components/WikiDiffTab.tsx#L122)）

---

## 2. 组件规格表

### 2.1 Wiki 知识库 Tab（WikiTab.tsx）

| 组件 | 尺寸 / 间距 | 颜色语义 | 交互态 |
|------|-------------|----------|--------|
| 标题行 | `flex items-center gap-2`，标题 `text-sm font-medium` | `BookOpen size-4` | 静态 |
| "未启用"徽标 | `Badge variant=outline` | **硬编码** `text-amber-600 border-amber-300`（[:104](../test-platform-v2/frontend/src/pages/knowledge/components/WikiTab.tsx#L104)） | 仅 config 就绪且 `!wiki_enabled` 显示 |
| 刷新按钮 | `Button variant=outline size=sm h-8` 图标型 | 主题色 | loading→`Loader2 spin`；`disabled` |
| 导入蓝湖按钮 | `Button size=sm h-8` | primary | 受 `wiki:manage` 权限门控 |
| 左栏（320px 固定） | `grid lg:grid-cols-[320px_1fr] gap-3` | Card | — |
| 原始来源行 | `flex gap-2 text-sm` | 状态 `Badge`：active→secondary，其他→outline（[:131](../test-platform-v2/frontend/src/pages/knowledge/components/WikiTab.tsx#L131)） | 「编译」按钮 `h-6 px-2 text-xs`，编译中→spin |
| 页面树节点 | `button w-full px-2 py-1 rounded`（约 28px 高） | `hover:bg-muted`；选中 `bg-muted` | hover / 选中；**focus 仅靠全局 ring** |
| 页面审核徽标 | `Badge text-[10px]` | `REVIEW_VARIANT`：approved→default，pending→secondary，rejected→destructive，draft→outline（[:21-23](../test-platform-v2/frontend/src/pages/knowledge/components/WikiTab.tsx#L21)） | 静态；**文案裸英文** |
| 右栏预览 | `Card min-h-[360px] CardContent p-4` | — | detailLoading→居中 spin |
| 正文 | `<pre> whitespace-pre-wrap text-xs bg-muted/40 p-3 max-h-[420px] overflow-auto font-mono` | muted 底 | 滚动 |
| 审核按钮组 | 驳回 `outline h-7` ／ 通过 `h-7 + CheckCircle2` | primary | 受 `wiki:approve` 且 `review_status!==approved` |

### 2.2 差异对比 Tab（WikiDiffTab.tsx）

| 组件 | 尺寸 / 间距 | 颜色语义 | 交互态 |
|------|-------------|----------|--------|
| 关键词输入 | `Input h-9 w-[240px]` | — | 空则禁用「发起对比」 |
| 左/右知识库选择 | `Select h-9 w-[170px] text-xs` | — | Radix 键盘可达 |
| 发起对比按钮 | `Button size=sm h-9` | primary | `running` / 空 query / `!wiki:diff` 三重禁用 |
| 历史任务选择 | `Select h-9 w-[220px] ml-auto` | — | 仅 `tasks.length>0` |
| 三栏栅格 | `grid lg:grid-cols-[1fr_1.4fr_1fr] gap-3`（中栏更宽） | — | <1024px 降为单列堆叠 |
| 契约视图 | `<pre> whitespace-pre-wrap text-[11px] bg-muted/40 max-h-[360px] overflow-auto font-mono`（[:32](../test-platform-v2/frontend/src/pages/knowledge/components/WikiDiffTab.tsx#L32)） | muted | 滚动；空→"（暂无）" |
| 严重级徽标 | `Badge text-[10px]` | **`SEVERITY_VARIANT`：P0→destructive，P1→destructive，P2→secondary，P3→outline**（[:23-25](../test-platform-v2/frontend/src/pages/knowledge/components/WikiDiffTab.tsx#L23)） | 静态 |
| 维度 / 类型徽标 | `Badge secondary / outline text-[10px]` | 中性 | 静态 |
| 差异条目 | `button w-full rounded-md border p-2` | `hover:bg-muted` | hover；focus 靠全局 ring |
| 严重级筛选 | `Select h-7 w-[90px] ml-auto` | — | all / P0–P3 |
| 维度筛选 | `Select h-7 w-[110px]` | — | all + 8 维度 |

### 2.3 差异详情 Drawer（WikiDiffDetailDrawer.tsx，Radix Sheet）

| 组件 | 尺寸 / 间距 | 颜色语义 | 交互态 |
|------|-------------|----------|--------|
| Sheet 容器 | `SheetContent sm:max-w-[520px] overflow-auto` | 右侧滑出 | Radix：Esc 关闭 + 焦点陷阱 |
| 标题徽标组 | 严重级 / 维度 / 类型 `Badge` | 同 `SEVERITY_VARIANT` | 静态 |
| 左右取值对照 | `grid grid-cols-2 gap-2`，`rounded-md border p-2 whitespace-pre-wrap` | 中性边框 | 空值→"—" |
| 建议框 | `rounded-md border p-2`（[:67](../test-platform-v2/frontend/src/pages/knowledge/components/WikiDiffDetailDrawer.tsx#L67)） | **硬编码** `border-blue-200 bg-blue-50 text-blue-700` | 仅有 suggestion 时 |
| 证据 | `text-xs font-mono break-all` 裸串（[:73](../test-platform-v2/frontend/src/pages/knowledge/components/WikiDiffDetailDrawer.tsx#L73)） | muted | 静态 |
| 底部动作 | 忽略 `outline sm` ／ 确认 `outline sm` ／ 生成待审用例 `sm primary` | primary | 受 `wiki:diff`；生成后按钮禁用 |

### 2.4 导入蓝湖 Dialog（WikiImportDialog.tsx，Radix Dialog）

| 组件 | 尺寸 / 间距 | 颜色语义 | 交互态 |
|------|-------------|----------|--------|
| Dialog 容器 | `DialogContent sm:max-w-[560px]` | — | Radix：焦点陷阱 + Esc |
| URL 输入 | `Label htmlFor + Input`（[:87-93](../test-platform-v2/frontend/src/pages/knowledge/components/WikiImportDialog.tsx#L87)） | — | ✅ 标签关联规范 |
| 补充说明 | `Label + Textarea rows=3` | — | ✅ 标签关联 |
| 三开关 | `flex justify-between` + `Switch id`（RAG/Wiki/图谱） | — | ✅ 标签关联，Radix 键盘可达 |
| 结果提示 | `rounded-md border p-3`（[:120-125](../test-platform-v2/frontend/src/pages/knowledge/components/WikiImportDialog.tsx#L120)） | **硬编码** 成功 `emerald-200/50/700`、失败 `amber-200/50/700` | 仅有 result 时 |
| 底部动作 | 关闭 `outline` ／ 开始导入 `primary` | primary | 空 URL / loading 禁用 |

**Badge 严重级配色语义（P0–P3）汇总**——当前实现：

| 级别 | 期望语义 | 当前 variant | 实际视觉 | 问题 |
|------|----------|--------------|----------|------|
| P0 | 最高危（红） | `destructive` | 红 | — |
| P1 | 高危（橙/深红） | `destructive` | **红（与 P0 同色）** | ⚠️ 无法区分 |
| P2 | 中（黄/灰蓝） | `secondary` | 灰 | 可接受 |
| P3 | 低（中性） | `outline` | 描边 | 可接受 |

---

## 3. 布局与响应式策略

### 3.1 差异对比三栏降级

- 断点：`grid grid-cols-1 lg:grid-cols-[1fr_1.4fr_1fr]`（[WikiDiffTab.tsx:149](../test-platform-v2/frontend/src/pages/knowledge/components/WikiDiffTab.tsx#L149)）。
- **≥1024px（lg）**：左契约 : 差异列表 : 右契约 = 1 : 1.4 : 1，中栏加宽承载差异卡片，合理。
- **<1024px**：直接坍缩为**单列纵向堆叠**（左契约→差异列表→右契约）。此时左右契约上下排列，**丧失"并排对照"语义**——用户需上下滚动比对 JSON，是差异对比场景的核心体验损失。
- **缺失中间断点**：无 `md:` 两栏过渡。平板竖屏（768–1023px）与手机同样吃单列，1024px 处从 1 栏直接跳 3 栏，跨度过大。

**建议降级策略**：`md:` 增设"差异列表 + 单契约切换（左/右 Tab 切）"的两栏中间态；或窄屏下左右契约用 `Tabs` 切换而非堆叠，保留对照心智。

### 3.2 Wiki Tab 布局

- `grid lg:grid-cols-[320px_1fr]`（[WikiTab.tsx:120](../test-platform-v2/frontend/src/pages/knowledge/components/WikiTab.tsx#L120)）：左固定 320px 页面树 + 右自适应预览。<1024px 坍缩单列（树在上、预览在下），符合主从模式，合理。

### 3.3 Tab 条在 Tablet 的表现

- 知识中心共 **9 个 TabsTrigger**（[index.tsx:33-70](../test-platform-v2/frontend/src/pages/knowledge/index.tsx#L33)），每个含图标 + 中文文案。shadcn `TabsList` 默认不换行/不横向滚动，9 项在平板竖屏（768px）会**挤压或溢出**。属既有共性问题，新增两 Tab 加剧，非本能力独有，记录待知识中心整体优化。

---

## 4. 状态设计核对（Loading / Empty / Error / 未启用[503] 四态）

逐组件核对代码，✅ 齐备 / ⚠️ 有但有缺陷 / ❌ 缺失：

| 组件 | Loading | Empty | Error | 未启用(503) |
|------|---------|-------|-------|-------------|
| **WikiTab** | ✅ Skeleton（[:126](../test-platform-v2/frontend/src/pages/knowledge/components/WikiTab.tsx#L126),[:146](../test-platform-v2/frontend/src/pages/knowledge/components/WikiTab.tsx#L146)）+ 详情 spin | ✅ "暂无来源/页面"文案 | ❌ **缺失**：`load` 全量 `.catch(()=>null)`（[:40-44](../test-platform-v2/frontend/src/pages/knowledge/components/WikiTab.tsx#L40)），接口失败静默当空 | ⚠️ 有"未启用"徽标但依赖 config 加载成功；config 失败则无提示 |
| **WikiDiffTab** | ⚠️ 有 spin 但**与 failed 混用**（见 P2-4） | ✅ 初始引导文案 + "未发现差异" | ⚠️ 仅 toast；`failed` 复用加载态 | ✅ "未启用"徽标（[:109](../test-platform-v2/frontend/src/pages/knowledge/components/WikiDiffTab.tsx#L109)），但按钮未按 `wiki_diff_enabled` 禁用 |
| **DetailDrawer** | ⚠️ 动作 `busy` 禁用，无 spinner | ✅ 空值→"—" | ✅ 动作失败 toast | N/A（依附 Tab） |
| **ImportDialog** | ✅ 按钮 `Loader2`（[:150](../test-platform-v2/frontend/src/pages/knowledge/components/WikiImportDialog.tsx#L150)） | N/A | ⚠️ 仅 toast，无内联错误块 | ✅ toast 文案提示"需启用 Wiki 且有 wiki:manage" |

**关键缺口**：
1. WikiTab 无 Error 态——加载失败与"真的没数据"视觉不可区分。
2. WikiDiffTab 的 `failed` 未做独立失败态（见走查 P2-4）。
3. "未启用(503)"依赖前端 config 标志位而非后端 503 真态，config 拉取失败时降级不可靠。

---

## 5. 设计 QA 走查发现（按 P0–P3）

> 首个实现必有问题，以下均为真实代码事实。

### 🔴 P1-1 严重级 Badge 颜色语义不一致：P0 与 P1 同为红色

`SEVERITY_VARIANT` 将 **P0 与 P1 同映射为 `destructive`（红）**，见 [WikiDiffTab.tsx:23-25](../test-platform-v2/frontend/src/pages/knowledge/components/WikiDiffTab.tsx#L23) 与 [WikiDiffDetailDrawer.tsx:12-14](../test-platform-v2/frontend/src/pages/knowledge/components/WikiDiffDetailDrawer.tsx#L12)。差异对比的核心价值是**按严重级分诊**，最高两级视觉无法区分，直接削弱功能价值；筛选出 P0 与 P1 后徽标同色，用户需读文字才能分辨，违背"颜色即语义"。
**建议**：P0 用 `destructive` 实心红，P1 用橙色描边/浅红（新增 `severity-p1` 语义类或 `border-orange-400 text-orange-600` + 暗色变体），P2 黄，P3 灰，形成四级可辨梯度。

### 🟠 P1-2 硬编码语义色导致深色模式对比度失效

多处直接写死浅色系（`-50` 底 + `-700` 字），无 `dark:` 变体：
- 建议框 `border-blue-200 bg-blue-50 text-blue-700`（[WikiDiffDetailDrawer.tsx:67](../test-platform-v2/frontend/src/pages/knowledge/components/WikiDiffDetailDrawer.tsx#L67)）
- 导入结果 `emerald-200/50/700` 与 `amber-200/50/700`（[WikiImportDialog.tsx:123-125](../test-platform-v2/frontend/src/pages/knowledge/components/WikiImportDialog.tsx#L123)）
- "未启用"徽标 `text-amber-600 border-amber-300`（[WikiTab.tsx:104](../test-platform-v2/frontend/src/pages/knowledge/components/WikiTab.tsx#L104)、[WikiDiffTab.tsx:110](../test-platform-v2/frontend/src/pages/knowledge/components/WikiDiffTab.tsx#L110)）

深色模式下，`bg-blue-50` / `bg-emerald-50` 仍是浅底，叠加深色页面背景既突兀又刺眼；且这些色**未随主题反转**，浅字浅底组合在部分场景对比度低于 **WCAG AA 4.5:1**。与项目 [batch-e-design-spec.md](batch-e-design-spec.md) 强调的 `text-muted-hc` 高对比 Token 方向相悖。
**建议**：改用带暗色变体的语义类，如 `bg-blue-50 dark:bg-blue-950/40 text-blue-700 dark:text-blue-300 border-blue-200 dark:border-blue-800`，或抽出 `info/success/warning` 语义 Token 统一管理。

### 🟡 P2-3 状态标签裸英文，与全中文界面不一致

`review_status` / `task.status` / 原始来源 `status` 多处**直接渲染后端英文枚举**，未做中文映射：
- 页面树与预览审核状态 `approved/pending/rejected/draft`（[WikiTab.tsx:159](../test-platform-v2/frontend/src/pages/knowledge/components/WikiTab.tsx#L159)、[:185](../test-platform-v2/frontend/src/pages/knowledge/components/WikiTab.tsx#L185)）
- 原始来源 `active` 等（[WikiTab.tsx:131](../test-platform-v2/frontend/src/pages/knowledge/components/WikiTab.tsx#L131)）
- 历史任务 `#id title · status` 与"任务 failed…"（[WikiDiffTab.tsx:134](../test-platform-v2/frontend/src/pages/knowledge/components/WikiDiffTab.tsx#L134)、[:146](../test-platform-v2/frontend/src/pages/knowledge/components/WikiDiffTab.tsx#L146)）
- Drawer 处理状态 `pending/accepted/rejected`（[WikiDiffDetailDrawer.tsx:76](../test-platform-v2/frontend/src/pages/knowledge/components/WikiDiffDetailDrawer.tsx#L76)）

对比同页 `PAGE_TYPE_LABEL`（[WikiTab.tsx:16-20](../test-platform-v2/frontend/src/pages/knowledge/components/WikiTab.tsx#L16)）已做中文映射、`STATUS_HINT`（[WikiImportDialog.tsx:21](../test-platform-v2/frontend/src/pages/knowledge/components/WikiImportDialog.tsx#L21)）也已中文化，状态标签却漏译，一致性割裂。
**建议**：补 `REVIEW_STATUS_LABEL` / `TASK_STATUS_LABEL` 中文映射字典，与 `PAGE_TYPE_LABEL` 同风格。

### 🟡 P2-4 失败态误用加载动画，"失败"看起来像"进行中"

差异任务 `status !== 'success'` 时统一渲染**旋转 `Loader2` + "任务 {status}…"**（[WikiDiffTab.tsx:144-147](../test-platform-v2/frontend/src/pages/knowledge/components/WikiDiffTab.tsx#L144)）。当 `status === 'failed'`，页面仍显示转圈 + "任务 failed…"，让**已失败的任务看起来仍在跑**，用户会一直等待。轮询结束（8×1.2s）后若仍 `running` 也停在此态，无重试入口。
**建议**：拆分 `running`（spin + "对比中…"）与 `failed`（`AlertCircle` 红 + "对比失败" + 重试按钮）两态。

### 🟡 P2-5 原始 JSON 裸展示，可读性差

- Wiki 来源引用 `source_refs_json` 直接 `font-mono break-all` 输出转义串（[WikiTab.tsx:200](../test-platform-v2/frontend/src/pages/knowledge/components/WikiTab.tsx#L200)）
- 差异证据 `evidence_json` 同样裸串直出（[WikiDiffDetailDrawer.tsx:73](../test-platform-v2/frontend/src/pages/knowledge/components/WikiDiffDetailDrawer.tsx#L73)）

对非技术用户（产品/测试）近乎不可读，且 `break-all` 会在任意字符断行，长串糊成一片。相比之下，差异列表契约用 `JSON.stringify(json, null, 2)` 做了缩进（[WikiDiffTab.tsx:33](../test-platform-v2/frontend/src/pages/knowledge/components/WikiDiffTab.tsx#L33)），体验落差明显。
**建议**：`evidence_json` / `source_refs_json` 先 `JSON.parse` 再 `stringify(…,2)` 放入 `<pre>`（含解析失败兜底）；或渲染为"字段：值"列表。

### ⚪ P3-6 触控目标普遍小于 44px

页面树节点 `px-2 py-1`（约 28px 高，[WikiTab.tsx:154](../test-platform-v2/frontend/src/pages/knowledge/components/WikiTab.tsx#L154)）、编译按钮 `h-6`、审核按钮 `h-7`、筛选 `Select h-7`、差异卡 `p-2`，均低于 WCAG **触控目标 ≥44px**。桌面鼠标可用，触屏/平板误触率高。
**建议**：树节点最小 `min-h-[36px]`、行内动作 `h-8`，至少保证列表主点击区达标。

### ⚪ P3-7 差异卡片语义结构缺失（可访问性）

差异条目为多 `Badge` + 截断标题的复合 `button`（[WikiDiffTab.tsx:175-186](../test-platform-v2/frontend/src/pages/knowledge/components/WikiDiffTab.tsx#L175)），无 `aria-label` 汇总，屏幕阅读器读作零散"P0 业务规则 新增 标题"，且 `truncate` 标题无 `title` 提示；筛选 `Select` 无 `aria-label`（[:157](../test-platform-v2/frontend/src/pages/knowledge/components/WikiDiffTab.tsx#L157),[:164](../test-platform-v2/frontend/src/pages/knowledge/components/WikiDiffTab.tsx#L164)）。
**建议**：为条目按钮加 `aria-label="P0 业务规则差异：{title}"`，为筛选 `SelectTrigger` 加 `aria-label="按严重级筛选"`，标题加 `title`。

---

## 6. 优化建议清单（按优先级）

| # | 建议 | 关联发现 | 优先级 | 落地成本 |
|---|------|----------|--------|----------|
| 1 | P0/P1/P2/P3 建立四级可辨严重色梯度（P1 独立橙色 + 暗色变体） | P1-1 | **P1** | 小（改 `SEVERITY_VARIANT` 或 Badge class） |
| 2 | 硬编码 blue/emerald/amber 全部补 `dark:` 变体或抽 `info/success/warning` 语义 Token | P1-2 | **P1** | 中（多处 + 建 Token） |
| 3 | 新增 `REVIEW_STATUS_LABEL` / `TASK_STATUS_LABEL` 中文映射，统一状态文案 | P2-3 | P2 | 小 |
| 4 | 差异任务拆 `running`/`failed` 两态，失败给 `AlertCircle` + 重试 | P2-4 | P2 | 小 |
| 5 | `evidence_json` / `source_refs_json` 结构化展示（parse→缩进 pre + 兜底） | P2-5 | P2 | 小 |
| 6 | WikiTab 补 Error 态：`load` 失败区分"加载失败/无数据"，提供重试 | §4 缺口 | P2 | 中 |
| 7 | 差异对比窄屏改左右契约 `Tabs` 切换，保留对照心智；增 `md:` 中间断点 | §3.1 | P2 | 中 |
| 8 | 触控目标：树节点 `min-h-[36px]`、行内动作升 `h-8` | P3-6 | P3 | 小 |
| 9 | 差异条目 / 筛选 Select 补 `aria-label`，截断标题补 `title` | P3-7 | P3 | 小 |
| 10 | "未启用"从后端 503 真态驱动，避免 config 拉取失败时降级不可靠 | §4 缺口 | P3 | 中 |
| 11 | （长期）引入轻量 Markdown 渲染，Wiki 正文脱离 `<pre>` 裸文本 | §0 限制 | P3 | 大 |

---

## 7. 设计签核

**结论：有条件通过（Conditional Pass）**——整体沿用 shadcn/Tailwind 体系、与知识中心其余 Tab 视觉一致性良好，Dialog/Sheet 走 Radix 具备键盘可达与焦点管理基线。但存在 **2 项 P1**（严重级配色不可辨、深色模式对比度失效）需在下一切片修复方可达成"设计一致性 ≥95% + WCAG AA"目标；P2/P3 项排入迭代优化。

> 走查人：设计部门 🎨 ｜ 复核对象：DEV 部门 VNext-1..3 前端实现 ｜ 日期：2026-07-10

---

## 8. P1 收口记录（batch-20，提交 `2c7c1bb`，2026-07-10）

两项 P1 已修复并通过 typecheck + build，设计签核升级为 **通过（Pass）**：

- ✅ **P1-1 严重级四级可辨色梯度** — 新增 [`wikiSeverity.ts`](../test-platform-v2/frontend/src/pages/knowledge/components/wikiSeverity.ts) `severityBadge()` 共享助手：P0 `destructive` 实心红 / **P1 `outline` + 橙色描边（`border-orange-400 text-orange-600` + 暗色变体）** / P2 `secondary` 灰 / P3 `outline` 描边。`WikiDiffTab` 与 `WikiDiffDetailDrawer` 复用同一映射，消除原 P0/P1 同红不可辨。
- ✅ **P1-2 深色模式对比度** — 建议框 blue（Drawer:67）、导入结果 emerald/amber（ImportDialog:122-124）、"未启用" amber 徽标（WikiTab:104 / WikiDiffTab:110）全部补 `dark:` 变体（`dark:bg-*-950/40 dark:text-*-300/400 dark:border-*-700/800`），深色模式不再浅底刺眼，满足 WCAG AA。

P2/P3 项（状态中文映射、failed/running 分态、evidence 结构化、触控目标、aria-label）排入后续迭代，非合并阻断。

> 收口人：设计部门 🎨 ｜ 结论：**Pass** ｜ 日期：2026-07-10
