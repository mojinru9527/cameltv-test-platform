"""Batch 207 — AI intelligence provider reality tests.

Covers the synchronous LLM client (error classification), the real AI
provider (prompt → validated output schema), the honest deterministic
baseline, and the build_intelligence_provider factory gating.
"""
from __future__ import annotations

import json
from types import SimpleNamespace

import httpx
import pytest

from app.core import config
from app.modules.aitde.intelligence import llm_sync
from app.services import ai_client
from app.modules.aitde.intelligence.provider import (
    AiIntelligenceProvider,
    ContractContext,
    DeterministicScopeProvider,
    ScenarioContext,
    ScopeContext,
    ScopeIntentContext,
    build_intelligence_provider,
)
from app.modules.aitde.intelligence.llm_sync import (
    IntelligenceLLMError,
    IntelligenceLLMResponseError,
    call_llm_json,
)
from app.services.ai_config_service import (
    AIProviderUnconfiguredError,
    ai_config_service as _ai_cfg_svc,
)

_CFG = SimpleNamespace(model="test-model", api_base_url="https://ai.test", api_key="k")


class _FakeResponse:
    def __init__(self, content: str, status_code: int = 200):
        self._content = content
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise httpx.HTTPStatusError(
                "err", request=httpx.Request("POST", "https://ai.test"), response=self
            )

    def json(self):
        return {"choices": [{"message": {"content": self._content}}]}


@pytest.fixture(autouse=True)
def _ai_on(monkeypatch):
    monkeypatch.setattr(config.settings, "ai_enabled", True)
    monkeypatch.setattr(config.settings, "ai_retry_attempts", 2)
    monkeypatch.setattr(config.settings, "ai_timeout_seconds", 5.0)
    monkeypatch.setattr(_ai_cfg_svc, "resolve", lambda db, pid: _CFG)


def _fake_client(responses: dict):
    """Return a provider client that replies per prompt keyword."""
    calls: list[dict] = []

    def _client(*, db, project_id, system_prompt, user_payload, max_tokens=4096):
        calls.append({"prompt": system_prompt, "payload": user_payload})
        for keyword, payload in responses.items():
            if keyword in system_prompt:
                return json.loads(json.dumps(payload))
        raise AssertionError(f"unexpected prompt: {system_prompt[:60]}")

    _client.calls = calls  # type: ignore[attr-defined]
    return _client


def test_call_llm_json_retries_transient_then_succeeds(monkeypatch):
    ok = _FakeResponse(json.dumps({"ok": True}))
    calls = {"n": 0}

    def _flaky_post(*a, **k):
        calls["n"] += 1
        if calls["n"] == 1:
            raise httpx.TimeoutException("slow")
        return ok

    monkeypatch.setattr(ai_client.httpx, "post", _flaky_post)
    result = call_llm_json(
        db=None, project_id=1, system_prompt="s", user_payload={"a": 1}
    )
    assert result == {"ok": True}


def test_call_llm_json_invalid_json_raises_response_error(monkeypatch):
    monkeypatch.setattr(
        ai_client.httpx, "post", lambda *a, **k: _FakeResponse("not-json")
    )
    with pytest.raises(IntelligenceLLMResponseError):
        call_llm_json(db=None, project_id=1, system_prompt="s", user_payload={})


def test_call_llm_json_http_4xx_raises_llm_error(monkeypatch):
    monkeypatch.setattr(
        ai_client.httpx,
        "post",
        lambda *a, **k: _FakeResponse("{}", status_code=400),
    )
    with pytest.raises(IntelligenceLLMError):
        call_llm_json(db=None, project_id=1, system_prompt="s", user_payload={})


_SCOPE_ITEM = {
    "scope_key": "scope-1-1",
    "scope_type": "BUSINESS_FLOW",
    "name": "会员续费",
    "decision": "INCLUDE",
    "test_depth": "FULL",
    "risk_level": "P2",
    "reason": "续费后恢复权益",
    "confidence": 0.9,
    "source_refs": [{"artifact_id": 1, "fragment_id": 2}],
}


def test_ai_provider_analyze_scope_validates_output():
    client = _fake_client({"test scoping analyst": {"items": [_SCOPE_ITEM]}})
    prov = AiIntelligenceProvider(db=None, project_id=1, client=client)
    out = prov.analyze_scope(
        ScopeContext(mission_id=7, fragments=[(1, 2, "标题", "正文")])
    )
    assert out.mission_id == 7
    assert out.items[0].scope_key == "scope-1-1"
    assert client.calls[0]["payload"]["fragments"][0]["artifact_id"] == 1


def test_ai_provider_detect_ambiguities_and_intents():
    client = _fake_client(
        {
            "ambiguity and intent analyst": {
                "ambiguities": [
                    {
                        "ambiguity_key": "amb-1",
                        "title": "问题?",
                        "description": "d",
                        "severity": "P1",
                        "candidate_options": [
                            {"key": "a", "label": "纳入"},
                            {"key": "b", "label": "排除"},
                        ],
                        "confidence": 0.6,
                        "source_refs": [{"artifact_id": 1, "fragment_id": 2}],
                    }
                ],
                "intents": [
                    {
                        "intent_key": "intent-1",
                        "title": "t",
                        "business_goal": "g",
                        "required_outcomes": ["o"],
                        "risk_level": "P2",
                        "source_refs": [{"artifact_id": 1, "fragment_id": 2}],
                    }
                ],
            }
        },
    )
    prov = AiIntelligenceProvider(db=None, project_id=1, client=client)
    ctx = ScopeIntentContext(mission_id=7, scope_items=[_SCOPE_ITEM])
    amb = prov.detect_ambiguities(ctx)
    intent = prov.design_intents(ctx)
    assert amb.items[0].ambiguity_key == "amb-1"
    assert intent.items[0].intent_key == "intent-1"


def test_ai_provider_contract_and_scenarios_force_ai_inferred_not_required():
    scenario_item = {
        "scenario_key": "S-1",
        "title": "续费成功",
        "business_goal": "g",
        "priority": "P2",
        "risk_level": "P2",
        "given": {"membership": "expired"},
        "when": {"action": "renew"},
        "expected_state": {"membership": "active"},
        "source_refs": [{"artifact_id": 1, "fragment_id": 2}],
        "oracles": [
            {
                "oracle_key": "o1",
                "oracle_type": "DB",
                "target": {"entity": "membership"},
                "operator": "eq",
                "expected_value": {"status": "active"},
                "source_type": "AI_INFERRED",
                "source_refs": [{"artifact_id": 1, "fragment_id": 3}],
                "required": True,
                "confidence": 0.7,
            }
        ],
    }
    client = _fake_client(
        {
            "test contract builder": {
                "scope_revision": "h",
                "rules": [
                    {
                        "rule_key": "r1",
                        "title": "规则",
                        "kind": "BUSINESS_RULE",
                        "statement": "必须成立",
                        "risk_level": "P2",
                        "source_type": "REQUIREMENT_EXPLICIT",
                        "source_refs": [{"artifact_id": 1, "fragment_id": 2}],
                    }
                ],
                "required_outcomes": [],
            },
            "test scenario designer": {"items": [scenario_item]},
        },
    )
    prov = AiIntelligenceProvider(db=None, project_id=1, client=client)
    snapshot = prov.build_contract(
        ContractContext(mission_id=7, scope_items=[_SCOPE_ITEM], intents=[])
    )
    assert snapshot.rules[0].rule_key == "r1"
    out = prov.design_scenarios(
        ScenarioContext(mission_id=7, contract_version_id=5, rules=[], outcomes=[])
    )
    assert out.items[0].oracles[0].required is False


def test_deterministic_baseline_is_honest():
    prov = DeterministicScopeProvider()
    assert prov.mode == "deterministic"
    scope_out = prov.analyze_scope(
        ScopeContext(mission_id=7, fragments=[(1, 2, "标题", "正文内容")])
    )
    assert scope_out.items[0].confidence == pytest.approx(0.95)
    ctx = ScopeIntentContext(
        mission_id=7,
        scope_items=[
            dict(_SCOPE_ITEM, ai_confidence=0.95),
            dict(_SCOPE_ITEM, scope_key="scope-1-2", decision="EXCLUDE", ai_confidence=0.95),
            dict(_SCOPE_ITEM, scope_key="scope-1-3", ai_confidence=0.2),
        ],
    )
    amb = prov.detect_ambiguities(ctx)
    # only EXCLUDE / low-confidence items become ambiguities now
    keys = {a.ambiguity_key for a in amb.items}
    assert "amb-scope-1-1" not in keys
    assert "amb-scope-1-2" in keys
    assert "amb-scope-1-3" in keys
    scen = prov.design_scenarios(
        ScenarioContext(
            mission_id=7,
            contract_version_id=1,
            rules=[{"rule_key": "r1", "title": "t", "statement": "s", "risk_level": "P2"}],
            outcomes=[],
        )
    )
    oracle = scen.items[0].oracles[0]
    assert oracle.source_type == "RULE_BASELINE"
    assert oracle.required is False


def test_factory_gating(monkeypatch):
    monkeypatch.setattr(_ai_cfg_svc, "resolve", lambda db, pid: _CFG)
    assert isinstance(build_intelligence_provider(None, 1), AiIntelligenceProvider)

    def _raise_unconfigured(db, pid):
        raise AIProviderUnconfiguredError("nope")

    monkeypatch.setattr(_ai_cfg_svc, "resolve", _raise_unconfigured)
    assert isinstance(
        build_intelligence_provider(None, 1), DeterministicScopeProvider
    )

    monkeypatch.setattr(config.settings, "ai_enabled", False)
    assert isinstance(
        build_intelligence_provider(None, 1), DeterministicScopeProvider
    )


def test_missing_items_raises_response_error():
    client = _fake_client({"test scoping analyst": {"mission_id": 1}})
    prov = AiIntelligenceProvider(db=None, project_id=1, client=client)
    with pytest.raises(IntelligenceLLMResponseError):
        prov.analyze_scope(ScopeContext(mission_id=1, fragments=[]))


def test_empty_contract_rules_raise_response_error():
    client = _fake_client(
        {
            "test contract builder": {
                "scope_revision": "h",
                "rules": [],
                "required_outcomes": [],
            }
        }
    )
    prov = AiIntelligenceProvider(db=None, project_id=1, client=client)

    with pytest.raises(IntelligenceLLMResponseError, match="at least one rule"):
        prov.build_contract(
            ContractContext(mission_id=7, scope_items=[_SCOPE_ITEM], intents=[])
        )


def test_empty_scenario_items_raise_response_error():
    client = _fake_client({"test scenario designer": {"items": []}})
    prov = AiIntelligenceProvider(db=None, project_id=1, client=client)

    with pytest.raises(IntelligenceLLMResponseError, match="at least one item"):
        prov.design_scenarios(
            ScenarioContext(
                mission_id=7,
                contract_version_id=5,
                rules=[
                    {
                        "rule_key": "r1",
                        "title": "规则",
                        "statement": "必须成立",
                        "risk_level": "P2",
                    }
                ],
                outcomes=[],
            )
        )


def test_factory_disabled_when_settings_off(monkeypatch):
    monkeypatch.setattr(config.settings, "ai_enabled", False)
    assert isinstance(build_intelligence_provider(None, 1), DeterministicScopeProvider)
