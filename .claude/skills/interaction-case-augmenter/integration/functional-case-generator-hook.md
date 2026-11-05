# Mandatory Hook — Add Interaction Intelligence to the Existing Functional Case Generator

## Purpose

把现有功能用例生成器增强为“功能 + 交互 + 历史 Bug 知识检索”，不新建第二套测试用例生成流程，不因历史 Bug 数量机械增加用例。

## Insert point

在现有生成器完成 PRD/页面/接口/角色解析并生成基础功能场景之后、最终去重和序列化之前，加入下面的必经阶段。

## Runtime instruction (paste into the active generator Skill / system prompt)

```text
MANDATORY INTERACTION AND HISTORICAL BUG KNOWLEDGE ENRICHMENT

You are enriching the existing functional test cases, not creating a parallel suite.

A. Load project interaction rules and platform profile. Identify applicable views, controls, user roles, state transitions, input modalities, navigation, feedback, persistence, error recovery and admin-to-consumer behavior.

B. Keep the existing functional cases and schema. Add missing interaction assertions to an existing case whenever the same action path can validate them. Create a separate case only when a distinct failure mechanism needs an independently observable oracle.

C. Load the persistent project Bug Pattern Library from:
   .claude/skills/interaction-case-augmenter/references/historical-bug-pattern-library.json
   .claude/skills/interaction-case-augmenter/references/historical-bug-pattern-library.md
   .claude/skills/interaction-case-augmenter/references/bug-pattern-coverage.csv

D. For each relevant historical pattern, identify (1) detection point/location, (2) trigger conditions/action sequence, (3) expected observable oracle, and (4) existing test case IDs. Match by module/page/control/action/data/state/role/platform/dependency, not by title keyword alone.

E. Determine exactly one coverage state:
   COVERED_STRONG: existing test triggers the same failure condition and asserts the decisive oracle. Link Bug/Pattern ID only; add no case.
   COVERED_PARTIAL: related test exists but misses a necessary trigger or oracle. Enhance that existing case; do not add a parallel duplicate.
   GAP: no existing test can detect this failure mode and the current feature is applicable. Add the minimum necessary case or assertion.
   NOT_APPLICABLE: feature lacks the mechanism; skip and state why.
   NEEDS_CONFIRMATION: evidence or expected behavior is insufficient; do not guess.

F. De-duplicate across Bug records. Multiple Bugs sharing one failure pattern and one strong existing test do not create multiple tests. One case may link multiple Pattern IDs when it genuinely validates them.

G. Generic testing heuristics are not project historical Bugs. Label them GENERIC-RISK; do not invent Bug IDs, root causes or project history.

H. Optimize signal, not case count. No target percentage increase. Existing strong coverage => skip. Partial coverage => strengthen existing case. Only a verified gap => add a new case. It is valid to add zero cases.

I. Preserve project IDs, fields, priority labels, module mapping, storage path and import schema. Put Bug/Pattern links into existing supported metadata or companion coverage CSV; do not invent import columns.

J. At the end report counts: existing cases retained, existing cases enhanced, new cases added, strong-covered patterns skipped, not-applicable patterns, needs-confirmation patterns. For every added case, state the uncovered pattern and detection oracle.
```

## Orchestration

`load project case schema → parse requirement → generate base functional cases → interaction scan → pattern retrieval → existing-case coverage judgment → enhance/reuse/add minimal cases → de-duplicate → schema validation → update coverage map`

Important: Bug pattern mining/import is not run during every normal generation. It is a maintenance task performed only for initial import or newly discovered defects. Normal generation only reads the prepared Pattern Library and Coverage Map.

## Integration acceptance

1. The active generator must actually load this hook and references; copying Markdown files alone is not proof of runtime integration.
2. A pattern with strong coverage must produce no new test case.
3. A pattern with partial coverage must modify/augment the existing case, not create a duplicate.
4. An applicable uncovered pattern may add one minimum case with an explicit oracle.
5. Unrelated historical patterns must be skipped.
6. Existing functional case IDs, schema and baseline coverage must remain intact.
7. Run before/after sample generation and compare useful gap detection, duplication and generated/executed case count—not raw case count alone.
