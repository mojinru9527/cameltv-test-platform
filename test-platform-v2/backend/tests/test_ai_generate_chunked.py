"""C68-3 — AI 用例生成分批合并（batch-69）。"""
from __future__ import annotations

import pytest

from app.services.ai_service import (
    _CHUNK_FP_LIMIT,
    _dedupe_and_renumber,
    _split_extraction_chunks,
)


def _module(name: str, fp_count: int) -> dict:
    return {
        "id": f"MOD-{name}",
        "name": name,
        "description": name,
        "function_points": [
            {"id": f"FP-{name}-{i}", "title": f"{name}功能{i}", "description": "d"}
            for i in range(fp_count)
        ],
    }


class TestSplitExtractionChunks:
    def test_small_doc_single_chunk(self):
        extraction = {"modules": [_module("A", 10), _module("B", 10)]}
        chunks = _split_extraction_chunks(extraction, _CHUNK_FP_LIMIT)
        assert len(chunks) == 1

    def test_large_doc_split(self):
        extraction = {"modules": [_module("A", 40), _module("B", 30)]}
        chunks = _split_extraction_chunks(extraction, _CHUNK_FP_LIMIT)
        assert len(chunks) >= 2
        for chunk in chunks:
            total_fp = sum(len(m["function_points"]) for m in chunk)
            assert total_fp <= _CHUNK_FP_LIMIT

    def test_single_oversize_module_split(self):
        extraction = {"modules": [_module("A", 60)]}
        chunks = _split_extraction_chunks(extraction, _CHUNK_FP_LIMIT)
        assert len(chunks) == 3


class TestDedupeAndRenumber:
    def test_dedupe_by_title(self):
        cases = [
            {"id": "TC-1", "title": "重复用例", "steps": []},
            {"id": "TC-2", "title": "重复用例", "steps": []},
            {"id": "TC-3", "title": "独立用例", "steps": []},
        ]
        out = _dedupe_and_renumber(cases)
        assert len(out) == 2
        titles = {c["title"] for c in out}
        assert titles == {"重复用例", "独立用例"}
        assert len({c["id"] for c in out}) == 2

    def test_renumber_unique(self):
        cases = [
            {"id": "TC-X", "title": "a", "steps": []},
            {"id": "TC-X", "title": "b", "steps": []},
        ]
        out = _dedupe_and_renumber(cases)
        assert len({c["id"] for c in out}) == 2
