"""V16-025 发布审计（机器可查项，不能替代独立人工验收）。

检查：
1. 禁止旧 body 断言 E2E 文件复活；
2. tests/e2e/aiqe 不得用整文件 skipif/importorskip 把产品 TC 记成 PASS；
3. app/aiqe 不得硬编码弱口令/私钥/AWS key；
4. V16 迁移必须有 downgrade；
5. requirements.yaml：VERIFIED 必须有 tests+evidence；BLOCKED 必须有 blocked_reason/review_by；
6. docs 不得出现伪造的 GA/10-10 通过声明。

用法：python scripts/aiqe/check_release_audit.py
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "test-platform-v2" / "backend"
SECRET_PATTERNS = (
    re.compile(r"admin123"),
    re.compile(r"password123"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(r"sk-[A-Za-z0-9]{20,}"),
)
FAKE_GA_PATTERNS = (
    re.compile(r"10\s*/\s*10\s+(?:PASS|通过)", re.I),
    re.compile(r"GA\s*(?:已)?通过", re.I),
    re.compile(r"PRODUCTION_OBSERVED", re.I),
)


class AuditError(ValueError):
    pass


def scan_secrets(directory: Path) -> list[str]:
    errors: list[str] = []
    for path in sorted(directory.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for pattern in SECRET_PATTERNS:
            if pattern.search(text):
                try:
                    shown = path.relative_to(ROOT)
                except ValueError:
                    shown = path
                errors.append(f"SECRET: {shown} 命中 {pattern.pattern}")
    return errors


def scan_e2e_tests(directory: Path) -> list[str]:
    errors: list[str] = []
    fake = directory / "test_tc_aiqe_001_010.py"
    if fake.exists():
        errors.append("FAKE_E2E: 旧 body 断言文件不得存在")
    for path in sorted(directory.glob("test_*.py")):
        text = path.read_text(encoding="utf-8")
        if "pytestmark = pytest.mark.skipif" in text:
            errors.append(f"SKIP_E2E: {path.name} 不得用整文件 skipif 代替 BLOCKED")
        if "pytest.importorskip" in text and "playwright" in text:
            errors.append(f"SKIP_E2E: {path.name} 不得用 importorskip 隐藏环境缺失")
    return errors


def scan_migrations(directory: Path) -> list[str]:
    errors: list[str] = []
    for path in sorted(directory.glob("2026*_v16_*.py")):
        text = path.read_text(encoding="utf-8")
        if "def downgrade(" not in text:
            errors.append(f"MIGRATION: {path.name} 缺少 downgrade")
    return errors


def check_requirements(path: Path) -> list[str]:
    errors: list[str] = []
    try:
        document = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        return [f"TRACEABILITY: 无法读取 {exc}"]
    requirements = (document or {}).get("requirements") or []
    for item in requirements:
        req_id = str(item.get("id") or "?")
        status = str(item.get("status") or "")
        tests = item.get("tests") or {}
        if status in {"VERIFIED", "ACCEPTED"}:
            if not tests.get("success") or not tests.get("negative"):
                errors.append(f"TRACEABILITY: {req_id} VERIFIED 缺 success/negative 测试")
            if not item.get("evidence"):
                errors.append(f"TRACEABILITY: {req_id} VERIFIED 缺 evidence")
        if status == "BLOCKED":
            if not item.get("blocked_reason"):
                errors.append(f"TRACEABILITY: {req_id} BLOCKED 缺 blocked_reason")
            if not item.get("review_by"):
                errors.append(f"TRACEABILITY: {req_id} BLOCKED 缺 review_by")
    return errors


def scan_docs(directory: Path) -> list[str]:
    errors: list[str] = []
    for path in sorted(directory.glob("*.md")):
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if any(token in line for token in ("不得", "禁止", "未", "不可", "NOT_RUN", "不宣称")):
                continue
            for pattern in FAKE_GA_PATTERNS:
                if pattern.search(line):
                    errors.append(
                        f"DOCS: {path.name}:{lineno} 出现不可证实的声明 {pattern.pattern!r}"
                    )
    return errors


def run_audit(root: Path) -> dict:
    backend = root / "test-platform-v2" / "backend"
    docs = root / "docs" / "aiqe" / "v1.6"
    errors: list[str] = []
    errors += scan_secrets(backend / "app" / "aiqe")
    errors += scan_e2e_tests(backend / "tests" / "e2e" / "aiqe")
    errors += scan_migrations(backend / "alembic" / "versions")
    errors += check_requirements(docs / "traceability" / "requirements.yaml")
    errors += scan_docs(docs)
    return {"ok": not errors, "errors": errors, "root": str(root)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    report = run_audit(Path(args.root))
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        for error in report["errors"]:
            print(f"::error::[release-audit] {error}")
        print(f"release audit: {len(report['errors'])} error(s)")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
