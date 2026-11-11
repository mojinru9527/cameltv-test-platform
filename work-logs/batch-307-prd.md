# Batch 307（M4 / TA-028）— Platform Acceptance Matrix：PRD

> **部门**：🟦 Product · **日期**：2026-11-12 · **批次模式**：完整（前端）
> **分支**：feature/batch-307-m4-platform-matrix · **基线**：origin/main `9688c1f8a`
> **里程碑**：M4 第 5 批（收口）

## 1. 问题

同一条 AC 在多端（Web/H5/小程序/Android/iOS）的验收结果需要并排展示：每端有独立
build/device/profile/actual/evidence，还要看到跨端语义类型，避免“一端通过就算全通过”。

## 2. 目标

1. `<PlatformMatrix />`：AC × 平台矩阵；
2. 每端独立展示 `actual`、`build · device · profile`、证据引用；
3. 跨端语义类型（如“跨端一致性”）以 Badge 展示；
4. 缺失平台显示 `—`；空态提示。

## 3. 验收

| # | 标准 | 证据 |
|---|------|------|
| A1 | 同 AC 多端独立数据 | `PlatformMatrix.test.tsx` 第 1 条 |
| A2 | 语义类型展示 | 同上 |
| A3 | 缺失平台占位/空态 | 第 2 条 |
| A4 | typecheck/build/全量 | 560 passed + build |

## 4. 非目标

- 后端 binding 存储（后续 `platform_bindings` 表）；
- 与 Run 详情联动。
