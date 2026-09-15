# Batch PRD-lite — Legacy history backfill

mode: light
executor: codex
date: 2026-09-16
豁免理由：这是内部历史迁移工具，不新增运行时接口、不改变 Schema、不引入新的执行模型；复用现有 `legacy_bridge`，仅补齐 `LegacyExecutionLink`。

## Problem

生产 `api_execution_task_item` 共 1999 条，其中 1942 条尚未写入 `legacy_execution_links`。PR-09 要求历史映射完成，否则删除 Legacy 表会丢失可追溯历史。

## Goal

提供一个默认 dry-run、显式 `--apply` 的幂等 backfill 工具：

- 只处理未链接的 `ApiExecutionTaskItem`。
- 复用 `legacy_bridge.bridge_api_item(run_id=None)` 创建 canonical `ExecutionRun`、Step、Evidence、AssertionResult 和 `LegacyExecutionLink`。
- 不修改 Legacy 表，不创建第二套执行体系。
- 重复执行不得产生重复 link 或重复 canonical run。

## Acceptance

1. dry-run 准确报告 total/linked/unlinked/selected。
2. `--apply` 后每个 selected item 恰有 1 条 `API_TASK_ITEM` link，且指向同一项目的 canonical Run。
3. 再次 apply/dry-run 显示 selected=0，且 canonical run 数不新增。
4. request/response/assertion JSON 被安全解析，坏 JSON 不导致整批失败。
5. 单元测试覆盖 dry-run、apply、幂等、项目隔离过滤。

## Out of scope

- 删除 Legacy 表/模型/worker。
- UI_RUN 映射（现有 73 条已链接）。
- 生产 apply 后的签字与观察期完成。
