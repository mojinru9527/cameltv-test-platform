# Batch client-perf — PM Plan

> **PM (🟨)** | Date: 2026-07-19

## 规格摘要

**原始需求**: 客户端性能采集功能——Android/iOS 双端，6 项指标（FPS/CPU/Mem/Jank/启动/ANR），零侵入采集，对标 PerfDog 数据口径，接入 SoloX 引擎
**技术栈**: FastAPI + SQLAlchemy + WebSocket / React 18 + shadcn/ui + Recharts / SoloX (solox PyPI)
**目标时间**: 5 个 Slice 迭代

## 开发任务

### Slice 1: 后端基础设施 — DB + SoloX 封装

#### [ ] Task 1.1: 新增性能采集 DB 模型
**描述**: 创建 `PerfSession`、`PerfMetric`、`PerfDevice` 三个 ORM 模型，编写 Alembic 迁移
**验收标准**:
- `PerfSession`: 采集会话（设备ID/packagename/平台/状态/开始时间/时长/摘要JSON）
- `PerfMetric`: 时序指标点（session_id/时间戳/指标类型/数值/单位）
- `PerfDevice`: 设备信息缓存（序列号/型号/系统版本/平台/最后连接时间）
- `alembic upgrade head` 成功建表，`pytest` 验证 CRUD
**涉及文件**:
- `backend/app/models/perf.py` — 新建 ORM 模型
- `backend/app/models/__init__.py` — 注册新模型
- `backend/alembic/versions/` — 新建迁移脚本
**参考**: PRD §5 / AV Check 模型 `av_check.py` 作为模板

#### [ ] Task 1.2: SoloX 封装服务
**描述**: 创建 `PerfCollectorService`，封装 SoloX 的 `AppPerformanceMonitor` Python API
**验收标准**:
- `list_devices(platform)`: 调用 SoloX `Devices` 类返回设备列表
- `list_apps(device_id, platform)`: 返回设备已安装 App 列表
- `start_collect(device_id, pkg_name, metrics, duration)`: 启动采集进程
- `stop_collect(session_id)`: 停止采集
- `collect_single(device_id, pkg_name, metric_type)`: 单次采样（用于轮询/心跳）
- Mock 模式下返回模拟数据（无设备时开发可进行）
- 单元测试覆盖所有方法
**涉及文件**:
- `backend/app/services/perf_collector_service.py` — 新建
- `backend/tests/test_perf_collector.py` — 新建
**参考**: SoloX Python API 文档 / `ffmpeg_service.py` 子进程模式

#### [ ] Task 1.3: WebSocket 端点
**描述**: 在 FastAPI 中新增 WebSocket 路由，用于实时推送性能数据到前端
**验收标准**:
- `ws://host/api/v1/perf/{session_id}/stream` 建立连接
- 后端每 500ms 推送一次全量指标快照（JSON）
- 客户端断开时自动清理
- 无活跃采集时拒绝连接（返回提示）
- 并发连接数 ≥ 5
**涉及文件**:
- `backend/app/api/v1/perf_ws.py` — 新建 WebSocket 路由
- `backend/app/api/v1/router.py` — 注册 WebSocket 路由
**参考**: FastAPI WebSocket 文档

### Slice 2: 后端 API + 种子数据

#### [ ] Task 2.1: REST API 端点
**描述**: 创建性能采集 CRUD API
**验收标准**:
- `POST /api/v1/perf-sessions` — 创建采集会话 → 返回 session_id
- `GET /api/v1/perf-sessions` — 列表（分页 + 过滤：平台/设备/App/日期范围）
- `GET /api/v1/perf-sessions/{id}` — 详情（含统计摘要）
- `DELETE /api/v1/perf-sessions/{id}` — 删除会话及关联指标
- `POST /api/v1/perf-sessions/{id}/start` — 启动采集
- `POST /api/v1/perf-sessions/{id}/stop` — 停止采集
- `GET /api/v1/perf-sessions/{id}/metrics?types=cpu,fps` — 获取时序数据
- `GET /api/v1/perf-sessions/{id}/report` — 生成统计报告 JSON
- `GET /api/v1/perf-devices` — 列出当前连接设备
- `POST /api/v1/perf-sessions/compare` — 两个 session 对比
- 所有端点需鉴权（JWT）
**涉及文件**:
- `backend/app/api/v1/perf.py` — 新建 API 路由
- `backend/app/schemas/perf.py` — 新建 Pydantic schema
- `backend/app/services/perf_service.py` — 新建业务服务层
- `backend/app/api/v1/router.py` — 注册路由
**参考**: AV Check `av_check.py` 的 API 模式

#### [ ] Task 2.2: 菜单和权限种子数据
**描述**: 新增「性能测试」菜单项和对应权限点
**验收标准**:
- 菜单: `menu:perftest` → "性能测试" → `/perftest` → `Gauge` 图标，排序 10.5（在 apitest 和 special 之间）
- 权限点: `perftest:list`, `perftest:create`, `perftest:delete`, `perftest:execute`, `perftest:report`
- 种子数据可重复执行不报错（幂等）
**涉及文件**:
- `backend/app/seed.py` — `_MENUS` 追加 + `_ACTIONS` 追加

### Slice 3: 前端 — 路由 + 设备选择 + 实时仪表盘

#### [ ] Task 3.1: 路由 + 菜单 + API 层
**描述**: 注册前端路由、API 客户端函数、类型定义
**验收标准**:
- 路由 `/perftest` → `PerfTestPage`（lazy import）
- API 客户端 `frontend/src/api/perftest.ts`（所有 REST 端点 + WebSocket 连接函数）
- TypeScript 类型 `PerfSession`, `PerfDevice`, `PerfMetric`, `PerfReport`
- 侧边栏正确显示「性能测试」菜单（受权限控制）
**涉及文件**:
- `frontend/src/router/index.tsx` — 新增路由
- `frontend/src/api/perftest.ts` — 新建 API 客户端
- `frontend/src/types/index.ts` — 新增类型
- `frontend/src/layouts/MainLayout.tsx` — 图标映射（Gauge → `Gauge` from lucide-react）

#### [ ] Task 3.2: 设备选择 + 会话管理页面
**描述**: 性能测试主页面——设备列表 + 创建采集会话
**验收标准**:
- 设备列表卡片：设备名称/型号/系统版本/状态指示灯
- 点击设备 → 列出已安装 App → 选择目标 App
- 指标勾选（FPS/CPU/内存/Jank/启动/ANR）——全部默认勾选
- 采集时长设置（30s/60s/300s/自定义）
- 「开始采集」按钮 → 跳转到实时监控页
- 三态：Loading（设备扫描中）/ Empty（无设备连接，显示 ADB/tidevice 安装指引）/ Error（连接失败）
**涉及文件**:
- `frontend/src/pages/perftest/index.tsx` — 新建主页面
- `frontend/src/pages/perftest/DeviceSelector.tsx` — 设备选择组件
- `frontend/src/pages/perftest/SessionForm.tsx` — 会话表单组件

#### [ ] Task 3.3: 实时监控仪表盘
**描述**: 采集过程中实时展示性能曲线
**验收标准**:
- 使用 Recharts `<LineChart>` 展示 FPS/CPU/内存时序图
- WebSocket 连接实时推送数据点，每 500ms 更新一次图表
- 显示当前值数字面板（如 "FPS: 58.2 / CPU: 23% / Mem: 345MB"）
- Jank 事件在 FPS 曲线上以红点标注
- 「停止采集」按钮 → 弹出确认 → 停止采集 → 跳转到报告页
- WebSocket 断开时显示重连提示 + 自动重连
- 兜底：WebSocket 不可用时自动降级为 HTTP 轮询（500ms）
**涉及文件**:
- `frontend/src/pages/perftest/MonitorDashboard.tsx` — 新建仪表盘页面
- `frontend/src/hooks/usePerfWebSocket.ts` — 新建 WebSocket Hook（含自动重连+降级轮询）

### Slice 4: 前端 — 报告 + 历史对比

#### [ ] Task 4.1: 采集报告页
**描述**: 采集结束后的统计报告视图
**验收标准**:
- 每个指标一个卡片：样本数 / 均值 / 中位数 / P95 / 最小值 / 最大值 / 标准差
- 完整时序曲线（静态，无实时更新）
- 异常时段标注——FPS < 阈值、Jank 事件、ANR/崩溃时间点
- 阈值线标注在图表上（如 FPS 低于 24 的红线）
- 「导出报告」按钮 → JSON 下载（Phase 1），CSV（Phase 2）
**涉及文件**:
- `frontend/src/pages/perftest/ReportView.tsx` — 新建报告页
- `frontend/src/components/charts/MetricCard.tsx` — 指标统计卡片组件

#### [ ] Task 4.2: 历史会话列表 + 对比
**描述**: 会话历史列表 + 对比视图
**验收标准**:
- 历史会话列表（表格：时间/设备/App/平台/时长/指标数）
- 支持按平台/设备/App 过滤
- 选择 2 个会话 → 「对比」按钮
- 对比视图：并排显示两个会话的关键指标差异
  - Δ FPS、Δ CPU%、Δ 内存 MB
  - 差异超阈值（>10%）红色高亮
  - 底部附差异分析小结
**涉及文件**:
- `frontend/src/pages/perftest/HistoryList.tsx` — 历史列表组件
- `frontend/src/pages/perftest/CompareView.tsx` — 对比视图组件

### Slice 5: 集成 + 文档 + 测试

#### [ ] Task 5.1: 环境检测脚本 + 安装文档
**描述**: 提供一键检测脚本 + 用户文档
**验收标准**:
- `scripts/check_perf_env.py` 检测：Python 3.10+, adb, tidevice (iOS), solox 包
- 输出友好提示（✅/❌ + 修复指引）
- `docs/perf-setup.md` 用户文档：安装步骤 / 设备连接 / 常见问题
**涉及文件**:
- `scripts/check_perf_env.py` — 新建
- `test-platform-v2/docs/perf-setup.md` — 新建

#### [ ] Task 5.2: 集成测试 + E2E 验证
**描述**: 全链路集成测试
**验收标准**:
- Mock 模式全链路测试（创建会话 → 采集模拟数据 → 实时推送 → 停止 → 报告 → 对比）
- 权限测试（无权限用户看不到菜单/API 403）
- WebSocket 断线重连测试
- 并发采集测试（2 个会话同时采集不冲突）
**涉及文件**:
- `backend/tests/test_perf_api.py` — 新建 API 测试
- `backend/tests/test_perf_websocket.py` — 新建 WebSocket 测试

## 质量要求

- [x] 响应式（Desktop + Tablet）
- [x] OpenAPI 同步（`/docs` 可查看所有新端点）
- [x] 单元测试覆盖（目标 ≥ 80%）
- [x] 无障碍（ARIA labels, 键盘导航）
- [x] 无 console 报错/告警
- [x] 权限鉴权（所有 API 需 JWT + 权限点校验）
- [x] WebSocket 降级兜底（轮询 500ms）

## 技术备注

**依赖**: `solox` PyPI 包、ADB（Android）、iTunes + tidevice（iOS，Windows）
**风险**: iOS 17+ 在 Windows 可能不可用（SoloX 已知限制）→ 文档注明，优先 Android 验证
**关键决策**: 先做 Android 端全链路（Slice 1-4），iOS 适配在 Slice 4-5
