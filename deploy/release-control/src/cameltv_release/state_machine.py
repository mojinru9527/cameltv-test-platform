"""Legal, fail-closed state transitions for the local release-control core."""
from __future__ import annotations

from cameltv_release.contracts import ReleaseManifest
from cameltv_release.store import CreateDeploymentResult, ReleaseStore


_ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    "DRAFT": {"VALIDATED"},
    "VALIDATED": {"TEST_DEPLOYING", "TEST_FAILED"},
    "TEST_DEPLOYING": {"TEST_VERIFYING", "TEST_FAILED"},
    "TEST_VERIFYING": {"TEST_VERIFIED", "TEST_FAILED"},
    "TEST_FAILED": {"TEST_ROLLING_BACK"},
    "TEST_ROLLING_BACK": {"TEST_ROLLED_BACK"},
}


class ReleaseControlService:
    """Test-only command facade with no runner, Docker, or network integration."""

    def __init__(self, store: ReleaseStore) -> None:
        self.store = store

    def request_test_deploy(
        self,
        manifest: ReleaseManifest,
        environment: str,
        actor: str,
        idempotency_key: str,
    ) -> CreateDeploymentResult:
        """Create or replay a test deployment; every other environment fails closed."""
        if environment != "test":
            return CreateDeploymentResult(code="PRODUCTION_NOT_CONFIGURED")
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
