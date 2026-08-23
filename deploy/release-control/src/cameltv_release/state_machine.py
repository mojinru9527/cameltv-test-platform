"""Legal, fail-closed state transitions for the local release-control core."""
from __future__ import annotations

from cameltv_release.contracts import ReleaseManifest
from cameltv_release.store import CreateDeploymentResult, ReleaseStore


_ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    "DRAFT": {"VALIDATED", "CANCELLED"},
    "VALIDATED": {"TEST_DEPLOYING", "TEST_FAILED", "PROD_DEPLOYING", "CANCELLED"},
    "TEST_DEPLOYING": {"TEST_VERIFYING", "TEST_FAILED"},
    "TEST_VERIFYING": {"TEST_VERIFIED", "TEST_FAILED"},
    "TEST_FAILED": {"TEST_ROLLING_BACK"},
    "TEST_ROLLING_BACK": {"TEST_ROLLED_BACK"},
    # 腾讯云 production 链路（release-platform batch）
    "TEST_VERIFIED": {"PROD_DEPLOYING", "CANCELLED"},
    "PROD_DEPLOYING": {"PROD_OBSERVING", "PROD_FAILED"},
    "PROD_OBSERVING": {"PRODUCTION_VERIFIED", "PROD_FAILED"},
    "PROD_FAILED": {"PROD_ROLLING_BACK"},
    "PROD_ROLLING_BACK": {"PROD_ROLLED_BACK"},
    "SUPERSEDED": set(),
    "CANCELLED": set(),
}


_TERMINAL_OR_UNLOCK_STATES = {
    "TEST_VERIFIED",
    "TEST_FAILED",
    "TEST_ROLLED_BACK",
    "PRODUCTION_VERIFIED",
    "PROD_FAILED",
    "PROD_ROLLED_BACK",
    "CANCELLED",
}


class ReleaseControlService:
    """Command facade with no runner, Docker, or network integration.

    Executor execution is deliberately outside this service: callers run the
    executor first, then record outcomes through legal transitions.
    """

    def __init__(self, store: ReleaseStore) -> None:
        self.store = store

    def request_deploy(
        self,
        manifest: ReleaseManifest,
        environment: str,
        actor: str,
        idempotency_key: str,
    ) -> CreateDeploymentResult:
        """Create or replay a deployment for test or production."""
        if environment not in {"test", "production"}:
            return CreateDeploymentResult(code="UNSUPPORTED_ENVIRONMENT")
        return self.store.create_deployment(manifest, environment, actor, idempotency_key)

    def transition(self, deployment_id: str, to_state: str, phase: str, actor: str = "system") -> CreateDeploymentResult:
        """Move a deployment through one legal transition without executing infrastructure."""
        try:
            deployment = self.store.get_deployment(deployment_id)
        except KeyError:
            return CreateDeploymentResult(code="DEPLOYMENT_NOT_FOUND")
        if to_state not in _ALLOWED_TRANSITIONS.get(deployment.state, set()):
            return CreateDeploymentResult(code="INVALID_TRANSITION", deployment=deployment)
        changed = self.store.transition_deployment(
            deployment_id,
            deployment.state,
            to_state,
            phase,
            f"state transition to {to_state}",
            actor,
        )
        if not changed:
            return CreateDeploymentResult(code="INVALID_TRANSITION")
        return CreateDeploymentResult(code="ACCEPTED", deployment=self.store.get_deployment(deployment_id))
