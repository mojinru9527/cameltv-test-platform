"""OpenAPI adapter (V30-023).

V3.0 only produces a snapshot / summary of an OpenAPI source — it does NOT
execute any endpoint. If the content is a valid OpenAPI document we emit one
fragment per endpoint (method + path summary); otherwise a single summary
fragment is produced.
"""
from __future__ import annotations

import json

from app.modules.aitde.common.enums import SourceType
from app.modules.aitde.sources.adapters.base import (
    SourceAdapter,
    SourceFragmentDraft,
)


class OpenApiAdapter:
    source_type = SourceType.OPENAPI.value

    def can_handle(self, artifact_source_type: str) -> bool:
        return artifact_source_type == self.source_type

    def normalize(self, content: str) -> list[SourceFragmentDraft]:
        drafts: list[SourceFragmentDraft] = []
        try:
            spec = json.loads(content)
            paths = spec.get("paths", {}) if isinstance(spec, dict) else {}
        except ValueError:
            paths = {}

        if not paths:
            drafts.append(
                SourceFragmentDraft(
                    fragment_key="OPENAPI-SUMMARY-0001",
                    title="OpenAPI 概要",
                    text=content or "",
                    location="OPENAPI#summary",
                    sequence=1,
                )
            )
            return drafts

        seq = 0
        for path, methods in paths.items():
            for method in ("get", "post", "put", "delete", "patch"):
                if method not in methods:
                    continue
                seq += 1
                op = methods[method]
                summary = op.get("summary") or op.get("description") or ""
                body = f"{method.upper()} {path}\n{summary}".strip()
                drafts.append(
                    SourceFragmentDraft(
                        fragment_key=f"OAS-{seq:04d}",
                        title=f"{method.upper()} {path}",
                        text=body,
                        location=f"OPENAPI#{method.upper()} {path}",
                        sequence=seq,
                    )
                )
        return drafts


adapter: SourceAdapter = OpenApiAdapter()  # type: ignore[assignment]
