# Batch 324 — Design / QA / Leader

## 接口

```python
DeviceBroker(devices)
  .register(device) / .list_devices(platform, capability)
  .allocate(platform="android", capabilities=()) -> Device(busy)
  .release(device_id) -> Device(available)
  .health() -> {available,busy,offline}
```

## 决策

| ID | 决策 | 理由 |
|----|------|------|
| D-324-1 | 内存池 | 真机池管理先固化状态机，持久化后续 |
| D-324-2 | iOS 硬门禁 | C84-1 未解除不得接入 |
| D-324-3 | 能力全匹配 | 防止分配到缺能力设备 |

## QA

| # | 结果 | 证据 |
|---|:----:|------|
| A1–A6 | ✅ | 6 单测全过 |
| A7 | ✅ | 全量通过；ratchet PASS |

## Leader Verdict

# ✅ APPROVED

- TA-039 验收达成（Android 优先、能力匹配、iOS 门禁）；
- 全量 + ratchet 通过，无迁移。

放行：合入 main → TA-040 小程序 Adapter。
