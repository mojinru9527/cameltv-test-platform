"""SourceAdapter registry (V30-021)."""
from __future__ import annotations

from app.modules.aitde.sources.adapters.base import (
    SourceAdapter,
    SourceFragmentDraft,
    stable_content_hash,
    split_text_into_fragments,
)
from app.modules.aitde.sources.adapters.manual_note_adapter import ManualNoteAdapter
from app.modules.aitde.sources.adapters.openapi_adapter import OpenApiAdapter
from app.modules.aitde.sources.adapters.requirement_adapter import RequirementAdapter

ADAPTERS: dict[str, SourceAdapter] = {
    adapter.source_type: adapter
    for adapter in (
        RequirementAdapter(),
        OpenApiAdapter(),
        ManualNoteAdapter(),
    )
}


def get_adapter(source_type: str) -> SourceAdapter:
    return ADAPTERS[source_type]


__all__ = [
    "SourceAdapter",
    "SourceFragmentDraft",
    "stable_content_hash",
    "split_text_into_fragments",
    "ADAPTERS",
    "get_adapter",
]
