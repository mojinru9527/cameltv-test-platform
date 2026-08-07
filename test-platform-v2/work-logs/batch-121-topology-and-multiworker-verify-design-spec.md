# Batch 121 — Design Spec（全量拓扑入库 + 多 worker 验证）

> **Design (🎨)** | Date: 2026-08-08 | Status: 就绪

## 0. 技术体系确认

shadcn/ui + Tailwind；后端 FastAPI + SQLAlchemy + Alembic。C120-2 无 UI；C120-1 前端复用 InteractionGapPanel 视觉。

## 1. 组件规格表

### C120-1 InteractionGapPanel 全量模式
| 组件 | 规格 | 交互 |
|------|------|------|
| 数据源 | 后端 `GET /interaction-coverage/topology`（全量 3172）→ `POST /gaps` | 挂载即全量计算 |
| 摘要 | 覆盖率 Badge + 已覆盖/总数 + 缺口数 | 只读 |
| 缺口列表 | 上限 50 条 + 「共 N 条缺口」提示 | 只读 |
| 四态 | Loading/Empty/Error/数据 | 同 batch-120 |

内置 8 条代表边移除（转全量）；文本展示沿用 toLabel 截断 + title 提示。

## 2. 布局与响应式

沿用 batch-120 卡片布局，无新增断点。

## 3. 状态设计核对（四态）

| 组件 | Loading | Empty | Error | 未启用 |
|------|---------|-------|-------|--------|
| 全量缺口面板 | Skeleton | 无缺口 | ErrorState+重试 | 拓扑未入库时提示 |

## 4. 设计 QA 走查发现

### 🟡 P2-1 全量缺口展示量
3172 边缺口可能上千条 → 列表截断 50 + 总数提示，避免 DOM 过大。
### ⚪ P3-1 分页/筛选后续迭代。

## 5. 设计签核

结论：**有条件通过**（P2-1 实现时落实）。
