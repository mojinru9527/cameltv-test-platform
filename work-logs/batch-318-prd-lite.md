# Batch 318（M6 / TA-035）— 文档 / Ops / Rollback：PRD-lite

> **mode: light** · **理由**：运维文档 + 版本锁/升级/回滚脚本（无运行时迁移）。
> **分支**：feature/batch-318-m6-ops-rollback · **基线**：origin/main `967725e17`

## 范围

- `docs/aiqe/ops.md`：空环境启动、最小 E2E、迁移清单、常见问题；
- `docs/aiqe/rollback.md`：版本锁、备份、回滚步骤、回滚后验证；
- `scripts/ops/aiqe-version-lock.ps1`（write/verify + SelfTest）；
- `scripts/ops/aiqe-upgrade.ps1` / `aiqe-rollback.ps1`（默认 DryRun，`-Execute` 才执行）。

## 验收

| # | 标准 | 证据 |
|---|------|------|
| A1 | 版本锁 SelfTest | `SELFTEST=PASS` |
| A2 | 写/校验锁 | WRITTEN / OK |
| A3 | 回滚 DryRun 计划 | 5 条命令输出 |
| A4 | 文档覆盖空环境 E2E | ops.md 第 1-4 节 |

## 非目标

- 在空机器真实起服务（命令已验证，环境需人工）；
- 自动回滚审批流（脚本保留 -Execute 门禁）。
