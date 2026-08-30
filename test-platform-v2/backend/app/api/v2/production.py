"""AITDE V3.6 production API (V36-013/014).

Production is an Evidence Source, not a Test Runtime. All endpoints operate in a
read-only posture enforced by the policy/service layer; the security boundary is
``ReadOnlyBrowserPolicy`` / ``ProductionDbGuard`` + a truly read-only DB account,
never the UI. Sensitive values are never returned.
"""
from __future__ import annotations

import json

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.v2.deps import require_aitde_v3
from app.core.deps import CurrentUser, get_current_user, get_db
from app.modules.aitde.production import repository as repo
from app.modules.aitde.production import services, schemas
from app.schemas.common import R

router = APIRouter(
    prefix="/production",
    tags=["AITDE - Production Evidence"],
    dependencies=[Depends(require_aitde_v3)],
)


@router.post("/observation-sessions", response_model=R[dict])
def start_observation_session(
    payload: schemas.ObservationSessionCreate,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    sid = services.production_observer_service.start(
        db,
        project_id=payload.project_id,
        environment_id=payload.environment_id,
        mission_id=payload.mission_id,
        worker_id=payload.worker_id,
        mode=payload.mode.value,
        started_by=payload.started_by or current.user.id,
        policy_version=payload.policy_version,
    )
    return R.ok({"id": sid})


@router.post("/observation-sessions/{session_id}/stop", response_model=R[dict])
def stop_observation_session(
    session_id: int,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    services.production_observer_service.stop(db, session_id, user_id=current.user.id)
    return R.ok({"id": session_id})


@router.get("/observation-sessions/{session_id}", response_model=R[dict])
def get_observation_session(
    session_id: int,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return R.ok(services.production_observer_service.status(db, session_id))


@router.get("/journeys", response_model=R[list])
def list_journeys(
    session_id: int | None = None,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    rows = repo.list_journeys(db, current.project_id or 0, session_id)
    return R.ok(
        [
            {
                "id": r.id,
                "project_id": r.project_id,
                "session_id": r.session_id,
                "name": r.name,
                "journey_hash": r.journey_hash,
                "summary_json": r.summary_json,
                "source_ref_json": r.source_ref_json,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ]
    )


@router.get("/journeys/{journey_id}", response_model=R[dict])
def get_journey(
    journey_id: int,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    row = repo.get_journey(db, journey_id)
    if row is None:
        return R.err(code=404, msg="journey not found")
    steps = repo.list_journey_steps(db, journey_id)
    return R.ok(
        {
            "id": row.id,
            "project_id": row.project_id,
            "session_id": row.session_id,
            "name": row.name,
            "journey_hash": row.journey_hash,
            "summary_json": json.loads(row.summary_json or "{}"),
            "source_ref_json": json.loads(row.source_ref_json or "{}"),
            "created_at": row.created_at.isoformat() if row.created_at else None,
            "steps": [
                {
                    "sequence": s.sequence,
                    "event_type": s.event_type,
                    "semantic_action": json.loads(s.semantic_action_json or "{}"),
                    "url_template": s.url_template,
                    "xhr_refs": json.loads(s.xhr_refs_json or "{}"),
                    "evidence_refs": json.loads(s.evidence_refs_json or "[]"),
                }
                for s in steps
            ],
        }
    )


@router.post("/data/inspect", response_model=R[dict])
def inspect_data(
    payload: schemas.DbInspectRequest,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # The row provider is a no-op for a plain API call; service-layer guards and
    # query audit still run. Real probes are driven by a capability worker.
    result = services.production_db_explorer.inspect(
        db,
        project_id=payload.project_id,
        data_source_id=payload.data_source_id,
        session_id=payload.session_id,
        sql=payload.sql,
        schema=payload.schema_name,
        table_names=payload.table_names,
    )
    return R.ok(result)


@router.post("/entity-graphs/extract", response_model=R[dict])
def extract_entity_graph(
    payload: schemas.EntityGraphExtractRequest,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    graph, content_hash = services.entity_graph_extractor.extract(
        root_entity_type=payload.root_entity_type,
        root_ref_hash=payload.root_ref_hash,
        child_loader=lambda *a: [],
    )
    row = repo.create_entity_graph_snapshot(
        db,
        {
            "project_id": payload.project_id,
            "mission_id": payload.mission_id,
            "source_environment_id": payload.source_environment_id,
            "root_entity_type": payload.root_entity_type,
            "root_ref_hash": payload.root_ref_hash,
            "graph_json": json.dumps(graph, ensure_ascii=False),
            "content_hash": content_hash,
        },
    )
    return R.ok({"id": row.id, "content_hash": content_hash, "nodes": len(graph["nodes"]), "edges": len(graph["edges"])})


@router.post("/templates", response_model=R[dict])
def build_template(
    payload: schemas.TemplateBuildRequest,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    snapshot = repo.get_entity_graph_snapshot(db, payload.entity_graph_snapshot_id)
    if snapshot is None:
        return R.err(code=404, msg="entity graph snapshot not found")
    rules = repo.list_masking_rules(db, payload.masking_profile_id) if payload.masking_profile_id else []
    template = services.prod_template_builder.build(
        name=payload.name,
        graph=json.loads(snapshot.graph_json or "{}"),
        masking_profile_id=payload.masking_profile_id,
        rules=rules,
        project_id=payload.project_id,
        mission_id=payload.mission_id,
        created_by=payload.created_by or current.user.id,
    )
    row = repo.create_prod_template(
        db,
        {
            "project_id": payload.project_id,
            "mission_id": payload.mission_id,
            "name": payload.name,
            "entity_graph_snapshot_id": payload.entity_graph_snapshot_id,
            "masking_profile_id": payload.masking_profile_id,
            "template_json": json.dumps(template, ensure_ascii=False),
            "validation_status": "PENDING",
            "created_by": payload.created_by or current.user.id,
        },
    )
    return R.ok({"id": row.id, "validation_status": row.validation_status})


@router.post("/templates/{template_id}/validate", response_model=R[dict])
def validate_template(
    template_id: int,
    payload: schemas.TemplateValidateRequest,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    row = repo.get_prod_template(db, template_id)
    if row is None:
        return R.err(code=404, msg="template not found")
    template = json.loads(row.template_json or "{}")
    report = services.masking_service.validation_report(
        profile_id=row.masking_profile_id or 0, record=template
    )
    status = "VALID" if report["valid"] else "INVALID"
    repo.update_prod_template(db, template_id, {"validation_status": status})
    return R.ok({"validation_status": status, "leaks": report["leaks"]})


@router.post("/templates/{template_id}/materialize", response_model=R[dict])
def materialize_template(
    template_id: int,
    payload: schemas.TemplateMaterializeRequest,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    mid = services.template_materializer.materialize(
        db,
        template_id=template_id,
        target_environment_id=payload.target_environment_id,
        project_id=payload.project_id,
    )
    return R.ok({"materialization_id": mid})


@router.post("/evidence/{journey_id}/analyze-gaps", response_model=R[dict])
def analyze_gaps(
    journey_id: int,
    payload: schemas.GapAnalysisRequest,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    row = repo.get_journey(db, journey_id)
    if row is None:
        return R.err(code=404, msg="journey not found")
    journey = {
        "events": [
            {
                "url": s.url_template,
                "semantic_action": json.loads(s.semantic_action_json or "{}"),
            }
            for s in repo.list_journey_steps(db, journey_id)
        ]
    }
    proposals = services.production_evidence_to_design_service.analyze_gaps(journey=journey)
    return R.ok(
        [
            {"kind": p["kind"], "title": p["title"], "confidence": p["confidence"], "auto_approved": p.get("auto_approved", False)}
            for p in proposals
        ]
    )
