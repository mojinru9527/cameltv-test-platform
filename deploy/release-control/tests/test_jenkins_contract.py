from __future__ import annotations

from cameltv_release.jenkins_adapter import JenkinsReleaseCommand, render_jenkins_release_job


def test_jenkins_release_command_accepts_only_test_release_identity() -> None:
    command = JenkinsReleaseCommand(
        release_id="b62-test-20260802-0001",
        environment="test",
        idempotency_key="release-request-1",
    )

    assert command.as_parameters() == {
        "RELEASE_ID": "b62-test-20260802-0001",
        "DEPLOY_ENV": "test",
        "IDEMPOTENCY_KEY": "release-request-1",
    }


def test_jenkins_release_command_rejects_production() -> None:
    command = JenkinsReleaseCommand(
        release_id="b62-test-20260802-0001",
        environment="production",
        idempotency_key="production-request-1",
    )

    try:
        command.as_parameters()
    except ValueError as error:
        assert str(error) == "PRODUCTION_NOT_CONFIGURED"
    else:
        raise AssertionError("production command unexpectedly accepted")


def test_jenkins_release_job_has_no_source_build_or_production_deploy_path() -> None:
    job = render_jenkins_release_job()

    assert "RELEASE_ID" in job
    assert "IDEMPOTENCY_KEY" in job
    assert "PRODUCTION_NOT_CONFIGURED" in job
    assert "EXTERNAL_EXECUTOR_NOT_CONFIGURED" in job
    for forbidden in ("checkout", "docker build", ":latest", "docker compose", "git clone"):
        assert forbidden not in job.lower()
