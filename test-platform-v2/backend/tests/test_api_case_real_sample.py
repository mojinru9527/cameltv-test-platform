"""Batch 103 — 真实业务样本驱动的接口用例生成（C103-4）。"""
from __future__ import annotations

from app.services.api_case_generation_service import generate_cases_from_real_sample


def _endpoint() -> dict:
    return {
        "service_name": "camel-service",
        "module": "news-controller",
        "method": "POST",
        "path": "/ee/news/list_visible",
        "summary": "新闻列表查询",
        "request_schema": {"body": {"properties": {}, "required": []}},
    }


def _real_sample() -> dict:
    return {
        "method": "POST",
        "url": "https://api.cameltv.live/camel-service/ee/news/list_visible",
        "body": {
            "sorts": [{"key": "top", "sort": "desc"}, {"key": "updateTime", "sort": "desc"}],
            "page": 2,
            "size": 30,
            "queryList": [{"isOrNotRange": 0, "key": "language", "type": "String", "value1": "0", "value2": ""}],
            "locale": "en",
        },
        "source": "生产真实请求样本",
    }


class TestGenerateCasesFromRealSample:
    def test_positive_case_keeps_real_body(self):
        cases = generate_cases_from_real_sample(_endpoint(), _real_sample())
        positive = next(c for c in cases if c["positive_negative"] == "positive")
        assert "page" in positive["api_body"]
        assert '"size": 30' in positive["api_body"]
        assert positive["test_data_note"].startswith("数据来源：生产真实请求样本")

    def test_field_level_coverage(self):
        cases = generate_cases_from_real_sample(_endpoint(), _real_sample())
        pns = {c["positive_negative"] for c in cases}
        assert {"positive", "negative", "boundary"} <= pns
        methods = {c["case_design_method"] for c in cases}
        assert methods >= {"等价类划分", "边界值分析", "错误推测", "场景法", "组合覆盖"}
        assert len(cases) >= 30  # 5 字段 × (边界+类型+缺失+null) + 组合场景

    def test_no_meaningless_placeholder(self):
        cases = generate_cases_from_real_sample(_endpoint(), _real_sample())
        for c in cases:
            # 正向与组合用例的 body 必须保留真实字段值
            if c["positive_negative"] in ("positive", "boundary") and "sorts" in c["api_body"]:
                assert '"top"' in c["api_body"] or "queryList" in c["api_body"]
