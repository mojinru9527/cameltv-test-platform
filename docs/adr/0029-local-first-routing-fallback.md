---
title: "ADR-0029: 本地优先路由与云端失败兜底"
owner: "tech-lead"
last_reviewed: "2026-09-13"
status: "active"
expires: "2027-09-13"
tags: ["adr", "ai", "routing", "fallback", "local-first"]
related: ["0027-ai-local-first-gateway.md", "0028-local-ai-runtime-shadow-mode.md"]
---

# ADR-0029: 本地优先路由与云端失败兜底

## 状态

已采纳。Batch 237 实现路由计划；生产默认仍为 `cloud_only`。

## 决策

1. 使用显式模式：`cloud_only`、`shadow`、`local_preferred`、`local_only`。
2. `local_preferred` 在本地 runtime 可用时本地优先，失败后按配置回云端。
3. `local_only` 无本地 runtime 时直接失败，禁止暗中回云。
4. `shadow` 以云端为主，本地为观察对端；`local_preferred` 的 shadow 对端为云端。
5. 路由来源与 fallback 来源写回调用结果，供执行证据和调试使用。
6. fallback 结果不写入本地 Provider 的 exact cache，避免缓存键与来源错配。

## 弃选方案

| 方案 | 否决理由 |
|------|----------|
| 自动根据 shadow 分数切换 | 缺少稳定阈值与审批，容易引入静默行为变化 |
| local-only 失败自动回云 | 会掩盖配置错误并产生不可控成本 |
| 全局替换 Provider 配置 | 无法保留项目级 Provider 与回退语义 |
