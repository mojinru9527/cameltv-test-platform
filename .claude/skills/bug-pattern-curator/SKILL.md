---
name: bug-pattern-curator
description: 仅用于首次导入或增量整理项目历史 Bug：去重、分类、提炼为 interaction-case-augmenter 可检索的 Pattern Library，并核对现有用例覆盖强度。它不为每个 Bug 生成测试用例，也不在每次需求生成用例时执行。
owner: qa-team
last_reviewed: 2026-11-06
status: active
expires: 2027-05-05
tags: [bug-pattern, knowledge-base, maintenance]
related: ["../interaction-case-augmenter/SKILL.md", "references/bug-taxonomy.md"]
---

# Bug Pattern Curator — 历史缺陷知识维护

## 定位

按需运行的**知识库维护** Skill，不是第二个用例生成器。产物供 `../interaction-case-augmenter/` 读取。
任务是让主生成器「知道过去哪些机制容易出错、应该在哪测」，不是扩大每轮测试范围。

## 触发条件

仅以下情况运行：
- 首次导入历史 Bug 数据；
- 有新修复 Bug / 线上缺陷 / UAT 缺陷需要沉淀；
- 维护人员要求重新分类、去重或检查知识库质量；
- 现有测试用例变更，需要刷新 Pattern 覆盖映射。

普通的新需求用例生成**不调用**本 Skill。

## 输入

缺陷平台导出（PingCode/禅道/Jira）、Excel/CSV、Issue、测试报告、缺陷复盘、PR/Commit 修复说明。
先识别可读范围与来源，不得声称检查了不可访问的数据。

本项目已知可用输入：
- `未来娃屿-测试问题登记表.xlsx`（客户缺陷登记，含「测试验证」「处理状态（开发填）」）
- `未来娃屿测试bug统计.xlsx`（历史去重台账）
- `未来娃屿深度测试问题清单_*.xlsx` / `未来娃屿bug复测结果_*.xlsx`
- `work-logs/` 与各轮测试报告中的缺陷章节

## 执行步骤

1. **去重优先**：按原始 Bug ID、来源链接、标题/症状、触发序列、影响对象识别已导入项。已存在且未变化的 Bug 不重复导入；新证据只追加到原记录。
2. **规范化**：提取 `bug_id`、来源、版本、平台、模块/页面/控件、角色、前置条件、步骤、实际/预期、严重度、根因、修复状态、证据。未知值写 `unknown`。
3. **排除非 Bug**：需求变更、设计意见、误报、纯环境事故单独标注，不计入产品缺陷模式统计。
4. **多轴分类**：症状、交互失效模式、可能根因、平台/设备、业务影响。症状不得冒充根因（分类见 `references/bug-taxonomy.md`）。
5. **聚类**：相同失效机制可聚为一个 Pattern，保留全部原始 Bug ID；仅症状相似但触发机制不明时不要强行合并。
6. **提炼检测策略**：每个 Pattern 必须写清 `detection_point`、`trigger_signature`、`test_oracle`、适用范围与排除条件。
7. **核对既有用例**：逐条找到现有用例 ID，核实当前版本实际步骤与断言。Coverage Map 只是索引，不是覆盖证据；用例已删除/过期/步骤变更必须重新判定。覆盖分 `strong / partial / none / unknown`。
8. **只维护知识，不生成回归用例**：
   - strong → 记录关联，标记 skip；
   - partial → 记录需增强的既有用例；
   - none → 登记 coverage gap，留给主生成 Skill 在新需求相关时补测；
   - unknown → 等待证据，不编造。
9. **更新主 Skill 读取的文件**：
   - `../interaction-case-augmenter/references/historical-bug-pattern-library.json`
   - `../interaction-case-augmenter/references/historical-bug-pattern-library.md`
   - `../interaction-case-augmenter/references/bug-pattern-coverage.csv`
   - 由 JSON 生成的运行时摘要 `.claude/skills/test-case-design/bug-pattern-digest.md`

## Pattern 最低字段

`pattern_id, pattern_name, source_bug_ids, source_evidence, symptom, mechanism, confidence, applicability, trigger_signature, detection_point, test_oracle, existing_test_ids, coverage_strength, generation_action, last_reviewed`

结构校验：`../interaction-case-augmenter/references/historical-bug-pattern.schema.json`（`additionalProperties: false`，不得加自定义字段）。

## 学习规则

- 「学习」= 维护项目持久化知识库，不是微调模型权重。
- 每次新增 Bug 只更新 Pattern 证据/适用范围/覆盖状态，不必新建 Pattern。
- 每次新增或增强用例后更新 Coverage Map，使主生成器下次能跳过已强覆盖模式。
- 一个 Bug 已被现有用例强覆盖，不再要求新增重复回归用例。
- 旧用例只验证「页面能打开」而没有触发历史 Bug 关键动作与断言 → **不算强覆盖**。
- 历史 Bug 的修复版本与复测结果必须有证据；无证据不得标记已修复/回归通过。
- 对真实用户数据、账号、Token、Cookie 和业务敏感信息脱敏。

## 输出

1. `historical-bug-pattern-library.json`（机器检索）
2. `historical-bug-pattern-library.md`（人工评审摘要）
3. `bug-pattern-coverage.csv`（模式↔用例覆盖关系）
4. `bug-import-report.md`（导入/去重/分类/质量报告：新增 Bug 数、跳过重复数、合并 Pattern 数、strong/partial/none/unknown 数、证据不足项）
