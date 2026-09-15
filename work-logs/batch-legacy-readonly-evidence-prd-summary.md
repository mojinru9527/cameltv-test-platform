# Batch PRD-lite — Legacy readonly production evidence

mode: light
executor: codex
date: 2026-09-16
豁免理由：纯生产证据与机器门禁状态更新，不新增运行时行为、接口、Schema 或执行体系。

## Goal

将已经在生产验证的 `legacy_urls_readonly_or_redirect` 门禁从保守 `false` 更新为 `true`，并记录 release 0002、410 实测、历史映射与恢复演练证据。

## Scope

- `legacy_delete_gate.json` 仅更新该单项 flag。
- 新增生产证据 work-log。
- 不修改 Legacy 代码，不删除表/worker，不修改 canonical ExecutionRun。

## Acceptance

- 生产 `release-20260916-0002` 为 `PRODUCTION_VERIFIED`。
- task cancel/retry/delete 与 runner claim 实测返回 410。
- Legacy 三表指纹与观察基线一致。
- `legacy_new_writes_zero_full_cycle` 和 signoff 继续保持 false。
