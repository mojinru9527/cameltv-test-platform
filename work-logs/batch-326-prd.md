# Batch 326（M8 / TA-041 + TA-042）— Desktop / IoT Drivers：PRD

> **模式**：完整 · **分支**：feature/batch-326-m8-desktop-iot-drivers · **基线**：`2f4f2d1d9`

## 目标

1. Desktop Driver：Electron / Windows UIA / AppleScript，按 OS 解析后端，动作失败即停；
2. IoT Driver：mqtt/http/serial，默认只读（read/measure/telemetry/status），写操作拒绝；
3. 未知后端/协议/动作显式报错。

## 验收

| # | 标准 | 证据 |
|---|------|------|
| A1 | OS→后端 | `test_resolve_backend_by_os` |
| A2 | 桌面动作成功 | `test_desktop_execute_success` |
| A3 | 失败停止 | `test_desktop_failure_stops` |
| A4 | 非法后端/动作 | `test_desktop_invalid_backend_and_action` |
| A5 | IoT 协议 | `test_iot_protocols_and_readonly` |
| A6 | 只读/遥测 | `test_iot_telemetry_and_write_rejected` |
| A7 | 全量 + ratchet | CI |

## 非目标

- 真实 UIA/AppleScript/串口连接（executor/transport 注入）。
