# Batch 299（M3 / TA-023）— Interference Detectors：PRD

> **部门**：🟦 Product · **日期**：2026-11-11 · **批次模式**：完整
> **分支**：feature/batch-299-m3-interference-detectors · **基线**：origin/main `36a16fd5e`
> **里程碑**：M3 第 8 批

## 1. 问题

执行环境抖动（CPU 限流、内存压力、网络延迟、DNS 失败、磁盘满、进程崩溃、端口冲突、
依赖 5xx、时钟偏移、锁竞争）会污染 Run 结果。需要 10 类预置检测信号，且检测本身不能改
Run 状态（避免“检测即副作用”）。

## 2. 目标

1. 10 个检测器 + 统一 `detect(payload)` 纯函数；
2. 每类信号含 kind/severity/evidence；
3. 检测不修改 payload、不写库、不改 Run；
4. 严重度分级（warning/critical）；
5. 输入非法类型拒绝。

## 3. 验收

| # | 标准 | 证据 |
|---|------|------|
| A1 | 10 类各自命中 | `test_each_kind_detected`（10 组） |
| A2 | 干净 payload 无信号 | `test_clean_payload_has_no_signals` |
| A3 | 极端值 critical | `test_critical_severity_for_extremes` |
| A4 | 多信号顺序 | `test_multiple_signals_and_order` |
| A5 | 纯函数/确定性 | `test_detection_is_pure_and_deterministic` |
| A6 | 不改 Run 状态 | `test_detection_does_not_touch_run_state` |
| A7 | 非法输入 | `test_invalid_payload_rejected` |
| A8 | 全量 + ratchet | CI |

## 4. 非目标

- 真实节点采集器（Runner 侧 detectors 后续接）；
- 信号入库/UI 展示（interference_observations 表后续）；
- 自动降噪/合并。
