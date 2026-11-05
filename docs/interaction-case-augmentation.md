---
title: "用例生成交互增强与历史缺陷学习（skill pack v1.1.0 适配）"
owner: "qa-team"
last_reviewed: "2026-11-06"
status: "active"
expires: "2027-05-06"
tags: ["case-generation", "interaction", "bug-pattern", "skill"]
related: ["../.claude/skills/interaction-case-augmenter/SKILL.md", "../.claude/skills/bug-pattern-curator/SKILL.md", "../.claude/skills/test-case-design/SKILL.md"]
---

# 用例生成交互增强与历史缺陷学习

> 来源：`cameltv-qa-skill-pack v1.1.0`（2026-11-05）。本页记录**适配到本仓库后的落地形态**，不是原包 README 的拷贝。

## 1. 目标与边界

| 目标 | 非目标 |
|---|---|
| 功能用例生成时自动补齐交互校验（页面/控件/状态/反馈/导航/输入/权限/平台） | 不新建第二套平行用例体系 |
| 历史缺陷整理为项目级 Pattern Library，生成时按覆盖判定复用 | 不按 Bug 数量机械生成回归用例 |
| 强覆盖跳过、部分覆盖增强、真实缺口才新增 | 不设「用例必须增长 X%」目标 |
| 补齐 C 端交互与接口 oracle 的判定强度 | 不改变既有用例 ID、字段与导入 Schema |

## 2. 资产位置

| 资产 | 路径 | 作用 |
|---|---|---|
| 主增强 Skill | `.claude/skills/interaction-case-augmenter/SKILL.md` | 生成期方法、Phase A–G、覆盖判定 |
| 缺陷知识库（机器） | `.claude/skills/interaction-case-augmenter/references/historical-bug-pattern-library.json` | 唯一检索事实源，schema 校验 |
| 缺陷知识库（人工） | `.claude/skills/interaction-case-augmenter/references/historical-bug-pattern-library.md` | 模式索引与统计 |
| 覆盖映射 | `.claude/skills/interaction-case-augmenter/references/bug-pattern-coverage.csv` | Pattern ↔ 既有用例 ↔ 判定 ↔ 动作 |
| 通用交互清单 | `.claude/skills/interaction-case-augmenter/references/universal-interaction-checklist.md` | A–I 检查点 |
| 知识维护 Skill | `.claude/skills/bug-pattern-curator/SKILL.md` | 首次/增量导入缺陷，按需运行 |
| 交互规范中心 | `tests/test-case-standards/interaction-testing/` | 方法论、平台 Profile、后台↔C 端、权限层级 |
| 运行时清单（功能） | `.claude/skills/test-case-design/interaction-checklist.md` | 注入生成 prompt |
| 运行时清单（接口） | `.claude/skills/test-case-design/api-interaction-checklist.md` | 注入生成 prompt |
| 运行时摘要 | `.claude/skills/test-case-design/bug-pattern-digest.md` | 29 条模式压缩表，注入 prompt |
| 生成入口 | `.claude/skills/test-case-design/SKILL.md` 第 7 步 | 强制阶段 |

## 3. 运行时如何真正生效

平台 AI 生成链路：`test-platform-v2/backend/app/services/ai_service.py`

```
_load_skill_context_for("functional")
  = SKILL.md + case-template.md + functional-checklist.md + 功能测试输出用例要求.md
    + interaction-checklist.md + bug-pattern-digest.md
_load_skill_context_for("api")
  = api-checklist.md + 接口测试输出用例要求.md + 接口测试考虑点【辅助作用】.md
    + api-interaction-checklist.md + bug-pattern-digest.md + SKILL.md
```

守卫测试：`test-platform-v2/backend/tests/test_interaction_skill_context.py`

- 证明两个 kind 都加载增强层；
- 证明增强层缺失时**只退化不报错**；
- 证明 13 个 Skill/规范资产真实存在；
- 证明 29 条 Pattern 满足 schema、且 `coverage_strength ↔ generation_action` 一一对应；
- 证明 digest 体积受控（< 16K 字符），不会挤占生成上下文。

> 只把 Markdown 复制进 `.claude/skills/` 而不改加载器，在线生成行为不会改变。

## 4. 覆盖判定口径

| 判定 | 含义 | 生成动作 |
|---|---|---|
| `COVERED_STRONG` | 既有用例的触发条件 + 检测位置 + 关键 oracle 能捕获该失效 | 只关联 Pattern/Bug ID，不新增 |
| `COVERED_PARTIAL` | 有相关用例但缺触发条件或断言 | 增强该用例步骤/预期，不建平行用例 |
| `GAP`（库中记 `none`） | 无用例能触发并发现，且当前需求适用 | 新增一条最小可判定用例 |
| `NOT_APPLICABLE` | 当前需求无该机制 | 跳过并写理由 |
| `NEEDS_CONFIRMATION` | 证据/预期不足 | 标 `OPEN`，不猜测 |

## 5. 未来娃屿首轮导入结果（2026-11-06）

- 来源：`未来娃屿-测试问题登记表.xlsx`（35 条）、`未来娃屿测试bug统计.xlsx`（52 条台账）、`未来娃屿深度测试问题清单_20261104.xlsx`（42 条）、安全/基础设施/接口回归报告。
- 聚类为 **29 个 Pattern**（CAMEL-BP-001 ~ 029）。
- 覆盖判定：**strong 6 / partial 16 / none 7**（判定依据写进 `bug-pattern-coverage.csv` 的 `reason` 列）。
- 口径：automated 关键词匹配只产出候选，最终强度按「触发条件是否为用例主题 + 断言是否可捕获」人工裁定，避免标题相似误判强覆盖。

## 6. 维护流程

- **正常生成**：只读 Pattern Library + Coverage Map，不挖掘历史 Bug。
- **新增缺陷 / 复测结论变化**：调用 `bug-pattern-curator` 更新 JSON + MD + CSV，并重新生成 digest；不在生成时临时挖掘。
- **新增/增强用例后**：回写 `bug-pattern-coverage.csv` 的 `existing_test_ids` 与判定，使下一轮能正确跳过。

## 7. 评估口径（不只看用例数）

| 指标 | 说明 |
|---|---|
| 历史缺陷模式命中率 | 本轮实际验证到的 Pattern / 适用 Pattern |
| 强覆盖误判率 | 被判 strong 却仍复现缺陷的比例，目标 0 |
| 重复用例率 | 新增用例与既有用例在触发+oracle 上重复的比例 |
| 真实缺口数 | 判 none 且当前需求适用的 Pattern 数 |
| 单位用例发现价值 | 新增缺陷数 / 新增用例数 |

禁止用「用例总数增长」作为增强效果证明。
