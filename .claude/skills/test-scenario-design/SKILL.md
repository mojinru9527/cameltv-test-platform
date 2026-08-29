---
name: test-scenario-design
description: Use when generating or reviewing AITDE test scenarios from a frozen contract — "生成场景", "场景设计", "scenario", "scenario design". Produces TestScenario + Oracle candidates bound to a FROZEN contract version.
---

# AITDE 场景设计（Test Scenario Design）

## 目标
把一份 FROZEN Contract 展开为 **TestScenario + Oracle**（建模，不执行）。

## 前置
- Contract version = **FROZEN**（否则 `409 CONTRACT_NOT_FROZEN`）。

## 强制输出契约（每个 Scenario）
```json
{
  "scenario_key": "MEMBER-RENEW-001",
  "title": "readable",
  "business_goal": "goal",
  "priority": "P0|P1|P2|P3",
  "risk_level": "P0|P1|P2|P3",
  "given": {...}, "when": {...}, "expected_state": {...},
  "source_refs": [{"artifact_id": 1, "fragment_id": 2}],
  "oracles": [
    {
      "oracle_key": "membership-active",
      "oracle_type": "UI|API|DB|EVENT|LOG|CONTRACT|VISUAL|PERFORMANCE",
      "target": {...}, "operator": "eq", "expected_value": {...},
      "source_type": "AI_INFERRED|REQUIREMENT_EXPLICIT|TESTER_APPROVED",
      "source_refs": [{"artifact_id": 1, "fragment_id": 3}],
      "required": true, "confidence": 0.7
    }
  ]
}
```

## 去重
`scenario_key` + `given + when + expected` 内容 hash 相同 → 视为重复，不重复生成。

## Oracle Guard
- `source_type == AI_INFERRED` 的 Oracle 在 Tester 批准前不能成为 `required` 且 `review_status=APPROVED`。
- Oracle 的 `source_type` 与最终评审权在 Tester。

## 关键纪律
- 只从 FROZEN rule 派生 Scenario，不超出契约。
- 生成后由 Tester Review（approve/reject/request_change），再进入 Executor。
