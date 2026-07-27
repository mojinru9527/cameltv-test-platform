#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CamelTv 文档保鲜检查脚本
============================

检查所有 Markdown 文档的 YAML frontmatter 元数据是否过期。
配合 CI (Jenkins / GitHub Actions) 每月 1 日自动运行。

用法:
    python scripts/check_doc_freshness.py           # 检查所有文档
    python scripts/check_doc_freshness.py --fix     # 交互式建议修复
    python scripts/check_doc_freshness.py --json    # JSON 输出（CI 集成）
    python scripts/check_doc_freshness.py --ci      # CI 模式：严格检查，有违规即 exit 1

规则 (来自 docs/document-standards.md):
    - CLAUDE.md:     6 个月过期
    - ADR:           12 个月过期
    - README:        6 个月过期
    - PRD:           与产品版本绑定（跳过自动检查）
    - Runbook/运维:  3 个月过期
    - 设计方案:      项目结束即 deprecated

退出码:
    0 — 所有文档保鲜
    1 — 有过期文档
    2 — 有即将过期文档（仅 --ci 模式）
    3 — 脚本运行错误
"""

import os
import sys
import json
import argparse
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional

# 强制 UTF-8 输出（Windows GBK 兼容）
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

try:
    import yaml
except ImportError:
    print("ERROR: PyYAML required. Install: pip install pyyaml", file=sys.stderr)
    sys.exit(3)

# ── 配置 ────────────────────────────────────────────

REPO_ROOT = Path(__file__).resolve().parent.parent

# 按文件类型定义默认审核周期（月）
DEFAULT_PERIODS = {
    "CLAUDE.md": 6,
    "ADR": 12,
    "README": 6,
    "PRD": None,       # 跳过自动检查
    "runbook": 3,
    "design": None,    # 项目结束即 deprecated，跳过自动检查
}

# 排除目录
EXCLUDE_DIRS = {
    "venv", ".venv", "node_modules", ".git",
    ".pytest_cache", "__pycache__", ".claude", ".agents",
    "dist", "build", ".tox", ".mypy_cache",
}

# 忽略这些具体路径
IGNORE_PATHS = {
    "docs/adr/template.md",  # 模板文件，非实际 ADR
}

# 忽略这些目录下的文件（open-source community files，非项目文档）
EXCLUDE_FILE_PATTERNS = [
    "CHANGELOG.md",
    "CONTRIBUTING.md",
    "CODE_OF_CONDUCT.md",
    "SECURITY.md",
    "DEMO.md",
    "DEPLOY.md",
    "RELEASE_NOTES_",
    "LICENSE.md",
    "LICENCE.md",
]

# 忽略这些目录下的所有 md（非项目文档域）
EXCLUDE_DIR_PATTERNS = [
    ".github/",
    "venv/",
    ".venv/",
    "node_modules/",
    ".claude/",
    ".agents/",
    "__pycache__/",
]

def _is_excluded(rel_path: str) -> bool:
    """检查文件是否应排除。"""
    # 目录排除
    for pat in EXCLUDE_DIR_PATTERNS:
        if pat in rel_path:
            return True
    # 文件名排除（仅对 lanhu-mcp 等开源项目）
    fname = rel_path.split("/")[-1]
    for pat in EXCLUDE_FILE_PATTERNS:
        if pat in fname or pat in fname.split("_")[0] if "_" in fname else False:
            return True
    return False

TODAY = date.today()


# ── 分类逻辑 ────────────────────────────────────────

def classify_doc(filepath: Path) -> Optional[str]:
    """根据文件路径和内容判断文档类型。"""
    rel = str(filepath.relative_to(REPO_ROOT)).replace("\\", "/")
    name = filepath.name

    if name == "CLAUDE.md":
        return "CLAUDE.md"
    if name == "README.md" or name.endswith("/README.md"):
        return "README"
    if "/adr/" in rel and name not in ("README.md", "template.md"):
        return "ADR"
    if "runbook" in rel.lower() or "运维" in rel:
        return "runbook"
    if "方案" in name or "设计" in name:
        return "design"
    if "PRD" in name or "prd" in rel.lower():
        return "PRD"

    # 默认按 README 周期
    return "README"


def get_period_months(filepath: Path) -> Optional[int]:
    """获取文件类型的默认审核周期（月）。None 表示跳过自动检查。"""
    doc_type = classify_doc(filepath)
    return DEFAULT_PERIODS.get(doc_type)


# ── Frontmatter 解析 ───────────────────────────────

def parse_frontmatter(filepath: Path) -> Optional[dict]:
    """解析 Markdown 文件的 YAML frontmatter。返回 dict 或 None。"""
    try:
        content = filepath.read_text(encoding="utf-8")
    except Exception as e:
        print(f"WARN: Cannot read {filepath}: {e}", file=sys.stderr)
        return None

    lines = content.split("\n")
    if not lines or lines[0].strip() != "---":
        return None

    end_idx = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end_idx = i
            break

    if end_idx is None:
        return None

    yaml_str = "\n".join(lines[1:end_idx])
    try:
        return yaml.safe_load(yaml_str) or {}
    except yaml.YAMLError:
        return None


def parse_date(value) -> Optional[date]:
    """将字符串或 date 对象转为 date。"""
    if value is None:
        return None
    if isinstance(value, date):
        return value
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, str):
        for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y-%m-%dT%H:%M:%S"):
            try:
                return datetime.strptime(value[:10], fmt).date()
            except ValueError:
                continue
    return None


# ── 检查逻辑 ────────────────────────────────────────

def check_file(filepath: Path) -> dict:
    """检查单个文件，返回结果 dict。"""
    rel = str(filepath.relative_to(REPO_ROOT)).replace("\\", "/")
    result = {
        "file": rel,
        "status": "ok",
        "issues": [],
        "frontmatter": None,
    }

    fm = parse_frontmatter(filepath)
    result["frontmatter"] = fm

    if fm is None:
        result["status"] = "no_frontmatter"
        result["issues"].append("缺少 YAML frontmatter")
        return result

    # 检查必填字段
    for field in ("title", "owner", "last_reviewed", "status"):
        if field not in fm:
            result["issues"].append(f"缺少必填字段: {field}")

    doc_status = fm.get("status", "active")

    # deprecated/archived 文档提醒
    if doc_status == "deprecated":
        # 检查是否超过 3 个月
        lr = parse_date(fm.get("last_reviewed"))
        if lr and (TODAY - lr).days > 90:
            result["status"] = "needs_archive"
            result["issues"].append(f"status=deprecated 超过 3 个月（last_reviewed={lr}），应归档")
        else:
            result["status"] = "deprecated"
        return result

    if doc_status == "archived":
        result["status"] = "archived"
        return result

    if doc_status == "draft":
        result["status"] = "draft"
        return result  # 草稿不强制保鲜

    # active 文档：检查保鲜
    period_months = get_period_months(filepath)
    if period_months is None:
        result["status"] = "skipped"
        return result

    last_reviewed = parse_date(fm.get("last_reviewed"))
    expires = parse_date(fm.get("expires"))

    deadline = None
    if expires:
        deadline = expires
    elif last_reviewed:
        deadline = last_reviewed + timedelta(days=period_months * 30)

    if deadline is None:
        result["issues"].append("无法确定审核截止日期（last_reviewed 和 expires 均缺失）")
        result["status"] = "warning"
        return result

    days_left = (deadline - TODAY).days

    # 分级判断
    if days_left < 0:
        result["status"] = "expired"
        result["issues"].append(
            f"文档已过期 {abs(days_left)} 天（截止 {deadline}，周期 {period_months} 个月）"
        )
    elif days_left <= 30:
        result["status"] = "expiring_soon"
        result["issues"].append(
            f"文档将在 {days_left} 天后过期（截止 {deadline}）"
        )
    elif days_left <= 60:
        result["status"] = "warning"
        result["issues"].append(
            f"建议尽快审核（截止 {deadline}，剩余 {days_left} 天）"
        )

    return result


def collect_files() -> list:
    """收集所有需检查的 Markdown 文件。"""
    files = []
    for dirpath, dirnames, filenames in os.walk(REPO_ROOT):
        # 排除目录
        dirnames[:] = [
            d for d in dirnames
            if d not in EXCLUDE_DIRS
            and not d.startswith(".")
        ]

        for fname in filenames:
            if not fname.endswith(".md"):
                continue
            fpath = Path(dirpath) / fname
            rel = str(fpath.relative_to(REPO_ROOT)).replace("\\", "/")

            if rel in IGNORE_PATHS:
                continue
            if _is_excluded(rel):
                continue

            files.append(fpath)

    return sorted(files)


# ── 输出格式化 ──────────────────────────────────────

def print_report(results: list, ci_mode: bool = False):
    """打印人类可读的报告。"""
    total = len(results)
    expired = [r for r in results if r["status"] == "expired"]
    expiring = [r for r in results if r["status"] == "expiring_soon"]
    warnings = [r for r in results if r["status"] == "warning"]
    no_fm = [r for r in results if r["status"] == "no_frontmatter"]
    needs_archive = [r for r in results if r["status"] == "needs_archive"]
    ok = [r for r in results if r["status"] in ("ok", "skipped", "draft", "archived", "deprecated")]

    print(f"\n{'='*60}")
    print(f"  文档保鲜检查报告 — {TODAY}")
    print(f"{'='*60}")
    print(f"  总计: {total}  正常: {len(ok)}  过期: {len(expired)}")
    print(f"  即将过期: {len(expiring)}  警告: {len(warnings)}")
    print(f"  缺 frontmatter: {len(no_fm)}  待归档: {len(needs_archive)}")
    print(f"{'='*60}\n")

    def print_group(title, items, symbol):
        if not items:
            return
        print(f"  {symbol} {title} ({len(items)}):")
        for r in items:
            print(f"    [{r['status']}] {r['file']}")
            for issue in r["issues"]:
                print(f"           → {issue}")
        print()

    print_group("已过期", expired, "[EXPIRED]")
    print_group("即将过期(<=30天)", expiring, "[SOON]")
    print_group("警告(<=60天)", warnings, "[WARN]")
    print_group("缺少 frontmatter", no_fm, "[NO-FM]")
    print_group("待归档", needs_archive, "[ARCHIVE]")

    if not expired and not expiring and not warnings and not no_fm:
        print("  [OK] 所有文档保鲜，无异常。\n")

    if ci_mode and (expired or expiring):
        print("  CI 检查失败：有过期或即将过期的文档。")
        print("  请更新文档的 last_reviewed 和 expires 字段。\n")


def print_json_report(results: list):
    """JSON 输出模式。"""
    summary = {
        "date": str(TODAY),
        "total": len(results),
        "expired": sum(1 for r in results if r["status"] == "expired"),
        "expiring_soon": sum(1 for r in results if r["status"] == "expiring_soon"),
        "warning": sum(1 for r in results if r["status"] == "warning"),
        "no_frontmatter": sum(1 for r in results if r["status"] == "no_frontmatter"),
        "needs_archive": sum(1 for r in results if r["status"] == "needs_archive"),
        "ok": sum(1 for r in results if r["status"] in ("ok", "skipped", "draft", "archived", "deprecated")),
        "violations": [
            {
                "file": r["file"],
                "status": r["status"],
                "issues": r["issues"],
            }
            for r in results
            if r["status"] in ("expired", "expiring_soon", "warning", "no_frontmatter", "needs_archive")
        ],
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2, default=str))


# ── 交互式修复 ──────────────────────────────────────

def suggest_fix(filepath: Path):
    """为过期文档建议更新后的 frontmatter 值。"""
    fm = parse_frontmatter(filepath)
    if fm is None:
        print(f"  → 建议：添加 YAML frontmatter（参考 docs/document-standards.md 模板）")
        return

    print(f"  当前 frontmatter:")
    for k, v in fm.items():
        print(f"    {k}: {v}")
    print(f"  → 建议更新：last_reviewed: {TODAY}")
    if "expires" in fm:
        suggested_expires = TODAY + timedelta(days=180)
        print(f"  → 建议更新：expires: {suggested_expires}")


def fix_mode(results: list):
    """交互式修复模式。"""
    problems = [
        r for r in results
        if r["status"] in ("expired", "expiring_soon", "warning", "no_frontmatter")
    ]
    if not problems:
        print("[OK] 无需要修复的文档。")
        return

    print(f"\n发现 {len(problems)} 个需要关注的文档:\n")
    for i, r in enumerate(problems, 1):
        print(f"{i}. [{r['status']}] {r['file']}")
        for issue in r["issues"]:
            print(f"     {issue}")

    print(f"\n建议操作：")
    print(f"  1. 更新 last_reviewed 为当前日期 ({TODAY})")
    print(f"  2. 更新 expires 为合适的未来日期")
    print(f"  3. 如果文档不再有效，将 status 改为 'deprecated' 或 'archived'")
    print(f"\n详细修复建议：")
    for r in problems:
        print(f"\n── {r['file']} ──")
        fpath = REPO_ROOT / r["file"]
        suggest_fix(fpath)


# ── 主入口 ──────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="CamelTv 文档保鲜检查",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python scripts/check_doc_freshness.py               # 人类可读报告
  python scripts/check_doc_freshness.py --ci           # CI 严格模式
  python scripts/check_doc_freshness.py --json         # JSON 输出
  python scripts/check_doc_freshness.py --fix          # 交互式修复建议
        """,
    )
    parser.add_argument("--fix", action="store_true", help="显示修复建议")
    parser.add_argument("--json", action="store_true", help="JSON 格式输出")
    parser.add_argument("--ci", action="store_true", help="CI 严格模式（violation → exit 1）")
    args = parser.parse_args()

    files = collect_files()
    if not files:
        print("ERROR: No markdown files found", file=sys.stderr)
        sys.exit(3)

    results = [check_file(f) for f in files]

    if args.json:
        print_json_report(results)
    elif args.fix:
        fix_mode(results)
    else:
        print_report(results, ci_mode=args.ci)

    # 退出码
    has_expired = any(r["status"] == "expired" for r in results)
    has_expiring = any(r["status"] == "expiring_soon" for r in results)

    if args.ci:
        if has_expired or has_expiring:
            sys.exit(1)
    elif has_expired:
        sys.exit(1)
    elif has_expiring:
        sys.exit(2)

    sys.exit(0)


if __name__ == "__main__":
    main()
