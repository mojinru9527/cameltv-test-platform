"""C68-3 — AI 用例生成分批合并（batch-69）。"""
from __future__ import annotations

import pytest
import asyncio

from app.core.config import settings as _settings
from app.services.ai_service import (
    _CHUNK_FP_LIMIT,
    _dedupe_and_renumber,
    _split_extraction_chunks,
    generate_test_cases,
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


class TestChunkedConcurrentGeneration:
    def test_chunks_merge_in_order(self, monkeypatch):
        monkeypatch.setattr(_settings, "ai_api_key", "test-key")
        calls = []

        async def fake_call(system_prompt, user_message, label, max_tokens=None):
            calls.append(label)
            idx = len(calls)
            return {
                "result": {
                    "functional_cases": [
                        {"id": f"TC-{idx}-1", "title": f"case-{label}-1", "steps": []},
                        {"id": f"TC-{idx}-2", "title": f"case-{label}-2", "steps": []},
                    ],
                    "api_cases": [],
                },
                "raw": "{}",
                "finish_reason": "stop",
                "truncated": False,
                "error": None,
            }

        monkeypatch.setattr("app.services.ai_service._call_ai_api", fake_call)
        extraction = {
            "modules": [
                _module("A", 15),
                _module("B", 15),
                _module("C", 15),
            ]
        }
        result = asyncio.run(
            generate_test_cases(
                content="# 测试需求\n\n模块 A 功能说明",
                file_type="md",
                extraction=extraction,
            )
        )
        cases = result.get("functional_cases") or []
        assert len(cases) == 6  # 3 块 × 2 条
        assert len(calls) == 3  # 并发合并后仍 3 次调用
        # 编号唯一
        assert len({c["id"] for c in cases}) == 6
