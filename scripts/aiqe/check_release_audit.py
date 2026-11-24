"""V16-025 发布审计（机器可查项，不能替代独立人工验收）。

检查：
1. 禁止旧 body 断言 E2E 文件复活；
2. tests/e2e/aiqe 不得用整文件 skipif/importorskip 把产品 TC 记成 PASS；
3. app/aiqe 不得硬编码弱口令/私钥/AWS key；
4. V16 迁移必须有 downgrade；
5. requirements.yaml：VERIFIED 必须有 tests+evidence；BLOCKED 必须有 blocked_reason/review_by；
6. docs 不得出现与 ``release-verdict.json`` 矛盾的 GA / 10-10 / Gate / TC 声明；
7. 生成型文档（矩阵、发布判定、E2E 覆盖）必须与生成器输出一致（禁止手改）。

用法：
    python scripts/aiqe/check_release_audit.py
    python scripts/aiqe/check_release_audit.py --json
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "test-platform-v2" / "backend"
DOCS = ROOT / "docs" / "aiqe" / "v1.6"
SECRET_PATTERNS = (
    re.compile(r"admin123"),
    re.compile(r"password123"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(r"sk-[A-Za-z0-9]{20,}"),
)
# 只匹配“肯定式”GA 声明；否定句（不得/禁止/未/不是/不构成）另行豁免。
FAKE_GA_PATTERNS = (
    re.compile(r"10\s*/\s*10\s*(?:PASS|通过|VERIFIED|完全)", re.I),
    re.compile(r"GA\s*(?:已)?通过", re.I),
    re.compile(r"PRODUCTION_DEPLOYED", re.I),
)
NEGATION_TOKENS = (
    "不得",
    "禁止",
    "未",
    "不可",
    "不能",
    "不是",
    "并非",
    "不构成",
    "不宣称",
    "NOT_RUN",
    "NOT_PROVEN",
    "不得宣称",
    "旧声明",
    "原声明",
    "更正",
)
TC_CLAIM_RE = re.compile(r"TC-AIQE-(\d{3})[^\n]{0,40}?(VERIFIED|PASS|通过)")
COUNT_CLAIM_RE = re.compile(r"(\d{1,3})\s*(?:条|/|个)?\s*(?:需求)?\s*VERIFIED")
GENERATED_DOCS = {
    "E2E-Coverage-and-Blockers.md": "e2e",
    "V1.6-Release-Verdict.md": "verdict",
    "V1.6-Requirement-Code-Test-Evidence-Matrix.md": "matrix",
}
HISTORICAL_MARKERS = ("STATUS: HISTORICAL", "历史归档", "superseded", "已被取代")


class AuditError(ValueError):
    pass


def _relative(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def scan_secrets(directory: Path) -> list[str]:
    errors: list[str] = []
    for path in sorted(directory.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for pattern in SECRET_PATTERNS:
            if pattern.search(text):
                errors.append(f"SECRET: {_relative(path)} 命中 {pattern.pattern}")
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
    """否定式声明豁免；肯定式 GA/10-10 声明按当前仓库事实直接拒绝。"""
    errors: list[str] = []
    for path in sorted(directory.rglob("*.md")):
        if path.name in GENERATED_DOCS:
            continue
        text = path.read_text(encoding="utf-8")
        if _is_historical(text):
            continue
        for lineno, line in enumerate(text.splitlines(), 1):
            if any(token in line for token in NEGATION_TOKENS):
                continue
            for pattern in FAKE_GA_PATTERNS:
                if pattern.search(line):
                    errors.append(
                        f"DOCS: {_relative(path)}:{lineno} 出现不可证实的声明 {pattern.pattern!r}"
                    )
    return errors


def _load_verdict() -> dict:
    """优先实时计算（避免陈旧 JSON），失败时回退到已提交文件。"""
    spec = importlib.util.spec_from_file_location("release_verdict", ROOT / "scripts/aiqe/release_verdict.py")
    if spec and spec.loader:
        module = importlib.util.module_from_spec(spec)
        sys.modules["release_verdict"] = module
        try:
            spec.loader.exec_module(module)
            return module.build_verdict()
        except Exception:  # pragma: no cover - 生成器异常时回退
            pass
        finally:
            sys.modules.pop("release_verdict", None)
    path = DOCS / "release-verdict.json"
    if not path.exists():
        raise AuditError("缺少 release-verdict.json 且无法计算判定")
    return json.loads(path.read_text(encoding="utf-8"))


def _is_historical(text: str) -> bool:
    head = "\n".join(text.splitlines()[:12])
    return any(marker in head for marker in HISTORICAL_MARKERS)


def check_doc_consistency(verdict: dict, docs: Path = DOCS) -> list[str]:
    errors: list[str] = []
    summary = verdict.get("summary") or {}
    gates = verdict.get("gates") or {}
    ga_signed = bool(verdict.get("ga_ready"))
    product_pass = int(summary.get("product_tc_pass") or 0)
    verified_count = int(summary.get("verified") or 0)
    gate_f = str((gates.get("F") or {}).get("status") or "")

    matrix = yaml.safe_load((docs / "traceability/requirements.yaml").read_text(encoding="utf-8"))
    tc_status = {
        str(entry.get("id")): str(
            ((entry.get("e2e") or {}).get("product") or {}).get("status") or ""
        ).upper()
        for entry in matrix.get("requirements") or []
        if str(entry.get("id", "")).startswith("TC-AIQE-")
    }

    for path in sorted(docs.rglob("*.md")):
        if path.name in GENERATED_DOCS:
            continue
        text = path.read_text(encoding="utf-8")
        if _is_historical(text):
            continue
        current_gate = ""
        for lineno, line in enumerate(text.splitlines(), 1):
            gate_match = re.search(r"Gate\s*([A-G])", line)
            if gate_match and line.lstrip().startswith("#"):
                current_gate = gate_match.group(1)
            if any(token in line for token in NEGATION_TOKENS):
                continue
            if path.name == "V1.6-GA-Release-Report.md" and "[x]" in line and current_gate:
                status = str((gates.get(current_gate) or {}).get("status") or "")
                if status != "PASS":
                    errors.append(
                        f"DOCS: {path.name}:{lineno} Gate {current_gate} 标 [x]，但机器判定为 {status or 'N/A'}"
                    )
            for match in TC_CLAIM_RE.finditer(line):
                tc_id = f"TC-AIQE-{match.group(1)}"
                claimed = match.group(2).upper()
                actual = tc_status.get(tc_id, "")
                if claimed in {"VERIFIED", "PASS", "通过"} and actual != "PASS":
                    errors.append(
                        f"DOCS: {_relative(path)}:{lineno} 声称 {tc_id} {claimed}，"
                        f"但矩阵产品状态为 {actual or 'N/A'}"
                    )
            if re.search(r"10\s*/\s*10", line) and product_pass < 10:
                errors.append(
                    f"DOCS: {_relative(path)}:{lineno} 声称 10/10，但产品级 TC PASS 仅 {product_pass}/10"
                )
            for match in COUNT_CLAIM_RE.finditer(line):
                claimed_count = int(match.group(1))
                if claimed_count != verified_count and claimed_count not in {0, 10}:
                    errors.append(
                        f"DOCS: {_relative(path)}:{lineno} 声称 {claimed_count} 条 VERIFIED，"
                        f"但矩阵为 {verified_count}"
                    )
            if ga_signed is False and re.search(r"GA\s*(?:已)?通过|GA_SIGNED", line):
                errors.append(
                    f"DOCS: {_relative(path)}:{lineno} 声称 GA 通过，但判定为 GA_NOT_READY"
                )
            if gate_f != "PASS" and "PRODUCTION_DEPLOYED" in line.upper():
                errors.append(
                    f"DOCS: {_relative(path)}:{lineno} 声称 PRODUCTION_DEPLOYED，"
                    f"但 Gate F 为 {gate_f or 'N/A'}"
                )
    return errors


def _run(command: list[str], cwd: Path = ROOT) -> subprocess.CompletedProcess:
    return subprocess.run(
        command, cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace"
    )


def check_generated_docs() -> list[str]:
    """生成型文档必须与生成器输出一致；禁止手工编辑。"""
    errors: list[str] = []
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        matrix_out = tmp_path / "matrix.md"
        proc = _run(
            [
                sys.executable,
                "scripts/aiqe/check_traceability.py",
                "--emit-markdown",
                str(matrix_out),
            ]
        )
        if proc.returncode != 0:
            errors.append(f"GENERATED: 生成追踪矩阵失败: {proc.stdout[-400:]}")
        else:
            committed = DOCS / "V1.6-Requirement-Code-Test-Evidence-Matrix.md"
            if not committed.exists() or committed.read_text(encoding="utf-8") != matrix_out.read_text(
                encoding="utf-8"
            ):
                errors.append(
                    "GENERATED: V1.6-Requirement-Code-Test-Evidence-Matrix.md 与生成器输出不一致"
                )
        verdict_md = tmp_path / "verdict.md"
        e2e_md = tmp_path / "e2e.md"
        proc = _run(
            [
                sys.executable,
                "scripts/aiqe/release_verdict.py",
                "--emit-markdown",
                str(verdict_md),
                "--emit-e2e-doc",
                str(e2e_md),
            ]
        )
        if proc.returncode != 0:
            errors.append(f"GENERATED: 生成发布判定失败: {proc.stdout[-400:]}")
        else:
            for committed_name, generated in (
                ("V1.6-Release-Verdict.md", verdict_md),
                ("E2E-Coverage-and-Blockers.md", e2e_md),
            ):
                committed = DOCS / committed_name
                if not committed.exists() or committed.read_text(
                    encoding="utf-8"
                ) != generated.read_text(encoding="utf-8"):
                    errors.append(f"GENERATED: {committed_name} 与生成器输出不一致")
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
    try:
        verdict = _load_verdict()
    except AuditError as exc:
        errors.append(f"VERDICT: {exc}")
    else:
        errors += check_doc_consistency(verdict, docs)
        if root == ROOT:
            errors += check_generated_docs()
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
