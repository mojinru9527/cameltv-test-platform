"""v1.5 §06 REST 契约：新增能力 API 的端到端冒烟（AUD-004/013/014/015/017/018/019/020）。"""
from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.aiqe.models.run import TestRun
from app.models.project import Project, ProjectMember
from app.models.rbac import Role
from app.models.user import User

BASE = "/api/v1/aiqe"


def _seed(db: Session) -> None:
    role = Role(code="tester", name="测试", data_scope="project")
    db.add(role)
    db.flush()
    db.add_all(
        [
            User(id=1, username="cap", password="x", nickname="C", email="c@c.local", status=1),
            Project(id=1, code="cap-proj", name="Cap", owner_id=1, status=1),
        ]
    )
    db.flush()
    db.add(ProjectMember(project_id=1, user_id=1, role_id=role.id))
    db.commit()


@pytest.fixture()
def api(db_session: Session) -> Iterator[TestClient]:
    _seed(db_session)
    from app.core.db import get_db
    from app.core.deps import CurrentUser, get_current_user
    from app.main import app

    perms = ["menu:aiqe_runs", "defect:list", "defect:update", "aiqe:learning:approve"]

    def _db():
        yield db_session

    def _user():
        return CurrentUser(
            user=db_session.get(User, 1),
            permissions=perms,
            project_id=1,
            system_permissions=perms,
        )

    app.dependency_overrides[get_db] = _db
    app.dependency_overrides[get_current_user] = _user
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


def _contract(api: TestClient, *, oracle: bool = True) -> dict:
    resp = api.post(
        f"{BASE}/contracts",
        json={
            "requirement_id": "REQ-API-1",
            "title": "赛事发布后可见直播",
            "business_goal": "发布即播",
            "source_refs": ["prd:spec.md#直播"],
            "acceptance_criteria": [
                {
                    "ac_id": "AC-001",
                    "given": "管理员登录",
                    "when": "发布赛事",
                    "then": ["用户端出现直播入口"],
                    "priority": "P0",
                    "oracle_type": "product_rule" if oracle else "",
                    "oracle_ref": "PRD#1" if oracle else "",
                    "platforms": ["web_desktop"],
                }
            ],
        },
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]


def _approved_contract(api: TestClient) -> dict:
    contract = _contract(api)
    assert api.post(
        f"{BASE}/contracts/{contract['id']}/transition", json={"target": "REVIEW_REQUIRED"}
    ).status_code == 200
    assert api.post(
        f"{BASE}/contracts/{contract['id']}/approve-ac", json={"ac_id": "AC-001"}
    ).status_code == 200
    approved = api.post(
        f"{BASE}/contracts/{contract['id']}/transition", json={"target": "APPROVED"}
    )
    assert approved.status_code == 200, approved.text
    frozen = api.post(
        f"{BASE}/contracts/{contract['id']}/transition", json={"target": "FROZEN"}
    )
    assert frozen.status_code == 200, frozen.text
    return frozen.json()["data"]


# ── 1. Contract / Case ──────────────────────────────────
def test_contract_lifecycle_and_invalid_source_ref(api: TestClient):
    bad = api.post(
        f"{BASE}/contracts",
        json={"requirement_id": "REQ-BAD", "title": "x", "source_refs": ["https://evil"]},
    )
    assert bad.status_code == 422

    contract = _approved_contract(api)
    assert contract["status"] == "FROZEN"
    assert contract["revision_checksum"].startswith("sha256:")
    assert contract["acceptance_criteria"][0]["approval_status"] == "APPROVED"

    detail = api.get(f"{BASE}/contracts/{contract['id']}")
    assert detail.status_code == 200


def test_p0_contract_without_oracle_cannot_be_approved(api: TestClient):
    contract = _contract(api, oracle=False)
    api.post(f"{BASE}/contracts/{contract['id']}/transition", json={"target": "REVIEW_REQUIRED"})
    resp = api.post(f"{BASE}/contracts/{contract['id']}/transition", json={"target": "APPROVED"})
    assert resp.status_code == 400
    assert "Oracle" in resp.json()["msg"]


def test_case_create_review_and_coverage(api: TestClient):
    contract = _approved_contract(api)
    case_payload = {
        "title": "直播入口可见",
        "priority": "P0",
        "contract_id": contract["id"],
        "contract_revision": contract["revision"],
        "covers_ac_ids": ["AC-001"],
        "preconditions": ["已发布"],
        "fixtures": ["match-1"],
        "cleanup": ["删除 fixture"],
        "platform_targets": ["web_desktop"],
        "oracle_type": "requirement_ac",
        "oracle_ref": "AC-001",
        "steps": [
            {
                "step_id": "S1",
                "driver": "playwright",
                "action": "open",
                "assertions": [{"operator": "exists", "expected": True}],
            }
        ],
    }
    created = api.post(f"{BASE}/cases", json=case_payload)
    assert created.status_code == 200, created.text
    case = created.json()["data"]
    assert case["automation_grade"] == "A"
    assert case["review_status"] == "DRAFT"

    coverage = api.get(f"{BASE}/contracts/{contract['id']}/coverage").json()["data"]
    assert coverage["coverage"]["AC-001"] == "PARTIAL"

    reviewed = api.post(
        f"{BASE}/cases/{case['case_id']}/review", json={"decision": "APPROVED"}
    )
    assert reviewed.status_code == 200, reviewed.text
    coverage = api.get(f"{BASE}/contracts/{contract['id']}/coverage").json()["data"]
    assert coverage["coverage"]["AC-001"] == "COVERED"


# ── 2. Experiments ─────────────────────────────────────
def test_experiment_create_launch_sync(api: TestClient, db_session: Session):
    baseline = TestRun(
        project_id=1,
        run_key="RUN-API-EXP",
        status="COMPLETED",
        outcome="FAIL",
        commit_sha="a" * 40,
        environment_snapshot_json={"contract_checksum": "c1"},
    )
    db_session.add(baseline)
    db_session.flush()
    db_session.commit()

    created = api.post(
        f"{BASE}/runs/{baseline.id}/experiments",
        json={
            "experiment_key": "E2",
            "change": {"fixture_namespace": "aiqe-exp-1"},
            "idempotency_key": "exp-api-1",
        },
    )
    assert created.status_code == 200, created.text
    experiment = created.json()["data"]
    assert experiment["status"] == "VALIDATED"
    assert experiment["verification_run_id"] is None

    launched = api.post(f"{BASE}/experiments/{experiment['id']}/launch")
    assert launched.status_code == 200, launched.text
    data = launched.json()["data"]
    assert data["verification_run_id"]
    assert data["status"] == "QUEUED"

    synced = api.post(f"{BASE}/experiments/{experiment['id']}/sync")
    assert synced.status_code == 200
    assert synced.json()["data"]["status"] in {"QUEUED", "UNKNOWN", "COMPLETED"}


def test_experiment_rejects_wrong_variable(api: TestClient, db_session: Session):
    baseline = TestRun(project_id=1, run_key="RUN-API-EXP2", status="COMPLETED")
    db_session.add(baseline)
    db_session.commit()
    resp = api.post(
        f"{BASE}/runs/{baseline.id}/experiments",
        json={
            "experiment_key": "E2",
            "change": {"feature_flag": "on"},
            "idempotency_key": "exp-api-2",
        },
    )
    assert resp.status_code == 400


# ── 3. Observations / Triage ───────────────────────────
def test_observations_and_triage_lifecycle(api: TestClient, db_session: Session):
    run = TestRun(project_id=1, run_key="RUN-API-OBS", status="COMPLETED", outcome="FAIL")
    db_session.add(run)
    db_session.commit()

    detected = api.post(
        f"{BASE}/runs/{run.id}/observations",
        json={"payload": {"ui": {"overlap_ratio": 0.95}}},
    )
    assert detected.status_code == 200, detected.text
    items = detected.json()["data"]["items"]
    assert items[0]["category"] == "UI_OVERLAY"
    assert items[0]["recommended_experiment"] == "E4"

    listed = api.get(f"{BASE}/runs/{run.id}/observations").json()["data"]["items"]
    assert len(listed) == len(items)

    triage = api.post(f"{BASE}/runs/{run.id}/triage")
    assert triage.status_code == 200
    triage_id = triage.json()["data"]["id"]
    assert api.post(
        f"{BASE}/triage/{triage_id}/transition", json={"target": "EVIDENCE_COLLECTED"}
    ).status_code == 200
    illegal = api.post(f"{BASE}/triage/{triage_id}/transition", json={"target": "ATTRIBUTED"})
    assert illegal.status_code == 400


# ── 4. Benchmark ───────────────────────────────────────
def test_benchmark_dataset_flow(api: TestClient):
    dataset = api.post(
        f"{BASE}/benchmarks/datasets", json={"dataset_key": "api-ds", "task_type": "learning"}
    )
    assert dataset.status_code == 200, dataset.text
    dataset_id = dataset.json()["data"]["id"]
    for index in range(10):
        added = api.post(
            f"{BASE}/benchmarks/datasets/{dataset_id}/samples",
            json={"sample_id": f"s-{index}", "golden_labels": ["A"], "labeler": "qa"},
        )
        assert added.status_code == 200, added.text
    frozen = api.post(f"{BASE}/benchmarks/datasets/{dataset_id}/freeze")
    assert frozen.status_code == 200, frozen.text
    data = frozen.json()["data"]
    assert data["sample_count"] == 10
    assert data["gate_eligible"] is False
    assert len(data["content_hash"]) == 64
    assert api.get(f"{BASE}/benchmarks/runs/unknown-run").status_code == 404


# ── 5. Impact ──────────────────────────────────────────
def test_impact_plan_with_identical_shas(api: TestClient):
    resp = api.post(
        f"{BASE}/impact/plan",
        json={"base_sha": "HEAD", "head_sha": "HEAD"},
    )
    # short/низкий SHA 校验：HEAD 不是十六进制 → 422
    assert resp.status_code == 422


def test_impact_plan_with_real_commit_range(api: TestClient, db_session: Session):
    import subprocess
    from pathlib import Path

    repo_root = Path(__file__).resolve().parents[3]
    head = subprocess.run(
        ["git", "-C", str(repo_root), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        check=False,
    ).stdout.strip()
    assert len(head) == 40, head
    resp = api.post(
        f"{BASE}/impact/plan", json={"base_sha": head, "head_sha": head}
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert data["base_sha"] == head
    assert data["changed_files"] == []
    assert data["mandatory_case_ids"] == []


# ── 6. Platform ────────────────────────────────────────
def test_platform_binding_preflight_matrix(api: TestClient):
    binding = api.post(
        f"{BASE}/platforms/bindings",
        json={"target_type": "AC", "target_id": "AC-001", "platform_id": "native_ios"},
    )
    assert binding.status_code == 400  # AC 不存在，先创建契约再绑定

    matrix = api.get(f"{BASE}/platforms/matrix")
    assert matrix.status_code == 200
    data = matrix.json()["data"]
    assert len(data["platforms"]) == 9
    assert data["unverified_platforms"]

    preflight = api.post(f"{BASE}/platforms/preflight", json={"platforms": ["native_ios"]})
    assert preflight.status_code == 200
    assert preflight.json()["data"]["allowed"] is False
    assert preflight.json()["data"]["blockers"][0]["code"] == "PLATFORM_UNAVAILABLE"


def test_platform_binding_with_existing_ac(api: TestClient):
    contract = _approved_contract(api)
    binding = api.post(
        f"{BASE}/platforms/bindings",
        json={"target_type": "AC", "target_id": "AC-001", "platform_id": "web_desktop"},
    )
    assert binding.status_code == 200, binding.text
    assert binding.json()["data"]["capability_status"] == "UNAVAILABLE"
    assert contract["status"] == "FROZEN"


# ── 7. Agent task plan ─────────────────────────────────
def test_agent_task_plan(api: TestClient):
    resp = api.post(f"{BASE}/agent-tasks", json={"goal": "分析体育赛事需求并准备测试"})
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert data["a0_status"] == "COMPLETED"
    keys = [task["agent_key"] for task in data["tasks"]]
    assert keys.index("A1") < keys.index("A2") < keys.index("A3")
    assert data["a0_output"]["note"].startswith("A0 完成只代表")
