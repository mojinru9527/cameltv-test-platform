"""Requirement document adapter (V30-022).

Reuses the platform's requirement content model. Normalization turns the raw
document text into stable, hash-addressed fragments keyed by position. The
actual parsing/import logic stays in the legacy requirement services; this
adapter only performs the AITDE normalization contract.
"""
from __future__ import annotations

from app.modules.aitde.common.enums import SourceType
from app.modules.aitde.sources.adapters.base import (
    SourceAdapter,
    SourceFragmentDraft,
    split_text_into_fragments,
)


class RequirementAdapter:
    source_type = SourceType.REQUIREMENT.value

    def can_handle(self, artifact_source_type: str) -> bool:
        return artifact_source_type == self.source_type

    def normalize(self, content: str) -> list[SourceFragmentDraft]:
        return split_text_into_fragments(
            content,
            fragment_key_prefix="REQ",
            title_prefix="需求片段",
            location_prefix="REQ",
        )


adapter: SourceAdapter = RequirementAdapter()  # type: ignore[assignment]
