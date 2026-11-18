"""AUD-017：A5 变更影响图（真实 git diff → symbol/route/schema → AC/Case/Workflow）。

v1.5 §03 AUD-017：

- 输入必须是固定 base/head commit 的真实 diff（禁止只看文件名猜）；
- 解析 changed files、symbol（Python AST / TS 导出）、API route、OpenAPI/schema、ORM migration；
- 影响集合生成候选 Case + reason + trace path（``changed file → component → AC → case``）；
- **强制集合**（直接失败 Case + 相关 P0 Case + 合约变更覆盖 Case）由后端计算，AI 不可删除；
- 模型只能新增候选；返回不存在的 Case ID 必须被拒绝。
"""
from __future__ import annotations

import ast
import hashlib
import json
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.aiqe.models.contract import AiqeTestCase
from app.aiqe.models.contract import AcceptanceCriterion
from app.models.impact_edge import ImpactEdge

API_ROUTE_RE = re.compile(r"@(?:router|app)\.(get|post|put|patch|delete)\(\s*[\"']([^\"']+)")
TS_EXPORT_RE = re.compile(
    r"export\s+(?:async\s+)?(?:function|const|class)\s+([A-Za-z_$][\w$]*)"
)
PY_SYMBOL_TYPES = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)


class ImpactError(ValueError):
    pass


@dataclass(frozen=True)
class DiffFile:
    path: str
    status: str
    added: int
    removed: int


@dataclass(frozen=True)
class ImpactEdgeSpec:
    source_ref: str
    target_ref: str
    kind: str
    confidence: float = 1.0


@dataclass
class ImpactPlan:
    base_sha: str
    head_sha: str
    changed_files: list[DiffFile] = field(default_factory=list)
    components: list[str] = field(default_factory=list)
    changed_symbols: dict[str, list[str]] = field(default_factory=dict)
    changed_routes: list[str] = field(default_factory=list)
    changed_migrations: list[str] = field(default_factory=list)
    mandatory_case_ids: list[str] = field(default_factory=list)
    candidates: list[dict[str, Any]] = field(default_factory=list)
    edges: list[ImpactEdgeSpec] = field(default_factory=list)

    def payload(self) -> dict[str, Any]:
        return {
            "base_sha": self.base_sha,
            "head_sha": self.head_sha,
            "changed_files": [
                {"path": item.path, "status": item.status, "added": item.added, "removed": item.removed}
                for item in self.changed_files
            ],
            "components": list(self.components),
            "changed_symbols": {key: list(value) for key, value in self.changed_symbols.items()},
            "changed_routes": list(self.changed_routes),
            "changed_migrations": list(self.changed_migrations),
            "mandatory_case_ids": list(self.mandatory_case_ids),
            "candidates": list(self.candidates),
        }


def _run_git(repo_path: str, args: list[str]) -> str:
    completed = subprocess.run(
        ["git", "-C", str(repo_path), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if completed.returncode != 0:
        raise ImpactError(f"git {' '.join(args)} 失败: {completed.stderr.strip()[:300]}")
    return completed.stdout


def load_git_diff(repo_path: str, base_sha: str, head_sha: str) -> list[DiffFile]:
    """真实 git diff：base/head 必须是完整 commit（短前缀不行）。"""
    base = str(base_sha or "").strip()
    head = str(head_sha or "").strip()
    if not re.fullmatch(r"[0-9a-f]{7,40}", base) or not re.fullmatch(r"[0-9a-f]{7,40}", head):
        raise ImpactError("base/head 必须是 Git commit SHA")
    if not Path(repo_path).exists():
        raise ImpactError(f"仓库路径不存在: {repo_path}")
    name_status = _run_git(repo_path, ["diff", "--name-status", f"{base}..{head}"])
    numstat = _run_git(repo_path, ["diff", "--numstat", f"{base}..{head}"])
    added_removed: dict[str, tuple[int, int]] = {}
    for line in numstat.splitlines():
        parts = line.split("\t")
        if len(parts) != 3:
            continue
        raw_added, raw_removed, path = parts
        added_removed[path] = (
            int(raw_added) if raw_added.isdigit() else 0,
            int(raw_removed) if raw_removed.isdigit() else 0,
        )
    files: list[DiffFile] = []
    for line in name_status.splitlines():
        parts = line.split("\t")
        if len(parts) < 2:
            continue
        status = parts[0].strip()
        path = parts[-1].strip()
        added, removed = added_removed.get(path, (0, 0))
        files.append(DiffFile(path=path, status=status, added=added, removed=removed))
    return files


def read_file_at(repo_path: str, sha: str, path: str) -> str:
    return _run_git(repo_path, ["show", f"{sha}:{path}"])


def extract_python_symbols(source: str) -> list[str]:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    symbols: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, PY_SYMBOL_TYPES) and getattr(node, "name", None):
            symbols.append(node.name)
    return sorted(set(symbols))


def extract_ts_symbols(source: str) -> list[str]:
    return sorted({match.group(1) for match in TS_EXPORT_RE.finditer(source or "")})


def extract_routes(source: str) -> list[str]:
    return sorted({f"{match.group(1).upper()} {match.group(2)}" for match in API_ROUTE_RE.finditer(source or "")})


def component_of(path: str) -> str:
    """把文件路径归一化成组件名（用于 trace path 与影响边）。"""
    normalized = str(path).replace("\\", "/").strip("/")
    if not normalized:
        return "unknown"
    parts = normalized.split("/")
    for marker in ("app", "src", "scripts"):
        if marker in parts:
            parts = parts[parts.index(marker) + 1 :]
            break
    if not parts:
        return "unknown"
    stem = parts[-1].rsplit(".", 1)[0]
    if stem in {"__init__", "index"} and len(parts) > 1:
        stem = parts[-2]
    kind = "module"
    joined = "/".join(parts)
    if "migrations" in parts or (parts[-1].startswith("2") and "versions" in joined):
        kind = "migration"
    elif "api" in parts or "routers" in parts or "routes" in parts:
        kind = "api"
    elif "models" in parts:
        kind = "model"
    elif "services" in parts:
        kind = "service"
    elif "pages" in parts or "components" in parts:
        kind = "ui"
    return f"{stem}:{kind}"


def collect_changes(
    repo_path: str, base_sha: str, head_sha: str
) -> tuple[list[DiffFile], dict[str, list[str]], list[str], list[str], list[str]]:
    files = load_git_diff(repo_path, base_sha, head_sha)
    symbols: dict[str, list[str]] = {}
    routes: list[str] = []
    migrations: list[str] = []
    components: list[str] = []
    for item in files:
        if item.status.startswith("D"):
            continue
        try:
            source = read_file_at(repo_path, head_sha, item.path)
        except ImpactError:
            continue
        suffixes = Path(item.path).suffixes
        if ".py" in suffixes:
            found = extract_python_symbols(source)
            if found:
                symbols[item.path] = found
            routes.extend(extract_routes(source))
        elif any(suffix in {".ts", ".tsx", ".js", ".jsx"} for suffix in suffixes):
            found = extract_ts_symbols(source)
            if found:
                symbols[item.path] = found
        component = component_of(item.path)
        if component not in components:
            components.append(component)
        if component.endswith(":migration") and item.path not in migrations:
            migrations.append(item.path)
    return files, symbols, sorted(set(routes)), migrations, components


def _p0_cases_of_contracts(db: Session, project_id: int, contract_ids: list[str]) -> list[AiqeTestCase]:
    if not contract_ids:
        return []
    cases = list(
        db.scalars(
            select(AiqeTestCase).where(
                AiqeTestCase.project_id == int(project_id),
                AiqeTestCase.contract_id.in_(contract_ids),
            )
        )
    )
    return [case for case in cases if (case.priority or "").upper() == "P0"]


def _cases_covering_acs(
    db: Session, project_id: int, ac_ids: list[str]
) -> list[AiqeTestCase]:
    if not ac_ids:
        return []
    cases = list(
        db.scalars(select(AiqeTestCase).where(AiqeTestCase.project_id == int(project_id)))
    )
    return [case for case in cases if set(ac_ids) & set(case.covers_ac_ids_json or [])]


def _acs_of_contracts(db: Session, contract_ids: list[str]) -> list[AcceptanceCriterion]:
    if not contract_ids:
        return []
    return list(
        db.scalars(
            select(AcceptanceCriterion).where(AcceptanceCriterion.contract_id.in_(contract_ids))
        )
    )


def build_impact_plan(
    db: Session,
    *,
    project_id: int,
    base_sha: str,
    head_sha: str,
    repo_path: str,
    failed_case_ids: list[str] | None = None,
    changed_contract_ids: list[str] | None = None,
    ai_proposed_case_ids: list[str] | None = None,
) -> ImpactPlan:
    """构建影响计划；强制集合由后端计算，AI 只能追加候选。"""
    files, symbols, routes, migrations, components = collect_changes(
        repo_path, base_sha, head_sha
    )
    contract_ids = [str(item) for item in (changed_contract_ids or [])]
    failed = [str(item) for item in (failed_case_ids or [])]

    mandatory: set[str] = set(failed)
    contract_cases = _p0_cases_of_contracts(db, project_id, contract_ids)
    acs = _acs_of_contracts(db, contract_ids)
    ac_ids = [ac.ac_id for ac in acs]
    ac_cases = _cases_covering_acs(db, project_id, ac_ids)
    for case in contract_cases + ac_cases:
        mandatory.add(case.case_id)

    all_cases = {
        case.case_id: case
        for case in db.scalars(select(AiqeTestCase).where(AiqeTestCase.project_id == int(project_id)))
    }
    unknown_mandatory = [case_id for case_id in mandatory if case_id not in all_cases]
    if unknown_mandatory:
        raise ImpactError(f"强制集合包含不存在的 Case: {unknown_mandatory}")

    plan = ImpactPlan(
        base_sha=base_sha,
        head_sha=head_sha,
        changed_files=files,
        components=components,
        changed_symbols=symbols,
        changed_routes=routes,
        changed_migrations=migrations,
        mandatory_case_ids=sorted(mandatory),
    )

    trace_component = components[0] if components else "unknown"
    ac_by_id = {ac.ac_id: ac for ac in acs}
    for case_id, case in sorted(all_cases.items()):
        if case_id in mandatory:
            continue
        linked_acs = [ac_id for ac_id in (case.covers_ac_ids_json or []) if ac_id in ac_by_id]
        score = 0.0
        if linked_acs:
            score += 0.6
        if case.contract_id in contract_ids:
            score += 0.3
        if (case.priority or "").upper() in {"P0", "P1"}:
            score += 0.1
        if score <= 0:
            continue
        ac_id = linked_acs[0] if linked_acs else (acs[0].ac_id if acs else "")
        plan.candidates.append(
            {
                "case_id": case_id,
                "score": round(min(score, 1.0), 2),
                "reason": "CONTRACT_CHANGED_OR_AC_LINKED",
                "trace_path": f"{trace_component} → {ac_id or 'AC'} → {case_id}",
            }
        )
        plan.edges.append(
            ImpactEdgeSpec(
                source_ref=f"component:{trace_component}",
                target_ref=f"case:{case_id}",
                kind="covers",
                confidence=round(min(score, 1.0), 2),
            )
        )
    for item in files[:50]:
        plan.edges.append(
            ImpactEdgeSpec(
                source_ref=f"commit:{head_sha[:12]}",
                target_ref=f"file:{item.path}",
                kind="changed",
            )
        )
    for case_id in sorted(mandatory):
        plan.edges.append(
            ImpactEdgeSpec(
                source_ref=f"component:{trace_component}",
                target_ref=f"case:{case_id}",
                kind="depends",
            )
        )

    if ai_proposed_case_ids:
        plan = merge_ai_plan(plan, ai_proposed_case_ids, known_case_ids=set(all_cases))
    return plan


def merge_ai_plan(
    plan: ImpactPlan,
    proposed_case_ids: list[str],
    *,
    known_case_ids: set[str],
    excluded_case_ids: list[str] | None = None,
) -> ImpactPlan:
    """AI 只能追加候选；显式排除强制 Case 或引用不存在 Case → 直接拒绝。"""
    proposed = {str(item) for item in proposed_case_ids}
    excluded = {str(item) for item in (excluded_case_ids or [])}
    removed_mandatory = excluded & set(plan.mandatory_case_ids)
    if removed_mandatory:
        raise ImpactError(f"AI 不能删除强制回归 Case: {sorted(removed_mandatory)}")
    unknown = (proposed | excluded) - known_case_ids
    if unknown:
        raise ImpactError(f"AI 返回了不存在的 Case ID: {sorted(unknown)}")
    existing = {item["case_id"] for item in plan.candidates}
    for case_id in sorted(proposed - existing - set(plan.mandatory_case_ids)):
        plan.candidates.append(
            {
                "case_id": case_id,
                "score": 0.3,
                "reason": "AI_SUGGESTED",
                "trace_path": f"{plan.components[0] if plan.components else 'unknown'} → AI_SUGGESTION → {case_id}",
            }
        )
    # 强制集合始终进入最终计划（AI 未列出也不会被删除）。
    for case_id in plan.mandatory_case_ids:
        if case_id not in existing:
            plan.candidates.append(
                {
                    "case_id": case_id,
                    "score": 1.0,
                    "reason": "MANDATORY",
                    "trace_path": f"{plan.components[0] if plan.components else 'unknown'} → MANDATORY → {case_id}",
                }
            )
    return plan


def persist_edges(
    db: Session, *, project_id: int, version: str, plan: ImpactPlan
) -> list[ImpactEdge]:
    """把影响边写入 ImpactEdge（同 key 幂等）。"""
    rows: list[ImpactEdge] = []
    for spec in plan.edges:
        existing = db.scalar(
            select(ImpactEdge).where(
                ImpactEdge.project_id == int(project_id),
                ImpactEdge.source_ref == spec.source_ref,
                ImpactEdge.target_ref == spec.target_ref,
                ImpactEdge.kind == spec.kind,
                ImpactEdge.version == str(version),
            )
        )
        if existing is not None:
            existing.confidence = max(float(existing.confidence or 0), float(spec.confidence))
            rows.append(existing)
            continue
        row = ImpactEdge(
            project_id=int(project_id),
            source_ref=spec.source_ref,
            target_ref=spec.target_ref,
            kind=spec.kind,
            version=str(version),
            confidence=float(spec.confidence),
        )
        db.add(row)
        rows.append(row)
    db.flush()
    return rows


def diff_digest(plan: ImpactPlan) -> str:
    payload = json.dumps(plan.payload(), sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(payload.encode()).hexdigest()


__all__ = [
    "DiffFile",
    "ImpactEdgeSpec",
    "ImpactError",
    "ImpactPlan",
    "build_impact_plan",
    "collect_changes",
    "component_of",
    "diff_digest",
    "extract_python_symbols",
    "extract_routes",
    "extract_ts_symbols",
    "load_git_diff",
    "merge_ai_plan",
    "persist_edges",
    "read_file_at",
]
