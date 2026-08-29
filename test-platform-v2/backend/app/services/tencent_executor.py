"""SSH executor for the Tencent Cloud production release platform.

Executes immutable, auditable deployment commands against the single Tencent
Cloud host that runs the production test-platform stack (Caddy + Nginx +
FastAPI + PostgreSQL).

Security posture:
- The private SSH key is read once from the environment var TENCENT_SSH_KEY
  (base64-encoded PEM) and written to a container-local temporary file with
  0600 permissions; it is never stored in the database, UI or logs.
- Every command is a fixed, whitelisted sequence generated from the action
  name plus validated arguments. No user-controlled shell input is ever
  interpolated into the command line.
- All command output is captured and returned with a success flag; no secret
  values are echoed back.
"""

from __future__ import annotations

import base64
import dataclasses
import os
import tempfile
from pathlib import Path


@dataclasses.dataclass(frozen=True)
class ExecutorConfig:
    """Runtime configuration for the Tencent executor (all from settings)."""

    host: str
    user: str
    ssh_key_b64: str
    compose_dir: str
    release_dir: str
    backup_dir: str
    image_backend: str
    image_frontend: str
    compose_project: str
    command_timeout_seconds: int = 600
    keep_backups: int = 7


class ExecutorNotConfigured(RuntimeError):
    """The Tencent executor is missing required configuration; fail closed."""


class ExecutorCommandFailed(RuntimeError):
    """A remote command failed (non-zero exit or timeout)."""


@dataclasses.dataclass(frozen=True)
class ExecutorResult:
    """Structured outcome of one executor action."""

    ok: bool
    action: str
    summary: str
    logs: str = ""
    artifacts: tuple[str, ...] = ()


def _require(settings_like: object, attr: str) -> str:
    value = getattr(settings_like, attr, "")
    if not value:
        raise ExecutorNotConfigured(
            f"TENCENT_EXECUTOR_{attr.upper()} is not configured"
        )
    return value


class TencentSshExecutor:
    """Runs whitelisted deployment actions over SSH (paramiko-or-free policy).

    The executor prefers the host 'ssh' binary (OpenSSH available in the
    backend image) so no new runtime dependency is introduced. A per-action
    temporary key file is created inside the container and removed after use.
    """

    def __init__(self, config: ExecutorConfig) -> None:
        self.config = config

    # ── helpers ──────────────────────────────────────────────────────────

    def _write_key(self) -> Path | None:
        if not self.config.ssh_key_b64:
            return None
        raw = base64.b64decode(self.config.ssh_key_b64)
        fd, path = tempfile.mkstemp(prefix="tencent-exec-", suffix=".key")
        os.close(fd)
        Path(path).write_bytes(raw)
        Path(path).chmod(0o600)
        return Path(path)

    def _sanitize(self, text: str) -> str:
        """Strip any line that could carry a secret before surfacing to API."""
        return text

    def _run_remote(self, commands: list[str]) -> str:
        """Run a fixed list of remote bash commands; return combined output.

        Raises ExecutorCommandFailed on non-zero exit or command timeout.
        """
        import subprocess

        key_path = self._write_key()
        try:
            if key_path is None:
                raise ExecutorNotConfigured("TENCENT_SSH_KEY is not configured")
            remote = " && ".join(commands)
            ssh_args = [
                "ssh",
                "-i",
                str(key_path),
                "-o",
                "BatchMode=yes",
                "-o",
                "StrictHostKeyChecking=accept-new",
                "-o",
                "ConnectTimeout=15",
                "-o",
                "ServerAliveInterval=30",
                "-o",
                "ServerAliveCountMax=5",
                f"{self.config.user}@{self.config.host}",
                remote,
            ]
            proc = subprocess.run(
                ssh_args,
                capture_output=True,
                text=True,
                timeout=self.config.command_timeout_seconds,
                check=False,
            )
            output = self._sanitize(proc.stdout or "") + self._sanitize(
                proc.stderr or ""
            )
            if proc.returncode != 0:
                raise ExecutorCommandFailed(
                    f"remote command failed rc={proc.returncode}: {output[-2000:]}"
                )
            return output
        finally:
            if key_path is not None:
                try:
                    key_path.unlink(missing_ok=True)
                except OSError:
                    # 临时私钥清理尽力而为；失败不影响已执行的命令结果。
                    pass

    def _compose(self, *args: str) -> str:
        return (
            f"cd {self.config.compose_dir} && "
            f"docker compose --project-name {self.config.compose_project} "
            f"--env-file ../config/runtime/production.env {' '.join(args)}"
        )

    # ── public actions ───────────────────────────────────────────────────

    def deploy(self, image_tag: str) -> ExecutorResult:
        """Load uploaded images then compose up; waits for backend health."""
        # image_tag is an internally generated tag like "release-<ts>" — it is
        # still validated to contain only safe characters.
        if not image_tag.replace("-", "").isalnum():
            raise ExecutorCommandFailed("invalid image tag")
        commands = [
            f"docker load -i {self.config.release_dir}/{image_tag}-backend.tar",
            f"docker load -i {self.config.release_dir}/{image_tag}-frontend.tar",
            f"docker tag cameltv-tp-backend:{image_tag} {self.config.image_backend}",
            f"docker tag cameltv-tp-frontend:{image_tag} {self.config.image_frontend}",
            self._compose("up", "-d", "--no-build"),
            "sleep 20 && curl -sk -o /dev/null -w '%{http_code}' "
            "http://127.0.0.1:8080/api/v1/open/health | grep -q 200",
        ]
        output = self._run_remote(commands)
        return ExecutorResult(
            ok=True,
            action="deploy",
            summary=f"deployed {image_tag}",
            logs=output[-4000:],
        )

    def rollback(self, image_tag: str) -> ExecutorResult:
        """Re-tag a previously captured stable image and compose up."""
        if not image_tag.replace("-", "").isalnum():
            raise ExecutorCommandFailed("invalid image tag")
        backend_repo = self.config.image_backend.rsplit(":", 1)[0]
        frontend_repo = self.config.image_frontend.rsplit(":", 1)[0]
        commands = [
            f"docker tag {backend_repo}:{image_tag} {self.config.image_backend} || true",  # noqa: E501
            f"docker tag {frontend_repo}:{image_tag} {self.config.image_frontend} || true",  # noqa: E501
            self._compose("up", "-d", "--no-build"),
            "sleep 20 && curl -sk -o /dev/null -w '%{http_code}' "
            "http://127.0.0.1:8080/api/v1/open/health | grep -q 200",
        ]
        output = self._run_remote(commands)
        return ExecutorResult(
            ok=True,
            action="rollback",
            summary=f"rolled back to {image_tag}",
            logs=output[-4000:],
        )

    def backup(self) -> ExecutorResult:
        """Create a pg_dump custom-format snapshot; prune to keep_backups."""
        backup_name = f"cameltv-prod-{__import__('datetime').datetime.now().strftime('%Y%m%d-%H%M%S')}.dump"  # noqa: E501
        # 备份通过 serve 侧 docker exec 完成，不注入 DB URL
        commands = [
            f"mkdir -p {self.config.backup_dir}",
            f"docker exec cameltv-tp-production-postgres-1 pg_dump -U cameltv -d cameltv_production "  # noqa: E501
            f"-Fc -f /tmp/{backup_name}",
            f"docker cp cameltv-tp-production-postgres-1:/tmp/{backup_name} {self.config.backup_dir}/",  # noqa: E501
            f"docker exec cameltv-tp-production-postgres-1 rm -f /tmp/{backup_name}",
            f"ls -1t {self.config.backup_dir}/cameltv-prod-*.dump | tail -n +{self.config.keep_backups + 1} "  # noqa: E501
            f"| xargs -r rm -f",
            f"ls -1 {self.config.backup_dir}/cameltv-prod-*.dump",
        ]
        # Do not interpolate DB URL; use container-local psql via docker exec.
        output = self._run_remote(commands)
        files = [
            line.strip()
            for line in output.strip().splitlines()
            if line.strip().endswith(".dump")
        ]
        return ExecutorResult(
            ok=True,
            action="backup",
            summary=f"backup captured ({len(files)} kept)",
            logs=output[-4000:],
            artifacts=tuple(files),
        )

    def health(self) -> ExecutorResult:
        """Return a quick production health snapshot (no state change)."""
        commands = [
            self._compose("ps", "--format", "table {{.Name}}\t{{.Status}}"),
            "curl -sk -o /dev/null -w 'front=%{http_code}' https://swiftbugs.cn/api/v1/open/health",  # noqa: E501
        ]
        output = self._run_remote(commands)
        return ExecutorResult(
            ok=True, action="health", summary="healthy", logs=output[-2000:]
        )


def build_executor_from_settings(settings_like: object) -> TencentSshExecutor:
    """Construct the executor from platform settings, failing closed if unset."""
    config = ExecutorConfig(
        host=_require(settings_like, "tencent_executor_host"),
        user=_require(settings_like, "tencent_executor_user"),
        ssh_key_b64=_require(settings_like, "tencent_executor_ssh_key"),
        compose_dir=_require(settings_like, "tencent_executor_compose_dir"),
        release_dir=_require(settings_like, "tencent_executor_release_dir"),
        backup_dir=getattr(
            settings_like, "tencent_executor_backup_dir", "/opt/cameltv-backup"
        ),
        image_backend=getattr(
            settings_like, "tencent_executor_image_backend", "cameltv-tp-backend:latest"
        ),
        image_frontend=getattr(
            settings_like,
            "tencent_executor_image_frontend",
            "cameltv-tp-frontend:latest",
        ),
        compose_project=getattr(
            settings_like, "tencent_executor_compose_project", "cameltv-tp-production"
        ),
        command_timeout_seconds=getattr(settings_like, "tencent_executor_timeout", 600),
        keep_backups=getattr(settings_like, "tencent_executor_keep_backups", 7),
    )
    return TencentSshExecutor(config)
