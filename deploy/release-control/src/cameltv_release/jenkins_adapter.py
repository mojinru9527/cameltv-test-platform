"""Render a narrow Jenkins release-job contract without contacting Jenkins."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class JenkinsReleaseCommand:
    """The only deployment inputs Jenkins may receive from the control plane."""

    release_id: str
    environment: str
    idempotency_key: str

    def as_parameters(self) -> dict[str, str]:
        """Return the non-secret release-control job parameters."""
        if self.environment != "test":
            raise ValueError("PRODUCTION_NOT_CONFIGURED")
        return {
            "RELEASE_ID": self.release_id,
            "DEPLOY_ENV": self.environment,
            "IDEMPOTENCY_KEY": self.idempotency_key,
        }


def render_jenkins_release_job() -> str:
    """Return the safe job contract; execution remains an external future adapter."""
    return """pipeline {
  parameters {
    string(name: 'RELEASE_ID', trim: true)
    string(name: 'IDEMPOTENCY_KEY', trim: true)
    choice(name: 'DEPLOY_ENV', choices: ['test'])
  }
  stages {
    stage('Release Control') {
      steps {
        sh '''#!/bin/sh
          set -eu
          test -n "$RELEASE_ID"
          test -n "$IDEMPOTENCY_KEY"
          case "$DEPLOY_ENV" in
            test) ;;
            *) echo 'PRODUCTION_NOT_CONFIGURED'; exit 2 ;;
          esac
          echo 'EXTERNAL_EXECUTOR_NOT_CONFIGURED'
          exit 2
        '''
      }
    }
  }
}"""
