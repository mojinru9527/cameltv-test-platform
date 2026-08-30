"""AITDE V3.3 LegacyPlaywrightCompilerAdapter (V33-010).

Keeps the existing LLM→Playwright path ONLY for already-existing legacy cases,
and hard-rejects routing new Scenarios through it: new scenarios must go through
the deterministic Command IR compiler, never an LLM arbitrarily generating
``expect()`` from ``expected_result``.
"""
from __future__ import annotations

from typing import Any

from app.core.exceptions import APIException

# Source types that are pre-existing legacy UI cases (kept as-is on V33-010).
LEGACY_SOURCE_TYPES = {"SPEC", "MANUAL", "LLM", "PLAYWRIGHT"}


class LegacyPlaywrightCompilerAdapter:
    def is_legacy(self, source_type: str | None) -> bool:
        return (source_type or "").upper() in LEGACY_SOURCE_TYPES

    def compile_legacy(self, db, case, base_url: str) -> dict[str, Any]:
        """Compile an existing legacy case to a Playwright spec (kept unchanged).

        This is the ONLY allowed use of the LLM→Playwright path. If a caller
        marks a non-legacy source as legacy, it is rejected.
        """
        source_type = getattr(case, "source_type", None) or (case.get("source_type") if isinstance(case, dict) else None)
        if not self.is_legacy(source_type):
            raise APIException(
                code=400,
                msg="该来源不是既有 Legacy 用例，禁止走 LLM→Playwright 任意生成路径",
                http_status=400,
            )
        from app.services.case_compiler_service import compile_to_playwright

        return compile_to_playwright(db, case, base_url=base_url)

    @staticmethod
    def assert_deterministic_path(source_type: str | None) -> None:
        """New scenarios MUST go through the deterministic Command IR compiler."""
        if source_type and (source_type.upper() in LEGACY_SOURCE_TYPES):
            return  # legacy is allowed to keep its path
        # Command IR / future scenarios: never let LLM fabricate expect().
        raise APIException(
            code=400,
            msg="新场景必须走确定性 Command IR 编译器，禁止 LLM 任意生成 expect()",
            http_status=400,
        )
