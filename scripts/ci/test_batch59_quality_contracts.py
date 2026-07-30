"""Batch 59 regression contracts for repository-owned CI configuration.

These tests protect the exact failure modes found in the Batch 50–58 audit:
required PostgreSQL concurrency tests being skipped, frontend checks reporting
success without running, and Jenkins using stale runtime/build assumptions.
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MAIN_GATE = ROOT / ".github" / "workflows" / "main-quality-gate.yml"
PR_CHECK = ROOT / ".github" / "workflows" / "pr-check.yml"
JENKINSFILE = ROOT / "Jenkinsfile"
JENKINS_IMAGE = ROOT / "deploy" / "jenkins" / "Dockerfile"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _job_block(workflow: str, job_id: str) -> str:
    """Return one top-level workflow job for focused policy assertions."""
    match = re.search(
        rf"(?ms)^  {re.escape(job_id)}:\s*\n(.*?)(?=^  [a-zA-Z0-9_-]+:\s*\n|\Z)",
        workflow,
    )
    if not match:
        raise AssertionError(f"Missing workflow job: {job_id}")
    return match.group(0)


def _step_block(job: str, step_name: str) -> str:
    """Return a named workflow step without matching adjacent step policy."""
    match = re.search(
        rf"(?ms)^\s+- name: {re.escape(step_name)}\s*\n"
        rf"(.*?)(?=^\s+- (?:name:|uses:)|\Z)",
        job,
    )
    if not match:
        raise AssertionError(f"Missing workflow step: {step_name}")
    return match.group(0)


class FrontendQualityContractTests(unittest.TestCase):
    def test_frontend_checks_use_repository_scripts_and_fail_closed(self) -> None:
        workflow = _read(PR_CHECK)
        frontend = _job_block(workflow, "frontend-check")

        for name, command in (
            ("Lint", "npm run lint"),
            ("Unit Tests + Coverage", "npm run test:coverage"),
        ):
            with self.subTest(step=name):
                step = _step_block(frontend, name)
                self.assertIn(command, step)
                self.assertNotIn("continue-on-error", step)
                self.assertNotRegex(step, r"\|\|\s*(?:true|echo)")

    def test_a11y_uses_locked_playwright_and_fails_closed(self) -> None:
        workflow = _read(PR_CHECK)
        a11y = _job_block(workflow, "frontend-a11y")
        self.assertIn("npx playwright install --with-deps chromium", a11y)
        step = _step_block(a11y, "A11y Scan")
        self.assertIn("npm run test:a11y:ci", step)
        self.assertNotIn("continue-on-error", step)
        self.assertNotRegex(step, r"npm run test:a11y:ci\s*\|\|")


class PostgreSQLGateContractTests(unittest.TestCase):
    def _assert_pg_concurrency_gate(self, workflow_path: Path, job_id: str) -> None:
        workflow = _read(workflow_path)
        job = _job_block(workflow, job_id)
        self.assertIn("postgres:16-alpine", job)
        self.assertIn("BATCH48_RUN_PG_INTEGRATION: '1'", job)
        self.assertIn("BATCH48_PG_INTEGRATION_URL:", job)
        self.assertIn("test_batch48_postgresql_concurrency.py", job)
        self.assertIn("alembic upgrade head", job)

    def test_required_gate_runs_postgresql_concurrency_regressions(self) -> None:
        self._assert_pg_concurrency_gate(MAIN_GATE, "backend_tests")

    def test_extended_pg_gate_runs_postgresql_concurrency_regressions(self) -> None:
        self._assert_pg_concurrency_gate(PR_CHECK, "backend-check-pg")


class JenkinsRuntimeContractTests(unittest.TestCase):
    def test_jenkins_uses_current_node_and_root_backend_context(self) -> None:
        jenkins = _read(JENKINSFILE)
        jenkins_image = _read(JENKINS_IMAGE)
        self.assertIn("NODE_VERSION   = '22.22.0'", jenkins)
        self.assertIn("node --version", jenkins)
        self.assertIn("https://deb.nodesource.com/setup_22.x", jenkins_image)
        self.assertNotIn("setup_20.x", jenkins_image)
        self.assertIn(
            "docker build -t ${BACKEND_IMAGE}:${tag} "
            "-t ${BACKEND_IMAGE}:latest "
            "-f test-platform-v2/backend/Dockerfile .",
            jenkins,
        )

    def test_jenkins_generates_every_required_test_deployment_secret(self) -> None:
        jenkins = _read(JENKINSFILE)
        for key in (
            "SECRET_KEY",
            "ADMIN_PASSWORD",
            "TESTER_PASSWORD",
            "POSTGRES_PASSWORD",
            "DATABASE_URL",
        ):
            with self.subTest(key=key):
                self.assertIn(f'set_env_value "{key}"', jenkins)
        self.assertNotIn("please-change-me", jenkins)
        self.assertIn("get_or_create_secret", jenkins)
        self.assertIn("if [ ! -f .env ]; then", jenkins)
        self.assertNotIn("cp .env.example .env\n\n", jenkins)

    def test_jenkins_shell_gates_fail_fast_and_smoke_the_backend_container(self) -> None:
        jenkins = _read(JENKINSFILE)
        self.assertGreaterEqual(jenkins.count("set -euo pipefail"), 5)
        self.assertIn("docker compose exec -T backend python -c", jenkins)
        self.assertIn("http://localhost:8000/health", jenkins)
        self.assertNotIn("curl -s -o /dev/null -w '%{http_code}' http://localhost/health", jenkins)


if __name__ == "__main__":
    unittest.main()
