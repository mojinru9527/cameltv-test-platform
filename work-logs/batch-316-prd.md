# Batch 316（M6 / TA-034）— CamelTv Sports 纵向验收：PRD

> **部门**：🟦 Product · **日期**：2026-11-12 · **批次模式**：完整
> **分支**：feature/batch-316-m6-sports-vertical · **基线**：origin/main `9e2f6061c`
> **里程碑**：M6 第 2 批

## 1. 问题

平台需要一条真实业务纵向验收：TC-AIQE-001..010 全部可执行，并能演示“制造缺陷 → 发现 →
修复 → 全绿”。

## 2. 目标

1. `SportsVerticalAdapter` + 10 条纵向用例（直播入口/起播/暂停/清晰度/收藏/搜索/断流重连/
   比分/分享/弱网）；
2. 执行器注入（真实 UI/节点或 fake），汇总 total/passed/failed/evidence；
3. 断流重连可注入缺陷：修复前 1 条失败 + 证据，修复后 10/10 通过。

## 3. 验收

| # | 标准 | 证据 |
|---|------|------|
| A1 | 10 条用例定义 | `test_ten_cases_defined` |
| A2 | 健康时 10/10 | `test_all_cases_pass_when_healthy` |
| A3 | 制造 Bug 被发现 | `test_seeded_bug_is_discovered` |
| A4 | 修复后全绿 | `test_bug_fixed_all_green` |
| A5 | 全量 + ratchet | CI |

## 4. 非目标

- 真实浏览器执行（执行器由节点注入；本批固化场景契约）；
- 多端（Web/H5/小程序）矩阵（TA-028 已备组件）。
