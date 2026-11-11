# Batch 293 — Design / Dev

## 接口

```python
audit_ebpf() -> EbpfAudit(system, euid, is_root, cap_bpf, cap_sys_admin, ready, notes)
assert_ebpf_ready(audit)
redact_payload(value) -> Any

KeployDriver(bin, cwd, report_path="keploy-report.json", timeout_s=300,
             env, require_ebpf=False)
  .record(command, test_set="default") -> KeployResult
  .replay(test_set="default", times=2) -> KeployResult
```

## 流程

```text
record：guard(可选 eBPF) → [keploy, record, --test-set, S, *cmd]
        → 读取 report → dependencies 至少 1 条 → 递归脱敏 → 返回
replay：guard → 连续 N 次 [keploy, replay, --test-set, S]
        → 比较每次 tests.passed/failed → 不一致抛 ReplayUnstable
```

## 决策

| ID | 决策 | 理由 |
|----|------|------|
| D-293-1 | 报告文件作为契约（JSON） | Keploy 输出格式可能变，先用稳定中间层 |
| D-293-2 | 权限门禁默认关闭、生产开启 | 本机/CI 无 eBPF；真实环境 `require_ebpf=True` |
| D-293-3 | 回放只比较 passed/failed | MVP 稳定性口径；深度 diff 后续 |
| D-293-4 | 脱敏在返回前做（含依赖） | 防敏感头进入 Run 证据 |

## 文件

- `app/aiqe/drivers/keploy_driver.py`
- `tests/test_aiqe_keploy_driver.py`（8 条）
