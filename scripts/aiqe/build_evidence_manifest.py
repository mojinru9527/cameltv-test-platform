"""FIX-015：Release Evidence Manifest 生成器。

把发布验收依赖的证据文件汇总为可核验清单：相对路径、SHA256、大小、生成 Job、
commit SHA、是否缺失。任何缺失都会让 manifest ``complete=false``；
``--require-complete`` 时非零退出，禁止在证据不齐时签署 GA。
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]

EVIDENCE_SPECS: tuple[dict[str, str], ...] = (
    {"kind": "release_verdict", "path": "docs/aiqe/v1.6/release-verdict.json", "job": "Release Gate (GA verdict)"},
    {
        "kind": "release_verdict_markdown",
        "path": "docs/aiqe/v1.6/V1.6-Release-Verdict.md",
        "job": "Release Gate (GA verdict)",
    },
    {"kind": "product_results", "path": "docs/aiqe/v1.6/e2e/product-results.json", "job": "Product TC Runner"},
    {"kind": "runtime_index", "path": "docs/aiqe/v1.6/evidence/evidence-index.json", "job": "Unit / Integration Gate"},
    {"kind": "platform_results", "path": "docs/aiqe/v1.6/e2e/platform-results.json", "job": "Unit / Integration Gate"},
    {
        "kind": "credential_scan",
        "path": "docs/aiqe/v1.6/evidence/credential-scan.json",
        "job": "Credential Scan",
    },
    {
        "kind": "production_evidence",
        "path": "docs/aiqe/v1.6/governance/production-evidence.json",
        "job": "Production Stage Evidence",
    },
    {
        "kind": "branch_protection",
        "path": "docs/aiqe/v1.6/governance/branch-protection.json",
        "job": "Branch Ruleset Capture",
    },
    {
        "kind": "audit_closure",
        "path": "docs/aiqe/v1.6/V1.6.1-Audit-Closure-Report.md",
        "job": "Audit closure ledger",
    },
    {
        "kind": "audit_closure_validation",
        "path": "docs/aiqe/v1.6/governance/audit-closure.yaml",
        "job": "Audit closure ledger",
    },
    {
        "kind": "junit_unit",
        "path": "work-logs/evidence/aiqe-v16/junit-unit.xml",
        "job": "Unit / Integration Gate",
    },
    {
        "kind": "junit_platform",
        "path": "work-logs/evidence/aiqe-v16/junit-platform.xml",
        "job": "Unit / Integration Gate",
    },
    {
        "kind": "junit_runtime",
        "path": "work-logs/evidence/aiqe-v16/junit-runtime.xml",
        "job": "Runtime / Negative Security Gate",
    },
)


def sha256_file(path: Path) -> str:
    import hashlib

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_manifest(
    root: Path,
    *,
    commit_sha: str,
    workflow_run_id: str = "",
    environment: str = "",
    specs: tuple[dict[str, str], ...] = EVIDENCE_SPECS,
) -> dict[str, Any]:
    entries: list[dict[str, Any]] = []
    for spec in specs:
        rel = spec["path"]
        path = root / rel
        item: dict[str, Any] = {
            "kind": spec["kind"],
            "path": rel,
            "job": spec.get("job", ""),
            "commit_sha": commit_sha,
        }
        if path.is_file():
            item.update(
                {
                    "status": "PRESENT",
                    "sha256": sha256_file(path),
                    "size_bytes": path.stat().st_size,
                }
            )
        else:
            item.update({"status": "MISSING", "sha256": None, "size_bytes": None})
        entries.append(item)
    missing = [item["path"] for item in entries if item["status"] == "MISSING"]
    return {
        "schema_version": "1.0",
        "artifact_kind": "release-evidence-manifest",
        "generated_at": datetime.now(UTC).isoformat(),
        "commit_sha": commit_sha,
        "workflow_run_id": workflow_run_id,
        "environment": environment,
        "complete": not missing,
        "missing": missing,
        "entries": entries,
    }


def render_markdown(manifest: dict[str, Any]) -> str:
    lines = [
        "# AIQE V1.6.2 Release Evidence Manifest",
        "",
        "> 本文件由 `python scripts/aiqe/build_evidence_manifest.py --write` 生成，禁止手工编辑。",
        "",
        f"- commit_sha: `{manifest['commit_sha']}`",
        f"- workflow_run_id: `{manifest['workflow_run_id']}`",
        f"- environment: `{manifest['environment']}`",
        f"- complete: **{manifest['complete']}**",
        "",
        "| Kind | Path | Status | SHA256 | Size | Job |",
        "|---|---|---|---|---:|---|",
    ]
    for item in manifest["entries"]:
        digest = (item["sha256"] or "—")[:16]
        lines.append(
            f"| {item['kind']} | `{item['path']}` | {item['status']} | {digest} | "
            f"{item['size_bytes'] if item['size_bytes'] is not None else '—'} | {item['job']} |"
        )
    if manifest["missing"]:
        lines.extend(["", "## Missing", ""])
        lines.extend(f"- `{path}`" for path in manifest["missing"])
    lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
        except (AttributeError, ValueError):  # pragma: no cover
            pass
    parser = argparse.ArgumentParser(description="Release Evidence Manifest")
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument("--commit-sha", required=True)
    parser.add_argument("--workflow-run-id", default="")
    parser.add_argument("--environment", default="")
    parser.add_argument("--output", default="")
    parser.add_argument("--markdown", default="")
    parser.add_argument("--require-complete", action="store_true")
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    manifest = build_manifest(
        root,
        commit_sha=args.commit_sha,
        workflow_run_id=args.workflow_run_id,
        environment=args.environment,
    )
    output = Path(args.output) if args.output else root / "work-logs/evidence/aiqe-v16/evidence-manifest.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    if args.markdown:
        markdown = Path(args.markdown)
        markdown.parent.mkdir(parents=True, exist_ok=True)
        markdown.write_text(render_markdown(manifest) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"complete": manifest["complete"], "missing": len(manifest["missing"])}))
    if args.require_complete and not manifest["complete"]:
        for path in manifest["missing"]:
            print(f"::error::[evidence-manifest] 缺少证据: {path}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
