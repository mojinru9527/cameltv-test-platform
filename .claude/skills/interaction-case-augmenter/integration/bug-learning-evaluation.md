# Bug Knowledge Learning Evaluation

## Objective

证明历史 Bug 知识提高新需求用例的有效发现能力，而不是单纯增加用例数或执行时间。

## Golden evaluation set

为每一条真实历史 Bug Pattern 准备：
- 原 Bug ID 和证据；
- 最适用的功能/页面/控件/状态特征；
- detection_point；
- trigger_signature；
- test_oracle；
- 已有覆盖用例 ID 和人工确认的覆盖等级。

## Required behavior

| Fixture | Existing coverage | Expected generator behavior |
|---|---|---|
| Same Bug already imported, same signature | Strong | 不重复导入；新需求相关时只引用 Pattern，不加用例 |
| Pattern covered by an existing test with correct trigger + oracle | Strong | 0 new cases; retain trace link |
| Existing case mentions same page but misses trigger | Partial | Enhance existing case; no duplicate parallel case |
| Applicable pattern has no existing coverage | None | Add the minimum case/assertion that detects it |
| Pattern belongs to unrelated module/platform | N/A | Skip and report reason |
| Pattern root cause/evidence unclear | Unknown | Do not infer root cause; keep pending confirmation |
| Multiple Bugs map to one pattern and one oracle | Strong | One pattern / one coverage mapping; no N-times cases |
| One action path validates multiple patterns with independent assertions | Gap/partial | Merge into existing case if still independently diagnosable |

## Metrics

Do not use case-count growth as the success metric. Track:
1. Historical pattern retrieval precision: relevant patterns retrieved / all retrieved.
2. Strong-coverage decision precision: patterns marked strong that genuinely have matching trigger and oracle.
3. Duplicate case rate: new cases duplicating existing behavior/oracle.
4. Missed applicable patterns: relevant historical patterns not considered.
5. Genuine gap yield: added cases that close a verified gap.
6. Case enhancement yield: existing cases strengthened without parallel duplication.
7. Execution cost delta: added execution time attributable to net-new cases only.
8. Defect rediscovery: whether generated cases catch a seeded/replayed historical failure.

## Acceptance rule

The enhanced generator is better when it catches more seeded historical failure modes at equal or lower test-execution cost, with no regression in base functional coverage and no schema incompatibility. A run that adds zero test cases but improves traceability or correctly identifies strong coverage is a valid result.
