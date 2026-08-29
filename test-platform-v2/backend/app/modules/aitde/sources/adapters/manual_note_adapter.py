"""Manual note adapter (V30-024).

Simplest user supplement: the whole note becomes a single addressable fragment.
"""
from __future__ import annotations

from app.modules.aitde.common.enums import SourceType
from app.modules.aitde.sources.adapters.base import (
    SourceAdapter,
    SourceFragmentDraft,
    stable_content_hash,
)


class ManualNoteAdapter:
    source_type = SourceType.MANUAL_NOTE.value

    def can_handle(self, artifact_source_type: str) -> bool:
        return artifact_source_type == self.source_type

    def normalize(self, content: str) -> list[SourceFragmentDraft]:
        return [
            SourceFragmentDraft(
                fragment_key=f"NOTE-{stable_content_hash(content)}",
                title="人工补充说明",
                text=content or "",
                location="MANUAL_NOTE#body",
                sequence=1,
            )
        ]


adapter: SourceAdapter = ManualNoteAdapter()  # type: ignore[assignment]
