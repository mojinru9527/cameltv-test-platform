# Batch 326 — Design / QA / Leader

## 接口

```python
resolve_backend("windows"|"darwin"|"linux") -> backend
DesktopDriver(backend, executor).execute([DesktopAction]) -> {ok, error, actions}
IotDriver(protocol, transport).send({"op": readonly}) / .read_telemetry()
```

## 决策

| ID | 决策 | 理由 |
|----|------|------|
| D-326-1 | OS 映射后端 | Windows UIA / macOS AppleScript / Linux Electron |
| D-326-2 | 失败即停 | 避免后续动作在错误状态继续 |
| D-326-3 | IoT 默认只读 | 硬件写操作风险高，需审批扩展 |

## QA

| # | 结果 | 证据 |
|---|:----:|------|
| A1–A6 | ✅ | 6 单测 |
| A7 | ✅ | 全量 + ratchet PASS |

## Leader Verdict

# ✅ APPROVED

- TA-041/042 验收达成；全量 + ratchet 通过，无迁移。

放行：合入 main → Domain Packs（TA-043/044/045）。
