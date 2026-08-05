# Batch 90 — PRD-lite（C 条件追踪器卫生审计）

> **Product (🟦)** | Date: 2026-08-05 | Status: Review

```markdown
mode: light
豁免理由: 纯证据/内部流程批次（C89-2 追踪器卫生审计 + 旧孤儿复核），无新接口/新配置/新依赖/前端改动；
按 pipeline-modes.md 判定为轻量批次（PRD-lite + QA + Leader + 看板）。
非目标: 不改生产代码；不做外部项（iOS 真机/Test5/staging）；不重分类 WARN 豁免清单。
```

## 1. 问题陈述

C-CONDITIONS.md 是 Agent Team 的条件追踪事实源，但历史维护导致三类失真：
1. **Open 区 inline-CLOSED 挂账**（15 条）：条件已关闭但仍在 Open 区（如 C22-C2/C3、C58-*、CP-C1 等）；
2. **Open/Closed 重复挂账**（10 条）：同一条件同时出现在 Open 与 Closed 表（如 C75-4、C76-1、C77-1/2、C79-1、C80-1、C68-4 等）；
3. **旧孤儿长期未核**（2026-07 起 20+ 条）：batch-18/19/21/24/25v2/26KB/27/31 遗留，部分实际已实现但未关闭（如 C21-P1-2 在 batch-89 发现的同类问题）。

失真会让 Product 开工时误纳入已闭环条件、统计口径错误，并稀释真正待办项的可见度。

## 2. 成功指标

| 指标 | 基线 | 目标 |
|------|------|------|
| Open 区准确性 | 33（含 inline-CLOSED 与重复） | 27（7 门禁 + 20 外部 Deferred，逐条可追溯） |
| 重复/挂账清理 | 10 重复 + 15 inline | 全部归位（Closed 表或 Deferred） |
| 孤儿复核 | 20+ 未核 | 证据关闭或明确 Deferred（解除条件） |
| 审计门禁 | — | audit-cconditions 0 硬错；本批变更仅 docs + tracker |

## 3. 用户故事 + 验收标准

- As a **Product/Leader**, I want 条件追踪器只含真实待办，so that 每批开工无需被历史挂账误导。
  - Given 逐条核对 Open 区，When 对照 Closed 表与代码现状，Then 能关闭的关闭（带证据）、外部项标注 Deferred（带解除条件）、流程门禁保留。

## 4. 技术考量

- 证据来源：Closed 表现有记录、inline 标注、代码现状（模型/路由/前端组件/e2e）、历史 PR（#66/#105/#108/#123/#124/#126）。
- 外部/阻塞项（iOS 真机、Test5、staging、生产、人工审查、SOP、语料）统一转 Deferred 并写明解除条件。
- 本批无生产代码变更，仅 C-CONDITIONS.md + work-logs 工件。
