"""AUD-017：A5 变更影响图验收测试（真实 git diff + 强制集合不可删）。

对应 v1.5 §03 AUD-017「验收」：
- 真实 base/head commit diff → changed file/symbol/route/migration/component；
- 修改共享组件后能找出关联 Case，并且每条候选都有 trace path 与 reason；
- 强制集合（直接失败 + 合约变更覆盖的 P0 Case）由后端计算，AI 不能删除；
- A5 返回不存在的 Case ID 时后端拒绝。
"""
from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
from sqlalchemy import select

from app.aiqe.models.contract import AcceptanceCriterion, AiqeTestCase, RequirementContract
from app.aiqe.services.impact_service import (
    ImpactError,
    build_impact_plan,
    collect_changes,
    component_of,
    diff_digest,
    extract_python_symbols,
    extract_routes,
    extract_ts_symbols,
    load_git_diff,
    merge_ai_plan,
    persist_edges,
)
from app.models.impact_edge import ImpactEdge


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    assert result.returncode == 0, result.stderr
    return result.stdout.strip()


@pytest.fixture()
def repo(tmp_path):
    path = tmp_path / "repo"
    path.mkdir()
    _git(path, "init", "-q")
    _git(path, "config", "user.email", "qa@test.local")
    _git(path, "config", "user.name", "QA")
    (path / "app").mkdir()
    (path / "app" / "auth.py").write_text(
        "def login():\n    return 'ok'\n", encoding="utf-8"
    )
    _git(path, "add", ".")
    _git(path, "commit", "-q", "-m", "base")
    base = _git(path, "rev-parse", "HEAD")
    (path / "app" / "auth.py").write_text(
        "def login():\n    return 'ok'\n\n\ndef logout():\n    return 'bye'\n",
        encoding="utf-8",
    )
    (path / "app" / "api.py").write_text(
        "from fastapi import APIRouter\nrouter = APIRouter()\n\n"
        "@router.get('/sports/matches')\ndef list_matches():\n    return []\n",
        encoding="utf-8",
    )
    _git(path, "add", ".")
    _git(path, "commit", "-q", "-m", "change")
    head = _git(path, "rev-parse", "HEAD")
    return path, base, head


# ── 1. diff / symbol / route ────────────────────────────
def test_git_diff_reports_changed_files(repo):
    path, base, head = repo
    files = load_git_diff(str(path), base, head)
    by_path = {item.path: item for item in files}
    assert "app/auth.py" in by_path
    assert by_path["app/auth.py"].added >= 4
    assert "app/api.py" in by_path


def test_diff_requires_real_sha(repo):
    path, base, head = repo
    with pytest.raises(ImpactError):
        load_git_diff(str(path), "abc", head)
    with pytest.raises(ImpactError):
        load_git_diff(str(path / "missing"), base, head)


def test_symbols_and_routes_extraction():
    assert extract_python_symbols("def a():\n    pass\n\nclass B:\n    pass\n") == ["B", "a"]
    ts = "export function Foo() {}\nexport const Bar = () => {};\n"
    assert extract_ts_symbols(ts) == ["Bar", "Foo"]
    route_source = "@router.post('/orders')\ndef create():\n    pass\n"
    assert extract_routes(route_source) == ["POST /orders"]


def test_component_mapping_is_deterministic():
    assert component_of("test-platform-v2/backend/app/services/execution.py") == "execution:service"
    assert component_of("test-platform-v2/backend/app/api/v1/sports.py") == "sports:api"
    assert component_of("test-platform-v2/frontend/src/pages/runs/index.tsx") == "runs:ui"
    assert component_of("test-platform-v2/backend/alembic/versions/20260101_x.py") == "20260101_x:migration"


def test_collect_changes_builds_symbols_routes_components(repo):
    path, base, head = repo
    files, symbols, routes, _migrations, components = collect_changes(str(path), base, head)
    assert files
    assert "logout" in symbols.get("app/auth.py", [])
    assert "GET /sports/matches" in routes
    assert "auth:module" in components


# ── 2. 强制集合 + AI 不可删除 ───────────────────────────
def _seed_contract_cases(db):
    contract = RequirementContract(
        project_id=1,
        requirement_id="REQ-SPORT-9",
        revision=1,
        title="赛事发布",
        business_goal="发布即播",
        status="APPROVED",
        source_refs_json=["prd:spec.md#直播"],
    )
    db.add(contract)
    db.flush()
    db.add(
        AcceptanceCriterion(
            contract_id=contract.id,
            ac_id="AC-900",
            given="g",
            when="w",
            then_json=["t"],
            priority="P0",
            oracle_type="product_rule",
            oracle_ref="PRD#1",
        )
    )
    db.add_all(
        [
            AiqeTestCase(
                project_id=1,
                case_id="TC-P0-1",
                title="发布后直播入口可见",
                priority="P0",
                covers_ac_ids_json=["AC-900"],
                contract_id=contract.id,
                contract_revision=1,
                automation_grade="A",
                review_status="REVIEWED",
                steps_json=[],
                dedupe_key="k1",
            ),
            AiqeTestCase(
                project_id=1,
                case_id="TC-P2-1",
                title="后台列表样式",
                priority="P2",
                covers_ac_ids_json=[],
                contract_id=contract.id,
                contract_revision=1,
                automation_grade="B",
                review_status="REVIEWED",
                steps_json=[],
                dedupe_key="k2",
            ),
            AiqeTestCase(
                project_id=1,
                case_id="TC-OTHER-1",
                title="无关用例",
                priority="P3",
                covers_ac_ids_json=[],
                contract_id=None,
                automation_grade="B",
                review_status="REVIEWED",
                steps_json=[],
                dedupe_key="k3",
            ),
        ]
    )
    db.commit()
    return contract


def test_impact_plan_mandatory_and_candidates(db_session, repo):
    path, base, head = repo
    contract = _seed_contract_cases(db_session)
    plan = build_impact_plan(
        db_session,
        project_id=1,
        base_sha=base,
        head_sha=head,
        repo_path=str(path),
        failed_case_ids=["TC-OTHER-1"],
        changed_contract_ids=[contract.id],
    )
    # 直接失败 + 合约变更覆盖的 P0 都进入强制集合
    assert set(plan.mandatory_case_ids) == {"TC-OTHER-1", "TC-P0-1"}
    candidate_ids = {item["case_id"] for item in plan.candidates}
    assert "TC-P2-1" in candidate_ids
    for item in plan.candidates:
        assert item["reason"]
        assert "→" in item["trace_path"]
    assert plan.changed_files and plan.components
    assert diff_digest(plan)


def test_ai_cannot_remove_mandatory_or_invent_case_ids(db_session, repo):
    path, base, head = repo
    contract = _seed_contract_cases(db_session)
    plan = build_impact_plan(
        db_session,
        project_id=1,
        base_sha=base,
        head_sha=head,
        repo_path=str(path),
        changed_contract_ids=[contract.id],
    )
    known = {"TC-P0-1", "TC-P2-1", "TC-OTHER-1"}
    with pytest.raises(ImpactError):
        merge_ai_plan(
            plan,
            ["TC-P2-1"],
            known_case_ids=known,
            excluded_case_ids=["TC-P0-1"],
        )
    with pytest.raises(ImpactError):
        merge_ai_plan(plan, ["TC-NOT-EXIST"], known_case_ids=known)
    merged = merge_ai_plan(plan, ["TC-P2-1"], known_case_ids=known)
    final_ids = {item["case_id"] for item in merged.candidates}
    assert {"TC-P0-1", "TC-P2-1"} <= final_ids
    mandatory_entry = next(item for item in merged.candidates if item["case_id"] == "TC-P0-1")
    assert mandatory_entry["reason"] == "MANDATORY"


def test_edges_persisted_idempotently(db_session, repo):
    path, base, head = repo
    contract = _seed_contract_cases(db_session)
    plan = build_impact_plan(
        db_session,
        project_id=1,
        base_sha=base,
        head_sha=head,
        repo_path=str(path),
        changed_contract_ids=[contract.id],
    )
    persist_edges(db_session, project_id=1, version="v1", plan=plan)
    persist_edges(db_session, project_id=1, version="v1", plan=plan)
    db_session.commit()
    rows = list(db_session.scalars(select(ImpactEdge)))
    keys = {(row.source_ref, row.target_ref, row.kind, row.version) for row in rows}
    assert len(keys) == len(rows)  # 同 key 幂等，不重复
    assert any(row.kind == "changed" for row in rows)
    assert any(row.kind in {"covers", "depends"} for row in rows)
