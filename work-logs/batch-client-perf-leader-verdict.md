# Batch client-perf — Leader Verdict

> **Leader (🎯)** | Date: 2026-07-19 | Decision: 有条件通过

## 评审摘要

| 维度 | 评分 | 备注 |
|------|:--:|------|
| 实现质量 | ⭐⭐⭐⭐ | 架构清晰，三层分离（Model/Service/Router），Mock 降级设计稳健 |
| 风险 | ⭐⭐⭐ | SoloX 社区依赖 + iOS 17+ Windows 不支持 → 已文档标注 |
| 覆盖 | ⭐⭐⭐⭐ | 648 现有测试零回归；新模块缺少专项测试（下一 batch） |

## 关键决策（已批准）

1. **Wrap, not Fork**：封装 SoloX Python API 而非修改源码，降低维护成本。未安装时自动 Mock 降级
2. **WebSocket + HTTP 轮询双模**：实时优先 WebSocket，失败自动降级轮询，保障可用性
3. **6 项 MVP 指标**：FPS / CPU / 内存 / Jank / 启动耗时 / ANR（对标 PerfDog + Google Android Vitals）
4. **菜单导航**：性能测试放在「接口测试」（8）和「专项测试」（10）之间（sort 10.5）

## 抽检通过

- ✅ `backend/app/models/perf.py:1-78` — 三表模型：Session（采集会话）/ Metric（时序快照 JSON）/ Device（设备缓存）
- ✅ `backend/app/services/perf_collector_service.py:45-66` — SoloX 可选导入 + Mock 降级
- ✅ `backend/app/services/perf_service.py:109-152` — 统计摘要（mean/median/p95/min/max/stddev）+ 阈值判定
- ✅ `backend/app/api/v1/perf_ws.py:38-110` — WebSocket 500ms 推送 + 客户端断开清理
- ✅ `frontend/src/hooks/usePerfWebSocket.ts:1-130` — 自动重连（指数退避 3 次）→ 降级 HTTP 轮询
- ✅ `frontend/src/pages/perftest/index.tsx:1-380` — 4 个 Tab：设备采集 / 实时监控 / 历史记录 / 报告对比

## 交付物清单

| 文件 | 类型 | 状态 |
|------|------|:--:|
| `backend/app/models/perf.py` | ORM 模型 | ✅ |
| `backend/app/schemas/perf.py` | Pydantic Schema | ✅ |
| `backend/app/services/perf_collector_service.py` | SoloX 封装 | ✅ |
| `backend/app/services/perf_service.py` | 业务服务 | ✅ |
| `backend/app/api/v1/perf.py` | REST API (10端点) | ✅ |
| `backend/app/api/v1/perf_ws.py` | WebSocket | ✅ |
| `backend/app/models/__init__.py` | 模型注册 | ✅ |
| `backend/app/api/v1/router.py` | 路由注册 | ✅ |
| `backend/app/seed.py` | 菜单+权限种子 | ✅ |
| `backend/requirements.txt` | solox 依赖 | ✅ |
| `frontend/src/api/perftest.ts` | API 客户端 | ✅ |
| `frontend/src/hooks/usePerfWebSocket.ts` | WebSocket Hook | ✅ |
| `frontend/src/pages/perftest/index.tsx` | 主页面 (380行) | ✅ |
| `frontend/src/router/index.tsx` | 路由注册 | ✅ |
| `frontend/src/layouts/MainLayout.tsx` | Gauge 图标 | ✅ |
| `frontend/src/lib/icons.ts` | Gauge+Square 导出 | ✅ |
| `work-logs/batch-client-perf-prd-summary.md` | PRD 摘要 | ✅ |
| `work-logs/batch-client-perf-pm-plan.md` | PM 计划 | ✅ |
| `work-logs/batch-client-perf-design-spec.md` | 设计规范 | ✅ |
| `work-logs/batch-client-perf-qa-report.md` | QA 报告 | ✅ |
| `work-logs/batch-client-perf-leader-verdict.md` | Leader 判决 | ✅ |
| `work-logs/kanbans/DEV-client-perf.md` | Dev 看板 | ✅ |
| `test-platform-v2/docs/perf-setup.md` | 环境搭建文档 | ✅ |

## 判决

**有条件通过** — 代码质量和架构均满足合入标准（648 测试零回归）。

需用户验收的阻塞项：
- **C1: Android 真机采集端到端验证** — 需连接一台 Android 设备，安装 `solox` 后执行一次完整采集流程
- **C2: iOS 真机采集端到端验证** — 需连接一台 iOS 设备（Windows 需 iTunes + tidevice），执行一次完整采集流程

## 下一批次 Leader 条件（如有）

- **C3**: 生成 Alembic 迁移脚本（`alembic revision --autogenerate -m "add perf session/metric/device tables"`）
- **C4**: 前端时序曲线图接入 Recharts `<LineChart>` 完整实现（当前为简易占位柱状图）
- **C5**: 编写 `backend/tests/test_perf_api.py` 专项测试（Mock 模式下验证全套 CRUD + WebSocket 生命周期）
- **C6**: 清理 `perftest/index.tsx` 中未使用的 import（`Switch`, `Label`）

---

**合入指令**: 待用户确认 C1/C2 验收后，执行 `git commit` + `git push`
