# Batch 304（M4 / TA-026）— Defect Draft + Link：PRD

> **部门**：🟦 Product · **日期**：2026-11-12 · **批次模式**：完整
> **分支**：feature/batch-304-m4-defect-draft-link · **基线**：origin/main `3a04a0b9c`
> **里程碑**：M4 第 2 批

## 1. 问题

AIQE 失败后需要“一键转缺陷”，但缺陷必须带：结构化复现步骤、可跳转证据、关联验收标准（AC），
详情页要能看到 linked execution。手工拼描述易丢证据、重复建单。

## 2. 目标

1. `Defect` 增加 AIQE 关联字段：`aiqe_run_id / aiqe_node_run_id / reproduction_steps_json /
   evidence_refs_json / ac_refs_json / is_draft`；
2. `create_draft_from_failure()`：
   - 步骤必须含 `action + expected`；
   - 证据前缀白名单（artifact/event/run/node/signal）；
   - 至少 1 条 AC 且格式 `AC…`；
   - 同 Run + 标题幂等；
3. 迁移 `20261119`（SQLite/PG 可重跑）；
4. 缺陷详情页展示 linked execution、AC、复现步骤与证据（`AiqaLinkSection`）。

## 3. 验收

| # | 标准 | 证据 |
|---|------|------|
| A1 | 结构化草稿 + 字段落库 | `test_create_draft_with_structured_reproduction` |
| A2 | 缺 action/expected 拒绝 | `test_missing_action_rejected` / `test_missing_expected_rejected` |
| A3 | 空步骤拒绝 | `test_empty_steps_rejected` |
| A4 | 证据白名单 | `test_empty_evidence_rejected` / `test_invalid_evidence_prefix_rejected` |
| A5 | AC 必需且格式校验 | `test_ac_required_and_valid` |
| A6 | 幂等 | `test_idempotent_same_run_and_title` |
| A7 | 详情页展示 linked/AC/步骤/证据 | `AiqaLinkSection.test.tsx`（2 条） |
| A8 | 全量 + ratchet + typecheck | CI |

## 4. 非目标

- 缺陷草稿确认/关闭流程（人工）；
- API 路由（本批 service + UI；路由后续接入）；
- 附件自动上传（证据仍以引用形式）。
