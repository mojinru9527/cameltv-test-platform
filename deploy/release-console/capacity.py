"""Fail-closed disk admission for release upload and image import (stdlib only)."""
from __future__ import annotations

import argparse
import base64
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys

GIB = 1024**3


def required_bytes(archive_bytes: int, stage: str) -> int:
    if archive_bytes <= 0 or stage not in ('upload', 'import'):
        raise ValueError('positive archive bytes and upload/import stage required')
    return max(8 * GIB, archive_bytes * (3 if stage == 'upload' else 2) + 2 * GIB)


def validate_space(free: int, free_inodes: int, inodes: int, required: int) -> None:
    if free < required:
        raise RuntimeError(f'disk capacity insufficient: free={free}, required={required}')
    if inodes > 0 and free_inodes < max(1024, inodes // 20):
        raise RuntimeError(f'inode capacity insufficient: free={free_inodes}, total={inodes}')


def check(release_dir: str, stage: str, archive_bytes: int = 0, tag: str = '', runtime_mode: str = 'combined') -> dict:
    if runtime_mode not in ('combined', 'split'):
        raise ValueError('invalid runtime mode')
    release = Path(release_dir).resolve(strict=True)
    if not release.is_dir():
        raise ValueError('release directory is not a directory')
    if stage == 'import':
        if not re.fullmatch(r'release-\d{8}-\d{4}', tag):
            raise ValueError('expected release-YYYYMMDD-NNNN tag')
        parts = ('backend', 'frontend', 'runner') if runtime_mode == 'split' else ('backend', 'frontend')
        archives = [release / f'{tag}-{part}.tar' for part in parts]
        if any(p.is_symlink() or not p.is_file() or p.stat().st_size == 0 for p in archives):
            raise ValueError('all nonempty regular release archives are required')
        archive_bytes = sum(p.stat().st_size for p in archives)
    required = required_bytes(archive_bytes, stage)
    docker_root = subprocess.check_output(
        ['docker', 'info', '--format', '{{.DockerRootDir}}'], text=True, timeout=30,
    ).strip()
    if not docker_root or not Path(docker_root).is_absolute():
        raise RuntimeError('Docker root inspection failed')
    paths = [release, Path(docker_root).resolve(strict=True)]
    # Docker's containerd image store can live outside DockerRootDir.
    containerd = Path('/var/lib/containerd')
    if containerd.exists():
        paths.append(containerd.resolve(strict=True))
    devices = set()
    results = []
    for path in paths:
        device = path.stat().st_dev
        if device in devices:
            continue
        devices.add(device)
        free = shutil.disk_usage(path).free
        stats = os.statvfs(path)
        validate_space(free, stats.f_favail, stats.f_files, required)
        results.append({'path': str(path), 'free_bytes': free, 'required_bytes': required})
    return {'ok': True, 'stage': stage, 'archive_bytes': archive_bytes, 'filesystems': results}


def remote_check_command(release_dir: str, tag: str, runtime_mode: str = 'combined') -> str:
    source = base64.b64encode(Path(__file__).read_bytes()).decode('ascii')
    args = base64.b64encode(json.dumps({
        'release_dir': release_dir, 'stage': 'import', 'tag': tag, 'runtime_mode': runtime_mode,
    }).encode()).decode('ascii')
    code = (
        "import base64,json; ns={'__name__':'capacity_remote'}; "
        f"exec(base64.b64decode('{source}'),ns); "
        f"print(json.dumps(ns['check'](**json.loads(base64.b64decode('{args}')))))"
    )
    return 'python3 -c ' + shlex.quote(code)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stage', choices=['upload', 'import'], required=True)
    parser.add_argument('--release-dir', default='/opt/cameltv-release')
    parser.add_argument('--archive-bytes', type=int, default=0)
    parser.add_argument('--tag', default='')
    parser.add_argument('--runtime-mode', choices=['combined', 'split'], default='combined')
    args = parser.parse_args()
    try:
        result = check(**vars(args))
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as exc:
        sys.exit(f'capacity check failed: {exc}')
    print(json.dumps(result, sort_keys=True))


if __name__ == '__main__':
    main()
