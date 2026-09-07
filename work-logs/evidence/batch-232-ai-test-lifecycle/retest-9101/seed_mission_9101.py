"""Rebuild local QA Mission 9101 with traceable Test5 execution facts."""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[3]
sys.path.insert(0, str(REPO_ROOT / "test-platform-v2/backend"))

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.models.defect import Defect
from app.models.environment import Environment
from app.models.version_task import VersionTask
from app.modules.aitde.ai_closed_loop.models import ScenarioGapCandidate
from app.modules.aitde.ai_ops.models import AIOperationRecord
from app.modules.aitde.continuous.models import (
    BuildObservation,
    CampaignScenario,
    EnvironmentFingerprint,
    ExecutionCampaign,
    QualityGatePolicy,
    QualityGateResultRecord,
)
from app.modules.aitde.contract.models import TestContract, TestContractVersion
from app.modules.aitde.evidence.manifest import build_manifest, manifest_hash
from app.modules.aitde.evidence.service import store_artifact
from app.modules.aitde.execution.models import (
    AssertionResult,
    EnvironmentSnapshot,
    EvidenceArtifact,
    ExecutionRun,
    ExecutionStep,
    ReplayManifest,
    ScenarioAdapter,
)
from app.modules.aitde.mission.lifecycle import build_lifecycle
from app.modules.aitde.mission.models import Mission
from app.modules.aitde.scenario.models import TestOracle, TestScenario, TestScenarioVersion
from app.modules.aitde.scope.models import Ambiguity, ScopeItem, TestIntent
from app.modules.aitde.smart_regression.models import (
    ChangeItem,
    ChangeSet,
    ImpactAnalysisRun,
    ImpactResult,
    LineageEdge,
    RegressionSelection,
    RegressionSelectionItem,
)
from app.modules.aitde.sources.models import MissionSourceLink, SourceArtifact, SourceFragment


MISSION_ID = 9101
PROJECT_ID = 1
VERSION_TASK_ID = 9001
TARGET_PAGE = "https://camel-bball-test5.elelive.cn/basketball"
TARGET_API = (
    "https://camel-test5.elelive.cn/basketball-service/ee/sports_live/"
    "home_match?day=20260907&sportType=basketball"
)
DB_PATH = REPO_ROOT / "test-platform-v2/backend/data/platform-batch-232-ai-test-lifecycle.db"


def dump(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def digest(value: object) -> str:
    raw = value if isinstance(value, bytes) else dump(value).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def delete_where(db: Session, model: type, **filters: object) -> None:
    db.query(model).filter_by(**filters).delete(synchronize_session=False)


def clear_existing_facts(db: Session, mission: Mission) -> None:
    scenario_ids = [row.id for row in db.query(TestScenario).filter_by(mission_id=mission.id)]
    scenario_version_ids = [
        row.id
        for row in db.query(TestScenarioVersion).filter(
            TestScenarioVersion.scenario_id.in_(scenario_ids or [-1])
        )
    ]
    run_ids = [row.id for row in db.query(ExecutionRun).filter_by(mission_id=mission.id)]
    source_ids = [
        row.artifact_id for row in db.query(MissionSourceLink).filter_by(mission_id=mission.id)
    ]
    contract_ids = [row.id for row in db.query(TestContract).filter_by(mission_id=mission.id)]
    change_set_ids = [row.id for row in db.query(ChangeSet).filter_by(mission_id=mission.id)]
    impact_run_ids = [row.id for row in db.query(ImpactAnalysisRun).filter_by(mission_id=mission.id)]
    campaign_ids = [row.id for row in db.query(ExecutionCampaign).filter_by(mission_id=mission.id)]
    selection_ids = [row.id for row in db.query(RegressionSelection).filter_by(mission_id=mission.id)]

    db.query(RegressionSelectionItem).filter(
        RegressionSelectionItem.selection_id.in_(selection_ids or [-1])
    ).delete(synchronize_session=False)
    db.query(ImpactResult).filter(
        ImpactResult.impact_run_id.in_(impact_run_ids or [-1])
    ).delete(synchronize_session=False)
    db.query(ChangeItem).filter(ChangeItem.change_set_id.in_(change_set_ids or [-1])).delete(
        synchronize_session=False
    )
    db.query(CampaignScenario).filter(
        CampaignScenario.campaign_id.in_(campaign_ids or [-1])
    ).delete(synchronize_session=False)
    db.query(Defect).filter(Defect.aitde_run_id.in_(run_ids or [-1])).delete(
        synchronize_session=False
    )
    for model in (ReplayManifest, EvidenceArtifact, AssertionResult, ExecutionStep):
        db.query(model).filter(model.run_id.in_(run_ids or [-1])).delete(
            synchronize_session=False
        )
    db.query(ScenarioAdapter).filter(
        ScenarioAdapter.scenario_version_id.in_(scenario_version_ids or [-1])
    ).delete(synchronize_session=False)
    db.query(TestOracle).filter(
        TestOracle.scenario_version_id.in_(scenario_version_ids or [-1])
    ).delete(synchronize_session=False)
    db.query(TestScenarioVersion).filter(
        TestScenarioVersion.id.in_(scenario_version_ids or [-1])
    ).delete(synchronize_session=False)
    db.query(SourceFragment).filter(
        SourceFragment.artifact_id.in_(source_ids or [-1])
    ).delete(synchronize_session=False)
    db.query(TestContractVersion).filter(
        TestContractVersion.contract_id.in_(contract_ids or [-1])
    ).delete(synchronize_session=False)

    for model in (
        ScopeItem,
        Ambiguity,
        TestIntent,
        ExecutionRun,
        BuildObservation,
        ExecutionCampaign,
        QualityGateResultRecord,
        ChangeSet,
        ImpactAnalysisRun,
        LineageEdge,
        RegressionSelection,
        ScenarioGapCandidate,
        AIOperationRecord,
        TestContract,
        TestScenario,
        MissionSourceLink,
    ):
        delete_where(db, model, mission_id=mission.id)
    db.query(SourceArtifact).filter(SourceArtifact.id.in_(source_ids or [-1])).delete(
        synchronize_session=False
    )
    db.flush()


def add_ai_operation(db: Session, operation_type: str, result: dict) -> None:
    now = datetime.now()
    db.add(
        AIOperationRecord(
            project_id=PROJECT_ID,
            mission_id=MISSION_ID,
            operation_type=operation_type,
            status="SUCCEEDED",
            model_provider="tester-reviewed",
            model_name="deterministic-rebuild",
            model_config_hash=digest("batch-232"),
            prompt_version="batch-232-retest-v2",
            input_hash=digest({"mission_id": MISSION_ID, "operation": operation_type}),
            output_hash=digest(result),
            result_ref_json=dump(result),
            duration_ms=1,
            created_by=1,
            started_at=now,
            finished_at=now,
        )
    )


def add_run(
    db: Session,
    *,
    scenario: TestScenario,
    version: TestScenarioVersion,
    contract_version_id: int,
    environment_id: int,
    snapshot_id: int,
    outcome: str,
    steps: list[dict],
    assertions: list[dict],
    evidence_files: list[tuple[str, str, str]],
) -> ExecutionRun:
    now = datetime.now()
    adapter = ScenarioAdapter(
        scenario_id=scenario.id,
        scenario_version_id=version.id,
        adapter_type=version.case_type if version.case_type in {"API", "UI"} else "MANUAL",
        status="ACTIVE",
        source_asset_type="PLAYWRIGHT" if version.case_type != "API" else "HTTP",
        config_json=dump({"target": TARGET_PAGE if version.case_type != "API" else TARGET_API}),
        adapter_version="batch-232-retest-v2",
        created_by=1,
    )
    db.add(adapter)
    db.flush()
    run = ExecutionRun(
        project_id=PROJECT_ID,
        mission_id=MISSION_ID,
        scenario_id=scenario.id,
        scenario_version_id=version.id,
        contract_version_id=contract_version_id,
        adapter_id=adapter.id,
        environment_id=environment_id,
        environment_snapshot_id=snapshot_id,
        runtime_status="FINISHED",
        outcome=outcome,
        evidence_status="COMPLETE",
        trigger_type="MANUAL" if version.case_type == "FUNCTIONAL" else "SCHEDULED",
        started_at=now,
        finished_at=now,
        duration_ms=1000,
        created_by=1,
    )
    db.add(run)
    db.flush()

    step_rows: list[ExecutionStep] = []
    for sequence, item in enumerate(steps, start=1):
        row = ExecutionStep(
            run_id=run.id,
            sequence=sequence,
            step_key=item["name"],
            step_type=item.get("type", "ACTION"),
            status=item.get("status", "SUCCEEDED"),
            input_snapshot_json=dump(item.get("input", {})),
            output_snapshot_json=dump(item.get("output", {})),
            trace_id=f"b232-{version.case_type.lower()}-{sequence}",
            span_id=f"step-{sequence}",
            started_at=now,
            finished_at=now,
        )
        db.add(row)
        step_rows.append(row)
    db.flush()

    evidence_rows = []
    for evidence_type, filename, content_type in evidence_files:
        path = HERE / filename
        if not path.is_file() or path.stat().st_size == 0:
            raise RuntimeError(f"Missing evidence file: {path}")
        evidence_rows.append(
            store_artifact(
                db,
                project_id=PROJECT_ID,
                run_id=run.id,
                step_id=step_rows[-1].id,
                evidence_type=evidence_type,
                data=path.read_bytes(),
                content_type=content_type,
            )
        )
    db.flush()
    evidence_refs = [{"artifact_id": row.id} for row in evidence_rows]
    step_rows[-1].evidence_refs_json = dump(evidence_refs)

    assertion_rows: list[AssertionResult] = []
    for index, item in enumerate(assertions, start=1):
        row = AssertionResult(
            run_id=run.id,
            step_id=step_rows[-1].id,
            oracle_id=index,
            oracle_source_type="TEST_ORACLE",
            trust_status="TRUSTED",
            oracle_snapshot_json=dump({"name": item["name"]}),
            expected_json=dump(item["expected"]),
            actual_json=dump(item["actual"]),
            result=item["result"],
            reason_code="MATCH" if item["result"] == "PASS" else "RESOURCE_ERRORS_OBSERVED",
            evidence_refs_json=dump(evidence_refs),
            evaluated_at=now,
        )
        db.add(row)
        assertion_rows.append(row)
    db.flush()

    manifest = build_manifest(run, step_rows, assertion_rows, evidence_rows)
    db.add(
        ReplayManifest(
            run_id=run.id,
            schema_version="1.0",
            manifest_json=dump(manifest),
            manifest_hash=manifest_hash(manifest),
        )
    )
    return run


def main() -> None:
    engine = create_engine(f"sqlite:///{DB_PATH.as_posix()}")
    with Session(engine) as db:
        mission = db.get(Mission, MISSION_ID)
        if mission is None or mission.project_id != PROJECT_ID:
            raise RuntimeError("Mission 9101 was not found in project 1")
        clear_existing_facts(db, mission)

        task = db.get(VersionTask, VERSION_TASK_ID)
        if task is None:
            raise RuntimeError("VersionTask 9001 was not found")
        task.title = "体育平台 16.0.0 篮球多项目适配验收"
        task.version = "16.0.0"
        task.status = "executing"
        task.verdict = "blocked"
        task.summary = "Test5 已执行功能、接口和 UI 自动化；发现第三方登录与图片资源错误，待修复复验。"
        task.scope = dump({"mission_id": MISSION_ID, "target": TARGET_PAGE})
        task.risk = dump({"P2": ["Google 登录域名未授权", "部分图片代理/CDN 资源失败"]})

        environment = Environment(
            project_id=PROJECT_ID,
            name="体育平台 Test5",
            env_type="test",
            base_url=TARGET_PAGE,
            description="16.0.0 篮球多项目适配测试环境",
            is_production=False,
        )
        db.add(environment)
        db.flush()
        mission.title = "体育平台 16.0.0 篮球多项目适配"
        mission.version_label = "16.0.0"
        mission.version_task_id = task.id
        mission.default_environment_id = environment.id
        mission.status = "SCENARIO_READY"
        mission.acceptance_status = "FAIL"

        source_text = "\n".join(
            [
                "16.0.0 将篮球作为独立体育项目，入口为 /basketball。",
                "篮球首页必须展示直播赛事、Favorites、Competitions、Match Replays 与篮球新闻。",
                "篮球首页数据请求必须携带 sportType=basketball，并返回当日篮球分组数据。",
                "从 Competitions 进入篮球联赛详情后，URL、标题和内容必须保持篮球上下文。",
            ]
        )
        source = SourceArtifact(
            project_id=PROJECT_ID,
            source_type="REQUIREMENT",
            provider="batch-232-retest",
            name="体育平台 16.0.0 篮球多项目适配验收说明",
            uri=TARGET_PAGE,
            content_hash=digest(source_text.encode("utf-8")),
            version_label="16.0.0",
            parse_status="PARSED",
            normalized_text=source_text,
            metadata_json=dump({"target": TARGET_PAGE, "reviewed_by": "tester"}),
            created_by=1,
        )
        db.add(source)
        db.flush()
        db.add(
            MissionSourceLink(
                mission_id=mission.id,
                artifact_id=source.id,
                role="REQUIREMENT",
                is_primary=True,
                created_by=1,
            )
        )
        fragment_specs = [
            ("REQ-16-001", "篮球项目独立入口", "16.0.0 将篮球作为独立体育项目，入口为 /basketball。"),
            (
                "REQ-16-002",
                "篮球首页功能区",
                "篮球首页必须展示直播赛事、Favorites、Competitions、Match Replays 与篮球新闻。",
            ),
            (
                "REQ-16-003",
                "篮球数据接口隔离",
                "篮球首页数据请求必须携带 sportType=basketball，并返回当日篮球分组数据。",
            ),
            (
                "REQ-16-004",
                "篮球联赛详情上下文",
                "从 Competitions 进入篮球联赛详情后，URL、标题和内容必须保持篮球上下文。",
            ),
        ]
        fragments: list[SourceFragment] = []
        for sequence, (key, title, text) in enumerate(fragment_specs, start=1):
            row = SourceFragment(
                artifact_id=source.id,
                fragment_key=key,
                title=title,
                text=text,
                location_json=dump({"section": "16.0.0 篮球验收", "sequence": sequence}),
                content_hash=digest(text.encode("utf-8")),
                sequence=sequence,
            )
            db.add(row)
            fragments.append(row)
        db.flush()

        refs = [
            {"artifact_id": source.id, "fragment_id": fragment.id}
            for fragment in fragments
        ]
        scope_specs = [
            ("basketball-home", "篮球首页功能区", "FEATURE", "P1", refs[:2]),
            ("basketball-api", "篮球首页数据接口", "API", "P1", [refs[2]]),
            ("basketball-league", "篮球联赛详情导航", "BUSINESS_FLOW", "P1", [refs[3]]),
        ]
        for key, name, scope_type, risk, source_refs in scope_specs:
            db.add(
                ScopeItem(
                    mission_id=mission.id,
                    scope_key=key,
                    scope_type=scope_type,
                    name=name,
                    decision="INCLUDE",
                    test_depth="FULL",
                    risk_level=risk,
                    reason=f"16.0.0 新增篮球多项目能力：{name}",
                    ai_confidence=0.95,
                    review_status="APPROVED",
                    source_refs_json=dump(source_refs),
                    created_by_type="AI",
                    created_by=1,
                    reviewed_by=1,
                    reviewed_at=datetime.now(),
                )
            )
        db.add(
            TestIntent(
                mission_id=mission.id,
                intent_key="basketball-16-e2e",
                title="验证篮球独立项目从数据到页面的端到端一致性",
                business_goal="确保篮球入口、赛事数据、联赛导航和回放区域保持篮球上下文。",
                required_outcomes_json=dump(["首页功能可见", "接口返回篮球数据", "联赛导航正确"]),
                risk_level="P1",
                source_refs_json=dump(refs),
                review_status="APPROVED",
                created_by_type="AI",
                reviewed_by=1,
                reviewed_at=datetime.now(),
            )
        )

        contract_snapshot = {
            "schema_version": "1.0",
            "mission_id": mission.id,
            "scope_revision": "batch-232-retest-v2",
            "rules": [
                {
                    "rule_key": "basketball-route",
                    "title": "篮球独立入口",
                    "statement": "/basketball 必须展示篮球专属首页与内容模块。",
                    "risk_level": "P1",
                    "source_refs": refs[:2],
                },
                {
                    "rule_key": "basketball-api-isolation",
                    "title": "篮球接口隔离",
                    "statement": "首页赛事请求必须使用 sportType=basketball。",
                    "risk_level": "P1",
                    "source_refs": [refs[2]],
                },
                {
                    "rule_key": "basketball-league-context",
                    "title": "联赛导航保持篮球上下文",
                    "statement": "赛事列表进入联赛详情后 URL 与页面标题必须属于篮球。",
                    "risk_level": "P1",
                    "source_refs": [refs[3]],
                },
            ],
            "required_outcomes": [
                {
                    "outcome_key": "home-visible",
                    "statement": "Live Matches、Competitions、Match Replays 可见。",
                    "source_refs": [refs[1]],
                },
                {
                    "outcome_key": "api-valid",
                    "statement": "篮球接口 HTTP 和业务状态为 200，并返回当日分组。",
                    "source_refs": [refs[2]],
                },
                {
                    "outcome_key": "league-route-valid",
                    "statement": "可从 Competitions 进入篮球联赛详情。",
                    "source_refs": [refs[3]],
                },
            ],
        }
        contract = TestContract(
            mission_id=mission.id,
            name="16.0.0 篮球多项目验收契约",
            current_version_no=1,
            created_by=1,
        )
        db.add(contract)
        db.flush()
        contract_version = TestContractVersion(
            contract_id=contract.id,
            version_no=1,
            status="FROZEN",
            content_hash=digest(contract_snapshot),
            snapshot_json=dump(contract_snapshot),
            created_by_type="AI_REVIEWED",
            created_by=1,
            approved_by=1,
            approved_at=datetime.now(),
        )
        db.add(contract_version)
        db.flush()
        mission.current_contract_version_id = contract_version.id

        scenario_specs = [
            {
                "key": "BASKETBALL-FUNCTIONAL-001",
                "title": "篮球首页核心功能区展示",
                "type": "FUNCTIONAL",
                "role": "NEW",
                "module": "篮球/首页",
                "goal": "确认篮球独立入口具备直播、收藏、赛事、回放和新闻功能区。",
                "given": {"环境": "Test5", "入口": TARGET_PAGE},
                "when": {"action": "打开篮球首页并切换 Favorites 后返回 Live Matches"},
                "expected": {"篮球链接数": ">=5", "Match Replays": "可见", "Live Matches": "可见"},
                "refs": refs[:2],
            },
            {
                "key": "BASKETBALL-API-001",
                "title": "篮球首页赛事接口返回分组数据",
                "type": "API",
                "role": "CHANGED",
                "module": "篮球/赛事接口",
                "goal": "确认 sportType=basketball 的首页赛事接口返回当日篮球数据。",
                "given": {"环境": "Test5 API", "请求": TARGET_API},
                "when": {"action": "GET 首页篮球赛事接口"},
                "expected": {"HTTP 状态": 200, "业务状态": 200, "living_group": "数组"},
                "refs": [refs[2]],
            },
            {
                "key": "BASKETBALL-UI-001",
                "title": "从赛事列表进入 NBA 联赛详情",
                "type": "UI",
                "role": "NEW",
                "module": "篮球/联赛导航",
                "goal": "自动化验证篮球赛事导航和联赛详情上下文。",
                "given": {"环境": "Test5", "页面": TARGET_PAGE},
                "when": {"action": "点击 Competitions 并进入 National Basketball Association"},
                "expected": {"URL": "包含 /basketball/league/", "页面标题": "包含 Basketball"},
                "refs": [refs[3]],
            },
        ]
        scenario_rows: list[tuple[TestScenario, TestScenarioVersion]] = []
        for spec in scenario_specs:
            scenario = TestScenario(
                project_id=PROJECT_ID,
                mission_id=mission.id,
                scenario_key=spec["key"],
                current_version_no=1,
            )
            db.add(scenario)
            db.flush()
            version = TestScenarioVersion(
                scenario_id=scenario.id,
                version_no=1,
                contract_version_id=contract_version.id,
                title=spec["title"],
                business_goal=spec["goal"],
                case_type=spec["type"],
                requirement_role=spec["role"],
                module_key=spec["module"],
                priority="P1",
                risk_level="P1",
                given_model_json=dump(spec["given"]),
                when_model_json=dump(spec["when"]),
                expected_state_json=dump(spec["expected"]),
                source_refs_json=dump(spec["refs"]),
                review_status="APPROVED",
                content_hash=digest(spec),
                created_by_type="AI_REVIEWED",
                created_by=1,
                approved_by=1,
                approved_at=datetime.now(),
            )
            db.add(version)
            db.flush()
            db.add(
                TestOracle(
                    scenario_version_id=version.id,
                    oracle_key=f"{spec['key']}-EXPECTED",
                    oracle_type="UI" if spec["type"] != "API" else "API",
                    target_json=dump({"target": spec["module"]}),
                    operator="matches",
                    expected_value_json=dump(spec["expected"]),
                    source_type="REQUIREMENT_EXPLICIT",
                    source_refs_json=dump(spec["refs"]),
                    required=True,
                    confidence=1.0,
                    review_status="APPROVED",
                    created_by_type="AI_REVIEWED",
                    reviewed_by=1,
                    reviewed_at=datetime.now(),
                )
            )
            scenario_rows.append((scenario, version))

        fingerprint_value = digest(
            {"frontend": "16.0.0", "page": TARGET_PAGE, "api": TARGET_API, "date": "20260907"}
        )
        fingerprint = EnvironmentFingerprint(
            environment_id=environment.id,
            fingerprint_hash=fingerprint_value,
            build_label="sports-16.0.0-test5-20260907",
            components_json=dump(
                {"frontend": TARGET_PAGE, "api": "https://camel-test5.elelive.cn", "version": "16.0.0"}
            ),
            source_type="AUTO",
            confidence="HIGH",
        )
        db.add(fingerprint)
        db.flush()
        snapshot = EnvironmentSnapshot(
            environment_id=environment.id,
            mission_id=mission.id,
            build_label="sports-16.0.0-test5-20260907",
            frontend_version="16.0.0",
            service_versions_json=dump({"basketball-service": "test5-observed"}),
            manual_note=f"Observed by Playwright at {TARGET_PAGE}",
            fingerprint_hash=fingerprint_value,
            created_by_type="AUTO",
            confidence="HIGH",
        )
        db.add(snapshot)
        db.flush()

        functional_run = add_run(
            db,
            scenario=scenario_rows[0][0],
            version=scenario_rows[0][1],
            contract_version_id=contract_version.id,
            environment_id=environment.id,
            snapshot_id=snapshot.id,
            outcome="PASS",
            steps=[
                {"name": "打开篮球首页", "input": {"url": TARGET_PAGE}, "output": {"title": "Basketball Live Scores, Stats & Fixtures - Bball"}},
                {"name": "检查核心功能区", "output": {"live": True, "favorites": True, "competitions": True, "replays": True}},
                {"name": "切换收藏并返回直播", "output": {"basketball_links": 261, "live_visible": True}},
            ],
            assertions=[
                {"name": "Live Matches 可见", "expected": {"visible": True}, "actual": {"visible": True}, "result": "PASS"},
                {"name": "Match Replays 可见", "expected": {"visible": True}, "actual": {"visible": True}, "result": "PASS"},
            ],
            evidence_files=[
                ("SCREENSHOT", "functional-case.png", "image/png"),
                ("VIDEO", "functional-case.webm", "video/webm"),
            ],
        )
        api_run = add_run(
            db,
            scenario=scenario_rows[1][0],
            version=scenario_rows[1][1],
            contract_version_id=contract_version.id,
            environment_id=environment.id,
            snapshot_id=snapshot.id,
            outcome="PASS",
            steps=[
                {"name": "发送篮球赛事请求", "type": "API", "input": {"method": "GET", "url": TARGET_API}, "output": {"http_status": 200}},
                {"name": "解析篮球分组", "type": "ASSERT", "output": {"today": "20260907", "living_groups": 2, "category_groups": 1, "country_groups": 9}},
            ],
            assertions=[
                {"name": "HTTP 状态", "expected": {"status": 200}, "actual": {"status": 200}, "result": "PASS"},
                {"name": "业务状态", "expected": {"status": 200}, "actual": {"status": 200}, "result": "PASS"},
                {"name": "请求日期", "expected": {"today": "20260907"}, "actual": {"today": "20260907"}, "result": "PASS"},
                {"name": "直播分组", "expected": {"living_groups": ">=1"}, "actual": {"living_groups": 2}, "result": "PASS"},
            ],
            evidence_files=[
                ("RESPONSE", "api-case-result.json", "application/json"),
                ("PW_TRACE", "api-case.trace", "application/zip"),
            ],
        )
        ui_run = add_run(
            db,
            scenario=scenario_rows[2][0],
            version=scenario_rows[2][1],
            contract_version_id=contract_version.id,
            environment_id=environment.id,
            snapshot_id=snapshot.id,
            outcome="BUSINESS_FAIL",
            steps=[
                {"name": "打开篮球赛事列表", "input": {"url": TARGET_PAGE}, "output": {"loaded": True}},
                {"name": "选择 Competitions", "output": {"visible_competition_links": 60}},
                {"name": "进入 NBA 联赛详情", "output": {"url": f"{TARGET_PAGE}/league/National%20Basketball%20Association", "console_errors": 11}},
            ],
            assertions=[
                {"name": "联赛详情路由", "expected": {"contains": "/basketball/league/"}, "actual": {"matched": True}, "result": "PASS"},
                {"name": "页面资源无错误", "expected": {"console_errors": 0}, "actual": {"console_errors": 11, "causes": ["Google GSI 403", "image proxy 503/504", "NBA CDN HTTP2 error"]}, "result": "FAIL"},
            ],
            evidence_files=[
                ("SCREENSHOT", "ui-case.png", "image/png"),
                ("VIDEO", "ui-case.webm", "video/webm"),
            ],
        )
        db.flush()

        defect = Defect(
            project_id=PROJECT_ID,
            defect_id="B232-TEST5-001",
            title="篮球联赛页存在第三方登录与图片资源加载错误",
            description="自动化进入 NBA 联赛详情后观察到 Google GSI 403、图片代理 503/504 与 NBA CDN HTTP2 错误。",
            severity="P2",
            status="open",
            aitde_run_id=ui_run.id,
            creator_id=1,
        )
        db.add(defect)
        db.flush()

        build = BuildObservation(
            mission_id=mission.id,
            environment_id=environment.id,
            fingerprint_id=fingerprint.id,
            change_summary_json=dump({"version": "16.0.0", "target": TARGET_PAGE, "tested_at": "2026-09-07"}),
            status="EVALUATED",
        )
        db.add(build)
        db.flush()
        campaign = ExecutionCampaign(
            project_id=PROJECT_ID,
            mission_id=mission.id,
            name="16.0.0 Test5 功能/API/UI 自动化验收",
            campaign_type="FULL",
            environment_id=environment.id,
            build_observation_id=build.id,
            status="COMPLETED",
            created_by_type="TESTER",
        )
        db.add(campaign)
        db.flush()
        for (scenario, version), run in zip(
            scenario_rows, [functional_run, api_run, ui_run], strict=True
        ):
            db.add(
                CampaignScenario(
                    campaign_id=campaign.id,
                    scenario_id=scenario.id,
                    scenario_version_id=version.id,
                    selection_reason_json=dump({"reason": "16.0.0 新增/受影响范围", "source": "batch-232"}),
                    required="REQUIRED",
                    run_id=run.id,
                )
            )
        policy = db.query(QualityGatePolicy).filter_by(project_id=PROJECT_ID).first()
        if policy is None:
            policy = QualityGatePolicy(
                project_id=PROJECT_ID,
                name="测试环境完整验收",
                version="1.0",
                policy_json=dump({"required": ["scope", "contract", "execution", "evidence"]}),
            )
            db.add(policy)
            db.flush()
        gate_checks = [
            {"gate": "G1_SCOPE_APPROVED", "label": "范围已批准", "status": "PASS", "pass": True, "detail": "3/3"},
            {"gate": "G2_CONTRACT_FROZEN", "label": "契约已冻结", "status": "PASS", "pass": True, "detail": "v1"},
            {"gate": "G3_THREE_LANES_COVERED", "label": "功能/API/UI 覆盖", "status": "PASS", "pass": True, "detail": "3/3"},
            {"gate": "G4_EXECUTION_EVIDENCE_COMPLETE", "label": "逐用例证据完整", "status": "PASS", "pass": True, "detail": "3/3"},
            {"gate": "G5_UI_RESOURCE_ERRORS_ZERO", "label": "UI 资源错误为零", "status": "FAIL", "pass": False, "detail": "11 个 console error；缺陷 B232-TEST5-001"},
        ]
        gate = QualityGateResultRecord(
            mission_id=mission.id,
            campaign_id=campaign.id,
            build_observation_id=build.id,
            policy_id=policy.id,
            result="FAIL",
            checks_json=dump(gate_checks),
        )
        db.add(gate)

        change_set = ChangeSet(
            project_id=PROJECT_ID,
            mission_id=mission.id,
            change_type="PRD",
            source_from_ref="体育平台 15.x 篮球基线",
            source_to_ref="体育平台 16.0.0 篮球多项目适配",
            status="ANALYZED",
            content_hash=digest(fragment_specs),
        )
        db.add(change_set)
        db.flush()
        changes = [
            ("ADDED", "PAGE", "/basketball", None, {"route": "/basketball"}, "CONTRACT_RULE", refs[0]),
            ("CHANGED", "API_ENDPOINT", "home_match", {"sportType": "legacy"}, {"sportType": "basketball"}, "RECENT_CHANGE", refs[2]),
            ("ADDED", "JOURNEY", "basketball-to-league", None, {"route": "/basketball/league/*"}, "CONTRACT_RULE", refs[3]),
        ]
        for kind, entity_type, key, before, after, risk, source_ref in changes:
            db.add(
                ChangeItem(
                    change_set_id=change_set.id,
                    change_kind=kind,
                    entity_type=entity_type,
                    entity_key=key,
                    before_json=dump(before) if before is not None else None,
                    after_json=dump(after),
                    risk_hint=risk,
                    source_refs_json=dump([source_ref]),
                )
            )
        impact = ImpactAnalysisRun(
            project_id=PROJECT_ID,
            mission_id=mission.id,
            change_set_id=change_set.id,
            algorithm_version="batch-232-v2",
            status="COMPLETED",
            input_hash=digest(changes),
            finished_at=datetime.now(),
        )
        db.add(impact)
        db.flush()
        impact_reasons = [
            "篮球独立入口与首页模块新增",
            "home_match 请求参数切换为 sportType=basketball",
            "篮球赛事到联赛详情的导航链路新增",
        ]
        for index, ((scenario, version), reason) in enumerate(
            zip(scenario_rows, impact_reasons, strict=True)
        ):
            db.add(
                ImpactResult(
                    impact_run_id=impact.id,
                    scenario_id=scenario.id,
                    scenario_version_id=version.id,
                    impact_score=0.96 - index * 0.05,
                    risk_level="P1",
                    reasons_json=dump([reason]),
                    path_json=dump([["SOURCE_FRAGMENT", "CONTRACT_RULE", "SCENARIO_VERSION"]]),
                    decision="INCLUDE",
                )
            )
        selection = RegressionSelection(
            mission_id=mission.id,
            impact_run_id=impact.id,
            build_observation_id=build.id,
            selection_type="SMART",
            selected_json=dump(
                [
                    {"scenario_id": scenario.id, "scenario_version_id": version.id, "decision": "SELECTED", "reason": reason}
                    for (scenario, version), reason in zip(scenario_rows, impact_reasons, strict=True)
                ]
            ),
            excluded_json="[]",
            content_hash=digest(impact_reasons),
        )
        db.add(selection)
        db.flush()
        for (scenario, version), reason in zip(scenario_rows, impact_reasons, strict=True):
            db.add(
                RegressionSelectionItem(
                    selection_id=selection.id,
                    scenario_id=scenario.id,
                    scenario_version_id=version.id,
                    decision="SELECTED",
                    reason=reason,
                    source="IMPACT",
                )
            )

        for fragment, (scenario, version), run in zip(
            fragments[:3], scenario_rows, [functional_run, api_run, ui_run], strict=True
        ):
            db.add_all(
                [
                    LineageEdge(
                        project_id=PROJECT_ID,
                        mission_id=mission.id,
                        from_type="SOURCE_FRAGMENT",
                        from_id=fragment.id,
                        to_type="SCENARIO_VERSION",
                        to_id=version.id,
                        edge_type="DERIVES_FROM",
                        source_refs_json=dump([{"artifact_id": source.id, "fragment_id": fragment.id}]),
                        confidence=1.0,
                        created_by_type="SYSTEM",
                    ),
                    LineageEdge(
                        project_id=PROJECT_ID,
                        mission_id=mission.id,
                        from_type="SCENARIO_VERSION",
                        from_id=version.id,
                        to_type="EXECUTION_RUN",
                        to_id=run.id,
                        edge_type="VERIFIES",
                        source_refs_json=dump([{"run_id": run.id}]),
                        confidence=1.0,
                        created_by_type="SYSTEM",
                    ),
                ]
            )
        db.add(
            ScenarioGapCandidate(
                mission_id=mission.id,
                gap_type="PROD_NEW_STATE",
                title="第三方资源失败时的降级展示与生产复验",
                description="当前 Test5 观察到 Google GSI 403、图片代理 503/504 和 NBA CDN 错误；需补充资源失败降级用例，并在修复后复验。",
                source_refs_json=dump([refs[3]]),
                evidence_refs_json=dump([{"run_id": ui_run.id}, {"defect_id": defect.id}]),
                risk_level="P2",
                confidence=0.98,
                status="OPEN",
            )
        )
        add_ai_operation(db, "scope:analyze", {"scope_items": 3, "reviewed": True})
        add_ai_operation(db, "contract:build", {"contract_version_id": contract_version.id, "frozen": True})
        add_ai_operation(db, "scenario:design", {"case_types": ["FUNCTIONAL", "API", "UI"]})
        add_ai_operation(db, "scenario:gap", {"candidates": 1, "status": "review_required"})

        db.commit()
        result = build_lifecycle(db, mission.id, PROJECT_ID)
        print(
            dump(
                {
                    "mission_id": mission.id,
                    "integrity_status": result["integrity_status"],
                    "acceptance_status": result["mission"]["acceptance_status"],
                    "stages": {item["key"]: item["status"] for item in result["stages"]},
                    "supporting_stages": {
                        item["key"]: item["status"] for item in result["supporting_stages"]
                    },
                    "totals": result["totals"],
                    "artifacts": result["artifacts"],
                }
            )
        )


if __name__ == "__main__":
    main()
