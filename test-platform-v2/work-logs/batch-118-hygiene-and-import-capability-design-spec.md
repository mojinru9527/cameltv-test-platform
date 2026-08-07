# Batch 118 — Design Spec（卫生/收尾 + 需求导入能力 + 覆盖缺口展示）

> **Design (🎨)** | Date: 2026-08-07 | Status: 就绪

## 0. 技术体系确认

shadcn/ui（Radix + Tailwind + CVA），Token 走语义类；颜色改 `globals.css` CSS 变量，不在组件写死。参照 `cameltv-ui-conventions`：
- 现有可复用：`Tabs`（shadcn）、`Badge` variant、`Table`、`Card`、`AsyncState`、`severityBadge` 风格。
- 差异标注 UI 直接复用 `pages/requirement/components/VersionCompare.tsx` 的 change_type 徽标模式（new/modified/deleted → 中文标签）。

## 1. 组件规格表

### C117-1 AiResultModal「覆盖矩阵」Tab
| 组件 | 规格 | 交互 |
|------|------|------|
| TabsList | 现有 Tab 体系追加「覆盖矩阵」Trigger（`BarChart3 size-4 mr-1`） | 点击切换 |
| 覆盖率 Stat | `StatCard` 或 Card 内 `text-2xl` 百分比 + 文案（功能点/用例覆盖） | 只读 |
| 矩阵 Table | 列：功能点、用例数、覆盖数、覆盖率%、缺口 | 只读；缺口行用 `Badge`（warning 描边）标注 |
| 缺口列表 | 无缺口时 `EmptyState`（"暂无覆盖缺口"）；加载中 `Skeleton`；接口失败 `ErrorState` + 重试 | 只读 |

四态：Loading（Skeleton）/ Empty（EmptyState）/ Error（ErrorState+重试）/ 数据（Table）。数据来自 coverage_report JSON：`{feature_points, coverage_matrix: [{feature_point, case_count, covered, coverage_rate, gap}], total_coverage_rate, gaps: []}`。

### C102-4 差异标注（生产页面 vs 原型）
| 组件 | 规格 | 交互 |
|------|------|------|
| 差异列表 | Card 内 `space-y-2`，每行：页面名 + change_type Badge（`新增`=info 描边 / `变更`=warning 描边 / `删除`=danger 描边 / `未变`=muted） | 只读 |
| 摘要行 | `text-xs text-muted-foreground`：新增/变更/删除计数 | 只读 |

复用 VersionCompare 的 DiffPage/change_type 契约；本批仅交付数据端点 + 最小列表展示，不做左右对照大图（后续迭代）。

### C102-3 模块树直建
前端无独立「需求模块树」页面（`frontend/src/pages/` 无 requirement-modules 目录）→ **本批仅后端能力**（端点+单测），前端展示豁免并在工件记录。

## 2. 布局与响应式

- 新增内容均位于既有 Dialog/Tab 容器内，遵循现有 `Card > CardContent p-3/p-4`、工具条 `flex items-center gap-2`。
- 窄屏：矩阵 Table 水平滚动（`overflow-x-auto`），不额外做移动端专属布局（内部工具，桌面优先）。

## 3. 状态设计核对（四态）

| 组件 | Loading | Empty | Error | 未启用 |
|------|---------|-------|-------|--------|
| 覆盖矩阵 Tab | Skeleton 行 | EmptyState 无缺口/无数据 | ErrorState + 重试 | 生成结果无 coverage 时隐藏 Tab |
| 差异列表 | Skeleton 行 | EmptyState 无差异 | ErrorState | 无可比数据时置灰入口 |

## 4. 设计 QA 走查发现

### 🟡 P2-1 覆盖缺口状态标签
AI 生成结果字段为英文枚举/结构 → Tab 内文案全中文（覆盖矩阵/缺口/覆盖率），Badge 用语义色，避免裸英文。**建议**：沿用 `TYPE_LABELS` 字典风格集中映射。

### 🟡 P2-2 差异 change_type 中文映射
VersionCompare 现用英文 change_type → 差异列表需中文标签字典（新增/变更/删除/未变）。**建议**：新增 `DIFF_CHANGE_TYPE_LABEL` 字典，与 `REVIEW_STATUS_LABEL` 同风格。

### ⚪ P3-1 JSON 直出兜底
coverage_report 输出如含原始 JSON 片段，按 RECIPES §5 先 parse 再美化展示，失败兜底 `<pre className="whitespace-pre-wrap">`。

## 5. 设计签核

结论：**有条件通过**（P2-1/P2-2 中文映射在实现时落实；C102-3 前端豁免已记录）。
