"""AITDE V3.8 healing policy / approved-healing-apply guard tests.

V38-004 HealingPolicy (action-only), V38-005 ApprovedHealingApply (new
CommandPlanVersion, old plan/evidence retained). Invariants: Oracle/Contract/
Expected mutation is rejected wholesale; only an APPROVED, action-only proposal
produces a new version and never rewrites history.
"""

from __future__ import annotations

from app.modules.aitde.ai_closed_loop import service
from app.modules.aitde.browser.models import HealingProposal
from app.modules.aitde.command.models import CommandPlan, CommandPlanVersion
from app.modules.aitde.common.enums import (
    CommandPlanStatus,
    HealingPolicyDecision,
    HealingProposalStatus,
)


def test_healing_policy_allows_action_only_diff():
    verdict = service.HealingPolicy.decide(
        {"locator": "#old", "wait": 1000},
        {"locator": "#new", "wait": 2000},
    )
    assert verdict["decision"] == HealingPolicyDecision.ALLOW.value
    assert verdict["allowed"] is True


def test_healing_policy_rejects_oracle_mutation():
    verdict = service.HealingPolicy.decide({"locator": "#a"}, {"expected": "PASS"})
    assert verdict["decision"] == HealingPolicyDecision.REJECT.value
    assert verdict["allowed"] is False


def _base(db, after, status=HealingProposalStatus.APPROVED.value):
    plan = CommandPlan(scenario_adapter_id=10, current_version_no=1)
    db.add(plan)
    db.flush()
    src = CommandPlanVersion(
        command_plan_id=plan.id,
        version_no=1,
        scenario_version_id=5,
        contract_version_id=0,
        schema_version="1.0",
        plan_json="{}",
        plan_hash="s1",
        status=CommandPlanStatus.ACTIVE.value,
        generated_by_type="AI",
    )
    db.add(src)
    db.flush()
    proposal = HealingProposal(
        scenario_adapter_id=10,
        command_plan_version_id=src.id,
        proposal_type="LOCATOR",
        before_json='{"locator": "#a"}',
        after_json=repr(after).replace("'", '"'),
        reason="heal locator",
        status=status,
        created_by_type="AI",
    )
    db.add(proposal)
    db.flush()
    return proposal


def test_apply_healing_creates_new_command_plan_version(db):
    proposal = _base(db, {"locator": "#b", "wait": 3000})
    result = service.ApprovedHealingApply.apply(db, proposal.id, 7, "fix")
    assert result["old_retained"] is True
    assert result["version_no"] == 2
    assert result["status"] == CommandPlanStatus.VALIDATED.value
    # old version retained; a new version exists
    versions = db.query(CommandPlanVersion).all()
    assert len(versions) == 2


def test_apply_healing_rejects_non_approved(db):
    proposal = _base(db, {"locator": "#b"}, status=HealingProposalStatus.OPEN.value)
    try:
        service.ApprovedHealingApply.apply(db, proposal.id, 7)
        assert False, "non-APPROVED proposal must not apply"
    except ValueError:
        pass


def test_apply_healing_rejects_oracle_tainted(db):
    # Even an APPROVED proposal must not apply if it mutates an expected value.
    proposal = _base(db, {"expected": "PASS"})
    try:
        service.ApprovedHealingApply.apply(db, proposal.id, 7)
        assert False, "oracle-tainted proposal must not apply"
    except ValueError:
        pass
