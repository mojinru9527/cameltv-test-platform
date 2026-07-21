# Batch 26 — Design Spec

> **Design (🎨)** | Date: 2026-07-21 | Status: 就绪

## 0. 技术体系确认

shadcn/ui + Radix + Tailwind + CVA；Token 走语义类（`bg-muted` / `text-muted-foreground` / `border` / `variant`）。

所有新组件使用现有 shadcn/ui 原语：`Card`, `Badge`, `Button`, `Progress`, `Tabs`。不引入新 UI 库。

---

## 1. 组件规格表

### 1.1 Select 下拉框定位修复

| 组件 | 尺寸/间距 | 颜色语义 | 交互态 |
|------|----------|---------|--------|
| 过滤区 SelectContent | `position="popper"` | 沿用默认 | 展开即贴触发器下方 |
| 分页 SelectContent | `position="popper"` | 沿用默认 | 同上 |

**当前问题**（附锚点）:
- [testcase/index.tsx:272](test-platform-v2/frontend/src/pages/testcase/index.tsx#L272) — 全部域 `<SelectContent>` 无 position 属性
- [testcase/index.tsx:284](test-platform-v2/frontend/src/pages/testcase/index.tsx#L284) — 全部模块 `<SelectContent>` 无 position 属性
- [testcase/index.tsx:296](test-platform-v2/frontend/src/pages/testcase/index.tsx#L296) — 全部优先级 `<SelectContent>` 无 position 属性
- [testcase/index.tsx:470](test-platform-v2/frontend/src/pages/testcase/index.tsx#L470) — 分页 `<SelectContent>` 无 position 属性

**修复**: 以上 4 处各加 `position="popper"`。参照 CaseDrawer 中已有的正确用法 [CaseDrawer.tsx:305](test-platform-v2/frontend/src/pages/testcase/CaseDrawer.tsx#L305)。

### 1.2 表格行高对齐

| 组件 | 当前 | 目标 | 说明 |
|------|------|------|------|
| TableRow | 自然高度 ~36px | 与 DomainTree 节点一致 ~40px | 添加 `min-h-[40px]` 或等价 padding |
| TableCell | `py-2` (默认) | `py-2.5` | 增加上下内边距 4px |

**检查锚点**: [testcase/index.tsx:396](test-platform-v2/frontend/src/pages/testcase/index.tsx#L396) — `<TableRow>`

### 1.3 表格横向滚动条

| 组件 | 当前 | 修复 |
|------|------|------|
| 表格外层 div | `overflow-x-auto` + `min-w-[900px]` | 移除 `overflow-x-auto`，保留内层 overflow-y 滚动 |

**当前结构**:
```
div.overflow-x-auto              ← Line 374: 去掉 overflow-x-auto, min-w-[900px]
  Table.min-w-[900px]
```
**修复**: 将 `overflow-x-auto` 改为 `overflow-x-visible`，`min-w-[900px]` 保留以保证表头宽度。

### 1.4 新建用例弹窗 Tab 高度

| Tab | 当前 max-h | 修复 |
|-----|-----------|------|
| 新建模式 form | `max-h-[60vh]` (Line 229) | 保持 `60vh` |
| 编辑模式 CaseForm | `max-h-[50vh]` (Line 278) | 改为 `max-h-[60vh]` |

**修复锚点**: [CaseDrawer.tsx:278](test-platform-v2/frontend/src/pages/testcase/CaseDrawer.tsx#L278)

### 1.5 EvidenceTaskPanel — 固定任务面板

| 属性 | 规格 |
|------|------|
| 宽度 | `w-[260px]` shrink-0 |
| 高度 | `h-[calc(100vh-215px)]`（与用例左侧树一致） |
| 布局 | flex flex-col，顶部任务进度卡片 + 底部历史列表 |
| 滚动 | overflow-y-auto |
| 面板容器 | `<Card size="sm">` |

**组件结构**:
```
Card (size="sm", w-[260px], h-[calc(100vh-215px)])
├── CardHeader (border-b)
│   └── CardTitle: "证据任务"
├── 当前任务区 (p-3, border-b)
│   ├── StatusBadge (动画脉冲=running)
│   ├── ProgressBar (阶段: discovering→capturing→ocr→done)
│   └── 页面计数: "已采集 5/15 页"
├── 历史任务列表 (flex-1, overflow-y-auto)
│   └── 每个任务行:
│       ├── 版本号 + 状态徽标
│       ├── 时间 (相对时间: "3分钟前")
│       └── 操作按钮 (成功→查看, 失败→重试, 运行中→取消)
└── CardFooter (border-t)
    └── [新建采集] 按钮
```

**颜色语义**:
| 状态 | Badge variant | 说明 |
|------|--------------|------|
| pending | secondary | 灰色，等待中 |
| running | default + animate-pulse | 蓝色脉冲 |
| success | default (bg-emerald-50...) | 绿色 |
| failed | destructive | 红色 |
| cancelled | outline | 灰色边框 |

### 1.6 PrototypePreview — 原型截图预览

| 属性 | 规格 |
|------|------|
| 布局 | 左右双栏，左 60% 截图 + 右 40% OCR 文本 |
| 截图区 | `bg-muted` 居中展示，`max-h-[65vh]` object-contain |
| 翻页 | 底部居中：`◀ 上一页` + `第 3/15 页` + `下一页 ▶` |
| 页面导航条 | 顶部水平滚动条，每页一个小圆点/方块，颜色对应变动类型 |

**变动标记颜色**（用于页面导航 + 列表中）:
| change_type | 颜色 | Tailwind | Badge |
|-------------|------|----------|-------|
| 🆕 new | 绿色 | `border-emerald-400 bg-emerald-50` | `<Badge variant="default" className="bg-emerald-100...">新增</Badge>` |
| ✏️ modified | 黄色 | `border-amber-400 bg-amber-50` | `<Badge variant="secondary" className="bg-amber-100...">变更</Badge>` |
| ✓ unchanged | 灰色 | `border-slate-200 bg-slate-50` | 不显示标记（默认） |
| ❌ deleted | 红色 | `border-red-300 bg-red-50` | `<Badge variant="destructive">已删除</Badge>` |

### 1.7 VersionCompare — 版本对比

| 属性 | 规格 |
|------|------|
| 布局 | 上下结构：汇总卡片 + 分屏对比 |
| 汇总卡片 | 4 个 StatCard 水平排列：🆕新增 / ✏️修改 / ✓不变 / ❌删除 |
| 分屏区 | `grid grid-cols-2 gap-4`，每侧一张截图 + 页面名称 + 状态标记 |
| 对齐 | 左右同一页面索引对齐，missing 侧显示空状态占位 |

---

## 2. 布局与响应式

| 断点 | 布局变化 |
|------|---------|
| Desktop (≥1280px) | 需求管理页：左侧任务面板(260px) + 右侧内容区(flex-1) |
| Tablet (768-1279px) | 任务面板可折叠（ChevronLeft 收起），右侧内容区占满 |
| Mobile (<768px) | 任务面板变为底部 Sheet |

**需求管理页新布局**:
```
┌─ 需求管理页 (flex gap-4) ──────────────────────┐
│ ┌─ EvidenceTaskPanel ──┐ ┌─ 右侧内容区 ────────┐ │
│ │ w-[260px] shrink-0   │ │ flex-1              │ │
│ │ h-[calc(100vh-215px)]│ │   ├─ 蓝湖链接输入    │ │
│ │ overflow-y-auto       │ │   ├─ AI 操作按钮区   │ │
│ │                       │ │   └─ 文档列表/结果   │ │
│ └───────────────────────┘ └─────────────────────┘ │
└───────────────────────────────────────────────────┘
```

---

## 3. 状态设计核对（四态）

| 组件 | Loading | Empty | Error | 未启用 |
|------|---------|-------|-------|--------|
| EvidenceTaskPanel | Skeleton (3 行卡片) | "暂无采集任务" + 新建引导 | 红色卡片 + 重试按钮 | 面板显示但灰度（lanhu_evidence 未启用） |
| PrototypePreview | 截图区 skeleton + OCR 文本 skeleton | "该页面暂无截图" | "加载截图失败" + 重试 | 入口按钮 disabled + tooltip |
| VersionCompare | Skeleton 双栏 | "无上一版本可供对比"（首次上传） | "加载对比数据失败" | 入口按钮 hidden |
| 功能拆分标记 | Badge skeleton | 无版本标记（initial 模式） | — | — |

---

## 4. 设计 QA 走查

以下走查基于现有代码分析，标注了需修复的精确行号。

### 🔴 P0-1: 过滤区 Select 定位错误

**位置**: [testcase/index.tsx:272,284,296,470](test-platform-v2/frontend/src/pages/testcase/index.tsx)

所有过滤器 `<SelectContent>` 未指定 `position="popper"`，在 `height: calc(100vh - 215px)` 的 flex 容器中使用默认 `item-aligned` 定位导致下拉菜单偏移。

**建议**: 全部改为 `<SelectContent position="popper">`

### 🔴 P0-2: 重置后模块下拉不可用

**位置**: [testcase/index.tsx:177-181](test-platform-v2/frontend/src/pages/testcase/index.tsx#L177-L181)

`selModules` 在 `selDomain=''` 时返回 `[]` → 模块 Select 仅有 `<SelectItem value="">全部模块</SelectItem>` 一个选项 → Radix Select 检测到无有效选项而拒绝打开。

**建议**: 当 `selDomain` 为空时，返回所有域的模块合并列表，或显示 "请先选择域" 提示。

### 🟡 P2-1: 弹窗高度不一致

**位置**: [CaseDrawer.tsx:229](test-platform-v2/frontend/src/pages/testcase/CaseDrawer.tsx#L229) vs [CaseDrawer.tsx:278](test-platform-v2/frontend/src/pages/testcase/CaseDrawer.tsx#L278)

新建 form `max-h-[60vh]` vs 编辑 CaseForm `max-h-[50vh]`，高度差 10vh。

**建议**: 统一为 `max-h-[60vh]`。

### 🟡 P2-2: 表格 hover 触发横向滚动条

**位置**: [testcase/index.tsx:374](test-platform-v2/frontend/src/pages/testcase/index.tsx#L374)

`overflow-x-auto` 在外层 div，`min-w-[900px]` 在 Table 上 → hover 效果触发布局微调 → 滚动条闪现。

**建议**: `overflow-x-auto` → `overflow-x-visible`，或将其移到更内层的容器。

---

## 5. 设计签核

结论：**通过**（有条件 — 上述 P0-1/P0-2 为阻断项，Dev 必须修复）

P2 项建议修复但不阻塞合入。
