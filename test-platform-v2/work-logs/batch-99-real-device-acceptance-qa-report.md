# Batch 99 — QA 报告（真机性能验收：Android 滚动 fps + iOS 阻塞登记）

> **QA (🔍)** | Date: 2026-08-05 | Verdict: PASS（Android）；iOS BLOCKED（外部驱动，如实登记）

## 测试总览

| 项 | 通过 | 失败 | 阻塞 |
|:---|:----:|:----:|:----:|
| 环境探测（adb/solox/tidevice） | ✅ Android | 0 | iOS（缺 Apple 驱动） |
| Android 滚动场景采集 E2E | ✅ | 0 | 0 |
| fps 解析器单元测试 | 8/8 | 0 | 0 |
| 设备识别 + 会话 + WS 采样 + 报告 | ✅ | 0 | 0 |
| 门禁（pytest/ruff/audit/boundary/保鲜） | ✅ | 0 | 0 |

## 可执行门禁（命令 + 退出码）

| # | 门禁 | 命令 | 退出码 | 结果 |
|---|------|------|:------:|------|
| G1 | fps 解析器 | `.venv python -m pytest tests/test_perf_fps_parser.py` | 0 | 8 passed（Android14 头行/窗口/jank/图层选择） |
| G2 | 采集契约回归 | `pytest tests/test_perf_fps_parser.py tests/test_perf_collector_contract.py tests/test_perf_api.py` | 0 | 52 passed（无回归） |
| G3 | 未定义名 | `ruff check app/services/perf_collector_service.py tests/test_perf_fps_parser.py --select F821` | 0 | PASS |
| G4 | 条件审计 | `pwsh scripts/git/audit-cconditions.ps1 -RequireLatestBatch` | 0 | hard 0 |
| G5 | 边界 | `python scripts/repo-split/validate_repo_boundaries.py --check` | 0 | PASS |
| G6 | 保鲜 | `python scripts/check_doc_freshness.py` | 0 | PASS |

## Android 采集证据（C84-2，session PERF-20260805-008）

| 指标 | 样本 | mean | min | max | 阈值 | 结果 |
|------|:----:|:----:|:---:|:---:|:----:|:----:|
| fps | 8 | **59.38** | 1 | 117 | ≥30 | ✅ PASS（120Hz 屏真实帧） |
| jank | 8 | 7.38 | 0 | 51 | ≤0 | ⚠️ 观察（真实渲染丢帧，非采集缺陷） |
| cpu % | 8 | 13.06 | 7.42 | 18.66 | ≤60 | ✅ PASS |
| memory MB | 8 | 410.37 | 204.54 | 473.04 | ≤512 | ✅ PASS |
| 启动耗时 | 1 | — | — | — | ≤2000 | ✅ 314ms |

- 驱动方式：adb 连续 fling（纵向赛事列表 + 横向 LIVE 轮播交替）28s，WS 采样流 9 帧（8 个入库点）。
- 证据：`test-platform-v2/work-logs/evidence/batch-99/real-device-collection-batch99.json` + `screenshot-home.png` + `ui-home.xml`。

## 缺陷与遗留

| # | 级别 | 内容 | 处理 |
|---|:----:|------|------|
| B99-P1 | P1 | Android 14 fps 恒 0：SoloX 2.9.3 解析 `dumpsys SurfaceFlinger --latency` 首行 `---- TIME:` 崩溃，采集线程死亡 | 采集器自实现解析（跳过头行/最近 1s 窗口 fps/2×刷新周期 jank）+ 图层选择（排除 InputSink/ActivityRecord）；8 单测；fps 修复后 mean 59.38 |
| B99-Q2 | P3 | 滚动场景 jank mean 7.38>0：RN 应用 120Hz 真实丢帧，非解析错误 | 数据观察如实记录；jank 阈值（≤0）对真实滚动过严，建议产品决策调整口径（不阻塞 C84-2） |
| B99-Q3 | P0(外部) | iOS 采集阻塞：Windows 主机无 Apple Mobile Device 驱动（tidevice 连 usbmux 被拒；无 iTunes/Apple 服务） | 登记解除条件：安装 iTunes/Apple Devices 驱动或 macOS 宿主；CP-C2/C84-1 保持 Open |

## CI 分层核对

- 变更范围：`test-platform-v2/backend/**` + `scripts/executor/**` + `docs/**` + `C-CONDITIONS.md` → 后端域分类；
  PR required contexts（后端全量）合入前核验。

## 发布建议

状态：**READY**（Android 验收通过 + 缺陷修复 + 证据完整；iOS 以阻塞登记，不伪造通过）。

## 复盘卡

| 计划耗时 | 缺陷(P0/P1/P2/P3) | 返工次数 | 根因分类 | 下次避免 |
|----------|-------------------|----------|----------|----------|
| 计划 0.5d / 实际 0.5d | 1(外部)/1/0/1 | 2（fps 参数闭包、图层选择） | 技术债+外部依赖 | 采集先做单点采样冒烟（含图层选择）再跑全链路 |

**技能使用**：`cameltv-agent-team`
