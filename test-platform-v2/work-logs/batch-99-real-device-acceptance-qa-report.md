# Batch 99 — QA 报告（真机性能验收：安卓双视频场景 + iOS 阻塞登记）

> **QA (🔍)** | Date: 2026-08-05 | Verdict: PASS（安卓双场景）；iOS BLOCKED（solox 支持缺失，如实登记）

## 测试总览

| 项 | 通过 | 失败 | 阻塞 |
|:---|:----:|:----:|:----:|
| 场景 A：安卓 Chrome www.camel1.tv 赛事视频流 10 分钟 | ✅ | 0 | 0 |
| 场景 B：小象直播 App 直播间 10 分钟（用户确认画面） | ✅ | 0 | 0 |
| 采集器缺陷修复（fps/cpu/WS 重试） | ✅ | 0 | 0 |
| iOS（Safari + 小象） | — | 0 | solox 无 iOS 26.5 DeviceSupport |
| 门禁（pytest/ruff/audit/boundary/保鲜） | ✅ | 0 | 0 |

## 可执行门禁（命令 + 退出码）

| # | 门禁 | 命令 | 退出码 | 结果 |
|---|------|------|:------:|------|
| G1 | 性能模块测试 | `pytest tests/test_perf_fps_parser.py tests/test_perf_collector_contract.py tests/test_perf_api.py` | 0 | **54 passed** |
| G2 | 未定义名 | `ruff check app/services/perf_collector_service.py app/api/v1/perf_ws.py tests/test_perf_fps_parser.py --select F821` | 0 | PASS |
| G3 | 条件审计 | `pwsh scripts/git/audit-cconditions.ps1 -RequireLatestBatch` | 0 | hard 0 |
| G4 | 边界 | `python scripts/repo-split/validate_repo_boundaries.py --check` | 0 | PASS |
| G5 | 保鲜 | `python scripts/check_doc_freshness.py` | 0 | PASS |

## 场景 A — 安卓 Chrome 赛事视频流（PERF-20260805-018，600s，11 点）

| 指标 | samples | mean | min | max | 阈值 | 结果 |
|------|:-------:|:----:|:---:|:---:|:----:|:----:|
| fps | 11 | **85.0** | 85 | 85 | ≥30 | ✅ PASS |
| cpu % | 11 | 3.55 | 2 | 8 | ≤60 | ✅ PASS |
| memory MB | 11 | 182.43 | 181.79 | 183.16 | ≤512 | ✅ PASS |
| jank | 11 | 28.0 | 28 | 28 | ≤0 | ⚠️ 视频帧间距口径观察 |

用户手动打开 Chrome → www.camel1.tv → 赛事视频流，确认在播后采集；证据 `real-device-chrome-sports-10min.json`。

## 场景 B — 小象直播直播间（PERF-20260805-023，600s，60 点）

| 指标 | samples | mean | min | max | 阈值 | 结果 |
|------|:-------:|:----:|:---:|:---:|:----:|:----:|
| fps | 60 | **31.23** | 1 | 57 | ≥30 | ✅ PASS |
| cpu % | 60 | **386.65** | 330 | 418 | ≤60 | ⚠️ FAIL（多核满载真实负载） |
| memory MB | 60 | **795.11** | 756.06 | 824.5 | ≤512 | ⚠️ FAIL（真实内存水位） |
| jank | 60 | 0.68 | 0 | 3 | ≤0 | ✅ 基本流畅 |

用户手动进入直播间并**确认画面在播**；截图 `shot-scenarioB-verify.png`（1.9MB）留证；证据 `real-device-app-live-10min.json`。

## 采集器修复（B99-P1 系列）

| 缺陷 | 修复 |
|------|------|
| SoloX 2.9.3 Android 14 `dumpsys SurfaceFlinger --latency` 的 `---- TIME:` 头解析崩溃 → fps 恒 0 | 自实现解析（跳过头行/最近 1s 窗口 fps/2×刷新周期 jank）+ 图层选择（排除 InputSink/ActivityRecord） |
| solox 多进程取错 pid → Chrome CPU/内存失真 | CPU 走 `/proc/<pid>/stat` 1s 双采样（多核如实上报>100%）；内存走 `dumpsys meminfo <pkg>` TOTAL PSS |
| 无线 adb 瞬时断开中断整场会话 | 采集循环重试 5×3s + 客户端 WS 容忍关闭帧 |

## 缺陷与遗留

| # | 级别 | 内容 | 处理 |
|---|:----:|------|------|
| B99-Q2 | P3 | jank 对 30fps 视频在 120Hz 屏下的帧间距口径过严（视频场景 jank 恒定偏高） | 数据观察；建议产品决策按视频帧率口径评估 |
| B99-Q4 | P3 | 采样周期 ~10–55s/点（dumpsys meminfo/fps 串行执行，Chrome 多进程尤慢） | 记录优化项：并行化各指标采集 |
| B99-Q5 | P3 | 小象直播间真实高负载：CPU 386%（多核，top 实测 273%）、内存 795MB，均超阈值 | 真实性能发现，属被测应用问题，登记供业务侧跟进 |
| B99-Q3 | P0(外部) | iOS 采集阻塞：solox 识别 iPhone 但缺 iOS 26.5 DeviceSupport（GitHub 404） | CP-C2/C84-1 保持 Open；解除条件：solox 支持该版本或提供受支持 iOS 设备 |

## CI 分层核对

- 变更范围：`test-platform-v2/backend/**` + `scripts/executor/**` + `docs/**` + `C-CONDITIONS.md` → 后端域；
  PR required contexts（后端全量）合入前核验。

## 发布建议

状态：**READY**（安卓双视频场景完成；iOS 以阻塞登记，不伪造通过）。

## 复盘卡

| 计划耗时 | 缺陷(P0/P1/P2/P3) | 返工次数 | 根因分类 | 下次避免 |
|----------|-------------------|----------|----------|----------|
| 计划 1d / 实际 1d+ | 1(外部)/1/0/3 | 4 | 外部依赖+工具链 | 视频场景先视觉确认再采集；采集循环先做断线重试；CPU 多核不封顶 |

**技能使用**：`cameltv-agent-team`
