# Batch 300 — Design / Dev

## 接口

```python
FailureTriageAgent(llm).triage(failure_context: dict) -> {
  "execution_outcome": "FAIL|INCOMPLETE|ERROR|UNKNOWN",
  "attribution_status": "NEEDS_EXPERIMENT|UNKNOWN",
  "hypotheses": [{classification, summary, supporting_evidence,
                  contradicting_evidence, missing_evidence,
                  confidence: null, status: "PROPOSED"}],
  "human_review_required": true,
  "auto_close_defect": false,
}
```

## 12 类归因

PRODUCT_DEFECT / CROSS_FEATURE_DEFECT / ENVIRONMENT / TEST_DATA / CONCURRENCY /
THIRD_PARTY / NETWORK / TIME / AUTOMATION / REQUIREMENT_GAP / FLAKY / UNKNOWN

## 决策

| ID | 决策 | 理由 |
|----|------|------|
| D-300-1 | `confidence: None` 类型强约束 | 直接拒绝模型填百分比 |
| D-300-2 | auto_close 字段存在但必须 false | 显式记录“AI 无关闭权”，越权即报错 |
| D-300-3 | UNKNOWN 与 attribution_status 双向校验 | 防止“证据不足却给 NEEDS_EXPERIMENT” |
| D-300-4 | CROSS_FEATURE 必须带证据 | 对齐 §11.8 用户路径失败要求 |
| D-300-5 | 100 样本用合成标注跑 | 可重复、无网络依赖；真实 §21.4 集后续接入 |

## 文件

- `app/aiqe/agents/failure_triage_agent.py`
- `tests/test_aiqe_failure_triage_agent.py`（8 条，含 100 样本）
