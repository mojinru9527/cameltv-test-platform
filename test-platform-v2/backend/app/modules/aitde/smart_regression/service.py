"""AITDE V3.7 Impact Analysis + Smart Regression service layer (V37).

Deterministic lineage, change-set, impact-analysis, regression-selection,
coverage-guard and smart-campaign logic per the V3.7 plan §§5-10. No AI owns a
final PASS/FAIL decision: selection is computed by ``RegressionSelector`` +
``CoverageGuard``; AI output is at most assist evidence.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Any, Callable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.api_asset import ApiEndpoint
from app.models.defect import Defect
from app.models.production_evidence import ObservedJourney
from app.modules.aitde.common.enums import (
    CampaignScenarioRequired,
    ChangeSetStatus,
    ChangeSetType,
    ImpactDecision,
    ImpactRunStatus,
    LineageEdgeType,
    LineageNodeType,
    Outcome,
    RiskHint,
    RiskLevel,
    SelectionDecision,
    SelectionType,
)
from app.modules.aitde.contract.models import TestContractVersion
from app.modules.aitde.continuous.models import CampaignScenario, ExecutionCampaign
from app.modules.aitde.data.models import DataSource
from app.modules.aitde.execution.models import ExecutionRun
from app.modules.aitde.scenario.models import (
    TestOracle,
    TestScenario,
    TestScenarioVersion,
)
from app.modules.aitde.scope.models import ScopeItem, TestIntent
from app.modules.aitde.smart_regression import diff as diff_mod
from app.modules.aitde.smart_regression import repository as repo
from app.modules.aitde.smart_regression.models import (
    ChangeItem,
    ChangeSet,
    ImpactAnalysisRun,
    ImpactResult,
    LineageEdge,
    RegressionSelection,
)
from app.modules.aitde.sources.models import SourceArtifact, SourceFragment

# ────────────────────────────────────────────────────────────────────────────
# helpers
# ────────────────────────────────────────────────────────────────────────────

_HASH_ALG = "sha256"


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _dumps(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _content_hash(change_type: str, items: list[dict]) -> str:
    payload = [_dumps(i) for i in sorted(items, key=lambda x: _dumps(x))]
    return _sha(f"{change_type}|{'|'.join(payload)}")


def _priority_weight(risk_level: str) -> float:
    return {
        RiskLevel.P0.value: 5.0,
        RiskLevel.P1.value: 4.0,
        RiskLevel.P2.value: 2.0,
        RiskLevel.P3.value: 1.0,
    }.get((risk_level or "").upper(), 1.0)


def _risk_weight(risk_hint: str) -> float:
    return {
        RiskHint.P0_RULE.value: 5.0,
        RiskHint.CONTRACT_RULE.value: 4.0,
        RiskHint.LAST_BUSINESS_FAIL.value: 4.0,
        RiskHint.HISTORICAL_DEFECT.value: 3.0,
        RiskHint.PROD_REAL_WORLD.value: 3.0,
        RiskHint.RECENT_CHANGE.value: 2.0,
        RiskHint.UNKNOWN_CHANGE.value: 2.0,
        RiskHint.NONE.value: 1.0,
    }.get((risk_hint or "").upper(), 1.0)


def _nk(node_type: str, node_id: int) -> str:
    return f"{node_type}:{node_id}"


def _pk(node_type: str, node_id: int) -> tuple[str, int]:
    return node_type, node_id


def _parse_source_refs(raw: str) -> list[tuple[str, int]]:
    """Tolerantly extract ``(node_type, node_id)`` pairs from a source_refs JSON
    that may be ``[{type,id}]``, ``[{node_type,node_id}]`` or ``[{type,ref}]``."""
    refs: list[tuple[str, int]] = []
    if not raw:
        return refs
    try:
        data = json.loads(raw)
    except (ValueError, TypeError):
        return refs
    if not isinstance(data, list):
        return refs
    for entry in data:
        if not isinstance(entry, dict):
            continue
        candidate = (
            entry.get("type") or entry.get("node_type") or entry.get("entity_type")
        )
        id_val = (
            entry.get("id")
            or entry.get("node_id")
            or entry.get("entity_id")
            or entry.get("ref")
        )
        if candidate is None:
            continue
        try:
            refs.append((str(candidate).upper(), int(id_val)))
        except (TypeError, ValueError):
            continue
    return refs


# ────────────────────────────────────────────────────────────────────────────
# LineageService — V37-001
# ────────────────────────────────────────────────────────────────────────────


class LineageService:
    """Build/query the lineage graph; detect dangling edges (V37-001)."""

    _NODE_MODELS = {
        LineageNodeType.SOURCE_ARTIFACT.value: SourceArtifact,
        LineageNodeType.SOURCE_FRAGMENT.value: SourceFragment,
        LineageNodeType.SCOPE_ITEM.value: ScopeItem,
        LineageNodeType.TEST_INTENT.value: TestIntent,
        LineageNodeType.CONTRACT_RULE.value: TestContractVersion,
        LineageNodeType.SCENARIO.value: TestScenario,
        LineageNodeType.SCENARIO_VERSION.value: TestScenarioVersion,
        LineageNodeType.ORACLE.value: TestOracle,
        LineageNodeType.API_ENDPOINT.value: ApiEndpoint,
        LineageNodeType.DATA_ENTITY.value: DataSource,
        LineageNodeType.OBSERVED_JOURNEY.value: ObservedJourney,
        LineageNodeType.EXECUTION_RUN.value: ExecutionRun,
        LineageNodeType.DEFECT.value: Defect,
    }

    @staticmethod
    def add_edge(
        db: Session,
        project_id: int,
        mission_id: int | None,
        from_type: str,
        from_id: int,
        to_type: str,
        to_id: int,
        edge_type: str,
        source_refs: list | None = None,
        confidence: float = 1.0,
        created_by_type: str = "SYSTEM",
    ) -> LineageEdge | None:
        values = {
            "project_id": project_id,
            "mission_id": mission_id,
            "from_type": from_type,
            "from_id": from_id,
            "to_type": to_type,
            "to_id": to_id,
            "edge_type": edge_type,
            "source_refs_json": _dumps(source_refs or []),
            "confidence": confidence,
            "created_by_type": created_by_type,
        }
        return repo.insert_edge_ignoring_dupes(db, values)

    @staticmethod
    def list_edges(
        db: Session, project_id: int, mission_id: int | None = None
    ) -> list[dict]:
        return [
            LineageService._edge_dict(e)
            for e in repo.list_lineage_edges(db, project_id, mission_id)
        ]

    @staticmethod
    def dangling_edges(
        db: Session, project_id: int, mission_id: int | None = None
    ) -> list[dict]:
        dangling: list[dict] = []
        for edge in repo.list_lineage_edges(db, project_id, mission_id):
            if not LineageService._node_exists(db, edge.to_type, edge.to_id):
                dangling.append(
                    {
                        "id": edge.id,
                        **LineageService._edge_dict(edge),
                        "dangling_node": _nk(edge.to_type, edge.to_id),
                    }
                )
        return dangling

    @staticmethod
    def find_paths_to_scenarios(
        db: Session,
        project_id: int,
        mission_id: int | None,
        from_type: str,
        from_id: int,
    ) -> list[dict]:
        """BFS from a start node across ``lineage_edges`` to every reachable
        SCENARIO / SCENARIO_VERSION node. Returns path summaries."""
        edges = repo.list_lineage_edges(db, project_id, mission_id)
        adjacency: dict[str, list[tuple[str, int, str]]] = {}
        for e in edges:
            adjacency.setdefault(_nk(e.from_type, e.from_id), []).append(
                (e.to_type, e.to_id, e.edge_type)
            )

        start = _nk(from_type, from_id)
        targets = {
            LineageNodeType.SCENARIO.value,
            LineageNodeType.SCENARIO_VERSION.value,
        }
        found: list[dict] = []
        visited: set[str] = {start}
        queue: list[tuple[str, list[str]]] = [(start, [start])]
        depth = 0
        while queue:
            if depth > 8:
                break
            next_queue: list[tuple[str, list[str]]] = []
            depth += 1
            for node, path in queue:
                node_type, node_id = node.split(":", 1)
                for to_type, to_id, edge_type in adjacency.get(node, []):
                    to_key = _nk(to_type, to_id)
                    if to_key in visited:
                        continue
                    new_path = path + [to_key]
                    visited.add(to_key)
                    if to_type in targets:
                        found.append({"type": to_type, "id": to_id, "path": new_path})
                    # continue expanding through targets to reach deeper
                    # SCENARIO_VERSION nodes
                    next_queue.append((to_key, new_path))
            queue = next_queue
        return found

    @staticmethod
    def _node_exists(db: Session, node_type: str, node_id: int) -> bool:
        model = LineageService._NODE_MODELS.get(node_type.upper())
        if model is None:
            return True  # PAGE etc. have no node table — treat as present
        return db.get(model, node_id) is not None

    @staticmethod
    def _edge_dict(e: LineageEdge) -> dict:
        return {
            "id": e.id,
            "project_id": e.project_id,
            "mission_id": e.mission_id,
            "from": _nk(e.from_type, e.from_id),
            "from_type": e.from_type,
            "from_id": e.from_id,
            "to": _nk(e.to_type, e.to_id),
            "to_type": e.to_type,
            "to_id": e.to_id,
            "edge_type": e.edge_type,
            "source_refs": json.loads(e.source_refs_json or "[]"),
            "confidence": e.confidence,
            "created_by_type": e.created_by_type,
            "created_at": e.created_at.isoformat() if e.created_at else None,
        }


def lineage_add_edge(
    db: Session,
    project_id: int,
    mission_id: int | None,
    from_type: str,
    from_id: int,
    to_type: str,
    to_id: int,
    edge_type: str,
    source_refs: list | None = None,
) -> LineageEdge | None:
    return LineageService.add_edge(
        db,
        project_id,
        mission_id,
        from_type,
        from_id,
        to_type,
        to_id,
        edge_type,
        source_refs,
    )


def lineage_list(db: Session, project_id: int, mission_id: int | None = None) -> dict:
    return {"edges": LineageService.list_edges(db, project_id, mission_id)}


def lineage_dangling(
    db: Session, project_id: int, mission_id: int | None = None
) -> dict:
    return {"dangling": LineageService.dangling_edges(db, project_id, mission_id)}


# ────────────────────────────────────────────────────────────────────────────
# LineageBackfillService — V37-002
# ────────────────────────────────────────────────────────────────────────────


class LineageBackfillService:
    """Derive lineage edges for one Mission from existing V3.0-V3.6 records.

    Idempotent: re-running never duplicates edges (unique constraint + check).
    """

    @staticmethod
    def backfill(db: Session, project_id: int, mission_id: int) -> dict:
        created = 0

        artifacts = db.scalars(
            select(SourceArtifact).where(SourceArtifact.project_id == project_id)
        ).all()
        for artifact in artifacts:
            fragments = db.scalars(
                select(SourceFragment).where(SourceFragment.artifact_id == artifact.id)
            ).all()
            for frag in fragments:
                created += (
                    1
                    if LineageService.add_edge(
                        db,
                        project_id,
                        mission_id,
                        LineageNodeType.SOURCE_ARTIFACT.value,
                        artifact.id,
                        LineageNodeType.SOURCE_FRAGMENT.value,
                        frag.id,
                        LineageEdgeType.DERIVES_FROM.value,
                    )
                    else 0
                )

        scenarios = db.scalars(
            select(TestScenario).where(TestScenario.mission_id == mission_id)
        ).all()
        for scenario in scenarios:
            versions = db.scalars(
                select(TestScenarioVersion).where(
                    TestScenarioVersion.scenario_id == scenario.id
                )
            ).all()
            for ver in versions:
                created += (
                    1
                    if LineageService.add_edge(
                        db,
                        project_id,
                        mission_id,
                        LineageNodeType.SCENARIO.value,
                        scenario.id,
                        LineageNodeType.SCENARIO_VERSION.value,
                        ver.id,
                        LineageEdgeType.BINDS.value,
                    )
                    else 0
                )
                oracles = db.scalars(
                    select(TestOracle).where(TestOracle.scenario_version_id == ver.id)
                ).all()
                for oracle in oracles:
                    created += (
                        1
                        if LineageService.add_edge(
                            db,
                            project_id,
                            mission_id,
                            LineageNodeType.SCENARIO_VERSION.value,
                            ver.id,
                            LineageNodeType.ORACLE.value,
                            oracle.id,
                            LineageEdgeType.VERIFIES.value,
                        )
                        else 0
                    )
                if ver.contract_version_id:
                    created += (
                        1
                        if LineageService.add_edge(
                            db,
                            project_id,
                            mission_id,
                            LineageNodeType.CONTRACT_RULE.value,
                            ver.contract_version_id,
                            LineageNodeType.SCENARIO_VERSION.value,
                            ver.id,
                            LineageEdgeType.CONTRACTED_FOR.value,
                        )
                        else 0
                    )

        # source refs -> scope items / scenario versions
        scopes = db.scalars(
            select(ScopeItem).where(ScopeItem.mission_id == mission_id)
        ).all()
        for scope in scopes:
            for ntype, nid in _parse_source_refs(scope.source_refs_json):
                created += (
                    1
                    if LineageService.add_edge(
                        db,
                        project_id,
                        mission_id,
                        ntype,
                        nid,
                        LineageNodeType.SCOPE_ITEM.value,
                        scope.id,
                        LineageEdgeType.DERIVES_FROM.value,
                    )
                    else 0
                )

        for version in db.scalars(
            select(TestScenarioVersion).where(
                TestScenarioVersion.scenario_id.in_([s.id for s in scenarios])
            )
        ).all():
            for ntype, nid in _parse_source_refs(version.source_refs_json):
                created += (
                    1
                    if LineageService.add_edge(
                        db,
                        project_id,
                        mission_id,
                        ntype,
                        nid,
                        LineageNodeType.SCENARIO_VERSION.value,
                        version.id,
                        LineageEdgeType.APPLIES_TO.value,
                    )
                    else 0
                )

        # scenario_version -> business-fail runs
        for version in db.scalars(
            select(TestScenarioVersion).where(
                TestScenarioVersion.scenario_id.in_([s.id for s in scenarios])
            )
        ).all():
            runs = db.scalars(
                select(ExecutionRun).where(
                    ExecutionRun.scenario_version_id == version.id
                )
            ).all()
            for run in runs:
                if run.outcome == Outcome.BUSINESS_FAIL.value:
                    created += (
                        1
                        if LineageService.add_edge(
                            db,
                            project_id,
                            mission_id,
                            LineageNodeType.SCENARIO_VERSION.value,
                            version.id,
                            LineageNodeType.EXECUTION_RUN.value,
                            run.id,
                            LineageEdgeType.FAILED_IN.value,
                        )
                        else 0
                    )

        db.flush()
        return {
            "mission_id": mission_id,
            "created_edges": created,
            "edge_count": len(repo.list_lineage_edges(db, project_id, mission_id)),
        }


# ────────────────────────────────────────────────────────────────────────────
# ChangeSetService — V37-003..007
# ────────────────────────────────────────────────────────────────────────────


class ChangeSetService:
    """Detect a ChangeSet from a Diff Provider and normalize it (V37-003..007)."""

    _DIFF: dict[str, Callable] = {
        ChangeSetType.PRD.value: diff_mod.diff_requirement,
        ChangeSetType.OPENAPI.value: diff_mod.diff_openapi,
        ChangeSetType.DB_SCHEMA.value: diff_mod.diff_db_schema,
        ChangeSetType.UI_DISCOVERY.value: diff_mod.diff_ui_discovery,
        ChangeSetType.ENVIRONMENT.value: diff_mod.diff_environment,
        ChangeSetType.HISTORICAL_RISK.value: diff_mod.diff_historical_risk,
    }

    @staticmethod
    def detect(
        db: Session,
        project_id: int,
        mission_id: int,
        change_type: str,
        baseline: dict,
        current: dict,
        source_from_ref: str | None = None,
        source_to_ref: str | None = None,
    ) -> dict:
        change_type = (change_type or "").upper()
        provider = ChangeSetService._DIFF.get(change_type)
        if provider is None:
            raise ValueError(f"unknown change_type: {change_type}")

        if change_type == ChangeSetType.HISTORICAL_RISK.value:
            items = provider(
                current.get("signals") if isinstance(current, dict) else current
            )
        else:
            items = provider(baseline or {}, current or {})

        content_hash = _content_hash(change_type, items)
        existing = repo.latest_change_set_for_mission(db, mission_id, change_type)
        if existing is not None and existing.content_hash == content_hash:
            return ChangeSetService._changeset_dict(
                existing, repo.list_change_items(db, existing.id)
            )

        row = repo.create_change_set(
            db,
            project_id,
            mission_id,
            change_type,
            source_from_ref,
            source_to_ref,
            content_hash,
            ChangeSetStatus.DETECTED.value,
        )
        for item in items:
            repo.create_change_item(db, row.id, item)
        db.flush()
        db.refresh(row)
        return ChangeSetService._changeset_dict(row, repo.list_change_items(db, row.id))

    @staticmethod
    def get(db: Session, change_set_id: int) -> dict | None:
        row = repo.get_change_set(db, change_set_id)
        if row is None:
            return None
        return ChangeSetService._changeset_dict(row, repo.list_change_items(db, row.id))

    @staticmethod
    def _changeset_dict(row: ChangeSet, items: list[ChangeItem]) -> dict:
        return {
            "id": row.id,
            "project_id": row.project_id,
            "mission_id": row.mission_id,
            "change_type": row.change_type,
            "source_from_ref": row.source_from_ref,
            "source_to_ref": row.source_to_ref,
            "status": row.status,
            "content_hash": row.content_hash,
            "created_at": row.created_at.isoformat() if row.created_at else None,
            "items": [ChangeSetService._item_dict(i) for i in items],
        }

    @staticmethod
    def _item_dict(i: ChangeItem) -> dict:
        return {
            "id": i.id,
            "change_set_id": i.change_set_id,
            "change_kind": i.change_kind,
            "entity_type": i.entity_type,
            "entity_key": i.entity_key,
            "before": json.loads(i.before_json) if i.before_json else None,
            "after": json.loads(i.after_json) if i.after_json else None,
            "risk_hint": i.risk_hint,
            "source_refs": json.loads(i.source_refs_json or "[]"),
        }


# ────────────────────────────────────────────────────────────────────────────
# ImpactAnalyzer — V37-008
# ────────────────────────────────────────────────────────────────────────────


class ImpactAnalyzer:
    """Deterministic impact analysis over a ChangeSet via the lineage graph."""

    @staticmethod
    def analyze(
        db: Session,
        project_id: int,
        mission_id: int,
        change_set_id: int,
        algorithm_version: str = "v1",
    ) -> dict:
        changeset = repo.get_change_set(db, change_set_id)
        if changeset is None:
            raise ValueError(f"ChangeSet {change_set_id} not found")
        items = repo.list_change_items(db, change_set_id)

        input_hash = _content_hash(
            changeset.change_type,
            [
                {
                    "k": i.change_kind,
                    "t": i.entity_type,
                    "e": i.entity_key,
                    "r": i.risk_hint,
                }
                for i in items
            ],
        )

        run = repo.create_impact_run(
            db,
            project_id,
            mission_id,
            change_set_id,
            algorithm_version,
            input_hash,
            ImpactRunStatus.RUNNING.value,
        )

        unknown: list[dict] = []
        results: dict[int, dict] = {}

        for item in items:
            paths = ImpactAnalyzer._paths_for_item(db, project_id, mission_id, item)
            if not paths:
                unknown.append(
                    {
                        "entity_type": item.entity_type,
                        "entity_key": item.entity_key,
                        "risk_hint": item.risk_hint,
                    }
                )
                continue
            for p in paths:
                scenario_id, scenario_version_id = ImpactAnalyzer._resolve_scenario(
                    db, p
                )
                if scenario_id is None:
                    unknown.append(
                        {
                            "entity_type": item.entity_type,
                            "entity_key": item.entity_key,
                            "risk_hint": item.risk_hint,
                            "path": p["path"],
                        }
                    )
                    continue
                entry = results.setdefault(
                    scenario_id,
                    {
                        "scenario_id": scenario_id,
                        "scenario_version_id": scenario_version_id,
                        "impact_score": 0.0,
                        "risk_level": "P2",
                        "reasons": [],
                        "paths": [],
                    },
                )
                # prefer a resolved scenario version over the latest-unknown marker
                if entry["scenario_version_id"] in (
                    None,
                    0,
                ) and scenario_version_id not in (None, 0):
                    entry["scenario_version_id"] = scenario_version_id
                weight = _risk_weight(item.risk_hint)
                entry["impact_score"] += weight
                entry["reasons"].append(
                    f"{item.entity_type}:{item.entity_key} "
                    f"{item.change_kind} ({item.risk_hint})"
                )
                entry["paths"].append(p["path"])
                if item.risk_hint in {
                    RiskHint.P0_RULE.value,
                    RiskHint.CONTRACT_RULE.value,
                    RiskHint.LAST_BUSINESS_FAIL.value,
                }:
                    entry["risk_level"] = ImpactAnalyzer._raise_risk(
                        entry["risk_level"], "P1"
                    )

        # fold in scenario priority
        for scenario_id in list(results.keys()):
            entry = results[scenario_id]
            risk = ImpactAnalyzer._scenario_risk(db, scenario_id)
            entry["risk_level"] = ImpactAnalyzer._raise_risk(entry["risk_level"], risk)
            entry["impact_score"] += _priority_weight(risk)

        for entry in results.values():
            repo.create_impact_result(
                db,
                run.id,
                {
                    "scenario_id": entry["scenario_id"],
                    "scenario_version_id": entry["scenario_version_id"] or 0,
                    "impact_score": round(entry["impact_score"], 4),
                    "risk_level": entry["risk_level"],
                    "reasons_json": _dumps(entry["reasons"]),
                    "path_json": _dumps(entry["paths"]),
                    "decision": ImpactDecision.INCLUDE.value,
                },
            )

        run.status = ImpactRunStatus.COMPLETED.value
        run.finished_at = datetime.now()
        db.flush()
        db.refresh(run)
        return ImpactAnalyzer._run_dict(
            run, repo.list_impact_results(db, run.id), unknown
        )

    @staticmethod
    def get_run(db: Session, impact_run_id: int) -> dict | None:
        run = repo.get_impact_run(db, impact_run_id)
        if run is None:
            return None
        return ImpactAnalyzer._run_dict(run, repo.list_impact_results(db, run.id), [])

    @staticmethod
    def _paths_for_item(
        db: Session, project_id: int, mission_id: int, item: ChangeItem
    ) -> list[dict]:
        """Return lineage paths to a scenario for a change item.

        SCENARIO / SCENARIO_VERSION change items target the scenario directly;
        all other entity types traverse the lineage graph via ``LineageService``.
        """
        etype = item.entity_type
        if etype == LineageNodeType.SCENARIO.value:
            sid = ImpactAnalyzer._safe_int(item.entity_key)
            if not sid:
                return []
            return [{"type": etype, "id": sid, "path": [_nk(etype, sid)]}]
        if etype == LineageNodeType.SCENARIO_VERSION.value:
            vid = ImpactAnalyzer._safe_int(item.entity_key)
            ver = db.get(TestScenarioVersion, vid) if vid else None
            if ver is None:
                return []
            return [{"type": etype, "id": ver.id, "path": [_nk(etype, vid)]}]
        return LineageService.find_paths_to_scenarios(
            db, project_id, mission_id, etype, ImpactAnalyzer._safe_int(item.entity_key)
        )

    @staticmethod
    def _resolve_scenario(db: Session, path: dict) -> tuple[int | None, int | None]:
        if path["type"] == LineageNodeType.SCENARIO.value:
            return path["id"], None
        if path["type"] == LineageNodeType.SCENARIO_VERSION.value:
            ver = db.get(TestScenarioVersion, path["id"])
            return (ver.scenario_id, ver.id) if ver else (None, None)
        return None, None

    @staticmethod
    def _latest_version_id(db: Session, scenario_id: int) -> int | None:
        ver = db.scalars(
            select(TestScenarioVersion)
            .where(TestScenarioVersion.scenario_id == scenario_id)
            .order_by(TestScenarioVersion.version_no.desc())
        ).first()
        return ver.id if ver else None

    @staticmethod
    def _scenario_risk(db: Session, scenario_id: int) -> str:
        ver = db.scalars(
            select(TestScenarioVersion)
            .where(TestScenarioVersion.scenario_id == scenario_id)
            .order_by(TestScenarioVersion.version_no.desc())
        ).first()
        return ver.risk_level if ver else RiskLevel.P2.value

    @staticmethod
    def _raise_risk(current: str, candidate: str) -> str:
        order = {
            RiskLevel.P3.value: 0,
            RiskLevel.P2.value: 1,
            RiskLevel.P1.value: 2,
            RiskLevel.P0.value: 3,
        }
        return (
            current if order.get(candidate, 0) <= order.get(current, 0) else candidate
        )

    @staticmethod
    def _safe_int(value: str) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return 0

    @staticmethod
    def _run_dict(
        run: ImpactAnalysisRun, results: list[ImpactResult], unknown: list[dict]
    ) -> dict:
        return {
            "id": run.id,
            "project_id": run.project_id,
            "mission_id": run.mission_id,
            "change_set_id": run.change_set_id,
            "algorithm_version": run.algorithm_version,
            "status": run.status,
            "input_hash": run.input_hash,
            "created_at": run.created_at.isoformat() if run.created_at else None,
            "finished_at": run.finished_at.isoformat() if run.finished_at else None,
            "results": [ImpactAnalyzer._result_dict(r) for r in results],
            "unknown_changes": unknown,
        }

    @staticmethod
    def _result_dict(r: ImpactResult) -> dict:
        return {
            "id": r.id,
            "impact_run_id": r.impact_run_id,
            "scenario_id": r.scenario_id,
            "scenario_version_id": r.scenario_version_id,
            "impact_score": r.impact_score,
            "risk_level": r.risk_level,
            "reasons": json.loads(r.reasons_json or "[]"),
            "paths": json.loads(r.path_json or "[]"),
            "decision": r.decision,
        }


class ImpactExplanationService:
    """Deterministic impact explanation (V37-008). No AI required to explain."""

    @staticmethod
    def explain(db: Session, impact_run_id: int, scenario_id: int) -> dict | None:
        run = repo.get_impact_run(db, impact_run_id)
        if run is None:
            return None
        result = db.scalars(
            select(ImpactResult).where(
                ImpactResult.impact_run_id == impact_run_id,
                ImpactResult.scenario_id == scenario_id,
            )
        ).first()
        if result is None:
            return {
                "scenario_id": scenario_id,
                "paths": [],
                "reasons": [],
                "impact_score": 0.0,
            }
        return {
            "scenario_id": scenario_id,
            "scenario_version_id": result.scenario_version_id,
            "impact_score": result.impact_score,
            "risk_level": result.risk_level,
            "reasons": json.loads(result.reasons_json or "[]"),
            "paths": json.loads(result.path_json or "[]"),
        }


# ────────────────────────────────────────────────────────────────────────────
# RegressionSelector — V37-009
# ────────────────────────────────────────────────────────────────────────────


class RegressionSelector:
    """Build a regression selection: mandatory P0 + impacted + explicit excludes."""

    @staticmethod
    def select(
        db: Session,
        project_id: int,
        mission_id: int,
        impact_run_id: int,
        selection_type: str = SelectionType.SMART.value,
        build_observation_id: int | None = None,
    ) -> dict:
        linked = db.scalars(
            select(ImpactResult).where(ImpactResult.impact_run_id == impact_run_id)
        ).all()
        impacted: dict[str, dict] = {}
        for r in linked:
            impacted[f"{r.scenario_id}:{r.scenario_version_id}"] = {
                "scenario_id": r.scenario_id,
                "scenario_version_id": r.scenario_version_id,
                "risk_level": r.risk_level,
                "reason": "; ".join(json.loads(r.reasons_json or "[]")),
            }

        p0_ids: set[int] = set()
        for scenario in db.scalars(
            select(TestScenario).where(TestScenario.mission_id == mission_id)
        ).all():
            ver = ImpactAnalyzer._scenario_risk(db, scenario.id)
            if ver == RiskLevel.P0.value:
                p0_ids.add(scenario.id)
                impacted.setdefault(
                    f"{scenario.id}:{0}",
                    {
                        "scenario_id": scenario.id,
                        "scenario_version_id": None,
                        "risk_level": RiskLevel.P0.value,
                        "reason": "mandatory P0 include",
                    },
                )

        selected: list[dict] = []
        excluded: list[dict] = []
        for key, entry in impacted.items():
            version_id = (
                ImpactAnalyzer._latest_version_id(db, entry["scenario_id"])
                or entry["scenario_version_id"]
                or 0
            )
            selected.append(
                {
                    "scenario_id": entry["scenario_id"],
                    "scenario_version_id": version_id,
                    "decision": SelectionDecision.SELECTED.value,
                    "reason": entry["reason"],
                }
            )

        for scenario in db.scalars(
            select(TestScenario).where(TestScenario.mission_id == mission_id)
        ).all():
            if scenario.id in p0_ids or any(
                e["scenario_id"] == scenario.id for e in selected
            ):
                continue
            ver = ImpactAnalyzer._scenario_risk(db, scenario.id)
            excluded.append(
                {
                    "scenario_id": scenario.id,
                    "scenario_version_id": None,
                    "decision": SelectionDecision.EXCLUDED.value,
                    "reason": f"not impacted (risk {ver})",
                }
            )

        content_hash = _sha(f"{selection_type}|{_dumps(selected)}|{_dumps(excluded)}")
        row = repo.create_selection(
            db,
            mission_id,
            impact_run_id,
            build_observation_id,
            selection_type,
            _dumps(selected),
            _dumps(excluded),
            None,
            content_hash,
        )
        for item in selected:
            repo.create_selection_item(
                db,
                row.id,
                {
                    "scenario_id": item["scenario_id"],
                    "scenario_version_id": item["scenario_version_id"],
                    "decision": item["decision"],
                    "reason": item["reason"],
                    "source": "SYSTEM",
                },
            )
        db.flush()
        db.refresh(row)
        return RegressionSelector._selection_dict(row)

    @staticmethod
    def get(db: Session, selection_id: int) -> dict | None:
        row = repo.get_selection(db, selection_id)
        if row is None:
            return None
        return RegressionSelector._selection_dict(row)

    @staticmethod
    def _selection_dict(row: RegressionSelection) -> dict:
        return {
            "id": row.id,
            "mission_id": row.mission_id,
            "impact_run_id": row.impact_run_id,
            "build_observation_id": row.build_observation_id,
            "selection_type": row.selection_type,
            "selected": json.loads(row.selected_json or "[]"),
            "excluded": json.loads(row.excluded_json or "[]"),
            "fallback_reason": row.fallback_reason,
            "content_hash": row.content_hash,
            "created_at": row.created_at.isoformat() if row.created_at else None,
        }


# ────────────────────────────────────────────────────────────────────────────
# CoverageGuard — V37-010
# ────────────────────────────────────────────────────────────────────────────


class CoverageGuard:
    """Force a fallback profile when the selection is unsafe (V37-010)."""

    @staticmethod
    def guard(
        db: Session,
        project_id: int,
        mission_id: int,
        selection_id: int,
        unknown_changes: list[dict],
    ) -> dict:
        row = repo.get_selection(db, selection_id)
        if row is None:
            raise ValueError(f"selection {selection_id} not found")
        selected = json.loads(row.selected_json or "[]")
        mission_scenarios = list(
            db.scalars(
                select(TestScenario).where(TestScenario.mission_id == mission_id)
            ).all()
        )

        reason: str | None = None
        fallback_to: str | None = None
        if not selected:
            reason = "empty selection → fallback FULL"
            fallback_to = SelectionType.FULL.value
        elif unknown_changes:
            reason = (
                f"{len(unknown_changes)} unknown change(s) "
                f"no lineage path → fallback FULL"
            )
            fallback_to = SelectionType.FULL.value
        elif mission_scenarios and len(selected) < max(
            1, int(len(mission_scenarios) * 0.1)
        ):
            reason = "selection too small vs mission scope → fallback FULL"
            fallback_to = SelectionType.FULL.value

        if fallback_to:
            row.fallback_reason = reason
            db.flush()
            db.refresh(row)

        return {
            "ok": fallback_to is None,
            "selection_id": selection_id,
            "fallback_to": fallback_to,
            "fallback_reason": reason,
            "selected_count": len(selected),
            "mission_scenario_count": len(mission_scenarios),
        }


# ────────────────────────────────────────────────────────────────────────────
# SmartRegressionCampaignFactory — V37-011
# ────────────────────────────────────────────────────────────────────────────


class SmartRegressionCampaignFactory:
    """Freeze a RegressionSelection into a V3.5 ExecutionCampaign (V37-011)."""

    @staticmethod
    def create_campaign(
        db: Session,
        project_id: int,
        selection_id: int,
        name: str,
        environment_id: int = 0,
    ) -> dict:
        selection = repo.get_selection(db, selection_id)
        if selection is None:
            raise ValueError(f"selection {selection_id} not found")
        selected = json.loads(selection.selected_json or "[]")
        if not selected:
            raise ValueError("cannot create campaign from an empty selection")

        campaign = ExecutionCampaign(
            project_id=project_id,
            mission_id=selection.mission_id,
            name=name,
            campaign_type="CUSTOM",
            environment_id=environment_id,
            build_observation_id=selection.build_observation_id,
            status="DRAFT",
            created_by_type="SYSTEM",
        )
        db.add(campaign)
        db.flush()
        db.refresh(campaign)

        count = 0
        for item in selected:
            db.add(
                CampaignScenario(
                    campaign_id=campaign.id,
                    scenario_id=item["scenario_id"],
                    scenario_version_id=item["scenario_version_id"],
                    selection_reason_json=_dumps(
                        {"reason": item.get("reason", ""), "selection_id": selection_id}
                    ),
                    required=CampaignScenarioRequired.REQUIRED.value,
                )
            )
            count += 1
        db.flush()
        return {
            "campaign_id": campaign.id,
            "mission_id": selection.mission_id,
            "name": name,
            "campaign_type": campaign.campaign_type,
            "environment_id": environment_id,
            "status": campaign.status,
            "selection_id": selection_id,
            "scenario_count": count,
        }


# ────────────────────────────────────────────────────────────────────────────
# Historical risk signal collection
# ────────────────────────────────────────────────────────────────────────────


def collect_risk_signals(db: Session, mission_id: int) -> list[dict]:
    """Surface BusinessFail / recent-change risk signals for a Mission (V37-007)."""
    signals: list[dict] = []
    runs = db.scalars(
        select(ExecutionRun).where(ExecutionRun.mission_id == mission_id)
    ).all()
    for run in runs:
        if run.outcome == Outcome.BUSINESS_FAIL.value:
            signals.append(
                {
                    "scenario_id": run.scenario_id,
                    "scenario_version_id": run.scenario_version_id,
                    "risk_hint": RiskHint.LAST_BUSINESS_FAIL.value,
                    "reason": f"last execution BUSINESS_FAIL (run {run.id})",
                    "source_refs": [
                        {"type": LineageNodeType.EXECUTION_RUN.value, "id": run.id}
                    ],
                }
            )
    return signals


def detect_risk_signals(db: Session, mission_id: int, signals: list[dict]) -> dict:
    """Save a HISTORICAL_RISK ChangeSet from collected/external signals."""
    return ChangeSetService.detect(
        db, 0, mission_id, ChangeSetType.HISTORICAL_RISK.value, {}, {"signals": signals}
    )
