# Batch 158 — 生产 500 热修：统计口径 PG 裸子查询（PRD-lite）

> **Product (🟦)** | Date: 2026-08-12 | Status: Approved | Mode: light

mode: light
豁免理由: 纯 Bug 修复（一行条件表达式），无新接口/新配置/新依赖，紧急生产热修。
非目标: 不调整统计口径语义；不改其他模块。

## 1. 问题陈述
生产 `GET /api/v1/trace/coverage` 与 `GET /api/v1/dashboard/stats` 返回 500。
只读复现：`statistics_service._execution_filter` 在 `plan_case_ids_sub=None` 分支把标量子查询直接作为 WHERE 条件
`WHERE (SELECT test_plan_case.id ...)`，PostgreSQL 报 `argument of WHERE must be type boolean, not type integer`；
SQLite 宽松不报，故本地/CI 全绿，生产 PG 才炸。Batch 149 引入。

## 2. 修复
`_execution_filter` 补 `TestExecution.plan_case_id.in_(plan_case_ids)` 包装。

## 3. 验收标准
- 生产只读复验：project 1/7 的 stats/coverage/dashboard 全部 OK。
- 回归测试：PG 方言编译断言含 `IN (SELECT test_plan_case.id`，不含 `WHERE (SELECT`。

## 4. 技能使用
- cameltv-bug-guard（方言差异坑）、cameltv-agent-team 流水线
