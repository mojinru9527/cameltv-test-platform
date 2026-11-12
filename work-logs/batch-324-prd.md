# Batch 324（M8 / TA-039）— Mobile Device Broker：PRD

> **部门**：🟦 Product · **日期**：2026-11-12 · **批次模式**：完整
> **分支**：feature/batch-324-m8-device-broker · **基线**：origin/main `747e01915`
> **里程碑**：**M8 第 1 批**

## 1. 问题

真机执行需要设备池：注册、按平台/能力分配、释放、健康统计；iOS 受 C84-1 门禁未解除。

## 2. 目标

1. `DeviceBroker`：register / list / allocate / release / health；
2. Android 优先；能力（capabilities）必须全部满足；
3. iOS 未解除 C84-1 → `PlatformNotEnabled`；
4. 重复注册/未知平台/无可用设备显式报错。

## 3. 验收

| # | 标准 | 证据 |
|---|------|------|
| A1 | 分配/释放 | `test_allocate_and_release` |
| A2 | 能力匹配 | `test_capability_filtering` |
| A3 | 无设备 | `test_no_device_available` |
| A4 | iOS 门禁 | `test_ios_gated_by_c84_1` |
| A5 | 重复/未知平台 | `test_duplicate_and_unknown_platform` |
| A6 | 健康统计 | `test_health_counts` |
| A7 | 全量 + ratchet | CI |

## 4. 非目标

- 真实 Appium/设备连接（协议先固化）；
- iOS 实机（C84-1 解除后）。
