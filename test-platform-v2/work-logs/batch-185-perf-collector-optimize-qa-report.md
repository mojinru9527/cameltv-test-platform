# Batch 185 — QA 报告：性能采集优化（C99-1 ①②③）

> **mode: full** | 执行：DeepSeek_Harness（direct）| 日期：2026-08-16
> 分支：`feature/batch-185-perf-collector-optimize`

## 0. 结论

✅ **C99-1 ①②③ 全部闭环**：并行采样（单点≤2s）、jank 内容感知口径（30fps 视频不误报）、CPU 语义配置（raw/per_core）；另修复 iOS 分支 collectX 调用语义潜在 bug。

## 1. 验收证据

| 项 | 证据 |
|----|------|
| ① 并行采样 | `collect_single_snapshot` ThreadPoolExecutor(5) 并发；`test_metrics_collected_in_parallel` 断言 max_active==5、耗时<2.5×单指标；单指标失败降级测试 ✅ |
| ② jank 口径 | 中位间隔基线 + 2×刷新下限兜底 + <4 帧回退旧规则；新测试：30fps/120Hz→jank=0、60fps/120Hz→jank=0、UI 抖动 5×→jank≥1、小窗口回退 ✅ |
| ③ CPU 语义 | `PERF_CPU_REPORT_MODE=raw`（默认，>100% 如实）\|`per_core`（÷核数，adb possible 探测+本机回退）；raw=100%/per_core 8 核=12.5% 断言 ✅ |
| 附加修复 | iOS 分支 `apm.collectCpu` 等由「返回 bound method」改为「调用返回数据」（契约测试 BrokenMonitor 佐证） |
| 回归 | perf 全组 66 例绿（fps 12 + c99 6 + contract 8 + api 39+1）；全量 1544/0 |

## 2. 硬门禁

| 门禁 | 结果 |
|------|------|
| 后端 pytest 全量 | **1544 passed / 0 failed / 3 skipped**（含子模块初始化复跑） |
| ruff F821 | All checks passed |
| alembic | 无迁移 |

## 3. 复盘卡

| 字段 | 内容 |
|------|------|
| 计划耗时 | ~6h（计划）vs ~3h（实际） |
| 缺陷 | P0:0 / P1:0 / P2:1（iOS 分支 collectX 语义潜在 bug，本批测试暴露并修复）/ P3:3（测试自身：settings 未导入/采样不递增/契约语义误读） |
| 返工次数 | 3 |
| 根因分类 | 技术债 / 工具链 |
| 下次避免 | 契约类测试先读既有 contract 测试的 fake 语义；并发测试真线程 |
