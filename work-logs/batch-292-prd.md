# Batch 292（M3 / TA-017）— TesterArmy e2e Adapter PoC：PRD

> **部门**：🟦 Product · **日期**：2026-11-11 · **批次模式**：完整
> **分支**：feature/batch-292-m3-testerarmy-adapter · **基线**：origin/main `75a16352b`
> **里程碑**：M3 第 2 批

## 1. 问题

外部 e2e 工具（TesterArmy）版本漂移、重放不稳定、产物格式不统一，直接接入会污染 Run 证据。
TA-017 用 PoC 固化：固定版本、二次重放一致、退出码即断言、产物转 CamelTv 格式。

## 2. 目标

1. `TesterArmyAdapter(command, version=…)`：仅 argv 数组、必须 pin 版本、超时控制；
2. `run(replay=True)` 连跑两次，退出码不一致抛 `E2EReplayMismatch`；
3. 退出码 → 断言：0=PASS、1=FAIL、其它/超时=ERROR；
4. 产物按后缀映射：`.zip→trace`、`.png→screenshot`、`.json→report`、`.har→har` 等，
   附 size + sha256；
5. 注入 `TESTERARMY_VERSION` 与自定义 env。

## 3. 验收

| # | 标准 | 证据 |
|---|------|------|
| A1 | 成功执行 + 产物转换 | `test_pass_with_artifact_conversion` |
| A2 | 1 → FAIL，其它 → ERROR | `test_fail_exit_code` / `test_other_exit_code_is_error` |
| A3 | 版本/环境注入 | `test_version_is_injected` |
| A4 | 二次重放一致 | `test_replay_match` |
| A5 | 重放不一致拒绝 | `test_replay_mismatch_raises` |
| A6 | 超时 → ERROR | `test_timeout_maps_to_error` |
| A7 | 非法参数 | `test_invalid_arguments` |
| A8 | 全量 + ratchet | CI |

## 4. 非目标

- 真实 TesterArmy 二进制/镜像（PoC 用脚本模拟契约）；
- trace/artifact 深度转换（只做类型/哈希映射）；
- CI 调度接入（TA-019+）。
