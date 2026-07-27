# Batch client-perf — Design Spec

> **Design (🎨)** | Date: 2026-07-19 | Status: 草稿

## 0. 技术体系确认

shadcn/ui + Radix + Tailwind + CVA。Token 走语义类（`bg-muted` / `text-muted-foreground` / `border` / `variant`）。
图表库：**Recharts**（已在 workbench 模块使用，保持一致）。
图标：**Lucide**（`Gauge` 用于菜单图标）。

## 1. 组件规格表

### 1.1 页面结构

```
PerfTestPage (主页面，Tabs 切换)
├── Tab: "设备与采集" (默认)
│   ├── DeviceList (设备卡片列表)
│   │   └── DeviceCard × N
│   │       ├── 设备图标 (Smartphone / TabletSmartphone from lucide)
│   │       ├── 设备名 + 型号
│   │       ├── 系统版本 Badge
│   │       └── 连接状态指示灯 (🟢/🔴)
│   ├── AppSelector (选中设备后展开)
│   │   └── Select + 搜索框 → 选择目标 App
│   └── SessionForm (采集配置表单)
│       ├── CheckboxGroup: 指标多选 (FPS/CPU/Mem/Jank/启动/ANR)
│       ├── Slider/Select: 采集时长 (30s/60s/300s/自定义)
│       └── Button: "开始采集" (primary, disabled 直到设备+App均选中)
│
├── Tab: "实时监控" (采集进行中时激活)
│   ├── MetricsBar (顶部数字面板)
│   │   └── StatCard × 6: 当前值 (FPS/CPU%/Mem MB/Jank次/启动ms/ANR次)
│   ├── ChartGrid (曲线图网格)
│   │   └── LineChart × 4: FPS + Jank红点 / CPU趋势 / 内存趋势 / 网络流量(Phase2)
│   └── SessionControls (底部操作栏)
│       ├── 已采集时长计时器
│       ├── Button: "停止采集" (destructive variant)
│       └── Button: "标记时间点" (添加注释标记)
│
├── Tab: "历史记录"
│   └── DataTable
│       ├── 列: 时间 | 设备 | App | 平台 | 时长 | 指标数 | 操作
│       ├── FilterBar: 平台Select + 设备Select + App搜索
│       └── 操作列: "查看报告" "对比" Checkbox
│
└── Tab: "报告与对比"
    ├── ReportSummary (单次报告)
    │   ├── SessionMetaBar (会话元信息 Badge 行)
    │   ├── MetricCardGrid (6 个统计卡片)
    │   │   └── MetricCard × 6
    │   │       ├── 指标名 + 单位
    │   │       ├── 均值 (大号数字)
    │   │       ├── 统计行: 中位/P95/最小/最大/标准差
    │   │       └── 判定: ✅ 通过 / ⚠️ 警告 / ❌ 超标
    │   ├── FullTimelineChart (全量时序图，带阈值线 + 异常标注)
    │   └── AnomalyTimeline (异常时间轴: Jank/ANR/崩溃事件)
    │
    └── CompareView (两个 session 对比)
        ├── SessionA vs SessionB 元信息
        └── DeltaCardGrid
            └── DeltaCard × 6
                ├── 指标名
                ├── A值 vs B值
                └── Δ 差异 (绿色↓/红色↑，超阈值标注)
```

### 1.2 关键组件规格

| 组件 | 尺寸/间距 | 颜色语义 | 交互态 |
|------|----------|---------|--------|
| DeviceCard | `p-4 rounded-lg border` | `bg-card` / 选中: `border-primary ring-2 ring-primary/20` | hover: shadow-md, click: 选中高亮 |
| StatCard (实时值) | `p-3 min-w-[120px]` | 数字 `text-2xl font-bold` / 标签 `text-xs text-muted-foreground` | 值变化时 300ms 数字过渡动画 |
| MetricCard (报告) | `p-4 rounded-lg border` | 通过: `border-emerald-500/30 bg-emerald-50/30` / 警告: `border-amber-500/30` / 超标: `border-red-500/30` | — |
| LineChart | `h-[240px] w-full` | 线色: FPS `#22c55e` / CPU `#3b82f6` / Mem `#f59e0b` / Jank红点 `#ef4444` | 悬浮: tooltip 显示精确值+时间戳 |
| DeltaCard | `p-4 rounded-lg border` | Δ 改善: `text-emerald-600` / Δ 恶化: `text-red-600` / 无变化: `text-muted-foreground` | 差异 > 10% 红色背景闪烁 |
| SessionControls | `h-16 flex items-center gap-4 px-4 bg-muted/50 border-t` | 固定底部 | 计时器数字跳动 |
| FilterBar | `h-9 flex items-center gap-2` | 与全平台工具条一致 | — |

## 2. 布局与响应式

| 断点 | 布局 | 变化 |
|------|------|------|
| < 768px (Tablet) | 单列 | Tabs 横向滚动；MetricCard 2 列网格；Chart 单列堆叠 |
| 768–1024px (md) | 双列 | MetricCard 3 列网格；Chart 2 列 |
| ≥ 1024px (lg) | 主内容区 max-w-[1200px] | MetricCard 6 列；Chart 2×2 网格 |

设备选择区：始终单列卡片流（`grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3`）。

## 3. 状态设计核对（四态）

| 组件 | Loading | Empty | Error | 未启用(503) |
|------|---------|-------|-------|------------|
| DeviceList | Skeleton 卡片 × 3 + `Loader2` 动画 | "未检测到设备" + ADB/tidevice 安装指引链接 + 「刷新」按钮 | `AlertCircle` + 错误信息 + 「重试」 | — |
| AppSelector | `Loader2` + "正在获取应用列表…" | "此设备未安装应用" 或 "未找到匹配应用" | 同 DeviceList Error | — |
| MonitorDashboard | Skeleton 图表 + `Loader2` + "正在启动采集…" | — (采集已启动即无空态) | WebSocket 断开: `WifiOff` + "连接已断开，尝试重连…" + 自动重试倒计时 | "采集服务未就绪" (SoloX 不可用) |
| HistoryList | DataTable 内置 Skeleton 行 | "暂无采集记录" + 「去创建第一次采集」按钮 | DataTable 内置 Error | — |
| ReportView | Skeleton 卡片 + Skeleton 图表 | — (有 session 必有报告) | 报告生成失败: `AlertTriangle` + 错误原因 + 「重新生成」 | — |
| CompareView | Skeleton 对比卡片 | "请选择 2 个采集会话进行对比" | 同 ReportView Error | — |

## 4. API 契约设计

### 4.1 REST 端点一览

```
GET    /api/v1/perf-devices                       → DeviceListResponse
POST   /api/v1/perf-sessions                      → PerfSessionResponse
GET    /api/v1/perf-sessions                      → PaginatedSessionResponse
GET    /api/v1/perf-sessions/{id}                  → PerfSessionDetailResponse
DELETE /api/v1/perf-sessions/{id}                  → 204
POST   /api/v1/perf-sessions/{id}/start            → { status: "running", started_at: "..." }
POST   /api/v1/perf-sessions/{id}/stop             → { status: "stopped", duration_s: 300 }
GET    /api/v1/perf-sessions/{id}/metrics          → MetricTimeseriesResponse
GET    /api/v1/perf-sessions/{id}/report           → PerfReportResponse
POST   /api/v1/perf-sessions/compare               → CompareResponse
```

### 4.2 核心 Schema

```python
# PerfDevice
class PerfDeviceResponse(BaseModel):
    device_id: str       # ADB serial / iOS UDID
    device_name: str     # e.g. "Pixel 7"
    device_model: str    # e.g. "Pixel 7"
    platform: str        # "Android" | "iOS"
    os_version: str      # e.g. "Android 14"
    status: str          # "online" | "offline"
    installed_apps: list[str] | None  # lazy, only in device detail

# PerfSession
class PerfSessionCreate(BaseModel):
    device_id: str
    platform: str        # "Android" | "iOS"
    pkg_name: str
    metrics: list[str]   # ["cpu", "memory", "fps", "jank", "startup", "anr"]
    duration: int        # seconds, 0=unlimited

class PerfSessionResponse(BaseModel):
    session_id: str      # UUID
    device_id: str
    device_name: str
    platform: str
    pkg_name: str
    metrics: list[str]
    status: str          # "pending" | "running" | "completed" | "failed" | "cancelled"
    duration: int
    actual_duration_s: int | None
    created_at: datetime
    started_at: datetime | None
    ended_at: datetime | None
    summary: PerfSessionSummary | None

class PerfSessionSummary(BaseModel):
    total_samples: int
    metrics_summary: dict[str, MetricStats]  # keyed by metric_type

# MetricStats
class MetricStats(BaseModel):
    metric_type: str     # "cpu" | "memory" | "fps" | ...
    unit: str            # "%" | "MB" | "fps" | "ms"
    samples: int
    mean: float
    median: float
    p95: float
    min: float
    max: float
    stddev: float
    threshold: float
    threshold_comparator: str  # ">=" | "<="
    passed: bool

# PerfMetric (timeseries data point)
class MetricDataPoint(BaseModel):
    timestamp: float     # epoch seconds
    values: dict         # {"appCpuRate": 15.2, "systemCpuRate": 45.8} format varies by metric

# Report
class PerfReportResponse(BaseModel):
    session: PerfSessionResponse
    metrics: list[MetricStats]
    anomalies: list[AnomalyEvent]
    timeline_url: str    # relative URL for full timeseries data

class AnomalyEvent(BaseModel):
    timestamp: float
    event_type: str      # "jank" | "anr" | "crash" | "fps_drop" | "cpu_spike" | "memory_spike"
    detail: str
    metric_snapshot: dict | None

# Compare
class CompareRequest(BaseModel):
    session_a_id: str
    session_b_id: str

class CompareResponse(BaseModel):
    session_a: PerfSessionResponse
    session_b: PerfSessionResponse
    deltas: list[MetricDelta]

class MetricDelta(BaseModel):
    metric_type: str
    session_a_mean: float
    session_b_mean: float
    delta_absolute: float
    delta_percent: float
    direction: str        # "improved" | "degraded" | "unchanged"
    significant: bool     # |delta_percent| > 10%
```

### 4.3 WebSocket 协议

```
端点: ws://host/api/v1/perf-sessions/{id}/stream?token={jwt}

# 服务端 → 客户端: 每 500ms 推送
{
  "type": "metrics_snapshot",
  "session_id": "uuid",
  "timestamp": 1721400000.500,
  "elapsed_s": 15.5,
  "metrics": {
    "cpu": {"appCpuRate": 15.2, "systemCpuRate": 45.8},
    "memory": {"total": 128.5, "swap": 0.0},
    "fps": {"fps": 58.2, "jank": 0},
    "battery": {"level": 85, "temperature": 32.5},
    "network": {"send": 12.3, "recv": 145.6}
  },
  "events": []    // 异常事件列表，如 ANR/崩溃
}

# 服务端 → 客户端: 事件
{
  "type": "event",
  "session_id": "uuid",
  "timestamp": 1721400015.0,
  "event": {
    "event_type": "jank",
    "detail": "连续掉帧 5 帧 @ 15.5s",
    "metric_snapshot": {"fps": 12.0}
  }
}

# 服务端 → 客户端: 采集结束
{
  "type": "session_end",
  "session_id": "uuid",
  "reason": "user_stop" | "duration_reached" | "device_disconnected" | "error",
  "report_url": "/api/v1/perf-sessions/{id}/report"
}
```

## 5. 数据流

```
用户操作                  前端                      后端                      SoloX
------                   ----                      ----                      -----
选择设备+App  ─────→  POST /perf-sessions  ──→ 创建 PerfSession(DB)
                                             返回 session_id
点击"开始采集" ─────→  POST /{id}/start    ──→ PerfCollectorService.start()
                                              ↓
                    ← WebSocket 连接建立 ←──  启动 WebSocket 推送循环
                    ← metrics_snapshot   ←──  每500ms调用 SoloX API
                    ← metrics_snapshot   ←──  AppPerformanceMonitor.collectX()
                    ← event (jank/anr)   ←──  检测到异常事件
                                              ↓
点击"停止采集" ─────→  POST /{id}/stop    ──→ PerfCollectorService.stop()
                    ← session_end        ←──  计算统计摘要, 持久化
                    ← report_url         ←──  返回报告 URL
                                              ↓
点击"查看报告" ─────→  GET /{id}/report   ──→ 查询 DB 现成数据
                    ← PerfReportResponse ←──  无需实时计算
```

### WebSocket 降级策略

```
if (WebSocket 连接成功) {
    使用 WebSocket 实时推送
} else {
    // 降级到 HTTP 轮询
    setInterval(() => {
        GET /api/v1/perf-sessions/{id}/metrics?since={last_ts}
    }, 500)
}

// WebSocket 运行时断开 → 自动重连 (最多 3 次, 间隔 1s/2s/4s)
// 3 次失败后降级到 HTTP 轮询
```

## 6. 设计走查自检 (Red Flags)

对照 `cameltv-ui-conventions` 8 类红旗，逐一确认：

1. **严重级 Badge 颜色** ✅ — 设备状态用绿/红语义色 (bg-emerald-50/red-50)，判定通过/警告/超标用四级可辨色
2. **硬编码语义色无深色变体** ⚠️ 待验证 — FPS/CPU/Mem 的图表线色需在 `globals.css` 中定义 CSS 变量或确认 `dark:` 可辨
3. **状态标签裸英文** ✅ — 平台/状态等枚举均定义中文映射字典（`PLATFORM_LABEL`, `SESSION_STATUS_LABEL`）
4. **缺 Error 态 / 四态不全** ✅ — 设计已覆盖 7 个组件的四态（见 §3 表格）
5. **失败态误用加载动画** ✅ — 采集状态拆 `pending`(spin) / `running`(spin+进度) / `completed`(✓) / `failed`(AlertCircle红+重试)
6. **原始 JSON 裸展示** ✅ — 报告页统计数据用卡片呈现，不裸展示 JSON
7. **触控目标 < 44px** ✅ — DeviceCard `min-h-[80px]`，按钮 `h-9`/`h-10`，MetricCard `min-h-[120px]`
8. **响应式断点跨度过大** ⚠️ 待验证 — 已定义 md: 过渡态，需在实现时确认 Tabs 在 768px 不溢出（当前 4 个 Tab 不构成风险）

## 7. 设计签核

**结论**: 有条件通过

**P1 阻断项** (实现前需确认):
- 图表线色需实测深色模式可辨性（FPS 绿 `#22c55e` 在深色背景可能过亮）

**P2 改进项** (可以在后续迭代修复):
- 实时监控页可考虑添加「性能评分」综合指标（类似 PerfDog 的性能分）
