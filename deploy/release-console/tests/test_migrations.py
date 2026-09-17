import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import migrations  # noqa: E402 - conftest.py 已加路径；此处保留兼容直接 py 执行


class TargetRevisionTests(unittest.TestCase):
    def test_accepts_real_revision(self):
        manifest = {"database": {"target_revision": "20260922_ai_agent_token"}}
        self.assertEqual(migrations.target_revision(manifest), "20260922_ai_agent_token")

    def test_rejects_placeholder(self):
        manifest = {"database": {"target_revision": "see-verified-head"}}
        with self.assertRaises(migrations.MigrationNotConfigured):
            migrations.target_revision(manifest)

    def test_rejects_missing_or_malformed(self):
        for manifest in ({}, {"database": {}}, {"database": {"target_revision": "bad revision!"}}):
            with self.assertRaises((migrations.MigrationNotConfigured, migrations.MigrationFailed)):
                migrations.target_revision(manifest)


class SingleHeadTests(unittest.TestCase):
    def test_parses_noisy_output(self):
        output = (
            "INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.\n"
            "INFO  [alembic.runtime.migration] Will assume transactional DDL.\n"
            "20260922_ai_agent_token (batch27) (head)\n"
        )
        self.assertEqual(migrations.single_head(output), "20260922_ai_agent_token")

    def test_rejects_multiple_heads(self):
        output = "20260901_a (head)\n20260902_b (head)\n"
        with self.assertRaises(migrations.MigrationFailed):
            migrations.single_head(output)

    def test_rejects_empty_output(self):
        with self.assertRaises(migrations.MigrationFailed):
            migrations.single_head("")


class MigrationCommandTests(unittest.TestCase):
    def compose(self, *args):
        return "docker compose " + " ".join(args)

    def test_builds_upgrade_then_verified_current(self):
        commands = migrations.migration_commands(self.compose, target="20260922_ai_agent_token")
        self.assertEqual(len(commands), 2)
        self.assertIn("alembic upgrade 20260922_ai_agent_token", commands[0])
        self.assertIn("--no-deps", commands[0])
        self.assertIn("alembic current", commands[1])
        self.assertIn("= 20260922_ai_agent_token", commands[1])

    def test_rejects_placeholder_target(self):
        with self.assertRaises(migrations.MigrationFailed):
            migrations.migration_commands(self.compose, target="see-verified-head")


if __name__ == "__main__":
    unittest.main()
