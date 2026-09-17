"""C250-1：迁移状态必须取自**完整远端输出**，不能依赖被截断的 ``logs``。"""
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from tencent_executor import ExecutorConfig, TencentSshExecutor  # noqa: E402 - conftest.py 已加路径

HEAD = "20260922_ai_agent_token"
STATUS_LINE = f"CAMELTV_MIGRATION target={HEAD} actual={HEAD}"


def _manifest() -> dict:
    return {
        "schema_version": "1.0",
        "release_id": "release-20260917-0007",
        "git_sha": "a" * 40,
        "runtime_mode": "split",
        "database": {"alembic_heads": [HEAD], "target_revision": HEAD},
        "execution_config_sha256": "b" * 64,
        "backend": {"image": "cameltv-tp-backend", "digest": "sha256:" + "c" * 64},
        "frontend": {"image": "cameltv-tp-frontend", "digest": "sha256:" + "d" * 64},
        "runner": {"image": "cameltv-tp-runner", "digest": "sha256:" + "e" * 64},
        "ai-gateway": {"image": "cameltv-tp-ai-gateway", "digest": "sha256:" + "f" * 64},
    }


def _executor() -> TencentSshExecutor:
    config = ExecutorConfig(
        host="host", user="root", ssh_key_b64="", compose_dir="/opt/deploy",
        release_dir="/opt/cameltv-release", backup_dir="/opt/cameltv-backup",
        image_backend="cameltv-tp-backend:main", image_frontend="cameltv-tp-frontend:main",
        compose_project="cameltv-tp-production",
    )
    return TencentSshExecutor(config)


def _verbose_output() -> str:
    """状态行在前、大段 compose 输出在后（真实发布就是这个形状）。"""
    tail = "\n".join(f"Container cameltv-tp-production-frontend-1 Waiting {i}" for i in range(200))
    return f"{STATUS_LINE}\n{tail}\n"


class MigrationStatusCaptureTests(unittest.TestCase):
    def test_deploy_reads_migration_status_from_full_output(self):
        executor = _executor()
        executor._run_remote = lambda commands: _verbose_output()

        result = executor.deploy("release-20260917-0007", manifest=_manifest())

        # 现状（缺陷）：4000 字符窗口把状态行挤掉，事件里只剩 "publish succeeded"
        self.assertNotIn("CAMELTV_MIGRATION", result.logs)
        # 期望：迁移状态单独从完整输出解析并随结果返回
        self.assertEqual(result.migration_status, f"migration target={HEAD} actual={HEAD}")

    def test_deploy_without_migration_status_stays_none(self):
        executor = _executor()
        executor._run_remote = lambda commands: "Container x Healthy\n" * 200

        result = executor.deploy("release-20260917-0007", manifest=_manifest())

        self.assertIsNone(result.migration_status)


if __name__ == "__main__":
    unittest.main()
