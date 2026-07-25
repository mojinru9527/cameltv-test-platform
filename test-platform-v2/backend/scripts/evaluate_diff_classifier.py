"""Diff Classifier 评估脚本 — 基于标注语料计算召回率和误报率。

用法:
    python scripts/evaluate_diff_classifier.py --gold path/to/gold.json --pred path/to/pred.json

标注语料格式 (gold.json):
    [
      {
        "left_contract": { ... },
        "right_contract": { ... },
        "expected_diffs": [
          {"dimension": "需求范围", "diff_type": "missing_in_left", "title": "..."},
          ...
        ]
      },
      ...
    ]

预测格式 (pred.json) — classifier 输出的 classify() 返回值:
    [[{...}, {...}], ...]  — 每个元素是一个契约对的 diff 列表

输出:
    - Precision, Recall, F1 (micro 和 macro)
    - 按维度的细分指标
    - 误报和漏报样例
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from typing import Any


def _diff_key(d: dict) -> tuple[str, str]:
    """用 dimension + diff_type 作为匹配 key。"""
    return (d.get("dimension", ""), d.get("diff_type", ""))


def evaluate(gold_data: list[dict], pred_data: list[list[dict]]) -> dict:
    """评估 classifier 输出。

    gold_data: list of {left_contract, right_contract, expected_diffs}
    pred_data: list of classifier outputs (每个元素是一个对的所有 diffs)
    """
    if len(gold_data) != len(pred_data):
        raise ValueError(
            f"Gold ({len(gold_data)}) and pred ({len(pred_data)}) must have same length"
        )

    tp = 0
    fp = 0
    fn = 0
    false_positives: list[dict] = []
    false_negatives: list[dict] = []

    dimension_stats: dict[str, dict] = defaultdict(lambda: {"tp": 0, "fp": 0, "fn": 0})

    for i, (gold_item, pred_diffs) in enumerate(zip(gold_data, pred_data)):
        expected = gold_item.get("expected_diffs", [])
        expected_keys = {_diff_key(d) for d in expected}
        pred_keys = {_diff_key(d) for d in (pred_diffs or [])}

        # TP: 预测对且标注有
        matched = expected_keys & pred_keys
        tp += len(matched)

        # FP: 预测有但标注无
        unmatched_pred = pred_keys - expected_keys
        fp += len(unmatched_pred)
        for key in unmatched_pred:
            fp_item = next(d for d in (pred_diffs or []) if _diff_key(d) == key)
            false_positives.append({"pair_index": i, **fp_item})

        # FN: 标注有但预测无
        unmatched_gold = expected_keys - pred_keys
        fn += len(unmatched_gold)
        for key in unmatched_gold:
            fn_item = next(d for d in expected if _diff_key(d) == key)
            false_negatives.append({"pair_index": i, **fn_item})

        # 按维度统计
        for key in matched:
            dim = key[0]
            dimension_stats[dim]["tp"] += 1
        for key in unmatched_pred:
            dim = key[0]
            dimension_stats[dim]["fp"] += 1
        for key in unmatched_gold:
            dim = key[0]
            dimension_stats[dim]["fn"] += 1

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

    by_dimension = {}
    for dim, stats in sorted(dimension_stats.items()):
        p = stats["tp"] / (stats["tp"] + stats["fp"]) if (stats["tp"] + stats["fp"]) > 0 else 0.0
        r = stats["tp"] / (stats["tp"] + stats["fn"]) if (stats["tp"] + stats["fn"]) > 0 else 0.0
        f = 2 * p * r / (p + r) if (p + r) > 0 else 0.0
        by_dimension[dim] = {"precision": round(p, 4), "recall": round(r, 4), "f1": round(f, 4), **stats}

    return {
        "overall": {
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(f1, 4),
            "true_positives": tp,
            "false_positives": fp,
            "false_negatives": fn,
            "pairs_evaluated": len(gold_data),
        },
        "by_dimension": by_dimension,
        "false_positives": false_positives[:20],  # top 20 样例
        "false_negatives": false_negatives[:20],
    }


def generate_sample_gold() -> list[dict]:
    """生成标注语料样本（用于基线）。"""
    return [
        {
            "left_contract": {
                "scope": "用户登录模块",
                "rules": [{"rule": "用户名长度 3-20 字符"}],
                "fields": [{"name": "username", "type": "string", "required": True}],
                "apis": [{"method": "POST", "path": "/api/v1/login"}],
            },
            "right_contract": {
                "scope": "用户登录模块",
                "rules": [{"rule": "用户名长度 5-30 字符"}],
                "fields": [{"name": "username", "type": "string", "required": True}],
                "apis": [{"method": "POST", "path": "/api/v1/auth/login"}],
            },
            "expected_diffs": [
                {"dimension": "业务规则", "diff_type": "conflict", "title": "用户名长度规则不一致"},
                {"dimension": "接口", "diff_type": "changed", "title": "登录接口路径不一致"},
            ],
        },
        {
            "left_contract": {
                "scope": "订单查询",
                "apis": [{"method": "GET", "path": "/api/v1/orders"}],
                "fields": [{"name": "order_id", "type": "integer"}],
            },
            "right_contract": {
                "scope": "订单查询",
                "apis": [{"method": "GET", "path": "/api/v1/orders"}],
                "fields": [{"name": "order_id", "type": "integer"}],
            },
            "expected_diffs": [],  # 完全相同
        },
    ]


def main():
    parser = argparse.ArgumentParser(description="Evaluate diff classifier")
    parser.add_argument("--gold", help="Path to gold annotation JSON")
    parser.add_argument("--pred", help="Path to classifier prediction JSON")
    parser.add_argument("--sample", action="store_true", help="Generate sample gold annotation file")
    parser.add_argument("--output", "-o", default=None, help="Output path for evaluation report JSON")
    args = parser.parse_args()

    if args.sample:
        sample = generate_sample_gold()
        print(json.dumps(sample, ensure_ascii=False, indent=2))
        return

    if not args.gold or not args.pred:
        parser.error("--gold and --pred are required (or use --sample to generate sample data)")

    with open(args.gold, encoding="utf-8") as f:
        gold = json.load(f)
    with open(args.pred, encoding="utf-8") as f:
        pred = json.load(f)

    report = evaluate(gold, pred)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        print(f"Report written to {args.output}")

    print(json.dumps(report["overall"], ensure_ascii=False, indent=2))
    if report["false_positives"]:
        print(f"\n⚠️  Top false positives: {len(report['false_positives'])} (showing first 5)")
        for fp in report["false_positives"][:5]:
            print(f"  [{fp.get('dimension')}] {fp.get('diff_type')}: {fp.get('title', fp.get('suggestion', ''))}")
    if report["false_negatives"]:
        print(f"\n🔍 Top false negatives: {len(report['false_negatives'])} (showing first 5)")
        for fn in report["false_negatives"][:5]:
            print(f"  [{fn.get('dimension')}] {fn.get('diff_type')}: {fn.get('title', '')}")


if __name__ == "__main__":
    main()
