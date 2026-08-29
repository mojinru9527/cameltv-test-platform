"""One-shot generator for tests/fixtures/aitde/v3 (V30-124 Golden AI Evaluation).

Run from backend/: `python scripts/gen_golden_fixtures.py` (not shipped logic,
just corpus authoring — keeps the JSON files reviewable in git).
"""
import json
import os

BASE = os.path.join("tests", "fixtures", "aitde", "v3")


def w(path, obj):
    full = os.path.join(BASE, path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w", encoding="utf-8", newline="\n") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
        f.write("\n")


def ref(a=1, fr=1, loc="PRD 1.1"):
    return {"artifact_id": a, "fragment_id": fr, "location": loc}


# ── Layer 1: 5 requirement classes (V30-124) ──
w("inputs/crud.json", {
    "category": "simple-crud",
    "fragments": [
        {"artifact_id": 1, "fragment_id": 1, "title": "PRD 2.1 会员管理",
         "text": "管理员可以创建、查询、更新、删除会员档案；会员编号全局唯一。"},
    ],
})
w("inputs/state_machine.json", {
    "category": "state-machine",
    "fragments": [
        {"artifact_id": 1, "fragment_id": 2, "title": "PRD 3.2 订单状态",
         "text": "订单状态机：PENDING → PAID → SHIPPED → COMPLETED；PAID 后可申请取消，取消必须先退款。"},
        {"artifact_id": 2, "fragment_id": 1, "title": "PRD 3.4 幂等",
         "text": "重复支付回调必须幂等，不允许状态回退。"},
    ],
})
w("inputs/payment_order.json", {
    "category": "payment-order-loop",
    "fragments": [
        {"artifact_id": 1, "fragment_id": 3, "title": "PRD 4.1 支付闭环",
         "text": "用户下单 → 支付成功 → 生成支付流水；退款金额不得超过实付金额，退款后订单关闭。"},
    ],
})
w("inputs/rbac.json", {
    "category": "rbac",
    "fragments": [
        {"artifact_id": 1, "fragment_id": 4, "title": "PRD 5.1 权限",
         "text": "仅 ADMIN 角色可分配权限；操作必须校验角色，未授权返回 403。"},
    ],
})
w("inputs/ambiguous.json", {
    "category": "ambiguous",
    "fragments": [
        {"artifact_id": 1, "fragment_id": 5, "title": "PRD 6.1 超时",
         "text": "接口超时后系统进行相应处理。"},
        {"artifact_id": 1, "fragment_id": 6, "title": "PRD 6.2 导出",
         "text": "导出失败时给予提示并允许重试。"},
    ],
})

# ── Layer 2: golden outputs ──
w("scope_crud.json", {
    "schema_version": "1.0", "mission_id": 1,
    "items": [{"scope_key": "member-crud", "scope_type": "FEATURE", "name": "会员档案 CRUD",
               "decision": "INCLUDE", "test_depth": "FULL", "risk_level": "P2",
               "reason": "创建/查询/更新/删除四类主路径", "confidence": 0.9,
               "source_refs": [ref()]}],
})
w("scope_rbac.json", {
    "schema_version": "1.0", "mission_id": 1,
    "items": [{"scope_key": "rbac-assign", "scope_type": "FEATURE", "name": "权限分配与校验",
               "decision": "INCLUDE", "test_depth": "FULL", "risk_level": "P1",
               "reason": "未授权访问是安全问题", "confidence": 0.95,
               "source_refs": [ref(1, 4, "PRD 5.1")]}],
})
w("scope_ambiguous.json", {
    "schema_version": "1.0", "mission_id": 1,
    "items": [{"scope_key": "export-retry", "scope_type": "BUSINESS_FLOW", "name": "导出与重试",
               "decision": "INCLUDE", "test_depth": "SMOKE", "risk_level": "P3",
               "reason": "失败提示与重试路径", "confidence": 0.7,
               "source_refs": [ref(1, 6, "PRD 6.2")]}],
})
w("ambiguity_state_machine.json", {
    "schema_version": "1.0", "mission_id": 1,
    "items": [{"ambiguity_key": "paid-cancel-precondition", "title": "PAID 后取消是否必须先退款",
               "description": "PRD 3.2 写明取消必须先退款，但未说明未付款订单取消路径",
               "severity": "P1",
               "candidate_options": [{"key": "refund-first", "label": "先退款后取消"},
                                     {"key": "cancel-direct", "label": "直接取消"}],
               "confidence": 0.8, "source_refs": [ref(1, 2, "PRD 3.2")]}],
})
w("ambiguity_ambiguous.json", {
    "schema_version": "1.0", "mission_id": 1,
    "items": [{"ambiguity_key": "api-timeout-behavior", "title": "超时后系统行为未定义",
               "description": "PRD 6.1 未定义「相应处理」：重试、降级还是报错",
               "severity": "P2",
               "candidate_options": [{"key": "retry-once", "label": "自动重试一次"},
                                     {"key": "fail-fast", "label": "直接失败并提示"}],
               "confidence": 0.85, "source_refs": [ref(1, 5, "PRD 6.1")]}],
})
w("intent_crud.json", {
    "schema_version": "1.0", "mission_id": 1,
    "items": [{"intent_key": "member-data-accuracy", "title": "会员档案数据准确",
               "business_goal": "会员资料全生命周期可维护且不错乱",
               "required_outcomes": ["创建后的会员可被精确查询", "更新不产生脏字段"],
               "risk_level": "P2", "source_refs": [ref()]}],
})
w("intent_payment_order.json", {
    "schema_version": "1.0", "mission_id": 1,
    "items": [{"intent_key": "refund-never-overpay", "title": "退款金额受限",
               "business_goal": "退款金额不得超过实付金额",
               "required_outcomes": ["超额退款被拒绝", "全额退款后订单关闭"],
               "risk_level": "P0", "source_refs": [ref(1, 3, "PRD 4.1")]}],
})
w("contract_payment_order.json", {
    "schema_version": "1.0", "mission_id": 1, "scope_revision": "r1",
    "rules": [
        {"rule_key": "refund-amount-cap", "title": "退款上限", "kind": "BUSINESS_RULE",
         "statement": "退款金额 <= 实付金额", "risk_level": "P0",
         "source_type": "REQUIREMENT_EXPLICIT", "source_refs": [ref(1, 3, "PRD 4.1")]},
        {"rule_key": "idempotent-callback", "title": "回调幂等", "kind": "BUSINESS_RULE",
         "statement": "重复支付回调不改变状态", "risk_level": "P1",
         "source_type": "REQUIREMENT_EXPLICIT", "source_refs": [ref(2, 1, "PRD 3.4")]},
    ],
    "required_outcomes": [
        {"outcome_key": "order-closed-after-full-refund", "statement": "全额退款后订单关闭",
         "source_type": "TESTER_APPROVED", "source_refs": [ref(1, 3, "PRD 4.1")]},
    ],
})
w("contract_rbac.json", {
    "schema_version": "1.0", "mission_id": 1, "scope_revision": "r1",
    "rules": [
        {"rule_key": "rbac-admin-only-assign", "title": "仅 ADMIN 可分配权限",
         "kind": "BUSINESS_RULE", "statement": "非 ADMIN 调用分配接口必须 403",
         "risk_level": "P1", "source_type": "REQUIREMENT_EXPLICIT",
         "source_refs": [ref(1, 4, "PRD 5.1")]},
    ],
    "required_outcomes": [],
})
w("scenario_state_machine.json", {
    "schema_version": "1.0", "contract_version_id": 1, "mission_id": 1,
    "items": [
        {"scenario_key": "order-cancel-after-refund", "title": "PAID 订单先退款再取消",
         "business_goal": "状态机不被非法迁移破坏", "priority": "P1", "risk_level": "P1",
         "given": {"order.status": "PAID"}, "when": {"action": "cancel_with_refund"},
         "expected_state": {"order.status": "CANCELLED"},
         "source_refs": [ref(1, 2, "PRD 3.2")],
         "oracles": [{"oracle_key": "order-status-cancelled", "oracle_type": "API",
                      "target": {"path": "order.status"}, "operator": "eq",
                      "expected_value": {"value": "CANCELLED"},
                      "source_type": "AI_INFERRED", "required": False,
                      "confidence": 0.9, "source_refs": [ref(1, 2, "PRD 3.2")]}]},
        {"scenario_key": "order-status-never-regress", "title": "重复回调不回退状态",
         "business_goal": "幂等", "priority": "P1", "risk_level": "P1",
         "given": {"order.status": "SHIPPED"}, "when": {"action": "duplicate_paid_callback"},
         "expected_state": {"order.status": "SHIPPED"}, "source_refs": [ref(2, 1, "PRD 3.4")],
         "oracles": []},
    ],
})
w("scenario_crud.json", {
    "schema_version": "1.0", "contract_version_id": 1, "mission_id": 1,
    "items": [
        {"scenario_key": "member-create-then-query", "title": "创建会员后可查询",
         "business_goal": "CRUD 主路径", "priority": "P2", "risk_level": "P2",
         "given": {"member": "absent"}, "when": {"action": "create_member"},
         "expected_state": {"member.queryable": True}, "source_refs": [ref()],
         "oracles": []},
    ],
})

# ── Layer 3: negative fixtures (shared corpus with V30-123) ──
with open(os.path.join(BASE, "invalid", "malformed_json.json"), "w", encoding="utf-8") as f:
    f.write('{"schema_version": "1.0", "mission_id": 1, "items": [}')
w("invalid/missing_source_ref.json", {
    "schema_version": "1.0", "mission_id": 1,
    "items": [{"scope_key": "no-ref", "scope_type": "FEATURE", "name": "无来源",
               "decision": "INCLUDE", "test_depth": "FULL", "risk_level": "P2",
               "reason": "缺 source_refs", "confidence": 0.5, "source_refs": []}],
})
w("invalid/bad_enum.json", {
    "schema_version": "1.0", "mission_id": 1,
    "items": [{"scope_key": "magic", "scope_type": "MAGIC", "name": "非法枚举",
               "decision": "INCLUDE", "test_depth": "FULL", "risk_level": "P2",
               "reason": "scope_type 非法", "confidence": 0.5,
               "source_refs": [ref()]}],
})
w("invalid/fake_fragment_id.json", {
    "schema_version": "1.0", "mission_id": 1,
    "items": [{"scope_key": "ghost", "scope_type": "FEATURE", "name": "幽灵来源",
               "decision": "INCLUDE", "test_depth": "FULL", "risk_level": "P2",
               "reason": "artifact 不存在（非占位）", "confidence": 0.5,
               "source_refs": [ref(99999, 1, "PRD ?")]}],
})
w("invalid/confidence_range.json", {
    "schema_version": "1.0", "mission_id": 1,
    "items": [{"scope_key": "over-confident", "scope_type": "FEATURE", "name": "越界置信度",
               "decision": "INCLUDE", "test_depth": "FULL", "risk_level": "P2",
               "reason": "confidence > 1", "confidence": 1.5,
               "source_refs": [ref()]}],
})
w("invalid/oracle_required.json", {
    "schema_version": "1.0", "contract_version_id": 1, "mission_id": 1,
    "items": [
        {"scenario_key": "required-ai-oracle", "title": "AI_INFERRED 却 required",
         "business_goal": "违反 Oracle Guard", "priority": "P1", "risk_level": "P1",
         "given": {}, "when": {}, "expected_state": {},
         "source_refs": [ref()],
         "oracles": [{"oracle_key": "bad-required", "oracle_type": "API",
                      "target": {}, "operator": "eq", "expected_value": {},
                      "source_type": "AI_INFERRED", "required": True,
                      "confidence": 0.9, "source_refs": [ref()]}]},
    ],
})

# ── Layer 4: manifest ──
w("manifest.json", {
    "schema_version": "1.0",
    "doc": "V30-124 Golden AI Evaluation — 人工 Golden 期望 + AI 输出 Schema 语料",
    "requirement_classes": ["simple-crud", "state-machine", "payment-order-loop",
                            "rbac", "ambiguous"],
    "valid": [
        {"file": "scope_crud.json", "schema": "ScopeAnalysisOutput", "input": "inputs/crud.json",
         "golden": {"expected_scope_keys": ["member-crud"]}},
        {"file": "scope_rbac.json", "schema": "ScopeAnalysisOutput", "input": "inputs/rbac.json",
         "golden": {"expected_scope_keys": ["rbac-assign"]}},
        {"file": "scope_ambiguous.json", "schema": "ScopeAnalysisOutput",
         "input": "inputs/ambiguous.json",
         "golden": {"expected_scope_keys": ["export-retry"]}},
        {"file": "ambiguity_state_machine.json", "schema": "AmbiguityDetectionOutput",
         "input": "inputs/state_machine.json",
         "golden": {"expected_ambiguity_keys": ["paid-cancel-precondition"],
                    "min_candidate_options": 2}},
        {"file": "ambiguity_ambiguous.json", "schema": "AmbiguityDetectionOutput",
         "input": "inputs/ambiguous.json",
         "golden": {"expected_ambiguity_keys": ["api-timeout-behavior"],
                    "min_candidate_options": 2}},
        {"file": "intent_crud.json", "schema": "IntentDetectionOutput",
         "input": "inputs/crud.json",
         "golden": {"expected_intent_keys": ["member-data-accuracy"],
                    "required_outcomes_nonempty": True}},
        {"file": "intent_payment_order.json", "schema": "IntentDetectionOutput",
         "input": "inputs/payment_order.json",
         "golden": {"expected_intent_keys": ["refund-never-overpay"],
                    "required_outcomes_nonempty": True}},
        {"file": "contract_payment_order.json", "schema": "ContractSnapshot",
         "input": "inputs/payment_order.json",
         "golden": {"required_rule_keys": ["refund-amount-cap", "idempotent-callback"]}},
        {"file": "contract_rbac.json", "schema": "ContractSnapshot", "input": "inputs/rbac.json",
         "golden": {"required_rule_keys": ["rbac-admin-only-assign"]}},
        {"file": "scenario_state_machine.json", "schema": "ScenarioDesignOutput",
         "input": "inputs/state_machine.json",
         "golden": {"must_have_scenarios": ["order-cancel-after-refund",
                                            "order-status-never-regress"],
                    "ai_inferred_oracles_must_not_be_required": True}},
        {"file": "scenario_crud.json", "schema": "ScenarioDesignOutput",
         "input": "inputs/crud.json",
         "golden": {"must_have_scenarios": ["member-create-then-query"],
                    "ai_inferred_oracles_must_not_be_required": True}},
    ],
    "invalid": [
        {"file": "invalid/malformed_json.json", "schema": "ScopeAnalysisOutput",
         "reason": "malformed json"},
        {"file": "invalid/missing_source_ref.json", "schema": "ScopeAnalysisOutput",
         "reason": "source_refs min_length=1"},
        {"file": "invalid/bad_enum.json", "schema": "ScopeAnalysisOutput",
         "reason": "scope_type closed enum"},
        {"file": "invalid/confidence_range.json", "schema": "ScopeAnalysisOutput",
         "reason": "confidence 0..1"},
        {"file": "invalid/fake_fragment_id.json", "schema": "ScopeAnalysisOutput",
         "guard": "source_ref",
         "reason": "artifact_id>0 must exist (validate_source_refs)"},
        {"file": "invalid/oracle_required.json", "schema": "ScenarioDesignOutput",
         "guard": "oracle_guard",
         "reason": "AI_INFERRED oracle required=True violates Oracle Guard (repo layer)"},
    ],
})
print("golden fixture corpus generated")
