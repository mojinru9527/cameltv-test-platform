# Batch PRD — Legacy readonly boundary (PR-08)

mode: light
豁免理由：本批次只加 canonical path 的 legacy bridge 隔离守卫；历史 bridge 与自动创建逻辑暂保留兼容，不在未有版本周期证据时删除。

## Acceptance
- Campaign canonical service contains no legacy_bridge/_ensure_legacy_run usage.
- Existing bridge compatibility tests remain green.
- Delete phase remains gated by PR-09 conditions.
