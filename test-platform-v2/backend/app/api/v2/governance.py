"""AITDE v2 Enterprise Governance API (V40-009..020).

Exposes the governance services (retention / model policy / cost / DR /
readiness / RBAC / encryption / backup / SSO / acceptance report) under
``/api/v2`` and feature-gated. The family is read-mostly with explicit POST
actions; it never mutates production facts.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.v2.deps import require_aitde_v3
from app.core.deps import CurrentUser, get_db, require_permission
from app.modules.aitde.governance import service
from app.schemas.common import R

router = APIRouter(
    tags=["AITDE - Enterprise Governance"], dependencies=[Depends(require_aitde_v3)]
)


# ── Platform Readiness Gate (V40-018) ───────────────────────────────────────


@router.post("/governance/readiness", response_model=R[dict])
def evaluate_readiness(
    metrics: dict,
    current: CurrentUser = Depends(require_permission("governance:detail")),
    db: Session = Depends(get_db),
):
    return R.ok(service.PlatformReadinessEvaluator.evaluate(metrics))


# ── Encryption / Backup / SSO posture (V40-013/016/009) ─────────────────────


@router.get("/governance/encryption", response_model=R[dict])
def encryption_posture(
    current: CurrentUser = Depends(require_permission("governance:detail")),
    db: Session = Depends(get_db),
):
    return R.ok(service.EncryptionVerificationService.verify())


@router.get("/governance/backup", response_model=R[dict])
def backup_posture(
    current: CurrentUser = Depends(require_permission("governance:detail")),
    db: Session = Depends(get_db),
):
    return R.ok(service.BackupVerificationService.describe())


@router.get("/governance/sso", response_model=R[dict])
def sso_config(
    current: CurrentUser = Depends(require_permission("governance:detail")),
    db: Session = Depends(get_db),
):
    return R.ok(service.SsoService.describe())


# ── Retention (V40-012) ─────────────────────────────────────────────────────


@router.get("/governance/retention/evaluate", response_model=R[dict])
def retention_evaluate(
    artifact_type: str,
    sensitivity: str,
    age_days: int,
    current: CurrentUser = Depends(require_permission("governance:detail")),
    db: Session = Depends(get_db),
):
    return R.ok(
        service.RetentionService.evaluate(db, artifact_type, sensitivity, age_days)
    )


# ── Model policy (V40-014) ──────────────────────────────────────────────────


@router.post("/governance/models/check", response_model=R[dict])
def model_check(
    provider: str,
    model: str,
    sensitivity: str,
    current: CurrentUser = Depends(require_permission("governance:detail")),
    db: Session = Depends(get_db),
):
    return R.ok(
        service.ModelPolicyService.is_allowed(db, provider, model, sensitivity)
    )


# ── Cost ledger (V40-015) ───────────────────────────────────────────────────


@router.get("/governance/cost", response_model=R[dict])
def cost_usage(
    current: CurrentUser = Depends(require_permission("governance:detail")),
    db: Session = Depends(get_db),
):
    return R.ok(service.CostLedgerService.project_usage(db, current.project_id or 0))


# ── DR drills (V40-017) ─────────────────────────────────────────────────────


@router.get("/governance/dr", response_model=R[list[dict]])
def dr_runs(
    current: CurrentUser = Depends(require_permission("governance:detail")),
    db: Session = Depends(get_db),
):
    return R.ok(service.DrTestService.list(db, current.project_id or 0))


# ── RBAC cross-project matrix (V40-010) ─────────────────────────────────────


@router.post("/governance/rbac/cross-project", response_model=R[dict])
def rbac_cross_project(
    user_id: int,
    granted_project: int,
    denied_projects: list[int],
    permission_code: str,
    current: CurrentUser = Depends(require_permission("governance:detail")),
    db: Session = Depends(get_db),
):
    return R.ok(
        service.RbacPolicyService.cross_project_report(
            db, user_id, granted_project, denied_projects, permission_code
        )
    )


# ── Acceptance Report (V40-020) ─────────────────────────────────────────────


@router.post("/governance/acceptance-report", response_model=R[dict])
def acceptance_report(
    inputs: dict,
    current: CurrentUser = Depends(require_permission("governance:detail")),
    db: Session = Depends(get_db),
):
    return R.ok(service.AcceptanceReportService.build(inputs))
