# Batch 26-2 — 知识中心 UX 修复 Design Spec
> **Design (🎨)** | Date: 2026-07-21 | Status: 就绪

## 0. 技术体系确认
shadcn/ui + Radix + Tailwind + CVA。Token 走语义类（bg-muted / text-muted-foreground / border / variant）。图标集：Lucide Icons。

---

## 1. 组件规格表

### 1.1 知识源详情弹窗（复用组件，Slice 1/2/5/7 共用）

| 属性 | 规格 |
|------|------|
| 宽度 | `max-w-5xl w-[94vw]`（约 64rem / 1024px @ 1920 屏） |
| 高度 | `max-h-[92vh] overflow-y-auto` |
| 内容区文字 | `text-sm leading-relaxed`（最小 14px） |
| 代码/原始内容 | `text-sm` 等宽，最大高度 `max-h-[600px]` |
| 元数据网格 | `grid grid-cols-5 gap-3` |
| 切片卡片 | `p-4` 内边距，`max-h-96 overflow-auto` |
| 关闭按钮 | 右上角 X（Dialog 原生） |

### 1.2 分区折叠卡片（PlatformTab, Slice 2）

| 属性 | 规格 |
|------|------|
| 卡片 | `<Card>` 标准，`cursor-pointer` |
| 标题栏（可点击） | `CardHeader` 带 `onClick` + 展开图标 |
| 展开图标 | `ChevronDown`（展开）/ `ChevronRight`（折叠），`size-4 text-muted-foreground` |
| 过渡动画 | 无 JS 动画，直接条件渲染（`{expanded && <CardContent>}`） |
| hover 态 | `hover:bg-muted/30` 整个标题栏 |

### 1.3 知识域切换 Toggle（GraphTab, Slice 4）

| 属性 | 规格 |
|------|------|
| 形式 | 两个按钮的 ToggleGroup（`variant="outline"` + `data-[state=on]:bg-primary`） |
| 选项 | 「项目知识」「平台研发」 |
| 默认 | 「项目知识」 |
| 位置 | 图谱工具栏左侧 |

### 1.4 页面顶部搜索栏（index.tsx, Slice 3）

| 属性 | 规格 |
|------|------|
| 位置 | PageHeader 下方，Tab 栏上方 |
| 宽度 | 全宽 `w-full` |
| 布局 | `flex items-center gap-2` |
| 搜索框 | `<Input>` 带 Search 图标前缀，`flex-1 h-9` |
| 模式选择 | `<Select>` w-[180px]，选项：混合/关键词/向量 |
| 搜索按钮 | `<Button size="sm">搜索</Button>` |
| 容器样式 | `px-1 py-2` 上下间距 |

### 1.5 批量操作工具栏（ArtifactReviewTab, Slice 6）

| 属性 | 规格 |
|------|------|
| 触发条件 | 勾选 ≥1 条 pending 产物 → 显示「批量采纳」「批量驳回」 |
| 触发条件 | 勾选 ≥1 条 approved 产物 → 显示「批量导入」 |
| 按钮样式 | `variant="default"`（采纳）/ `variant="destructive"`（驳回）/ `variant="outline"`（导入） |
| 位置 | 表格上方工具栏右侧 |
| 计数器 | 按钮文本含选中数：`批量采纳 (${n})` |

---

## 2. 布局与响应式

### 2.1 知识中心页面整体布局

```
┌──────────────────────────────────────────┐
│ PageHeader（知识中心标题 + 描述）          │
├──────────────────────────────────────────┤
│ 🔍 搜索栏（常驻）  [___搜索框___] [模式▼] [搜索] │
├──────────────────────────────────────────┤
│ Tab 栏：概览 | 项目知识 | 平台研发 | 检索 | … │
├──────────────────────────────────────────┤
│                                          │
│ Tab 内容区                               │
│                                          │
└──────────────────────────────────────────┘
```

### 2.2 响应式断点

| 断点 | 弹窗宽度 | 元数据网格 |
|------|---------|-----------|
| ≥1024px (lg) | `max-w-5xl w-[94vw]` | `grid-cols-5` |
| 768-1023px (md) | `max-w-3xl w-[95vw]` | `grid-cols-3` |
| <768px (sm) | `max-w-full w-[98vw]` | `grid-cols-2` |

---

## 3. 状态设计核对（四态）

### 3.1 知识源条目（ProjectTab / PlatformTab）

| 状态 | 表现 |
|------|------|
| **Loading** | Skeleton 占位（4 行） |
| **Empty** | 居中插图 + "暂无知识" + 引导文字 |
| **Error** | 红色提示 + 重试按钮 |
| **正常** | 条目列表 + hover 高亮 `hover:bg-muted/50` |

### 3.2 分区折叠（PlatformTab）

| 状态 | 表现 |
|------|------|
| **折叠** | ChevronRight 图标 + 条目计数 badge |
| **展开** | ChevronDown 图标 + 条目列表 |
| **全部折叠** | 至少一个展开（area 分区始终默认展开） |

### 3.3 弹窗

| 状态 | 表现 |
|------|------|
| **Loading（切片）** | Loader2 居中旋转 |
| **Empty（切片）** | "该知识源暂无切片" 虚线边框占位 |
| **Error（加载失败）** | toast 提示 + 弹窗保持打开（展示已有元数据） |

---

## 4. 设计 QA 走查（对照 8 类红旗）

> 引用 `cameltv-ui-conventions` skill 的 Red Flags 逐项检查。

### 🟢 RF1: shadcn/ui 组件覆盖
- ✅ Dialog, Card, Table, Select, Button, Badge, Checkbox 均已使用
- ✅ 无裸 HTML form/input

### 🟢 RF2: 颜色语义
- ✅ 保鲜度：green-500 / yellow-500 / red-500
- ✅ 状态 Badge：destructive（驳回/弃用）、default（活跃/已采纳）、secondary（类型）
- ✅ 无硬编码 hex

### 🟢 RF3: Tailwind 类
- ✅ 使用语义类（bg-muted, text-muted-foreground, border）
- ✅ 无 style={{}} 内联样式

### 🟡 RF4: Select 在 Dialog 内
- ⚠️ 当前 SelectContent 未设置 `position="popper"`，可能导致错位
- **修复**：[select.tsx](test-platform-v2/frontend/src/components/ui/select.tsx) 检查 SelectContent 的 position prop

### 🟢 RF5: 间距一致性
- ✅ 使用 `space-y-4`, `gap-2`, `gap-3` Tailwind 间距类

### 🟢 RF6: 交互态
- ✅ 条目行：`hover:bg-muted/50 transition-colors`
- ✅ 按钮：`disabled` 态已处理

### 🟡 RF7: Select z-index
- ⚠️ SelectContent 默认 z-index 50（Radix），但 Dialog 的 z-index 也是 50，content 可能被遮挡
- **修复**：SelectContent 加 `z-[60]` 或在 Dialog 打开时将 Select portal 指向 Dialog 内

### 🟢 RF8: Loading 态
- ✅ Loader2 + animate-spin 已覆盖

---

## 5. 设计签核
**结论**：条件通过。P1 阻断项：
- RF4/RF7: Select 在 Dialog 内错位 → Slice 5 修复
- Slice 1-2 弹窗必须达到 max-w-5xl 规格
