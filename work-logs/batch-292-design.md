# Batch 292 — Design / Dev

## 接口

```python
TesterArmyAdapter(argv, version="1.2.3", cwd, env, timeout_s=300, artifacts_dir)
result = adapter.run(replay=True)
E2EResult(exit_code, status, stdout, stderr, duration_ms, artifacts, replay_exit_code)
```

## 规则

| 规则 | 实现 |
|------|------|
| 固定版本 | `version` 必填，注入 `TESTERARMY_VERSION` |
| 禁止 shell | 只接受 argv 数组，`shell=False` |
| 退出码 | 0→PASS，1→FAIL，其它→ERROR |
| 重放 | 第二次退出码必须等于第一次，否则 `E2EReplayMismatch` |
| 超时 | `TimeoutExpired` → exit -9 / ERROR / stderr 带 TIMEOUT |
| 产物 | 后缀映射 + size + sha256 |

## 决策

| ID | 决策 | 理由 |
|----|------|------|
| D-292-1 | PoC 用本地脚本模拟工具契约 | 不引入外部版本/网络依赖，先固化接口 |
| D-292-2 | 重放只比较退出码 | MVP 断言一致性；产物 diff 后续 |
| D-292-3 | 禁止 shell | 防注入，命令边界清晰 |
| D-292-4 | 超时=ERROR 而非 FAIL | 超时是基础设施问题，不是产品断言失败 |

## 文件

- `app/aiqe/drivers/external_e2e_driver.py`
- `tests/test_aiqe_testerarmy_adapter.py`（8 条）
