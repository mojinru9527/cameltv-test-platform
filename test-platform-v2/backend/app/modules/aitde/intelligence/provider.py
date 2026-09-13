"""IntelligenceProvider abstraction (V30-033/V30-034, Batch 207).

Business services depend on this protocol, never on a concrete LLM SDK. Two
concrete providers exist:

- ``DeterministicScopeProvider`` — pure rule baseline used when AI is not
  configured (or the configured model is unavailable). Outputs are honest:
  provenance is ``DETERMINISTIC``, oracles are ``RULE_BASELINE`` and never
  required at generation time.
- ``AiIntelligenceProvider`` — real, synchronous LLM-backed implementation.
  Each method renders one prompt from ``intelligence/prompts/`` and validates
  the model JSON into the strict Pydantic output schema. A configured model
  that returns an unusable shape raises ``IntelligenceLLMResponseError``
  (never silently falls back to the deterministic baseline — the service layer
  decides degradation and records it honestly).

``build_intelligence_provider(db, project_id)`` resolves the project's AI
config: configured -> AI provider; unconfigured/disabled -> deterministic.
"""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Protocol

from sqlalchemy.orm import Session

from app.modules.aitde.common.enums import (
    OracleType,
    RiskLevel,
    ScopeDecision,
    ScopeType,
    TestDepth,
)
from app.modules.aitde.contract.schemas import (
    ContractOutcome,
    ContractRule,
    ContractSnapshot,
)
from app.modules.aitde.scenario.schemas import (
    OracleCandidate,
    ScenarioCandidate,
    ScenarioDesignOutput,
)
from app.modules.aitde.scope.ambiguity_schemas import (
    AmbiguityCandidate,
    AmbiguityDetectionOutput,
    IntentCandidate,
    IntentDetectionOutput,
    Option,
)
from app.modules.aitde.scope.schemas import (
    ScopeAnalysisCandidate,
    ScopeAnalysisOutput,
    SourceRef,
)

_PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"
_CACHE_PREFIX_VERSION = "cache-v1"
_SOURCE_TYPE_AI_INFERRED = "AI_INFERRED"
_SOURCE_TYPE_RULE_BASELINE = "RULE_BASELINE"


def _source_refs(item: dict) -> list[SourceRef]:
    """Validate and preserve persisted provenance; deterministic output may not invent it."""
    return [SourceRef.model_validate(ref) for ref in item.get("source_refs") or []]


def _load_prompt(name: str) -> str:
    """Read the shared stable prefix before the operation-specific prompt."""
    common = (_PROMPTS_DIR / f"{_CACHE_PREFIX_VERSION}.txt").read_text(
        encoding="utf-8"
    )
    task = (_PROMPTS_DIR / f"{name}.txt").read_text(encoding="utf-8")
    return f"{common}\n\n--- OPERATION-SPECIFIC CONTRACT ---\n\n{task}"


@dataclass
class ScopeContext:
    mission_id: int
    fragments: list[tuple[int, int, str, str]]  # (artifact, fragment, title, text)


@dataclass
class ParsedFragment:
    artifact_id: int
    fragment_id: int
    title: str
    text: str


@dataclass
class ScopeIntentContext:
    mission_id: int
    scope_items: list[dict]  # {scope_key,name,decision,risk_level,ai_confidence,reason,review_status}


@dataclass
class ContractContext:
    mission_id: int
    scope_items: list[dict]  # approved INCLUDE scope items
    intents: list[dict]  # approved intents


@dataclass
class ScenarioContext:
    mission_id: int
    contract_version_id: int
    rules: list[dict]  # frozen contract rules ({rule_key,title,statement,risk_level})
    outcomes: list[dict]  # required outcomes


class IntelligenceProvider(Protocol):
    mode: str
    created_by_type: str

    def analyze_scope(self, context: ScopeContext) -> ScopeAnalysisOutput: ...

    def detect_ambiguities(
        self, context: ScopeIntentContext
    ) -> AmbiguityDetectionOutput: ...

    def design_intents(self, context: ScopeIntentContext) -> IntentDetectionOutput: ...

    def build_contract(self, context: ContractContext) -> ContractSnapshot: ...

    def design_scenarios(self, context: ScenarioContext) -> ScenarioDesignOutput: ...


class DeterministicScopeProvider:
    """Rule-based baseline (no external AI). Provenance is DETERMINISTIC."""

    mode = "deterministic"
    created_by_type = "DETERMINISTIC"

    def analyze_scope(self, context: ScopeContext) -> ScopeAnalysisOutput:
        items = []
        for i, (artifact_id, fragment_id, title, text) in enumerate(context.fragments):
            items.append(
                {
                    "scope_key": f"scope-{artifact_id}-{fragment_id}",
                    "scope_type": ScopeType.BUSINESS_FLOW.value,
                    "name": (title or text[:30] or f"片段 {i + 1}")[:255],
                    "decision": ScopeDecision.INCLUDE.value,
                    "test_depth": TestDepth.FULL.value,
                    "risk_level": RiskLevel.P2.value,
                    "reason": text[:200],
                    # Batch 207: a rule baseline is confident for a parsed
                    # fragment; low confidence is the exception, not the rule.
                    "confidence": 0.95,
                    "source_refs": [
                        SourceRef(artifact_id=artifact_id, fragment_id=fragment_id)
                    ],
                }
            )
        return ScopeAnalysisOutput(
            schema_version="1.0",
            mission_id=context.mission_id,
            items=[ScopeAnalysisCandidate.model_validate(x) for x in items],
        )

    def detect_ambiguities(
        self, context: ScopeIntentContext
    ) -> AmbiguityDetectionOutput:
        items = []
        for si in context.scope_items:
            # Batch 207: only genuine rule signals create an ambiguity — an
            # EXCLUDE decision, a genuinely low-confidence include, or a missing
            # reason. Confident INCLUDE items are NOT ambiguous (previously every
            # item was flagged because deterministic confidence 0.80 < 0.85).
            confidence = float(si.get("ai_confidence", 1.0) or 1.0)
            reason = str(si.get("reason") or "")
            is_uncertain = (
                si.get("decision") == "EXCLUDE"
                or confidence < 0.5
                or not reason.strip()
            )
            if not is_uncertain:
                continue
            items.append(
                AmbiguityCandidate(
                    ambiguity_key=f"amb-{si['scope_key']}",
                    title=f"{si.get('name', si['scope_key'])} 是否纳入测试范围?",
                    description=reason,
                    severity=RiskLevel(si.get("risk_level", "P2")),
                    candidate_options=[
                        Option(key="allow", label="纳入"),
                        Option(key="deny", label="排除"),
                        Option(key="out", label="本版本不测"),
                    ],
                    confidence=confidence,
                    source_refs=_source_refs(si),
                )
            )
        return AmbiguityDetectionOutput(
            schema_version="1.0", mission_id=context.mission_id, items=items
        )

    def design_intents(self, context: ScopeIntentContext) -> IntentDetectionOutput:
        items = []
        for si in context.scope_items:
            if si.get("decision") == "INCLUDE":
                items.append(
                    IntentCandidate(
                        intent_key=f"intent-{si['scope_key']}",
                        title=si.get("name", si["scope_key"]),
                        business_goal=si.get("reason", ""),
                        required_outcomes=[
                            f"{si.get('name', si['scope_key'])} 正确执行"
                        ],
                        risk_level=RiskLevel(si.get("risk_level", "P2")),
                        source_refs=_source_refs(si),
                    )
                )
        return IntentDetectionOutput(
            schema_version="1.0", mission_id=context.mission_id, items=items
        )

    def build_contract(self, context: ContractContext) -> ContractSnapshot:
        rules = [
            ContractRule(
                rule_key=f"rule-{si['scope_key']}",
                title=si.get("name", si["scope_key"]),
                kind="BUSINESS_RULE",
                statement=si.get("reason", ""),
                risk_level=RiskLevel(si.get("risk_level", "P2")),
                source_type=_SOURCE_TYPE_RULE_BASELINE,
                source_refs=_source_refs(si),
            )
            for si in context.scope_items
        ]
        outcomes = [
            ContractOutcome(
                outcome_key=f"outcome-{it['intent_key']}",
                statement=it.get("business_goal", ""),
                source_type=_SOURCE_TYPE_RULE_BASELINE,
                source_refs=_source_refs(it),
            )
            for it in context.intents
        ]
        return ContractSnapshot(
            schema_version="1.0",
            mission_id=context.mission_id,
            scope_revision=f"scope-hash-{len(context.scope_items)}",
            rules=rules,
            required_outcomes=outcomes,
        )

    def design_scenarios(self, context: ScenarioContext) -> ScenarioDesignOutput:
        items = []
        for i, rule in enumerate(context.rules):
            # Batch 207: a deterministic baseline oracle is a *proposal*, never a
            # required trusted oracle; it is not labelled AI_INFERRED.
            oracle = OracleCandidate(
                oracle_key=f"oracle-{rule['rule_key']}",
                oracle_type=OracleType.DB,
                target={"rule": rule.get("rule_key", "")},
                operator="eq",
                expected_value={"ok": True},
                source_type=_SOURCE_TYPE_RULE_BASELINE,
                source_refs=_source_refs(rule),
                required=False,
                confidence=0.7,
            )
            items.append(
                ScenarioCandidate(
                    scenario_key=f"{rule['rule_key']}-SCEN-{i + 1:03d}",
                    title=rule.get("title", rule["rule_key"]),
                    business_goal=rule.get("statement", ""),
                    case_type="FUNCTIONAL",
                    requirement_role="CHANGED",
                    module_key=rule.get("title", rule["rule_key"]),
                    priority=RiskLevel(rule.get("risk_level", "P2")),
                    risk_level=RiskLevel(rule.get("risk_level", "P2")),
                    given={"state": "precondition"},
                    when={"action": rule["rule_key"]},
                    expected_state=rule,
                    source_refs=_source_refs(rule),
                    oracles=[oracle],
                )
            )
        return ScenarioDesignOutput(
            schema_version="1.0",
            contract_version_id=context.contract_version_id,
            mission_id=context.mission_id,
            items=items,
        )


class LegacyAIServiceProvider(DeterministicScopeProvider):
    """Deprecated alias kept for import compatibility.

    Batch 207: services construct providers via ``build_intelligence_provider``;
    this class is retained only so existing imports keep resolving. It always
    behaves as the deterministic baseline (never fakes an AI call).
    """

    mode = "deterministic"
    created_by_type = "DETERMINISTIC"

    def __init__(self, ai_enabled: bool = False) -> None:  # noqa: ARG002
        super().__init__()


class AiIntelligenceProvider:
    """Real, synchronous LLM-backed intelligence provider (Batch 207).

    Each of the five methods renders its prompt template and validates the
    model's JSON into the strict output schema. A malformed model response
    raises ``IntelligenceLLMResponseError`` (never a silent deterministic
    fallback inside this class); transient network failures raise
    ``IntelligenceLLMError``. The service layer owns degradation decisions and
    records them via ``ai_ops``.
    """

    mode = "ai"
    created_by_type = "AI"

    def __init__(
        self,
        db: Session,
        project_id: int,
        client: Callable[..., dict[str, Any]] | None = None,
    ) -> None:
        self._db = db
        self._project_id = project_id
        if client is None:
            from app.modules.aitde.intelligence import llm_sync

            self._client: Callable[..., Any] = llm_sync.call_llm_json_full
            self._captures_metadata = True
        else:
            self._client = client
            self._captures_metadata = False
        self._operation_calls: list[dict[str, Any]] = []
        self._response_cache: dict[str, dict[str, Any]] = {}
        self._deduplicated_calls = 0

    # ── internals ────────────────────────────────────────────────────────
    def _call(self, prompt_name: str, user_payload: dict[str, Any]) -> dict[str, Any]:
        from app.modules.aitde.intelligence.llm_sync import IntelligenceLLMResponseError

        request_fingerprint = hashlib.sha256(
            (
                prompt_name
                + "|"
                + json.dumps(user_payload, ensure_ascii=False, sort_keys=True)
            ).encode("utf-8")
        ).hexdigest()
        if request_fingerprint in self._response_cache:
            self._deduplicated_calls += 1
            return deepcopy(self._response_cache[request_fingerprint])

        call_args = {
            "db": self._db,
            "project_id": self._project_id,
            "system_prompt": _load_prompt(prompt_name),
            "user_payload": user_payload,
        }
        if self._captures_metadata:
            payload, metadata = self._client(
                **call_args, prompt_version=prompt_name
            )
            self._operation_calls.append(metadata)
        else:
            payload = self._client(**call_args)
        if not isinstance(payload, dict):
            raise IntelligenceLLMResponseError(
                f"{prompt_name}: response is not a JSON object"
            )
        self._response_cache[request_fingerprint] = deepcopy(payload)
        return payload

    def operation_metadata(self) -> dict[str, Any]:
        """Aggregate metadata when one domain operation performs several calls."""
        if not self._operation_calls:
            return {}
        calls = self._operation_calls
        usages = [call.get("token_usage") or {} for call in calls]
        reported_usages = [usage for usage in usages if usage]
        numeric_keys = (
            "input_tokens",
            "output_tokens",
            "total_tokens",
            "cached_input_tokens",
            "uncached_input_tokens",
        )
        usage = (
            {
                key: sum(int(item.get(key) or 0) for item in reported_usages)
                for key in numeric_keys
            }
            if reported_usages
            else {}
        )
        cache_details_available = bool(reported_usages) and len(reported_usages) == len(
            usages
        ) and all(
            item.get("cache_details_available") is True for item in reported_usages
        )
        if reported_usages:
            usage["cache_details_available"] = cache_details_available
        usage["request_count"] = len(calls)
        usage["deduplicated_request_count"] = self._deduplicated_calls
        usage["exact_cache_hit_count"] = sum(
            1 for call in calls if call.get("exact_cache_status") == "hit"
        )
        usage["exact_cache_write_count"] = sum(
            1 for call in calls if call.get("exact_cache_status") == "write"
        )
        if cache_details_available:
            usage["cache_hit_rate"] = (
                round(usage["cached_input_tokens"] / usage["input_tokens"], 4)
                if usage["input_tokens"]
                else 0.0
            )
        elif reported_usages:
            usage.pop("cached_input_tokens", None)
            usage.pop("uncached_input_tokens", None)
        prompt_versions = sorted(
            {str(call.get("prompt_version") or "") for call in calls}
        )
        input_hashes = "|".join(str(call.get("input_hash") or "") for call in calls)
        first = calls[0]
        input_hash = (
            str(first.get("input_hash") or "")
            if len(calls) == 1
            else hashlib.sha256(input_hashes.encode("utf-8")).hexdigest()
        )
        return {
            "model_provider": first.get("model_provider") or "",
            "model_name": first.get("model_name") or "",
            "model_config_hash": first.get("model_config_hash") or "",
            "prompt_version": ",".join(filter(None, prompt_versions))[:128],
            "input_hash": input_hash,
            "duration_ms": sum(int(call.get("duration_ms") or 0) for call in calls),
            "token_usage": usage,
        }

    @staticmethod
    def _validate(model_cls: type, value: Any, prompt_name: str) -> Any:
        from app.modules.aitde.intelligence.llm_sync import IntelligenceLLMResponseError
        from pydantic import ValidationError

        try:
            return model_cls.model_validate(value)
        except ValidationError as exc:
            raise IntelligenceLLMResponseError(
                f"{prompt_name}: invalid item: {exc}"
            ) from exc

    # ── protocol methods ─────────────────────────────────────────────────
    def analyze_scope(self, context: ScopeContext) -> ScopeAnalysisOutput:
        fragments = [
            {"artifact_id": a, "fragment_id": f, "title": t, "text": text}
            for a, f, t, text in context.fragments
        ]
        payload = self._call(
            "scope_analysis_v1",
            {"mission_id": context.mission_id, "fragments": fragments},
        )
        raw_items = payload.get("items")
        if not isinstance(raw_items, list):
            from app.modules.aitde.intelligence.llm_sync import IntelligenceLLMResponseError

            raise IntelligenceLLMResponseError("scope_analysis_v1: missing items")
        items = [
            self._validate(ScopeAnalysisCandidate, raw, "scope_analysis_v1")
            for raw in raw_items
        ]
        return ScopeAnalysisOutput(
            schema_version="1.0", mission_id=context.mission_id, items=items
        )

    def _ambiguity_payload(self, context: ScopeIntentContext) -> dict[str, Any]:
        return {"mission_id": context.mission_id, "scope_items": context.scope_items}

    def detect_ambiguities(
        self, context: ScopeIntentContext
    ) -> AmbiguityDetectionOutput:
        payload = self._call("ambiguity_intent_v1", self._ambiguity_payload(context))
        raw_items = payload.get("ambiguities")
        if not isinstance(raw_items, list):
            from app.modules.aitde.intelligence.llm_sync import IntelligenceLLMResponseError

            raise IntelligenceLLMResponseError(
                "ambiguity_intent_v1: missing ambiguities"
            )
        items = [
            self._validate(AmbiguityCandidate, raw, "ambiguity_intent_v1")
            for raw in raw_items
        ]
        return AmbiguityDetectionOutput(
            schema_version="1.0", mission_id=context.mission_id, items=items
        )

    def design_intents(self, context: ScopeIntentContext) -> IntentDetectionOutput:
        payload = self._call("ambiguity_intent_v1", self._ambiguity_payload(context))
        raw_items = payload.get("intents")
        if not isinstance(raw_items, list):
            from app.modules.aitde.intelligence.llm_sync import IntelligenceLLMResponseError

            raise IntelligenceLLMResponseError("ambiguity_intent_v1: missing intents")
        items = [
            self._validate(IntentCandidate, raw, "ambiguity_intent_v1")
            for raw in raw_items
        ]
        return IntentDetectionOutput(
            schema_version="1.0", mission_id=context.mission_id, items=items
        )

    def build_contract(self, context: ContractContext) -> ContractSnapshot:
        payload = self._call(
            "contract_builder_v1",
            {
                "mission_id": context.mission_id,
                "scope_items": context.scope_items,
                "intents": context.intents,
            },
        )
        raw_rules = payload.get("rules")
        raw_outcomes = payload.get("required_outcomes")
        if not isinstance(raw_rules, list) or not raw_rules:
            from app.modules.aitde.intelligence.llm_sync import IntelligenceLLMResponseError

            raise IntelligenceLLMResponseError(
                "contract_builder_v1: expected at least one rule"
            )
        if not isinstance(raw_outcomes, list):
            from app.modules.aitde.intelligence.llm_sync import IntelligenceLLMResponseError

            raise IntelligenceLLMResponseError(
                "contract_builder_v1: missing required_outcomes"
            )
        rules = [
            self._validate(ContractRule, raw, "contract_builder_v1")
            for raw in raw_rules
        ]
        outcomes = [
            self._validate(ContractOutcome, raw, "contract_builder_v1")
            for raw in raw_outcomes
        ]
        return ContractSnapshot(
            schema_version="1.0",
            mission_id=context.mission_id,
            scope_revision=str(payload.get("scope_revision") or ""),
            rules=rules,
            required_outcomes=outcomes,
        )

    def design_scenarios(self, context: ScenarioContext) -> ScenarioDesignOutput:
        payload = self._call(
            "scenario_design_v1",
            {
                "mission_id": context.mission_id,
                "contract_version_id": context.contract_version_id,
                "rules": context.rules,
                "outcomes": context.outcomes,
            },
        )
        raw_items = payload.get("items")
        if not isinstance(raw_items, list) or not raw_items:
            from app.modules.aitde.intelligence.llm_sync import IntelligenceLLMResponseError

            raise IntelligenceLLMResponseError(
                "scenario_design_v1: expected at least one item"
            )
        items: list[ScenarioCandidate] = []
        for raw in raw_items:
            cand = self._validate(ScenarioCandidate, raw, "scenario_design_v1")
            for oracle in cand.oracles:
                # Schema guard: AI-inferred oracles are never required at
                # generation time (V3.9 invariant; a tester must promote them).
                if oracle.source_type == _SOURCE_TYPE_AI_INFERRED:
                    oracle.required = False
            items.append(cand)
        present_lanes = {candidate.case_type.value for candidate in items}
        missing_lanes = {"FUNCTIONAL", "API", "UI"} - present_lanes
        if missing_lanes:
            from app.modules.aitde.intelligence.llm_sync import IntelligenceLLMResponseError

            raise IntelligenceLLMResponseError(
                "scenario_design_v1: missing case lanes: "
                + ", ".join(sorted(missing_lanes))
            )
        return ScenarioDesignOutput(
            schema_version="1.0",
            contract_version_id=context.contract_version_id,
            mission_id=context.mission_id,
            items=items,
        )


def build_intelligence_provider(
    db: Session, project_id: int
) -> DeterministicScopeProvider | AiIntelligenceProvider:
    """Resolve the project's AI config and pick the provider.

    Configured -> real AI provider; disabled/unconfigured (or resolve failure)
    -> deterministic baseline. The deterministic path is honest: outputs are
    stamped DETERMINISTIC and never claim an AI origin.
    """
    from app.core.config import settings
    from app.services.ai_config_service import (
        AIProviderUnconfiguredError,
        ai_config_service,
    )

    if not settings.ai_enabled:
        return DeterministicScopeProvider()
    try:
        ai_config_service.resolve(db, project_id)
    except AIProviderUnconfiguredError:
        return DeterministicScopeProvider()
    except Exception:  # noqa: BLE001 - any resolve failure degrades safely
        return DeterministicScopeProvider()
    return AiIntelligenceProvider(db=db, project_id=project_id)
