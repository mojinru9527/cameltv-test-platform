# Batch 120 — Design Spec（异步多 worker + 采集对接 + 缺口前端）

> **Design (🎨)** | Date: 2026-08-07 | Status: 就绪

## 0. 技术体系确认

shadcn/ui + Tailwind 语义类；后端 FastAPI + SQLAlchemy + Alembic。C117-2 无 UI；两个前端面板复用 batch-119 视觉语言。

## 1. 组件规格表

### C119-1 ProductionDiffPanel 增强（采集对接）
| 组件 | 规格 | 交互 |
|------|------|------|
| 采集任务输入 | `Input h-8` + 「加载采集」按钮 | 输入任务 ID → 加载 pages → 填入清单 textarea |
| 加载反馈 | 成功 toast + 清单刷新；失败 ErrorState 文案 | 只读反馈 |

### C119-2 InteractionGapPanel（需求页新增）
| 组件 | 规格 | 交互 |
|------|------|------|
| 面板 | `Card > CardContent space-y-3` | 常驻卡片 |
| 摘要 | 覆盖率 Badge（success/danger）+ 边计数 | 只读 |
| 缺口列表 | 每行 `缺口` warning 徽标 + from_module → to（截断） | 只读，最多展示 50 条 |
| 四态 | Loading Skeleton / Empty（无缺口）/ Error（重试）/ 数据 | — |

内置代表边（模块级）：首页→/match-replay、首页→/worldcup-2026、首页→/football/{id}、首页→/q/news、首页→/my、/league/{name}→/football/{id}、/team/{name}→/football/{id}、/football/{id}→/team/{name} 等（取自 batch-113 3172 边证据常见入口，可编辑 textarea 覆盖）。

## 2. 布局与响应式

- 两个面板放需求页上传区之后，桌面优先，窄屏横向滚动。

## 3. 状态设计核对（四态）

| 组件 | Loading | Empty | Error | 未启用 |
|------|---------|-------|-------|--------|
| 差异面板采集加载 | Skeleton | 无样本 | ErrorState | 无任务 ID 置灰 |
| 缺口面板 | Skeleton 行 | EmptyState 无缺口 | ErrorState + 重试 | — |

## 4. 设计 QA 走查发现

### 🟡 P2-1 缺口条目中文可读
edge 的 to 为 URL → 展示时取 path 截断 + `title` 提示，避免长串溢出。
### ⚪ P3-1 内置代表边为静态样本
后续可将完整拓扑入库（3172 边）再全量计算（转下批）。

## 5. 设计签核

结论：**有条件通过**（P2-1 实现时落实；P3-1 转下批记录）。
