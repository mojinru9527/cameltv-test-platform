"""SourceAdapter shared protocol + fragment drafting (V30-021)."""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Protocol


@dataclass
class SourceFragmentDraft:
    """A not-yet-persisted fragment produced during normalization."""

    fragment_key: str
    title: str
    text: str
    location: str = ""
    sequence: int = 0


def stable_content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:32]


def split_text_into_fragments(
    text: str,
    *,
    fragment_key_prefix: str,
    title_prefix: str,
    location_prefix: str,
    max_len: int = 1200,
) -> list[SourceFragmentDraft]:
    """Deterministically split raw text into chunked fragments.

    Chunks are delimited by blank lines; oversized chunks are hard-split by
    character count so every fragment is addressable and hashable.
    """
    drafts: list[SourceFragmentDraft] = []
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    if not paragraphs:
        return drafts

    seq = 0
    chunk: list[str] = []
    chunk_len = 0

    def flush() -> None:
        nonlocal chunk, chunk_len, seq
        if not chunk:
            return
        body = "\n\n".join(chunk)
        seq_key = f"{fragment_key_prefix}-{seq + 1:04d}"
        drafts.append(
            SourceFragmentDraft(
                fragment_key=seq_key,
                title=f"{title_prefix} {seq + 1}",
                text=body,
                location=f"{location_prefix}#{seq + 1}",
                sequence=seq + 1,
            )
        )
        seq += 1
        chunk = []
        chunk_len = 0

    for para in paragraphs:
        if chunk_len + len(para) + 2 > max_len and chunk:
            flush()
        if len(para) > max_len:
            flush()
            body = para[:max_len]
            seq_key = f"{fragment_key_prefix}-{seq + 1:04d}"
            drafts.append(
                SourceFragmentDraft(
                    fragment_key=seq_key,
                    title=f"{title_prefix} {seq + 1}",
                    text=body,
                    location=f"{location_prefix}#{seq + 1}",
                    sequence=seq + 1,
                )
            )
            seq += 1
            continue
        chunk.append(para)
        chunk_len += len(para) + 2

    flush()
    return drafts


class SourceAdapter(Protocol):
    """Normalizes a source's raw content into addressable fragments."""

    source_type: str

    def can_handle(self, artifact_source_type: str) -> bool:
        ...

    def normalize(self, content: str) -> list[SourceFragmentDraft]:
        ...
