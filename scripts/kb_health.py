#!/usr/bin/env python3
"""CamelTv 知识库健康度报告生成器。

用法:
    python scripts/kb_health.py          # 人类可读报告
    python scripts/kb_health.py --json   # JSON 输出

依赖: scripts/check_doc_freshness.py (同目录)
"""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import date
from pathlib import Path

# Force UTF-8 on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

REPO_ROOT = Path(__file__).resolve().parent.parent

# 健康评分公式 (来自 docs/maintenance-guide.md):
#   健康评分 = (保鲜率 × 0.4) + (ADR 覆盖率 × 0.3) + (文档完整度 × 0.3)
#   >= 80% 健康 | 60-80% 需关注 | < 60% 需治理


def run_freshness_check() -> dict:
    """Run check_doc_freshness.py --json and return parsed result."""
    script = REPO_ROOT / "scripts" / "check_doc_freshness.py"
    result = subprocess.run(
        [sys.executable, str(script), "--json"],
        capture_output=True, text=True, encoding="utf-8",
    )
    if result.returncode not in (0, 1, 2):
        print(f"ERROR: freshness check failed: {result.stderr}", file=sys.stderr)
        sys.exit(3)
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as e:
        print(f"ERROR: cannot parse freshness output: {e}", file=sys.stderr)
        sys.exit(3)


def compute_health(freshness: dict) -> dict:
    """Compute health score from freshness data."""
    total = freshness.get("total", 0)
    if total == 0:
        return {"score": 0, "grade": "no_data", "breakdown": {}}

    # Freshness rate: (ok + skipped + draft + archived) / total
    ok_count = freshness.get("ok", 0)
    expired = freshness.get("expired", 0)
    expiring = freshness.get("expiring_soon", 0)
    no_fm = freshness.get("no_frontmatter", 0)

    freshness_rate = ok_count / total if total > 0 else 0

    # ADR coverage: count ADR files in docs/adr/ (excluding README and template)
    adr_dir = REPO_ROOT / "docs" / "adr"
    adr_files = [
        f for f in adr_dir.glob("*.md")
        if f.name not in ("README.md", "template.md")
    ] if adr_dir.exists() else []
    adr_count = len(adr_files)
    # Target: at least 6 ADRs for a mature project
    adr_coverage = min(adr_count / 6, 1.0)

    # Document completeness: based on presence of key docs
    key_docs = [
        "CLAUDE.md",
        "docs/document-standards.md",
        "docs/business-glossary.md",
        "docs/repo-map.md",
        "docs/common-pitfalls.md",
        "docs/maintenance-guide.md",
        "docs/testing-strategy.md",
        "docs/adr/README.md",
        ".github/pull_request_template.md",
        "scripts/check_doc_freshness.py",
    ]
    present = sum(1 for d in key_docs if (REPO_ROOT / d).exists())
    completeness = present / len(key_docs)

    # Weighted score
    score = round(
        freshness_rate * 0.4 * 100 +
        adr_coverage * 0.3 * 100 +
        completeness * 0.3 * 100,
        1,
    )

    if score >= 80:
        grade = "healthy"
    elif score >= 60:
        grade = "needs_attention"
    else:
        grade = "needs_governance"

    return {
        "date": str(date.today()),
        "score": score,
        "grade": grade,
        "breakdown": {
            "freshness_rate": round(freshness_rate * 100, 1),
            "adr_coverage": round(adr_coverage * 100, 1),
            "adr_count": adr_count,
            "document_completeness": round(completeness * 100, 1),
            "key_docs_present": present,
            "key_docs_total": len(key_docs),
        },
        "violations": {
            "expired": expired,
            "expiring_soon": expiring,
            "no_frontmatter": no_fm,
        },
        "missing_key_docs": [
            d for d in key_docs if not (REPO_ROOT / d).exists()
        ],
    }


def print_report(health: dict):
    b = health["breakdown"]
    v = health["violations"]
    grade_label = {
        "healthy": "健康",
        "needs_attention": "需关注",
        "needs_governance": "需治理",
        "no_data": "无数据",
    }

    print(f"\n{'='*55}")
    print(f"  CamelTv 知识库健康报告 — {health['date']}")
    print(f"{'='*55}")
    print(f"  综合评分: {health['score']} / 100  ({grade_label.get(health['grade'], health['grade'])})\n")

    print("  维度得分:")
    print(f"    文档保鲜率:    {b['freshness_rate']}%  (权重 40%)")
    print(f"    ADR 覆盖率:    {b['adr_coverage']}%  (权重 30%, {b['adr_count']} 篇)")
    print(f"    文档完整度:    {b['document_completeness']}%  (权重 30%, {b['key_docs_present']}/{b['key_docs_total']})\n")

    print("  待处理:")
    print(f"    过期文档:      {v['expired']}")
    print(f"    即将过期:      {v['expiring_soon']}")
    print(f"    缺 frontmatter: {v['no_frontmatter']}")

    missing = health.get("missing_key_docs", [])
    if missing:
        print(f"    缺失关键文档:  {len(missing)}")
        for m in missing:
            print(f"      - {m}")

    print(f"\n  评级: ", end="")
    if health["grade"] == "healthy":
        print("知识库健康，继续保持。")
    elif health["grade"] == "needs_attention":
        print("知识库需要关注，建议近期安排文档审核日。")
    else:
        print("知识库亟需治理，请尽快安排文档审核日。")
    print()


def print_json(health: dict):
    print(json.dumps(health, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="CamelTv 知识库健康度报告")
    parser.add_argument("--json", action="store_true", help="JSON 输出")
    args = parser.parse_args()

    freshness = run_freshness_check()
    health = compute_health(freshness)

    if args.json:
        print_json(health)
    else:
        print_report(health)
