from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from classify_ci_changes import classify_paths


SCRIPT = Path(__file__).with_name("classify_ci_changes.py")
ROOT = Path(__file__).resolve().parents[2]


def _workflow(name: str) -> str:
    return (ROOT / ".github" / "workflows" / name).read_text(encoding="utf-8")


def _job_block(workflow: str, job_id: str) -> str:
    match = re.search(
        rf"(?ms)^  {re.escape(job_id)}:\s*\n(.*?)(?=^  [a-zA-Z0-9_-]+:\s*\n|\Z)",
        workflow,
    )
    if not match:
        raise AssertionError(f"Missing workflow job: {job_id}")
    return match.group(0)


class ClassifyPathsTests(unittest.TestCase):
    def test_scope_matrix(self) -> None:
        cases = [
            ("docs", ["docs/adr/0014.md", "work-logs/batch.md"], False, False),
            ("git governance", ["scripts/git/verify.ps1", ".claude/skills/team/SKILL.md"], False, False),
            ("ops tooling", ["scripts/ops/release.ps1"], False, False),
            ("backend", ["test-platform-v2/backend/app/main.py"], True, False),
            ("backend submodule pointer", ["lanhu-mcp"], True, False),
            ("backend submodule config", [".gitmodules"], True, False),
            ("frontend", ["test-platform-v2/frontend/src/App.tsx"], False, True),
            (
                "mixed",
                ["test-platform-v2/backend/app/main.py", "test-platform-v2/frontend/src/App.tsx"],
                True,
                True,
            ),
            # CI 工作流/部署定义属治理层：不触发双端全量，由 ai-delivery-policy 校验
            ("workflow", [".github/workflows/main-quality-gate.yml"], False, False),
            ("deployment", ["deploy/docker-compose.yml"], False, False),
            ("jenkinsfile", ["Jenkinsfile"], False, False),
            ("release control", ["deploy/release-control/src/cameltv_release/cli.py"], False, False),
            # 平台自身部署编排仍保守双端全量
            ("platform deployment", ["test-platform-v2/deploy/docker-compose.yml"], True, True),
            ("unknown", ["new-runtime/component.bin"], True, True),
            ("empty", [], True, True),
        ]

        for label, paths, backend, frontend in cases:
            with self.subTest(label=label):
                result = classify_paths(paths)
                self.assertEqual(backend, result.backend)
                self.assertEqual(frontend, result.frontend)
                self.assertTrue(result.reasons)

    def test_markdown_is_neutral_even_inside_platform_domain(self) -> None:
        result = classify_paths(
            [
                "test-platform-v2/backend/README.md",
                "test-platform-v2/frontend/docs/usage.mdx",
            ]
        )
        self.assertFalse(result.backend)
        self.assertFalse(result.frontend)

    def test_windows_paths_are_normalized(self) -> None:
        result = classify_paths([r"test-platform-v2\frontend\src\App.tsx"])
        self.assertFalse(result.backend)
        self.assertTrue(result.frontend)

    def test_force_all_is_conservative(self) -> None:
        result = classify_paths(["docs/only.md"], force_all=True)
        self.assertTrue(result.backend)
        self.assertTrue(result.frontend)
        self.assertIn("force-all", result.reasons)


class ClassifierCliTests(unittest.TestCase):
    def test_null_delimited_file_and_github_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            changed = temp / "changed-files"
            output = temp / "github-output"
            changed.write_bytes(
                b"test-platform-v2/backend/app/main.py\0docs/change.md\0"
            )

            completed = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--files-from",
                    str(changed),
                    "--null",
                    "--github-output",
                    str(output),
                ],
                check=False,
                capture_output=True,
                text=True,
            )

            self.assertEqual(0, completed.returncode, completed.stderr)
            self.assertEqual(
                {"backend": True, "frontend": False},
                {
                    key: value
                    for key, value in json.loads(completed.stdout).items()
                    if key in {"backend", "frontend"}
                },
            )
            outputs = output.read_text(encoding="utf-8")
            self.assertIn("backend=true", outputs)
            self.assertIn("frontend=false", outputs)
            self.assertIn("reason=backend", outputs)


class WorkflowContractTests(unittest.TestCase):
    def test_required_workflows_are_not_top_level_path_filtered(self) -> None:
        for name in (
            "main-quality-gate.yml",
            "pr-check.yml",
            "ai-delivery-policy.yml",
        ):
            with self.subTest(workflow=name):
                trigger = _workflow(name).split("\njobs:", 1)[0]
                self.assertNotRegex(trigger, r"(?m)^\s+paths(?:-ignore)?:")

    def test_required_jobs_keep_names_and_fail_closed_detector_contract(self) -> None:
        workflow = _workflow("main-quality-gate.yml")
        self.assertIn("  detect_changes:", workflow)
        self.assertIn("scripts/ci/classify_ci_changes.py", workflow)
        self.assertIn("github.event.pull_request.base.sha", workflow)
        self.assertIn("github.event.pull_request.head.sha", workflow)
        # 并发取消：同一 PR 连续 push 时取消旧 run，避免排队
        self.assertIn("concurrency:", workflow)
        self.assertIn("cancel-in-progress: true", workflow)

        for job_id, display_name, domain in (
            ("backend-clean-checkout", "后端全新检出与全量回归", "backend"),
            ("frontend-clean-checkout", "前端全新检出与全量回归", "frontend"),
        ):
            with self.subTest(job=job_id):
                block = _job_block(workflow, job_id)
                self.assertIn(f"name: {display_name}", block)
                self.assertIn("needs: detect_changes", block)
                self.assertIn("if: ${{ always() }}", block)
                self.assertIn("DETECT_RESULT:", block)
                self.assertIn("DOMAIN_REQUIRED:", block)
                self.assertIn("SCOPE_REASON:", block)
                self.assertIn('"$DETECT_RESULT" != "success"', block)
                # 重型步骤按域内联执行，缺域时跳过但仍返回明确结果
                self.assertIn(
                    f"needs.detect_changes.outputs.{domain} == 'true'", block
                )

    def test_extended_jobs_are_scoped_by_domain(self) -> None:
        workflow = _workflow("pr-check.yml")
        self.assertIn("  detect_changes:", workflow)
        self.assertIn("scripts/ci/classify_ci_changes.py", workflow)

        for job_id, domain in (
            ("backend-check", "backend"),
            ("backend-check-pg", "backend"),
            ("frontend-a11y", "frontend"),
            ("frontend-check", "frontend"),
        ):
            with self.subTest(job=job_id):
                block = _job_block(workflow, job_id)
                self.assertIn("needs: detect_changes", block)
                self.assertIn(
                    f"needs.detect_changes.outputs.{domain} == 'true'", block
                )

    def test_trigger_model_split_pr_vs_push_vs_schedule(self) -> None:
        # PR 全量门禁：只在 pull_request + 手动触发；push 不再重复双端全量
        main_gate = _workflow("main-quality-gate.yml")
        self.assertNotRegex(
            main_gate.split("\njobs:", 1)[0], r"(?m)^\s+push:"
        )
        self.assertIn("workflow_dispatch:", main_gate)
        self.assertIn("--force-all", _job_block(main_gate, "detect_changes"))

        # 主干合并冒烟：push 到 main 的轻量校验
        merge_smoke = _workflow("main-merge-smoke.yml")
        self.assertIn("push:\n    branches: [main]", merge_smoke)
        self.assertIn("alembic", _job_block(merge_smoke, "merge-smoke"))
        self.assertIn("npm run typecheck", _job_block(merge_smoke, "merge-smoke"))

        # 观察项：每日定时 + 手动，不再挂 PR
        extended = _workflow("pr-check.yml")
        trigger = extended.split("\njobs:", 1)[0]
        self.assertNotRegex(trigger, r"(?m)^\s+pull_request:")
        self.assertRegex(trigger, r"(?m)^\s+schedule:")
        self.assertIn("workflow_dispatch:", extended)
        self.assertIn("--force-all", _job_block(extended, "detect_changes"))

    def test_ai_policy_runs_scope_contract_tests_and_governance_checks(self) -> None:
        workflow = _workflow("ai-delivery-policy.yml")
        block = _job_block(workflow, "delivery-policy")
        self.assertIn("name: AI/Git 交付策略", block)
        self.assertIn("python scripts/ci/test_classify_ci_changes.py", block)
        # 治理层配套：workflow YAML 语法校验 + deploy/release-control 冒烟
        self.assertIn(".github/workflows/*.yml", block)
        self.assertIn("deploy/release-control", block)


if __name__ == "__main__":
    unittest.main()
