---
name: test-failure-triage
description: 用于 AITDE V3.8 Failure Triage（V38-001/002/003）。Use when triaging a failed run into a hypothesis, reviewing/confirming an AI failure hypothesis, or when the AI must not mutate the formal Outcome. Triggers: "失败归因", "failure triage", "triage hypothesis", "归因分类".
---

# 失败归因（Failure Triage）
> AITDE V3.8 V38-001..003。AI **只产 hypothesis**，绝不修改正式 Outcome。

## 硬不变量

- `outcome` 由确定性 Runtime 判定，AI **只读**，绝不改写。
- 只写 `failure_hypotheses` 行；**绝不**回写 `execution_runs.outcome`。
- secret / PII 不入模型（`FailureEvidencePackBuilder` 负责脱敏）。
- 输出 `classification` 仅限：BUSINESS_LOGIC / AUTOMATION_ISSUE / DATA_ISSUE / ENV_ISSUE / FLAKY / UNKNOWN。

## 流程

1. `POST /api/v2/runs/{id}/triage` → 生成 hypothesis（status=GENERATED，不改 outcome）。
2. `GET /api/v2/runs/{id}/hypotheses` → 查看已生成 hypothesis。
3. `POST /api/v2/hypotheses/{id}/review`（REVIEWED/CONFIRMED/REJECTED）→ 人工确认，写审计。

## 提交前自检

- [ ] 未改动 `outcome`。
- [ ] 未把 BUSINESS_FAIL 误判为 flaky/pass。
- [ ] reviewer 与 reason 记录在案。
