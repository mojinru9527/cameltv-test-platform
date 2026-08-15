# Batch 185 — PRD：性能采集优化（C99-1 ①②③）

> **mode: full**（行为调整 + 新配置项，六部门工件）
> 来源：C-CONDITIONS C99-1（Batch 99 Leader 条件，P2）
> 执行：DeepSeek Harness（direct）| 日期：2026-08-16

---

## 1. 问题陈述

Batch 99 登记的「性能采集功能优化」四项，本批承接前三项代码可行动项：

1. **①采样周期并行化**（当前 10–55s/点 → 目标 ≤2s）：`collect_single_snapshot` 对 cpu/memory/fps/battery/network 五个指标**顺序**采集——CPU 内部 1s 双采样 + FPS dumpsys 查询 1-2s + 内存查询 ≈ 求和；battery/network 经 SoloX 较慢时单点可达 55s。
2. **②jank 视频帧率口径**：`_parse_surfaceflinger_latency` 以「帧间隔 > 2×刷新周期」判 jank——**30fps 视频在 120Hz 屏上每帧间隔=4×刷新周期，被系统性误报为 jank**（真实视频内容帧率与 UI 帧率不同源）。
3. **③多核 CPU 语义与阈值**：`_collect_cpu_android` 聚合多进程 utime+stime/窗口，多核下 >100% 如实上报但无语义说明、无归一选项。
4. **④iOS 26.5 支持**（solox DeviceSupport 缺失）——外部依赖，本批不承接（保持 C99-1 ④ 登记）。

## 2. 成功指标

| 指标 | 当前 | 目标 |
|------|------|------|
| 单点采样耗时 | 10–55s（顺序求和） | **≤2s+ε**（并行取 max；CPU 1s 窗口保留） |
| jank 误报（30fps 视频/120Hz 屏） | 系统性误报 | 内容感知口径：阈值=2×中位帧间隔（≥4 帧窗口），视频/UI 均不误报 |
| CPU 语义 | >100% 无说明 | `PERF_CPU_REPORT_MODE=raw|per_core` 配置（默认 raw 兼容现状；per_core ÷核数） |
| 回归 | — | test_perf_fps_parser 增视频场景；并行采集/CPU 归一单测；既有 perf 测试全绿 |

## 3. 验收

- Given 单点采集，When 五指标并行执行，Then 总耗时 ≈ max(各指标)（测试断言并行调用并发执行）。
- Given 30fps 视频帧序列（120Hz 屏，间隔≈4×刷新），When 解析，Then jank=0。
- Given UI 抖动帧序列（间隔突增>2×中位），When 解析，Then jank>0。
- Given PERF_CPU_REPORT_MODE=per_core，When 采集，Then 结果=raw÷核数；raw 模式保持 >100% 语义。

## 4. 非目标

- iOS 26.5 支持（solox 外部）；采集窗口调度（websocket 推送层）；前端指标展示改造。

## 5. C 条件

- C75-1 mode:full ✅；C75-3/C76-2/C78-1/C86-1/C104-5 ✅
- C99-1：①②③本批承接，完成后更新登记（④保持 Open 并注明外部解除条件）

## 6. 风险

| 风险 | 缓解 |
|------|------|
| 并行采集 adb 并发查询设备压力 | ThreadPoolExecutor 上限=指标数（5），adb 串行化由 adb server 自身处理；失败降级已有（单指标失败不影响整体） |
| jank 新口径改变既有阈值行为 | 中位基线+2×下限兜底（<4 帧回退旧规则）；fps 解析单测全量覆盖新旧场景 |
| CPU 归一配置默认值影响存量 | 默认 raw（行为不变），per_core 仅显式开启 |
