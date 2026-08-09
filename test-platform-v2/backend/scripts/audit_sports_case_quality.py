# -*- coding: utf-8 -*-
"""Audit the complete sports case asset before production import."""
from __future__ import annotations

import argparse
from collections import Counter
import json
import re
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from scripts.import_sports_cases import to_create


REPO_ROOT = Path(__file__).resolve().parents[3]
CONSOLIDATED = (
    REPO_ROOT
    / "test-platform-v2/work-logs/evidence/batch-125/module-cases-consolidated.json"
)
DEFAULT_REPORT = (
    REPO_ROOT
    / "test-platform-v2/work-logs/evidence/batch-130-case-module-quality/case-quality-audit.json"
)
_TERMINAL_NODE_RE = re.compile(
    r"(?:pc\s*[-_]?\s*web|pc端|安卓\s*[/+]?\s*ios|移动端?\s*[-_]?\s*web)",
    re.IGNORECASE,
)


def audit_consolidated(path: Path = CONSOLIDATED) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    ids: list[str] = []
    nature_counts: Counter[str] = Counter()
    module_natures: dict[str, set[str]] = {}
    module_categories: dict[str, set[str]] = {}
    issues = {
        "missing_title": 0,
        "missing_preconditions": 0,
        "invalid_steps": 0,
        "missing_expected_result": 0,
        "duplicate_case_ids": 0,
        "terminal_channel_taxonomy_nodes": 0,
        "source_module_mismatches": 0,
    }

    inventory_modules = [
        module for module in data["modules"] if module.get("adversarial_count")
    ]
    for module in data["modules"]:
        module_name = module["module"]
        module_natures.setdefault(module_name, set())
        module_categories.setdefault(module_name, set())
        for case in [*module["base"], *module["deep"]]:
            payload = to_create(case, module_name)
            ids.append(payload["case_id"])
            nature_counts[payload["positive_negative"]] += 1
            module_natures[module_name].add(payload["positive_negative"])
            if case.get("adversarial_category"):
                module_categories[module_name].add(case["adversarial_category"])
            if not payload["title"].strip():
                issues["missing_title"] += 1
            if not payload["preconditions"].strip():
                issues["missing_preconditions"] += 1
            if not payload["expected_result"].strip():
                issues["missing_expected_result"] += 1
            steps = json.loads(payload["steps"])
            if not steps or any(
                not str(step.get("desc") or "").strip()
                or not str(step.get("expected") or "").strip()
                for step in steps
            ):
                issues["invalid_steps"] += 1
            taxonomy_path = f"{payload['domain']}/{payload['module']}"
            if _TERMINAL_NODE_RE.search(taxonomy_path):
                issues["terminal_channel_taxonomy_nodes"] += 1
            if (
                payload["case_type"] != "api"
                and module_name.startswith(("用户端/", "运营后台/"))
            ):
                expected_domain = module_name
                if payload["domain"] != expected_domain:
                    issues["source_module_mismatches"] += 1

    issues["duplicate_case_ids"] = len(ids) - len(set(ids))
    paired = sum(
        {"positive", "negative"} <= module_natures[module["module"]]
        for module in inventory_modules
    )
    adversarial = sum(
        {"recovery", "repeat_concurrency"} <= module_categories[module["module"]]
        for module in inventory_modules
    )
    non_happy = nature_counts["negative"] + nature_counts["boundary"]
    ratio = round(non_happy / len(ids), 4) if ids else 0.0
    coverage = {
        "nature_counts": dict(nature_counts),
        "non_happy_ratio": ratio,
        "paired_inventory_modules": f"{paired}/{len(inventory_modules)}",
        "adversarial_modules": f"{adversarial}/{len(inventory_modules)}",
        "required_adversarial_categories": ["recovery", "repeat_concurrency"],
    }
    passed = (
        not any(issues.values())
        and paired == len(inventory_modules)
        and adversarial == len(inventory_modules)
        and ratio >= 0.45
    )
    return {
        "status": "pass" if passed else "fail",
        "source": str(path.relative_to(REPO_ROOT)).replace("\\", "/"),
        "totals": {
            "cases": len(ids),
            "unique_case_ids": len(set(ids)),
            "inventory_modules": len(inventory_modules),
            "taxonomy_entries": len(data["modules"]),
        },
        "coverage": coverage,
        "quality_issues": issues,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=CONSOLIDATED)
    parser.add_argument("--out", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()
    report = audit_consolidated(args.input)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
