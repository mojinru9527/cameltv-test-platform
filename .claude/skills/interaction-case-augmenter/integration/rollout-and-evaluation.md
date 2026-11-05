# Rollout and Evaluation Plan

## 1. Suggested repository placement

- `.claude/skills/interaction-case-augmenter/` — 主生成增强 Skill，统一执行交互扫描和历史 Bug Pattern 检索。
- `.claude/skills/bug-pattern-curator/` — 仅用于首次导入/增量维护历史 Bug 知识，不在每次用例生成时调用。
- `tests/test-case-standards/interaction-testing/` — 通用交互方法、后台/C端交互、角色权限及平台 Profile。
- `integration/functional-case-generator-hook.md` — 合入现有功能用例生成器的必经指令。

## 2. Bootstrap existing history once

1. 从用户提供的 Bug 导出文件/缺陷系统导出/报告中读取真实历史记录。
2. 按 Bug ID 和来源指纹跳过已导入记录，增量补充新证据。
3. 将相同失效机制聚类为 Pattern，保留所有来源 Bug ID。
4. 为每个 Pattern 写明检测位置、触发条件、oracle。
5. 对照现有功能用例判断 strong / partial / none / unknown。
6. 只把 Pattern Library 和 Coverage Map 写入主生成 Skill 的 references；不自动批量生成回归用例。

## 3. Normal generation loop

新需求只需要加载已经准备好的知识库：

`parse new requirement → build base functional cases → interaction scan → retrieve relevant Patterns → inspect existing coverage → skip/enhance/add-minimal → deduplicate → schema validation → update coverage map`

不在普通用例生成时再次全量挖掘历史 Bug。新 Bug 只有在被确认/修复或需要沉淀时，才通过 curator 增量维护。

## 4. Pilot

选择一个同时包含 C 端页面和后台管理对象的真实需求（Banner、文档或内容管理均可），使用同一份需求和相同既有用例分别运行旧生成器、新增强生成器。重点比较：

- 原有功能覆盖保留；
- 发现的交互断言缺口；
- 历史 Pattern 的相关性与检测位置准确性；
- strong/partial/gap/N/A 判定正确率；
- 旧用例增强数量与真实新增用例数量；
- 重复用例率和净执行时间变化；
- 用例导入 Schema 是否完全兼容。

## 5. Acceptance gates

- strong-covered Pattern 不新增用例；
- partial Pattern 先增强原用例；
- 只有适用且真实未覆盖的 Pattern 才新增最小用例；
- Pattern 必须可追溯真实 Bug ID 和证据；通用检查不得伪装为历史 Bug；
- 原功能用例编号/字段/导入结构不改变；
- 不以用例数量增长作为效果指标；
- 平台真实生成服务必须加载 Hook 和 Pattern Library，不能仅以文件复制作为接入完成。
