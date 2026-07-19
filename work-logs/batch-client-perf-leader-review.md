# Batch client-perf — Leader 双轴审查报告

> **Leader (🎯)** | Date: 2026-07-19 | Review type: 合入前双轴审查

## 审查概览

| 维度 | 子代理 | 发现数 | 硬违规 | 缺失 | 不一致 |
|------|--------|:-----:|:------:|:----:|:-----:|
| Standards | general-purpose | 7 | 2 | — | — |
| Spec | general-purpose | 15 | — | 6 | 9 |

---

## Standards 轴 — 代码规范审查

### 🔴 硬违规（合入前应修复）

| # | 文件 | 违规 | 依据 |
|---|------|------|------|
| S1 | `perftest/index.tsx` | 两个 `useEffect` 含异步请求无 cleanup（`cancelled` 或 `AbortController`） | `engineering-standards.md` §4.1 |
| S2 | `usePerfWebSocket.ts` | `connectWebSocket` 的 `useCallback` deps 中含内部 SET 的状态变量（`mode`, `reconnectCount`），且父级 `useEffect` 用 `eslint-disable` 掩盖 | `engineering-standards.md` §4.2 |

**S1 详情**：`loadDevices()` 和 `loadSessions()` 在 useEffect 中调用，无 cancelled 标志保护。React 18 StrictMode 下会产生重叠请求，快速切页时存在竞态。

**S2 详情**：`connectWebSocket` 内部 set `mode` 和 `reconnectCount`，但这两变量同时在 useCallback deps 中——违反循环依赖禁止规则。`ws.onclose` 闭包中读取的 `reconnectCount` 可能是过期值。

### 🟡 判断项（建议后续修复）

| # | 文件 | 问题 | 依据 |
|---|------|------|------|
| S3 | `perf.py` | `POST /compare` 注册在 5 个 `/{session_id}` 路由之后，若未来新增 `POST /{id}` 会被遮蔽 | bug-guard: static-before-dynamic |
| S4 | `perftest/index.tsx` | 4 个 `TabsContent` 缺 `forceMount` prop | `engineering-standards.md` §4.4 |
| S5 | `perf.py:194` | `delete_session` 在 Router 层直接操作 ORM (`db.delete`+`db.commit`)，未走 Service 层 | Backend CLAUDE.md 分层约定 |
| S6 | `perftest.ts` | `fetchDevices`/`fetchSessions`/`fetchMetrics` 用 `as any` 绕过类型检查 | TypeScript 最佳实践 |
| S7 | `perftest/index.tsx` | `DataTable` import 未使用（历史 tab 用原生 `<table>`） | Dead code |

### ✅ 规范遵从（亮点）

- **R envelope**: 10 端点全用 `R.ok(data=...)` + `response_model=R[...]`
- **APIException**: 100% 合规，零 `HTTPException`
- **Alembic 幂等**: 三表创建前均 `sa.inspect()` 守卫
- **测试基础设施**: `StaticPool` + envelope-aware 断言（`body["code"]`）+ 权限全覆盖
- **Pydantic v2 + SQLAlchemy 2.0**: 全模块 `Mapped[]`/`mapped_column()`/`model_config`
- **代码注释**: 所有 model/service/public function 有 docstring
- **技术栈**: shadcn/ui + Radix + Tailwind + Zustand（非 Redux）
- **WebSocket cleanup**: `usePerfWebSocket` 清理函数正确关闭连接+清除定时器

---

## Spec 轴 — 需求实现审查

### 🔴 缺失需求

| # | 来源 | 缺失内容 |
|---|------|---------|
| P1 | PRD US-3 | 实时曲线图「滑动可查看历史全量」— 当前仅保留最近 120 点，无滚动查看历史能力 |
| P2 | Design §3 | 四态覆盖缺口：DeviceList 缺 Error 内联态、AppSelector 缺 Loading/Error、MonitorDashboard 缺 503（SoloX 不可用）、HistoryList 缺 Loading/Error、ReportView/CompareView 缺 Loading/Error |
| P3 | Design §4.3 | WebSocket 缺独立 `event` 消息类型（Jank/ANR 仅在 report endpoint 暴露，非实时推送） |
| P4 | Design §4.3 | `session_end` 消息缺 `report_url` 字段 |
| P5 | Design §4.2 | `PerfReportResponse` Schema 缺 `timeline_url` 字段 |
| P6 | PM Plan 2.2 | 菜单 seed data（`menu:perftest` + 5 权限点）不在 diff 中 |

### 🟡 范围蔓延（实现了未要求的功能）

| # | 内容 | 说明 |
|---|------|------|
| P7 | `battery`、`network` 指标 | `METRIC_DEFS` 定义了 8 项指标，其中 `battery`/`network` 在 PRD 中明确列为 Phase 2 "非目标" |
| P8 | `elapsed_s` 字段 | `MetricDataPoint` 新增了 spec 未定义的 `elapsed_s`，前后端都有 |

### 🟡 实现与规格不一致

| # | Spec 要求 | 实际实现 |
|---|----------|---------|
| P9 | `GET /api/v1/perf-devices` | 实现为 `GET /api/v1/perf-sessions/devices` |
| P10 | DELETE 返回 204 | 返回 200 + `{"detail": "ok"}` |
| P11 | FPS 曲线色 `#22c55e` | 使用 `#10b981`（emerald-500 vs green-500） |
| P12 | `session_id` 为 UUID | 使用 `PERF-YYYYMMDD-NNN` 格式 |
| P13 | stop 返回 `"stopped"` | 返回实际状态（`completed`/`cancelled` 等） |
| P14 | SessionControls 固定底部 | 实现为 Card 内顶部状态栏 |
| P15 | 无 WebSocket 专项测试 | PM Plan Task 5.2 要求 `test_perf_websocket.py`，diff 中不存在 |

---

## 判决

**有条件通过** — 代码架构质量好、核心功能完整、测试覆盖充分（674/674 全量通过）。

### 合入前修复（P0）

- **S1**: `perftest/index.tsx` 中 `loadDevices`/`loadSessions` 的 useEffect 补 `cancelled` 标志
- **S2**: `usePerfWebSocket.ts` 中用 `useRef` 替代 `useCallback` deps 中的 `reconnectCount`/`mode`

### 合入后下一 batch 修复（P1-P2）

- S3-S7（5 项判断项）
- P1-P15（15 项 spec 偏差，其中 P6/P15 优先）

---

**审查人**: Leader Agent (双轴并行子代理)
**日期**: 2026-07-19
**审查范围**: `2454bce...7156c7c` — 12 source files + 6 work-log artifacts
