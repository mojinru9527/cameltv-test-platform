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
_SOURCE_TYPE_AI_INFERRED = "AI_INFERRED"
_SOURCE_TYPE_RULE_BASELINE = "RULE_BASELINE"


def _load_prompt(name: str) -> str:
    """Read a prompt template shipped next to this module."""
    return (_PROMPTS_DIR / f"{name}.txt").read_text(encoding="utf-8")


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
                    source_refs=[SourceRef(artifact_id=0, fragment_id=0)],
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
                        source_refs=[SourceRef(artifact_id=0, fragment_id=0)],
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
                source_refs=[SourceRef(artifact_id=0, fragment_id=0)],
            )
            for si in context.scope_items
        ]
        outcomes = [
            ContractOutcome(
                outcome_key=f"outcome-{it['intent_key']}",
                statement=it.get("business_goal", ""),
                source_type=_SOURCE_TYPE_RULE_BASELINE,
                source_refs=[SourceRef(artifact_id=0, fragment_id=0)],
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
                source_refs=[SourceRef(artifact_id=0, fragment_id=0)],
                required=False,
                confidence=0.7,
            )
            items.append(
                ScenarioCandidate(
                    scenario_key=f"{rule['rule_key']}-SCEN-{i + 1:03d}",
                    title=rule.get("title", rule["rule_key"]),
                    business_goal=rule.get("statement", ""),
                    priority=RiskLevel(rule.get("risk_level", "P2")),
                    risk_level=RiskLevel(rule.get("risk_level", "P2")),
                    given={"state": "precondition"},
                    when={"action": rule["rule_key"]},
                    expected_state=rule,
                    source_refs=[SourceRef(artifact_id=0, fragment_id=0)],
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

            self._client: Callable[..., dict[str, Any]] = llm_sync.call_llm_json
        else:
            self._client = client

    # ── internals ────────────────────────────────────────────────────────
    def _call(self, prompt_name: str, user_payload: dict[str, Any]) -> dict[str, Any]:
        from app.modules.aitde.intelligence.llm_sync import IntelligenceLLMResponseError

        payload = self._client(
            db=self._db,
            project_id=self._project_id,
            system_prompt=_load_prompt(prompt_name),
            user_payload=user_payload,
        )
        if not isinstance(payload, dict):
            raise IntelligenceLLMResponseError(
                f"{prompt_name}: response is not a JSON object"
            )
        return payload

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
        rules = [
            self._validate(ContractRule, raw, "contract_builder_v1")
            for raw in payload.get("rules") or []
        ]
        outcomes = [
            self._validate(ContractOutcome, raw, "contract_builder_v1")
            for raw in payload.get("required_outcomes") or []
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
        if not isinstance(raw_items, list):
            from app.modules.aitde.intelligence.llm_sync import IntelligenceLLMResponseError

            raise IntelligenceLLMResponseError("scenario_design_v1: missing items")
        items: list[ScenarioCandidate] = []
        for raw in raw_items:
            cand = self._validate(ScenarioCandidate, raw, "scenario_design_v1")
            for oracle in cand.oracles:
                # Schema guard: AI-inferred oracles are never required at
                # generation time (V3.9 invariant; a tester must promote them).
                if oracle.source_type == _SOURCE_TYPE_AI_INFERRED:
                    oracle.required = False
            items.append(cand)
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
