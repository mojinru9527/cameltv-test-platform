# Batch 119 — Design Spec（收尾与工具链清理）

> **Design (🎨)** | Date: 2026-08-07 | Status: 就绪

## 0. 技术体系确认

shadcn/ui（Radix + Tailwind + CVA），Token 走语义类。C102-4 面板复用 batch-118 `production-diff` 端点与 C117-1 覆盖矩阵 Tab 的视觉语言。

## 1. 组件规格表

### C102-4 ProductionDiffPanel（需求页）
| 组件 | 规格 | 交互 |
|------|------|------|
| 面板容器 | `Card > CardContent p-4 space-y-3` | 常驻卡片 |
| 数据入口 | 选择发布包（Select h-8）+ 生产页面清单来源（本批用可粘贴 label 列表 textarea 或内置默认样本） | 用户触发「生成差异」 |
| 摘要行 | 新增/一致/缺失计数 + Badge | 只读 |
| 差异列表 | 每行：名称 + change_type 徽标（`新增`=info 描边 / `一致`=success 描边 / `缺失`=warning 描边） | 只读 |
| 四态 | Loading（Skeleton）/ Empty（EmptyState 无差异）/ Error（ErrorState + 重试）/ 数据 | — |

### C114-1 缺口提示（后端为主）
本批仅后端端点 `POST /interaction-coverage/gaps`，输出 `{total_edges, covered_edges, coverage_rate, gaps:[{edge, covered}]}`；前端提示 UI 转下批（若时间允许最小 Badge 挂到现有交互页）。

## 2. 布局与响应式

- 面板放需求页 Upload Area 之后；窄屏列表横向滚动（overflow-x-auto）。
- 内部工具桌面优先，沿用 Card/Table/Badge 基线。

## 3. 状态设计核对（四态）

| 组件 | Loading | Empty | Error | 未启用 |
|------|---------|-------|-------|--------|
| 差异面板 | Skeleton 行 | EmptyState 无差异 | ErrorState + 重试 | 无发布包时置灰 |

## 4. 设计 QA 走查发现

### 🟡 P2-1 差异 change_type 中文映射
production-diff 返回 new/matched/missing 英文枚举 → 面板内中文标签（新增/一致/缺失）+ 语义色徽标，集中字典映射。
### ⚪ P3-1 生产页面清单粘贴体验
textarea 逐行粘贴 label 已够用；后续可对接平台采集数据（转下批）。

## 5. 设计签核

结论：**有条件通过**（P2-1 中文映射实现时落实；C114-1 前端提示转下批记录）。
