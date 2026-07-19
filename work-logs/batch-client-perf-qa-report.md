# Batch client-perf (C3-C6 补全) — QA 报告

> **QA (🔍)** | Date: 2026-07-19 | Verdict: PASS ✅

## 测试总览

| 条件数 | 通过 | 失败 | 阻塞 |
|--------|------|------|------|
| 4 | 4 | 0 | 0 |

## 逐条件验证

### C3: Alembic 迁移脚本
**变更文件**: [alembic/versions/20260719_perf_tables.py](test-platform-v2/backend/alembic/versions/20260719_perf_tables.py)
| 检查项 | 结果 | 说明 |
|--------|------|------|
| 迁移脚本可导入 | ✅ PASS | `revision=20260719_perf_tables`, `down_revision=20260716_case_cleanup` |
| 三表均创建 | ✅ PASS | `perf_device` / `perf_session` / `perf_metric` |
| 幂等性 (idempotent) | ✅ PASS | 每表创建前 `sa.inspect()` 检查 `existing` |
| downgrade 反向删除 | ✅ PASS | 按外键依赖顺序: perf_metric → perf_session → perf_device |
| 命名规范 | ✅ PASS | `YYYYMMDD_description` 格式 |
| 主键/索引/外键/默认值 | ✅ PASS | cascade FK, device_id unique index, server_default 全覆盖 |

### C4: Recharts 完整曲线图
**变更文件**: [frontend/src/pages/perftest/index.tsx:601-789](test-platform-v2/frontend/src/pages/perftest/index.tsx#L601)
| 检查项 | 结果 | 说明 |
|--------|------|------|
| Recharts import | ✅ PASS | ResponsiveContainer, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend |
| FPS + Jank 曲线图 | ✅ PASS | 双 Y 轴 (`yAxisId="fps"`)，FPS 用 monotone + Jank 用 stepAfter |
| CPU 曲线图 | ✅ PASS | Y 轴 domain=[0,100]，带阈值参考线 |
| 内存曲线图 | ✅ PASS | Y 轴 domain=[0, 'auto']，含 PSS 降级取值 |
| chartData useMemo | ✅ PASS | 仅依赖 snapshots，避免每次渲染重建 |
| 响应式布局 | ✅ PASS | `ResponsiveContainer width="100%"` + `lg:grid-cols-2` / `lg:col-span-2` |
| Tooltip 格式 | ✅ PASS | `labelFormatter` 用 `(v: any)` 兼容 Recharts v3 |
| 图表颜色语义 | ✅ PASS | FPS=emerald / CPU=blue / Memory=amber / Jank=red |
| 空数据兜底 | ✅ PASS | `connectNulls` + null 安全取值链 |
| 组件隔离 | ✅ PASS | 独立 `PerfTrendChart` 函数组件，不与页面耦合 |

### C5: 专项测试
**变更文件**: [tests/test_perf_api.py](test-platform-v2/backend/tests/test_perf_api.py)
| 检查项 | 结果 | 说明 |
|--------|------|------|
| 测试数量 | ✅ PASS | 26 tests, 11 classes |
| DeviceList | ✅ PASS | 验证 Mock 模式设备返回 + 必填字段 |
| Session CRUD | ✅ PASS | 创建/列表/查询/删除，含分页和过滤 |
| Session 生命周期 | ✅ PASS | start/stop/重复start拒绝/stop pending/多会话独立 |
| Metrics | ✅ PASS | 注入Mock快照 → 验证时序数据点 + sinceTs 过滤 |
| Report | ✅ PASS | 有数据报告(含metric_stats schema) + 空数据报告(空数组) |
| Compare | ✅ PASS | 两次会话对比(含delta字段) + 不存在的会话 |
| Permissions | ✅ PASS | 9 个端点未认证 → 401/403；设备端点 → 401 |
| Schema | ✅ PASS | PerfSessionOut 字段完整性 + metrics response schema |
| R envelope | ✅ PASS | 所有验证 `body["code"] == 0` + `body["data"]` |
| 测试隔离 | ✅ PASS | 使用 `db_session` fixture (in-memory SQLite)，不污染开发库 |

### C6: 清理未使用 import
**变更文件**: [frontend/src/pages/perftest/index.tsx:1-30](test-platform-v2/frontend/src/pages/perftest/index.tsx#L1)
| 检查项 | 结果 | 说明 |
|--------|------|------|
| `Switch` 移除 | ✅ PASS | 未使用，已从 import 中删除 |
| `Label` 保留 | ✅ PASS | 三处使用: L265(目标应用), L293(采集指标), L312(采集时长) |

## 附带 Bug 修复验证

| # | Bug | 文件 | 验证 |
|---|-----|------|:--:|
| B1 | SQLite 时区剥离导致 `can't subtract offset-naive and offset-aware datetimes` | `perf_service.py:167-168` | ✅ `.replace(tzinfo=None)` 归一化 |
| B2 | stop_session 在 never-started 会话上状态错设 "completed" | `perf_service.py:153-159` | ✅ 早返 "cancelled" |
| B3 | API 返回裸 dict 无 R 信封 | `perf.py` (全 10 端点) | ✅ 全部 `response_model=R[...]` + `R.ok(data=...)` |
| B4 | 使用 HTTPException 绕过 APIException handler | `perf.py` | ✅ 全部替换为 `APIException(code, msg)` |

## 回归测试

| 套件 | 结果 |
|------|:--:|
| perf 专项 (26 tests) | ✅ 26/26 |
| 全量后端 (674 tests) | ✅ 674/674，零回归 |
| TypeScript (perf 文件) | ✅ 零错误 |
| TypeScript (全量) | ⚠️ 1 预存错误: `requirement/ReviewPage.tsx:17` `Filter` icon 不存在 (与本次无关) |

## 缺陷列表

| # | 严重级 | 描述 | 证据 | 状态 |
|---|--------|------|------|------|
| D1 | P3 | `delete_session` 路由直接操作 ORM (`db.delete(session); db.commit()`)，未走 Service 层，与同文件其他端点风格不一致 | `perf.py:100-105` | 建议后续统一 |
| D2 | P3 | `list_sessions` 返回 dict 而非 `PerfSessionListResponse(**kw)`，与其他端点用 Pydantic model 构造响应的风格不一致 | `perf.py:72-77` | 建议后续统一 |

## 发布建议

**状态**: PASS ✅

- **必修复**: 0 项
- **建议修复**: 2 项 (P3，代码风格一致性，不阻塞发布)
- **待用户验收**: C1 Android 真机 / C2 iOS 真机（上一 batch 遗留，需用户在有设备环境验证）

---

**QA Agent**: 测试部门
**日期**: 2026-07-19
**下次复测**: C1/C2 真机验收后
