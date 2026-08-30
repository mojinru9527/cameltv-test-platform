"""AITDE v2 AI QA Closed Loop API (V38).

Failure triage, healing apply, flaky, strategy performance, scenario gap,
suggestion inbox, human feedback and offline model evaluation. Mounted under
``/api/v2`` and feature-gated. Safety invariants are enforced in the service
layer — the router only passes through and never broadens them.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.v2.deps import require_aitde_v3
from app.core.deps import CurrentUser, get_db, require_permission
from app.modules.aitde.ai_closed_loop import service
from app.modules.aitde.ai_closed_loop.schemas import (
    FeedbackIn,
    GapConvertIn,
    HealingApplyIn,
    HypothesisReviewIn,
    ModelEvaluationIn,
    SuggestionReviewIn,
    TriageIn,
)
from app.schemas.common import R

router = APIRouter(
    tags=["AITDE - AI QA Closed Loop"], dependencies=[Depends(require_aitde_v3)]
)


def _issue_404(msg: str) -> None:
    from app.core.exceptions import APIException

    raise APIException(code=404, msg=msg, http_status=404)


@router.post("/runs/{run_id}/triage", response_model=R[dict])
def triage_run(
    run_id: int,
    payload: TriageIn,
    current: CurrentUser = Depends(require_permission("execution:detail")),
    db: Session = Depends(get_db),
):
    try:
        return R.ok(
            service.FailureTriageAgent.triage(
                db,
                run_id,
                payload.context,
                payload.model_ref,
                payload.prompt_version,
            )
        )
    except ValueError as exc:
        _issue_404(str(exc))


@router.get("/runs/{run_id}/hypotheses", response_model=R[list])
def list_hypotheses(
    run_id: int,
    current: CurrentUser = Depends(require_permission("execution:detail")),
    db: Session = Depends(get_db),
):
    return R.ok(service.FailureTriageAgent.list_hypotheses(db, run_id))


@router.post(
    "/hypotheses/{hypothesis_id}/review", response_model=R[dict]
)
def review_hypothesis(
    hypothesis_id: int,
    payload: HypothesisReviewIn,
    current: CurrentUser = Depends(require_permission("execution:update")),
    db: Session = Depends(get_db),
):
    try:
        return R.ok(
            service.HypothesisReviewService.review(
                db, hypothesis_id, payload.status, payload.reviewed_by, payload.reason
            )
        )
    except ValueError as exc:
        _issue_404(str(exc))


@router.post("/healing-proposals/{proposal_id}/apply", response_model=R[dict])
def apply_healing(
    proposal_id: int,
    payload: HealingApplyIn,
    current: CurrentUser = Depends(require_permission("execution:update")),
    db: Session = Depends(get_db),
):
    try:
        return R.ok(
            service.ApprovedHealingApply.apply(
                db, proposal_id, payload.approved_by, payload.note
            )
        )
    except ValueError as exc:
        _issue_404(str(exc))


@router.get("/flaky", response_model=R[list])
def list_flaky(
    scenario_adapter_id: int | None = Query(default=None),
    current: CurrentUser = Depends(require_permission("execution:list")),
    db: Session = Depends(get_db),
):
    return R.ok(service.FlakyClusterService.list(db, scenario_adapter_id))


@router.get("/scenarios/{scenario_id}/stability", response_model=R[dict])
def scenario_stability(
    scenario_id: int,
    current: CurrentUser = Depends(require_permission("mission:detail")),
    db: Session = Depends(get_db),
):
    return R.ok(service.FlakyClusterService.stability(db, scenario_id))


@router.get("/ai-suggestions", response_model=R[list])
def list_suggestions(
    status: str | None = Query(default=None),
    current: CurrentUser = Depends(require_permission("execution:list")),
    db: Session = Depends(get_db),
):
    return R.ok(
        service.SuggestionInboxService.list(db, current.project_id or 0, status)
    )


@router.post("/ai-suggestions/{suggestion_id}/review", response_model=R[dict])
def review_suggestion(
    suggestion_id: int,
    payload: SuggestionReviewIn,
    current: CurrentUser = Depends(require_permission("execution:update")),
    db: Session = Depends(get_db),
):
    try:
        return R.ok(
            service.SuggestionInboxService.review(
                db, suggestion_id, payload.status, payload.reviewed_by, payload.reason
            )
        )
    except ValueError as exc:
        _issue_404(str(exc))


@router.get("/missions/{mission_id}/scenario-gaps", response_model=R[list])
def list_gaps(
    mission_id: int,
    current: CurrentUser = Depends(require_permission("mission:detail")),
    db: Session = Depends(get_db),
):
    return R.ok(service.ScenarioGapDetector.list(db, mission_id))


@router.post("/scenario-gaps/{gap_id}/convert", response_model=R[dict])
def convert_gap(
    gap_id: int,
    payload: GapConvertIn,
    current: CurrentUser = Depends(require_permission("mission:update")),
    db: Session = Depends(get_db),
):
    try:
        return R.ok(
            service.ScenarioGapDetector.convert(
                db, gap_id, payload.title, payload.risk_level
            )
        )
    except ValueError as exc:
        _issue_404(str(exc))


@router.post("/feedback", response_model=R[dict])
def add_feedback(
    payload: FeedbackIn,
    current: CurrentUser = Depends(require_permission("execution:list")),
    db: Session = Depends(get_db),
):
    return R.ok(
        service.HumanFeedbackService.add(
            db, {**payload.model_dump(), "created_by": current.user.id}
        )
    )


@router.get("/feedback", response_model=R[list])
def list_feedback(
    target_type: str | None = Query(default=None),
    current: CurrentUser = Depends(require_permission("execution:list")),
    db: Session = Depends(get_db),
):
    return R.ok(
        service.HumanFeedbackService.list(db, current.project_id or 0, target_type)
    )


@router.post("/model-evaluations", response_model=R[dict])
def create_model_evaluation(
    payload: ModelEvaluationIn,
    current: CurrentUser = Depends(require_permission("execution:update")),
    db: Session = Depends(get_db),
):
    return R.ok(
        service.PromptEvaluationService.evaluate(
            db, payload.model_dump()
        )
    )


@router.get("/model-evaluations", response_model=R[list])
def list_model_evaluations(
    current: CurrentUser = Depends(require_permission("execution:list")),
    db: Session = Depends(get_db),
):
    return R.ok(service.PromptEvaluationService.list(db))


@router.get("/model-evaluations/regression-check", response_model=R[dict])
def model_eval_regression_check(
    evaluation_suite: str = Query(default=""),
    current: CurrentUser = Depends(require_permission("execution:list")),
    db: Session = Depends(get_db),
):
    return R.ok(
        service.PromptEvaluationService.check_regression(db, evaluation_suite)
    )
