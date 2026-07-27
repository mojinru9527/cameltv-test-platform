# Batch 37 — Design Spec

> **Design (🎨)** | Date: 2026-07-23 | Status: 就绪

## 0. 技术体系确认

shadcn/ui + Radix + Tailwind + CVA；Token 走语义类（bg-muted / text-muted-foreground / border / variant）。

本批次涉及 3 个视觉变更：知识中心弹窗尺寸、导航菜单精简、全局字体放大。均不涉及新组件开发。

---

## 1. 知识中心：详情弹窗尺寸调整

### 现状

`ProjectTab.tsx:129` 和 `PlatformTab.tsx`（类似模式）：
```tsx
<DialogContent className="max-w-5xl max-h-[92vh] overflow-y-auto w-[95vw]">
```

- `max-w-5xl` = 1024px → 在 1920px 屏幕上仅占约 53% 宽度
- `w-[95vw]` 与 `max-w-5xl` 冲突，实际宽度受限于 1024px
- 切片列表内容区 `max-h-96`（384px）在高分辨率屏幕上仍有大量空余空间未利用

### 修改规格

| 属性 | 当前值 | 目标值 | 说明 |
|------|--------|--------|------|
| 弹窗最大宽度 | `max-w-5xl` (1024px) | `max-w-7xl` (1280px) | 提升 25% |
| 弹窗宽度占比 | `w-[95vw]` | `w-[95vw]` | 保持，小屏幕兜底 |
| 弹窗最大高度 | `max-h-[92vh]` | `max-h-[94vh]` | 稍微增大 |
| 切片内容最大高度 | `max-h-96` (384px) | `max-h-[600px]` | 大幅提升内容可见区 |
| 元数据网格 | `grid-cols-5` | `grid-cols-5` | 保持，1280px 下绰绰有余 |

### 三态设计

| 状态 | 表现 |
|------|------|
| **Loading** | 骨架/Spinner（已有 `<Loader2>`） |
| **Empty** | 「暂无项目知识」+ 引导文案（已有，[ProjectTab.tsx:74-80](test-platform-v2/frontend/src/pages/knowledge/components/ProjectTab.tsx#L74-L80)） |
| **Content** | 批次卡片 + 详情弹窗（新尺寸） |

---

## 2. 知识中心：数据源分类确认

### 现状分析

知识中心通过 `fetchKnowledgeSources()` API 获取数据，按 `para_category` 过滤：
- `ProjectTab` 使用 `para_category: 'project'` → 本应只显示项目知识
- `PlatformTab` 使用 `knowledge_domain: 'platform'` → 本应只显示平台研发知识

**问题**：如果后端 `para_category` 字段在数据入库时被误标，Agent Team 工件可能混入项目知识列表。

### 修改规格

| 组件 | 文件:行 | 当前筛选 | 建议筛选 |
|------|---------|----------|----------|
| ProjectTab | [ProjectTab.tsx:32](test-platform-v2/frontend/src/pages/knowledge/components/ProjectTab.tsx#L32) | `{ para_category: 'project', page_size: 100 }` | 增加 `knowledge_domain: 'project'` 确保双重过滤 |
| PlatformTab | [PlatformTab.tsx:53](test-platform-v2/frontend/src/pages/knowledge/components/PlatformTab.tsx#L53) | `{ knowledge_domain: 'platform', page_size: 200 }` | 保持，正确 |
| 空状态引导 | [ProjectTab.tsx:78](test-platform-v2/frontend/src/pages/knowledge/components/ProjectTab.tsx#L78) | 「导入需求文档和接口文档后」 | 保持，文案已准确 |

---

## 3. 导航菜单：隐藏未完成模块

### 影响范围

需隐藏的 4 个模块及其路由：

| 模块名 | 路由 | 后端路由文件 |
|--------|------|-------------|
| 版本测试任务 | `/version-mission` | `api/v1/version_mission.py` |
| 缺陷管理 | `/defect` | `api/v1/defect.py` |
| 测试数据集 | `/dataset` | `api/v1/dataset.py` |
| 集成配置 | `/integration` | `api/v1/integration.py` |

### 实现方案

**方案 A（推荐）**：在后端菜单数据库记录中标记 `visible=false`，`fetchMenus()` API 过滤
**方案 B**：前端硬编码黑名单过滤

选择方案 A——菜单由后端动态返回的设计已存在（`MainLayout.tsx:110-116` 调用 `fetchMenus()`），在后端菜单模型增加 `is_visible` 字段最为整洁。

### 菜单模型变更

```python
# 在 Menu 模型中添加字段
is_visible = Column(Boolean, default=True, nullable=False)
```

或在 `seed.py` 中直接不创建这 4 个模块的菜单记录（如当前已创建则需要软删除）。

### 前端不改动

`MainLayout.tsx` 中 `fetchMenus()` 返回的数据已自动过滤，前端无需代码改动。

---

## 4. 全局字体放大

### 现状测量

当前字体体系（Tailwind 默认 + 自定义 h1-h4）：

| 语义 | 当前 Tailwind 类 | 当前字号 | 对应 px (16px 基准) |
|------|-----------------|----------|---------------------|
| xs | `text-xs` | 0.75rem | 12px |
| sm | `text-sm` | 0.875rem | 14px |
| base | `text-base` | 1rem | 16px |
| lg | `text-lg` | 1.125rem | 18px |
| xl | `text-xl` | 1.25rem | 20px |
| 2xl | `text-2xl` | 1.5rem | 24px |
| h4 | 自定义 | 1rem | 16px |
| h3 | 自定义 | 1.125rem | 18px |
| h2 | 自定义 | 1.25rem | 20px |
| h1 | 自定义 | 1.5rem | 24px |
| 侧边栏菜单 | `text-sm` (cva) | 0.875rem | 14px |
| 侧边栏分组标题 | `text-xs` | 0.75rem | 12px |

**问题点**：
- 正文 `text-sm`（14px）远小于行业标准（16px）
- 侧边栏 14px 在 collapsed 模式尚可，expanded 模式下显小
- 标题层级 h4（16px）与正文 base（16px）相同，无层级感
- 数据表格大量使用 `text-sm`，长时阅读疲劳

### 目标字体规格

| 语义 | 目标 Tailwind 重定义 | 目标 rem | 目标 px (16px 基准) | 增幅 |
|------|---------------------|----------|---------------------|------|
| xs | `text-xs` | **0.8125rem** | **13px** | +1px |
| sm | `text-sm` | **0.9375rem** | **15px** | +1px |
| base | `text-base` | **1.0625rem** | **17px** | +1px |
| lg | `text-lg` | **1.1875rem** | **19px** | +1px |
| xl | `text-xl` | **1.3125rem** | **21px** | +1px |
| 2xl | `text-2xl` | **1.625rem** | **26px** | +2px |
| h4 | 自定义 | **1.125rem** | **18px** | +2px |
| h3 | 自定义 | **1.3125rem** | **21px** | +3px |
| h2 | 自定义 | **1.5rem** | **24px** | +4px |
| h1 | 自定义 | **1.75rem** | **28px** | +4px |
| 侧边栏菜单 | sidebar cva | **0.9375rem** | **15px** | +1px |
| 侧边栏分组标题 | sidebar cva | **0.8125rem** | **13px** | +1px |

### 实现方式

**Step 1**：在 `tailwind.config.cjs` 的 `theme.extend` 中添加 `fontSize` 覆盖：

```js
fontSize: {
  xs: '0.8125rem',
  sm: '0.9375rem',
  base: '1.0625rem',
  lg: '1.1875rem',
  xl: '1.3125rem',
  '2xl': '1.625rem',
}
```

**Step 2**：在 [globals.css:1770-1773](test-platform-v2/frontend/src/globals.css#L1770-L1773) 中更新 h1–h4：

```css
h1 { font-size: 1.75rem; font-weight: 700; letter-spacing: -0.02em; }
h2 { font-size: 1.5rem; font-weight: 600; letter-spacing: -0.01em; }
h3 { font-size: 1.3125rem; font-weight: 600; }
h4 { font-size: 1.125rem; font-weight: 600; }
```

**Step 3**：在 [sidebar.tsx:468-488](test-platform-v2/frontend/src/components/ui/sidebar.tsx#L468-L488) 中更新侧边栏按钮 cva：

```ts
size: {
  default: "h-8 text-[0.9375rem]",   // was text-sm
  sm: "h-7 text-xs",                  // was text-xs（inherit new xs = 13px）
  lg: "h-12 text-[0.9375rem]",       // was text-sm
},
```

**Step 4**：更新侧边栏分组标签字体（[sidebar.tsx:404](test-platform-v2/frontend/src/components/ui/sidebar.tsx#L404)）：
```tsx
// was "text-xs"
className={cn("... text-[0.8125rem] ...", className)}
```

### 风险点

| 风险 | 缓解 |
|------|------|
| 表格列宽被撑开 | TanStack Table 有固定列宽配置，逐页面验证 |
| 卡片内容溢出 | 增大后需调整 padding/margin |
| 移动端布局错乱 | 验证移动端断点下的表现 |
| CSS 硬编码字号的地方（如 `ui-concepts.css`） | 逐个检查并更新 |

---

## 5. 设计 QA 走查发现

> 走查范围：知识中心 + 导航菜单 + 全局字体

### 🟡 P2-01 知识中心 Tab 标签过多导致横向滚动

**事实**：[knowledge/index.tsx:89](test-platform-v2/frontend/src/pages/knowledge/index.tsx#L89) 有 13 个 Tab，`TabsList` 在小屏幕上需要横向滚动（`max-w-full overflow-x-auto`）。

**建议**：将低频 Tab（Wiki 知识库/知识差异对比/Skills/项目球）收入「更多」下拉菜单。本 Batch 暂不改动，记录为延伸优化项。

### 🟡 P2-02 空状态 Action 缺失

**事实**：[ProjectTab.tsx:74-80](test-platform-v2/frontend/src/pages/knowledge/components/ProjectTab.tsx#L74-L80) 空状态只有静态文案，没有「导入」按钮引导用户操作。

**建议**：添加「导入需求文档」按钮，链接到需求管理模块的导入功能。本 Batch 可一并修复。

### ⚪ P3-01 侧边栏 collapsed 模式下字号无需放大

**事实**：侧边栏 collapsed 模式仅显示图标（`size-4`），文字不可见。字号放大只影响 expanded 模式。

**建议**：无需处理，符合预期。

---

## 6. 设计签核

结论：**通过** — 3 个视觉变更（弹窗尺寸/导航/字体）均为低风险的增量调整，不涉及新组件或架构变更。
