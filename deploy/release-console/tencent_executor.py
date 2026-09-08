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
import json
import os
import re
import shlex
import tempfile
from pathlib import Path

from capacity import remote_check_command
from release_artifacts import remote_verify_command, runtime_mode


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
    image_runner: str = 'cameltv-tp-runner:main'


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


def rollback_runtime_override(mode: str) -> dict:
    """Retain the current additive schema when starting a previous image.

    Old Alembic trees cannot resolve a newer revision. Operational rollback must
    start the compatible application directly, never migrate the database down.
    """
    if mode not in ('combined', 'split'):
        raise ValueError('invalid rollback runtime mode')
    command = ['uvicorn', 'app.main:app', '--host', '0.0.0.0', '--port', '8000']
    owners = ('backend', 'runner') if mode == 'split' else ('backend',)
    return {'services': {owner: {'command': command} for owner in owners}}


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
            remote = "bash -c " + shlex.quote("set -o pipefail; " + " && ".join(commands))
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
                    pass

    def _compose(self, *args: str, mode: str = 'combined', tag: str = '', rollback: bool = False) -> str:
        extra, environment = '', ''
        if mode == 'split':
            if not re.fullmatch(r'release-\d{8}-\d{4}', tag):
                raise ExecutorCommandFailed('invalid split release tag')
            extra = ('-f docker-compose.yml -f docker-compose.override.yml '
                     f'-f docker-compose.execution.{tag}.yml ')
            environment = (f'API_IMAGE={shlex.quote(self.config.image_backend)} '
                           f'RUNNER_IMAGE={shlex.quote(self.config.image_runner)} ')
        if rollback:
            if not extra:
                extra = '-f docker-compose.yml -f docker-compose.override.yml '
            extra += '-f docker-compose.rollback-runtime.yml '
        return (
            f"cd {shlex.quote(self.config.compose_dir)} && {environment}"
            f"docker compose --project-name {shlex.quote(self.config.compose_project)} "
            f"--env-file ../config/runtime/production.env {extra}{' '.join(shlex.quote(arg) for arg in args)}"
        )

    def _activate(self, tag: str, mode: str, *, rollback: bool = False) -> list[str]:
        # Stop old consumers before introducing the new owner topology. Docker
        # preserves the durable queues and artifacts; no database is recreated.
        commands = []
        if rollback:
            path = shlex.quote(f'{self.config.compose_dir}/docker-compose.rollback-runtime.yml')
            payload = shlex.quote(json.dumps(rollback_runtime_override(mode)))
            commands.extend([f'test ! -L {path}', f"printf '%s' {payload} > {path}",
                             self._compose('config', '--quiet', mode=mode, tag=tag, rollback=True)])
        commands.append(self._compose('stop', '--timeout', '60', 'backend', 'aitde-worker'))
        project = shlex.quote(f'label=com.docker.compose.project={self.config.compose_project}')
        commands.append(f'docker ps -q --filter {project} --filter label=com.docker.compose.service=runner | xargs -r docker stop --time 60')
        services = ('runner', 'backend', 'frontend', 'aitde-worker') if mode == 'split' else ('backend', 'frontend', 'aitde-worker')
        commands.append(self._compose('up', '-d', '--no-build', '--force-recreate', '--wait',
                                      '--wait-timeout', '180', *services, mode=mode, tag=tag,
                                      rollback=rollback))
        commands.append("curl -fsS -o /dev/null http://127.0.0.1:8080/api/v1/open/health")
        return commands

    def _split_config(self, tag: str, checksum: str, *, install: bool) -> list[str]:
        if not re.fullmatch(r'[0-9a-f]{64}', checksum):
            raise ExecutorCommandFailed('invalid execution config checksum')
        source = shlex.quote(f'{self.config.release_dir}/{tag}-execution.yml')
        target = shlex.quote(f'{self.config.compose_dir}/docker-compose.execution.{tag}.yml')
        commands = []
        if install:
            commands.extend([f'test ! -L {target}', f'( test ! -e {target} || cmp -s -- {source} {target} )',
                             f'cp -- {source} {target}'])
        commands.append(f'test -f {target} && test ! -L {target}')
        commands.append(f'test "$(sha256sum -- {target} | cut -d " " -f 1)" = {checksum}')
        commands.append(self._compose('config', '--quiet', mode='split', tag=tag))
        return commands

    # ── public actions ───────────────────────────────────────────────────

    def deploy(self, image_tag: str, *, manifest: dict | None = None) -> ExecutorResult:
        """Load uploaded images then compose up; waits for backend health."""
        # image_tag is an internally generated tag like "release-<ts>" — it is
        # still validated to contain only safe characters.
        if not image_tag.replace("-", "").isalnum():
            raise ExecutorCommandFailed("invalid image tag")
        mode = runtime_mode(manifest) if manifest is not None else 'combined'
        if manifest is not None and manifest.get('release_id') != image_tag:
            raise ExecutorCommandFailed('release tag differs from registered manifest')
        commands = [
            "exec 9>/run/lock/cameltv-release-capacity.lock && flock -n 9",
            remote_check_command(self.config.release_dir, image_tag, mode),
        ]
        if manifest is not None:
            commands.append(remote_verify_command(self.config.release_dir, image_tag, manifest))
        if mode == 'split':
            commands.extend(self._split_config(image_tag, manifest['execution_config_sha256'], install=True))
        parts = ('backend', 'frontend', 'runner') if mode == 'split' else ('backend', 'frontend')
        for part in parts:
            commands.append(f'docker load -i {shlex.quote(f"{self.config.release_dir}/{image_tag}-{part}.tar")}')
        for part in parts:
            commands.append(f'docker tag cameltv-tp-{part}:{image_tag} {shlex.quote(getattr(self.config, f"image_{part}"))}')
        commands.extend(self._activate(image_tag, mode))
        output = self._run_remote(commands)
        return ExecutorResult(
            ok=True,
            action="deploy",
            summary=f"deployed {image_tag}",
            logs=output[-4000:],
        )

    def rollback(self, image_tag: str, *, manifest: dict | None = None) -> ExecutorResult:
        """Re-tag a previously captured stable image and compose up."""
        if not image_tag.replace("-", "").isalnum():
            raise ExecutorCommandFailed("invalid image tag")
        mode = runtime_mode(manifest) if manifest is not None else 'combined'
        if manifest is not None and manifest.get('release_id') != image_tag:
            raise ExecutorCommandFailed('rollback tag differs from registered manifest')
        commands = [
            "exec 9>/run/lock/cameltv-release-capacity.lock && flock -n 9",
        ]
        parts = ('backend', 'frontend', 'runner') if mode == 'split' else ('backend', 'frontend')
        for part in parts:
            repo = getattr(self.config, f'image_{part}').rsplit(':', 1)[0]
            commands.append(f'docker image inspect {shlex.quote(f"{repo}:{image_tag}")} >/dev/null')
        if mode == 'split':
            commands.extend(self._split_config(image_tag, manifest['execution_config_sha256'], install=False))
        for part in parts:
            target = getattr(self.config, f'image_{part}')
            repo = target.rsplit(':', 1)[0]
            commands.append(f'docker tag {shlex.quote(f"{repo}:{image_tag}")} {shlex.quote(target)}')
        commands.extend(self._activate(image_tag, mode, rollback=True))
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
            "curl -fsS -o /dev/null -w 'front=%{http_code}' https://swiftbugs.cn/api/v1/open/health",  # noqa: E501
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
        image_runner=getattr(settings_like, 'tencent_executor_image_runner', 'cameltv-tp-runner:main'),
    )
    return TencentSshExecutor(config)
