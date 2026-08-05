"""batch-18-C8 — diff classifier 标注语料评估基线。

构建 10 组「标注对（left, right, 期望差异签名集合）」，运行 diff_classifier.classify，
统计召回率（期望差异被识别）与误报数（非期望差异被报告），并断言基线质量。
"""
from __future__ import annotations

from app.services.wiki.diff_classifier import classify


def _contract(**over):
    base = {
        "requirement_key": "k", "title": "t", "module": "赛事模块",
        "client_scope": ["app"], "summary": "",
        "business_rules": [], "fields": [], "apis": [],
        "acceptance_criteria": [], "exception_paths": [], "test_cases": [],
        "source_refs": [{"source": "wiki_page", "id": 1}],
    }
    base.update(over)
    return base


# (left, right, expected set of (dimension, diff_type))
LABELED = [
    (
        _contract(business_rules=[{"id": "R1", "rule": "matchId 必填"}]),
        _contract(business_rules=[
            {"id": "R1", "rule": "matchId 必填"},
            {"id": "R2", "rule": "minis 范围 0-90"},
        ]),
        {("业务规则", "missing_in_left")},
    ),
    (
        _contract(fields=[{"name": "matchId", "type": "string", "required": True}]),
        _contract(fields=[{"name": "matchId", "type": "string", "required": False}]),
        {("字段", "conflict")},
    ),
    (
        _contract(apis=[]),
        _contract(apis=[{"method": "GET", "path": "/ee/test/matchpush"}]),
        {("接口", "missing_in_left")},
    ),
    (
        _contract(client_scope=["app"]),
        _contract(client_scope=["app", "web"]),
        {("客户端", "missing_in_left")},
    ),
    (
        _contract(),
        _contract(),
        set(),
    ),
    (
        _contract(business_rules=[{"id": "R1", "rule": "A 必填"}]),
        _contract(business_rules=[{"id": "R1", "rule": "A 必填且唯一"}]),
        {("业务规则", "conflict")},
    ),
    (
        _contract(fields=[{"name": "price", "type": "string"}]),
        _contract(fields=[{"name": "price", "type": "number"}]),
        {("字段", "conflict")},
    ),
    (
        _contract(exception_paths=[]),
        _contract(exception_paths=[{"name": "登录态失效", "rule": "返回 401"}]),
        {("异常路径", "missing_in_left")},
    ),
    (
        _contract(acceptance_criteria=[]),
        _contract(acceptance_criteria=[{"name": "AC1", "rule": "P0 通过"}]),
        {("验收标准", "missing_in_left")},
    ),
    (
        _contract(module="赛事模块"),
        _contract(module="支付模块"),
        {("需求范围", "conflict")},
    ),
]


def _metrics():
    significant = {"missing_in_left", "missing_in_right", "changed", "conflict"}
    expected_total = 0
    matched = 0
    false_positives = 0
    for left, right, expected in LABELED:
        items = classify(left, right)
        actual = {
            (i["dimension"], i["diff_type"])
            for i in items
            if i["diff_type"] in significant
        }
        expected_total += len(expected)
        matched += len(expected & actual)
        false_positives += len(actual - expected)
    recall = matched / expected_total if expected_total else 1.0
    return recall, false_positives, expected_total, matched


def test_labeled_baseline_recall_and_precision():
    recall, fp, expected_total, matched = _metrics()
    # 标注集基线：召回率 100%，误报 0（10 组结构化差异应全部命中）
    assert recall == 1.0, f"召回率 {recall:.2f}（{matched}/{expected_total}）"
    assert fp == 0, f"误报 {fp} 条"


def test_labeled_baseline_metrics_export():
    """把指标序列化到 evidence（batch-18-C8 交付物）。"""
    import json
    from pathlib import Path

    recall, fp, expected_total, matched = _metrics()
    report = {
        "labeled_pairs": len(LABELED),
        "expected_diffs": expected_total,
        "matched_diffs": matched,
        "false_positives": fp,
        "recall": round(recall, 4),
        "precision": round(matched / (matched + fp) if matched + fp else 1.0, 4),
    }
    out = Path(__file__).resolve().parent.parent / "work-logs" / "evidence" / "batch-96"
    out.mkdir(parents=True, exist_ok=True)
    (out / "diff-classifier-baseline.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False))
