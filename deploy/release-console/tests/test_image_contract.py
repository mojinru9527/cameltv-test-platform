"""C249-5：沿用旧镜像前的核对逻辑（纯函数 + 真实仓库源码）。"""
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import image_contract  # noqa: E402 - conftest.py 已加路径

ROOT = pathlib.Path(__file__).resolve().parents[3]
REAL_ENDPOINTS_FILE = ROOT / "test-platform-v2" / "backend" / "app" / "core" / "execution_dispatch.py"

SOURCE = """
RUNNER_ENDPOINTS = {
    'app.api.v1.requirement_ai_generate': {'generate_test_cases'},
    'app.api.v1.foo': {'a', 'b'},
}
"""


class ParseRunnerEndpointsTests(unittest.TestCase):
    def test_parses_modules_and_endpoints(self):
        parsed = image_contract.parse_runner_endpoints(SOURCE)
        self.assertEqual(sorted(parsed), ["app.api.v1.foo", "app.api.v1.requirement_ai_generate"])
        self.assertEqual(parsed["app.api.v1.foo"], ["a", "b"])

    def test_parses_the_real_repo_source(self):
        """真实源码必须仍是字面量（否则沿用镜像的核对会直接 fail-closed）。"""
        parsed = image_contract.parse_runner_endpoints(
            REAL_ENDPOINTS_FILE.read_text(encoding="utf-8")
        )
        self.assertTrue(parsed, "RUNNER_ENDPOINTS 不应为空")

    def test_missing_definition_raises(self):
        with self.assertRaises(ValueError):
            image_contract.parse_runner_endpoints("X = 1\n")

    def test_non_literal_definition_raises(self):
        with self.assertRaises(ValueError):
            image_contract.parse_runner_endpoints("RUNNER_ENDPOINTS = dict(foo=None)\n")


class ContractDiffTests(unittest.TestCase):
    def test_reports_missing_module_and_endpoints(self):
        repo = {"m1": ["a", "b"], "m2": ["c"]}
        image = {"m1": ["a"]}
        self.assertEqual(
            image_contract.contract_diff(repo, image),
            {"m1": ["b"], "m2": ["c"]},
        )

    def test_no_gap_when_image_is_superset(self):
        repo = {"m1": ["a"]}
        image = {"m1": ["a", "extra"], "m2": ["x"]}
        self.assertEqual(image_contract.contract_diff(repo, image), {})


class VerifyImageTests(unittest.TestCase):
    def test_ok_when_paths_and_contract_match(self):
        report = image_contract.verify_image(
            root="/app",
            part="runner",
            repo_source=SOURCE,
            exists={path: True for path in image_contract.required_paths("runner")},
            image_source=SOURCE,
        )
        self.assertTrue(report["ok"], report)

    def test_reports_missing_paths_and_endpoints(self):
        report = image_contract.verify_image(
            root="/app",
            part="runner",
            repo_source=SOURCE,
            exists={"alembic": True, "alembic/versions": False, "alembic.ini": True,
                    image_contract.RUNNER_ENDPOINTS_FILE: True},
            image_source="RUNNER_ENDPOINTS = {'app.api.v1.foo': {'a'}}\n",
        )
        self.assertFalse(report["ok"])
        self.assertEqual(report["missing_paths"], ["alembic/versions"])
        self.assertEqual(report["missing_endpoints"], {"app.api.v1.foo": ["b"],
                                                       "app.api.v1.requirement_ai_generate": ["generate_test_cases"]})

    def test_contract_error_when_image_has_no_endpoints_definition(self):
        report = image_contract.verify_image(
            root="/app",
            part="runner",
            repo_source=SOURCE,
            exists={path: True for path in image_contract.required_paths("runner")},
            image_source="X = 1\n",
        )
        self.assertFalse(report["ok"])
        self.assertIn("RUNNER_ENDPOINTS", report["contract_error"])

    def test_unknown_part_is_rejected(self):
        with self.assertRaises(ValueError):
            image_contract.required_paths("no-such-part")


if __name__ == "__main__":
    unittest.main()
