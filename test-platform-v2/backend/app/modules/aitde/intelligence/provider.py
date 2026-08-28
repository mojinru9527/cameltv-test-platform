"""IntelligenceProvider abstraction (V30-033/V30-034).

Business services depend on this protocol, never on a concrete LLM SDK. For V3.0
Scope the default implementation is deterministic (built from parsed source
fragments) so the review flow works without a live AI; ``LegacyAIServiceProvider``
is the thin wrapper over the platform's existing AI service for production.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.modules.aitde.common.enums import (
    RiskLevel,
    ScopeDecision,
    ScopeType,
    TestDepth,
)
from app.modules.aitde.scope.ambiguity_schemas import (
    AmbiguityCandidate,
    AmbiguityDetectionOutput,
    IntentCandidate,
    IntentDetectionOutput,
    Option,
)
from app.modules.aitde.scope.schemas import ScopeAnalysisOutput, SourceRef


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
    scope_items: list[dict]


class IntelligenceProvider(Protocol):
    def analyze_scope(self, context: ScopeContext) -> ScopeAnalysisOutput:
        ...

    def detect_ambiguities(
        self, context: ScopeIntentContext
    ) -> AmbiguityDetectionOutput:
        ...

    def design_intents(self, context: ScopeIntentContext) -> IntentDetectionOutput:
        ...


class DeterministicScopeProvider:
    """Build scope candidates from parsed fragments (no external AI)."""

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
                    "confidence": 0.80,
                    "source_refs": [
                        SourceRef(
                            artifact_id=artifact_id, fragment_id=fragment_id
                        )
                    ],
                }
            )
        return ScopeAnalysisOutput(
            schema_version="1.0",
            mission_id=context.mission_id,
            items=items,
        )

    def detect_ambiguities(
        self, context: ScopeIntentContext
    ) -> AmbiguityDetectionOutput:
        items = []
        for si in context.scope_items:
            # Flag uncertain / excluded scope as an open ambiguity to resolve.
            if si.get("ai_confidence", 1.0) < 0.85 or si.get("decision") == "EXCLUDE":
                items.append(
                    AmbiguityCandidate(
                        ambiguity_key=f"amb-{si['scope_key']}",
                        title=f"{si.get('name', si['scope_key'])} 是否纳入测试范围?",
                        description=si.get("reason", ""),
                        severity=RiskLevel(si.get("risk_level", "P2")),
                        candidate_options=[
                            Option(key="allow", label="纳入"),
                            Option(key="deny", label="排除"),
                            Option(key="out", label="本版本不测"),
                        ],
                        confidence=si.get("ai_confidence", 0.5),
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


class LegacyAIServiceProvider:
    """Wrap the platform AI service when configured; falls back to deterministic."""

    def __init__(self, ai_enabled: bool = False) -> None:
        self.ai_enabled = ai_enabled
        self._fallback = DeterministicScopeProvider()

    def analyze_scope(self, context: ScopeContext) -> ScopeAnalysisOutput:
        # A real integration would call the legacy AI service for scope analysis
        # and parse its JSON into ScopeAnalysisOutput. Until enabled, produce the
        # deterministic baseline so the review flow is always usable.
        return self._fallback.analyze_scope(context)

    def detect_ambiguities(
        self, context: ScopeIntentContext
    ) -> AmbiguityDetectionOutput:
        return self._fallback.detect_ambiguities(context)

    def design_intents(self, context: ScopeIntentContext) -> IntentDetectionOutput:
        return self._fallback.design_intents(context)
