# Batch 132 — Design Spec
> **Design (🎨)** | Date: 2026-08-10 | Status: 就绪

## 0. 技术体系确认
shadcn/ui + Radix + Tailwind + CVA；Token 走语义类（bg-muted / text-muted-foreground / border / variant）。真实栈不是 Ant Design。

## 1. 组件规格表
| 组件 | 尺寸/间距 | 颜色语义 | 交互态(默认/hover/focus/disabled) |
|------|----------|---------|----------------------------------|
| 直属核算行（可点击化） | 与树节点一致：`px-1.5 py-0.5 text-xs`，缩进 `pl-4` | 文字 `text-muted-foreground italic`（延续只读视觉）；图标 `FileText` 或 `CornerDownRight` muted | 默认 muted/斜体；hover `bg-muted/60 text-foreground`（提示可点）；focus-visible 走全局 ring；点击后 aria-pressed=true |
| 图谱图例用例计数 | `text-xs text-muted-foreground/60` | 常规 muted | 只读文字 |
| 分域 tab（项目知识/平台研发） | 已有实现（GraphTab 右上角） | 已有 | 保持不变 |

## 2. 布局与响应式
| 断点 | 布局 | 变化 |
|------|------|------|
| <1024px | 用例库左树隐藏（沿用现状） | 直属核算行随树隐藏 |
| lg 1024+ | 左树 220px + 右列表 | 直属核算行在子树顶部 |
| 图谱页 | 沿用现有画布 + 图例/详情面板 | 计数文案长度增加（"已入库 X / 全量 Y"），图例保持可读 |

## 3. 状态设计核对（四态）
| 组件 | Loading | Empty | Error | 未启用(503) |
|------|---------|-------|-------|-------------|
| 直属过滤列表 | AsyncState loading | 空态"暂无直属用例" | AsyncState error | 跟随用例库 |
| 图谱计数 | Skeleton | 0/0 显示 | toast 失败 | knowledge_graph_enabled 未启用提示 |

## 4. 设计 QA 走查发现（P0–P3）
### 🟡 P2-1 直属核算行可点化后防止误触
直属行变为可点击后，需保留 muted/斜体 + 鼠标指针提示，并在行尾加"查看"小图标（如 `Eye`/箭头），让用户明确它是"查看这批直属用例"的入口，而不是普通模块节点。**建议**：样式差异化 + aria-label"直属用例 N 条，点击查看/编辑"，hover 高亮。
### 🟡 P2-2 图谱计数口径文案
图例"用例"计数改为"已入库 X / 全量 Y"，避免 526/7559 困惑；实体统计同样口径。**建议**：文案 `用例 X/Y 已入库`。
### 🟡 P2-3 分域无来源实体
无来源孤儿实体不应在项目/平台两个 tab 都出现；归属"未分类"并仅在"全部"可见（或在项目域可见但明确标注"来源待补"）。**建议**：按 C126-1 回填来源后自然归域；过渡期在"全部"视图可见。

## 5. 设计签核
结论：有条件通过（P2-1/P2-2/P2-3 随本批实现处理，无 P1 阻断项）。
