# Batch 290（M2 / TA-015）— Driver Registry + Capability：PRD

> **部门**：🟦 Product · **日期**：2026-11-11 · **批次模式**：完整
> **分支**：feature/batch-290-m2-capability-registry · **基线**：origin/main `dfaba496c`

## 1. 问题

调度器此前只按 Run/节点状态推进，不知道节点是否真的具备 WebKit/DB 等能力；自描述若无
实测 evidence 支撑，会把任务派给跑不了的节点。

## 2. 目标

1. `node_capability_manifests` 表：node/driver/version/capabilities/platforms/并发/artifact 类型/
   `last_evidence_ref`/`available`；
2. `available` 必须由 `last_evidence_ref` 支撑（无 evidence 不可用）；
3. `select_nodes(required)`：缺任一能力的节点不会被选中（缺 WebKit 不接 WebKit 任务）；
4. `known_capabilities()` 接入 Workflow Validator 的 `registered_capabilities`；
5. 迁移 `20261115`。

## 3. 验收

| # | 标准 | 证据 |
|---|------|------|
| A1 | 无 evidence → unavailable | `test_register_without_evidence_is_unavailable` |
| A2 | 有 evidence → supports | `test_register_with_evidence_and_supports` |
| A3 | 缺 WebKit 不被选中 | `test_node_without_webkit_not_selected` |
| A4 | 多能力必须全覆盖 | `test_select_requires_all_capabilities` |
| A5 | upsert 单行更新 | `test_upsert_updates_single_row` |
| A6 | evidence 回填翻转 available | `test_record_evidence_flips_available` |
| A7 | 校验器接入 | `test_known_capabilities_drive_validator` |
| A8 | 全量 + ratchet | CI |

## 4. 非目标

- 节点心跳/租约（M3）；
- 实测探针执行（TA-013 Driver 后续跑 harness 生成 evidence）。
