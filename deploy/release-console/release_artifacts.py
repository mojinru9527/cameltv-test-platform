"""Inspect Docker export configs before import, without extracting archive files."""
from __future__ import annotations

import base64
import hashlib
import json
from pathlib import Path
import re
import shlex
import tarfile


def runtime_mode(manifest: dict) -> str:
    mode = manifest.get('runtime_mode', 'combined')
    if mode not in ('combined', 'split'):
        raise ValueError('invalid runtime mode')
    if mode == 'combined' and (manifest.get('runner') is not None or manifest.get('execution_config_sha256') is not None):
        raise ValueError('combined release includes split artifacts')
    if mode == 'split':
        if not isinstance(manifest.get('runner'), dict):
            raise ValueError('split release requires runner artifact')
        if not re.fullmatch(r'[0-9a-f]{64}', str(manifest.get('execution_config_sha256', ''))):
            raise ValueError('split release requires execution config checksum')
    return mode


def _regular(path: Path) -> None:
    if path.is_symlink() or not path.is_file() or path.stat().st_size == 0:
        raise ValueError(f'nonempty regular artifact required: {path.name}')


def _read_member(archive, name, max_bytes):
    member = archive.getmember(name)
    if not member.isfile() or member.size > max_bytes:
        raise ValueError('invalid or oversized image metadata member')
    with archive.extractfile(member) as stream:
        return stream.read(max_bytes + 1)


def verify(release_dir: str, tag: str, manifest: dict) -> dict:
    if not re.fullmatch(r'release-\d{8}-\d{4}', tag) or manifest.get('release_id') != tag:
        raise ValueError('release tag must match registered manifest')
    mode = runtime_mode(manifest)
    root = Path(release_dir).resolve(strict=True)
    parts = ('backend', 'frontend', 'runner') if mode == 'split' else ('backend', 'frontend')
    digests = {}
    for part in parts:
        artifact = manifest.get(part)
        if not isinstance(artifact, dict) or artifact.get('image') != f'cameltv-tp-{part}':
            raise ValueError(f'unexpected {part} repository')
        expected = artifact.get('digest', '')
        if not isinstance(expected, str) or not re.fullmatch(r'sha256:[0-9a-f]{64}', expected):
            raise ValueError(f'invalid {part} config digest')
        path = root / f'{tag}-{part}.tar'
        _regular(path)
        with tarfile.open(path, 'r:*') as archive:
            descriptors = json.loads(_read_member(archive, 'manifest.json', 1024 * 1024))
            if not isinstance(descriptors, list) or len(descriptors) != 1:
                raise ValueError('expected a single-image Docker export')
            descriptor = descriptors[0]
            if descriptor.get('RepoTags') != [f'cameltv-tp-{part}:{tag}']:
                raise ValueError(f'{part} archive tag does not match release')
            config = _read_member(archive, descriptor['Config'], 4 * 1024 * 1024)
            actual = 'sha256:' + hashlib.sha256(config).hexdigest()
            if actual != expected:
                raise ValueError(f'{part} archive digest does not match manifest')
            digests[part] = actual
    if mode == 'split':
        config_path = root / f'{tag}-execution.yml'
        _regular(config_path)
        if config_path.stat().st_size > 1024 * 1024:
            raise ValueError('execution configuration too large')
        if hashlib.sha256(config_path.read_bytes()).hexdigest() != manifest['execution_config_sha256']:
            raise ValueError('execution configuration checksum mismatch')
    return {'ok': True, 'runtime_mode': mode, 'config_digests': digests}


def remote_verify_command(release_dir: str, tag: str, manifest: dict) -> str:
    source = base64.b64encode(Path(__file__).read_bytes()).decode('ascii')
    payload = base64.b64encode(json.dumps(dict(release_dir=release_dir, tag=tag, manifest=manifest)).encode()).decode('ascii')
    code = ("import base64,json; ns={'__name__':'release_artifacts_remote'}; "
            f"exec(base64.b64decode('{source}'),ns); "
            f"print(json.dumps(ns['verify'](**json.loads(base64.b64decode('{payload}')))))")
    return 'python3 -c ' + shlex.quote(code)
