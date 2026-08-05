# Batch 91 — PRD-lite（Open 区可本地处理项收口）

> **Product (🟦)** | Date: 2026-08-05 | Status: Review

```markdown
mode: light
豁免理由: 验收/内部工具/纯文档（C90-1 统计脚本、C90-2 C21-P3 子项复核 + SOP 文档、C26KB-C3 检查点复核），
无新接口/新配置/新依赖/前端生产改动；按 pipeline-modes.md 判定轻量批次（PRD-lite + QA + Leader + 看板）。
非目标: 不改生产代码（除 audit-cconditions.ps1 统计输出）；不做外部 Deferred 项（真机/Test5/staging/账号/语料）。
```

## 1. 问题陈述

Batch 90 卫生审计后，Open 区剩余 29 项中 20 项为外部 Deferred。本批收口 3 个可本地处理项：
- **C90-1**：C-CONDITIONS 统计仍为手工维护（batch-90 校准过一次），需要脚本口径防漂移；
- **C90-2**：C21-P3 四子项（migration downgrade / playwright path traversal / diff_classifier docstring / VNext-N 编号）需逐一复核关闭；batch-18-C14《分环境灰度放量 SOP》文档缺失；
- **C26KB-C3**：知识中心 28 检查点（batch-26-KB 定义）从未在最终态复核通过率。

## 2. 成功指标

| 指标 | 基线 | 目标 |
|------|------|------|
| C90-1 | 手工统计 | audit-cconditions 输出 Open/Closed/Deferred 计数，维护约定引用脚本 |
| C90-2a | 四子项未复核 | 四子项逐项证据关闭（测试/守卫/docstring/编号约定） |
| C90-2b | SOP 缺失 | 《分环境灰度放量 SOP》文档落地 docs/ |
| C26KB-C3 | 未复核 | 28 检查点通过率 ≥90%（≥26/28），截图/代码锚点证据 |
| 门禁 | — | audit-cconditions 0 硬错；无生产代码回归 |

## 3. 用户故事 + 验收标准

- As a **Leader/Product**, I want 条件统计由脚本输出，so that 每批状态真实可信（C90-1）。
- As a **运维/发布负责人**, I want 灰度放量 SOP，so that 分环境发布/回滚有据可依（batch-18-C14）。
- As a **QA**, I want 知识中心 28 检查点最终复核，so that C26KB-C3 以证据关闭（≥90%）。

## 4. 技术考量

- C90-1：给 `audit-cconditions.ps1` 增加统计汇总输出（Open/Closed/Deferred 计数），复用现有解析逻辑，不改状态机规则。
- C90-2a：证据 = test_alembic_runbook.py（downgrade 覆盖）、lanhu_evidence.py:315 / ui_test.py:55（is_relative_to 守卫）、diff_classifier.py 模块 docstring、wiki 落地方案 VNext-1..6 编号。
- C90-2b：SOP 覆盖 环境分层（dev/test/staging/prod）→ 发布步骤 → 灰度节奏 → 回滚 → 检查清单。
- C26KB-C3：按 batch-26-KB QA 报告 28 检查点逐条核（浏览器 + API + 代码锚点），通过率 ≥90% 关闭；低于则登记缺陷。
