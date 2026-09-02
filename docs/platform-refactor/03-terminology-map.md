---
title: "引擎术语 → 业务 UI 词表映射表"
owner: "qa-team"
last_reviewed: "2026-09-02"
status: "active"
expires: "2027-03-02"
tags: ["terminology", "i18n", "ui-copy", "foolproof"]
related:
  - "docs/platform-refactor/04-foolproof-standards.md"
  - "docs/business-glossary.md"
---

# 引擎术语 → 业务 UI 词表映射表

> 用途：平台 UI 全部使用「业务测试员秒懂」的词；引擎概念只在专家模式/帮助/后台出现。
> 原则：**UI 说人话，引擎词进后台**。新页面文案一律查本表；本表未覆盖的新术语，先补表再上线。

## 1. 核心映射

| 引擎/内部词（禁用为普通用户文案） | 业务 UI 词 | 一句话解释（悬停/帮助用） |
|----------------------------------|-----------|--------------------------|
| Mission / VersionMission | 版本验收任务 / 版本任务 | 一个版本从需求到放行的完整测试 |
| Source / Sources | 需求与资料 | 需求文档、原型、接口文档、变更范围 |
| Ambiguity | 待澄清问题 | AI 没看懂、需要你确认的地方 |
| Scope | 测试范围 | 这版要测哪些功能点 |
| Contract | 验收点 | 什么才算「做对了」的确认清单 |
| Scenario | 场景 / 用例 | 一条可执行可验证的测试场景 |
| Oracle / Frozen Oracle | 预期结果 | 期望看到什么、判 PASS 的依据 |
| Action Plan / Command IR | 执行步骤 | AI 将怎么操作（浏览器/接口） |
| DataRequirement / Fixture | 测试数据准备 | 跑之前要造/准备的数据 |
| Runtime / Driver | 执行引擎 | 真正去执行测试的程序（不需要用户管） |
| ExecutionRun / Run | 执行记录 | 一次实际跑出来的结果 |
| Evidence | 证据 | 截图、请求/响应、回放，证明它跑过 |
| Replay | 证据回放 | 回看这次执行每一步发生了什么 |
| Acceptance / Verdict | 放行结论 | 这版能不能放行 |
| Campaign | 回归批次 | 一组自动回归 |
| Smart Regression | 影响面回归 | 这次改动会影响哪些旧功能 |
| Healing / Flaky | （专家）自动修复/不稳定用例 | 专家模式用 |
| Defect 分类（BUSINESS/AUTOMATION/DATA/ENV） | 业务问题 / 脚本问题 / 数据问题 / 环境问题 | 失败是谁造成的 |
| 人工确认 / HITL / Manual Assisted | 需要你确认 | 这步 AI 不能替你判断 |
| 置信度 confidence | AI 把握 | AI 对这个判断的把握程度 |

## 2. 文案硬规则

1. 按钮说动作和结果：「生成方案并让我审核」，不用「提交」；
2. 状态给下一步：「失败：环境不通，请检查目标环境」而不是红字报错；
3. 每个页面头部一行：「这个页面用来……你要做的第一件事是……」；
4. 危险动作（删除/生产执行/打回）按钮旁给「点了会发生什么」；
5. 空态给教学：「三步完成你的第一个 XX」；
6. 引擎术语出现在普通页面 = 该页未完成词表化，验收不过。

## 3. 维护

- 本表与 `docs/business-glossary.md` 对齐；新增术语由各批 Product 在 PRD 中登记并回填本表；
- 与前端组件 `TermTip`（batch-214 落地）联动：悬停解释数据源 = 本表。