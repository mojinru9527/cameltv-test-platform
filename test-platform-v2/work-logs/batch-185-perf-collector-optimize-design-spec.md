# Batch 185 — Design Spec：性能采集优化（C99-1 ①②③）

> 配套 PRD：`batch-185-perf-collector-optimize-prd-summary.md`

## 1. ① 并行化单点采样（`perf_collector_service.collect_single_snapshot`）

- 现状：`for metric, collect in collectors.items(): result[metric] = collect() or {}` 顺序执行。
- 改后：`concurrent.futures.ThreadPoolExecutor(max_workers=len(collectors))` 并发提交全部指标，
  `as_completed` 收集结果；**单指标失败仍降级**（{} + failures 记录，行为不变）。
- CPU 内部 1s 双采样窗口保留（精度）；单点总耗时 ≈ max(cpu≈1.2s, fps≈1.5s, mem≈1s, …) ≤ 2s+ε。

## 2. ② jank 内容感知口径（`_parse_surfaceflinger_latency`）

- 现状：`间隔 > 2×refresh_ns` 判 jank（120Hz 屏 refresh≈8.3ms；30fps 视频间隔≈33ms=4×刷新 → 误报）。
- 改后（≥4 帧有效窗口时）：
  1. 计算相邻帧间隔序列；
  2. `baseline = median(intervals)`（内容实际节奏，视频 30fps→33ms；UI 120fps→8.3ms）；
  3. `jank = interval > 2 × baseline`（且 `interval > 2 × refresh_ns` 下限兜底防退化）；
  4. `< 4 帧` 回退旧规则（`> 2 × refresh_ns`）。
- 语义：UI 场景 baseline≈刷新周期 → 阈值≈2×刷新（与旧规则等价）；视频场景 baseline≈内容周期 → 不误报。

## 3. ③ CPU 语义配置

- `app/core/config.py` 新增 `perf_cpu_report_mode: str = "raw"`（raw | per_core），.env.example 同步。
- `_collect_cpu_android`：`per_core` 时 `appCpuRate = round(total*100 / core_count, 2)`；
  `core_count` 读 `/sys/devices/system/cpu/possible`（"0-7" → 8），失败回退 `os.cpu_count()`，再失败回退 raw。
- raw 模式保持现状（>100% 如实）。

## 4. 测试（扩展既有 perf 测试）

| 文件 | 用例 |
|------|------|
| test_perf_fps_parser.py | + 30fps/120Hz 视频序列 → jank=0；+ 60fps/120Hz UI 抖动 → jank>0；+ <4 帧回退旧规则；+ 120fps 流畅 → jank=0 |
| test_perf_collector_contract.py | + 并行采集（mock 指标函数记录并发进入，断言 max 并发=指标数）；+ CPU per_core 归一 |
| test_perf_api.py | 回归（无破坏） |

## 5. 文档

- config.py/.env.example 注释：PERF_CPU_REPORT_MODE 语义（raw=聚合可>100%；per_core=除以核数）。
- CLAUDE.md 常见陷阱 perf 小节补充 C99-1 口径说明（可选）。
