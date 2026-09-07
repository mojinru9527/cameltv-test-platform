"""Preview protected release retention; apply only an unchanged approved digest."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import shutil
import stat
import subprocess
import sys
import time

TAG = r'release-\d{8}-\d{4}'
IMAGE = re.compile(rf'cameltv-tp-(backend|frontend):({TAG})')
ARCHIVE = re.compile(rf'({TAG})-(backend|frontend)\.tar')
LOCK_PATH = '/run/lock/cameltv-release-capacity.lock'


def docker(*args: str) -> str:
    return subprocess.check_output(['docker', *args], text=True, timeout=120)


def snapshot(release_dir: Path) -> tuple[list, list, list]:
    ids = sorted(set(docker('image', 'ls', '-aq', '--no-trunc').split()))
    images = json.loads(docker('image', 'inspect', *ids)) if ids else []
    ids = docker('ps', '-aq', '--no-trunc').split()
    containers = json.loads(docker('container', 'inspect', *ids)) if ids else []
    archives = []
    for path in sorted(release_dir.iterdir()):
        if not ARCHIVE.fullmatch(path.name):
            continue
        info = path.lstat()
        archives.append({'name': path.name, 'size': info.st_size,
                         'mtime_ns': info.st_mtime_ns,
                         'regular': stat.S_ISREG(info.st_mode)})
    # Drop env/config/labels so neither logs nor approval digests carry secrets.
    return ([{'Id': i['Id'], 'RepoTags': sorted(i.get('RepoTags') or []),
              'Created': i['Created']} for i in images],
            sorted([{'Image': c['Image']} for c in containers], key=lambda c: c['Image']),
            archives)


def build_plan(images: list, containers: list, archives: list,
               keep_tags: list[str], now: float) -> dict:
    keep = set(keep_tags)
    if len(keep) < 2 or any(not re.fullmatch(TAG, tag) for tag in keep):
        raise ValueError('pin at least two distinct release tags: current and verified rollback')
    refs = {tag: i['Id'] for i in images for tag in i['RepoTags']}
    for tag in keep:
        for part in ('backend', 'frontend'):
            if f'cameltv-tp-{part}:{tag}' not in refs:
                raise ValueError(f'pinned release pair missing: {tag} {part}')
    releases = {m[2] for ref in refs if (m := IMAGE.fullmatch(ref))}
    keep.update(sorted(releases, reverse=True)[:2])
    for tag in releases:
        created = datetime.strptime(tag[8:16], '%Y%m%d').replace(tzinfo=timezone.utc).timestamp()
        if now - created < 48 * 3600:
            keep.add(tag)
    protected_ids = {c['Image'] for c in containers}
    for entry in images:
        if entry.get('Created'):
            built_at = datetime.fromisoformat(entry['Created'].replace('Z', '+00:00')).timestamp()
            if now - built_at < 48 * 3600:
                protected_ids.add(entry['Id'])
        if any(not IMAGE.fullmatch(ref) or IMAGE.fullmatch(ref)[2] in keep
               for ref in entry['RepoTags']):
            protected_ids.add(entry['Id'])
    candidates = sorted(ref for ref, image_id in refs.items()
                        if IMAGE.fullmatch(ref) and image_id not in protected_ids)
    files = []
    for item in archives:
        match = ARCHIVE.fullmatch(item['name'])
        if (match and item['regular'] and match[1] not in keep
                and now - item['mtime_ns'] / 10**9 >= 48 * 3600):
            files.append(item)
    plan = {'keep_tags': sorted(keep), 'image_tags': candidates, 'archives': files,
            'archive_bytes': sum(f['size'] for f in files)}
    # Include the entire inspected reference/file inventory to reject changed approvals.
    payload = {'plan': plan, 'images': sorted(images, key=lambda i: i['Id']),
               'containers': containers, 'archives': archives}
    plan['digest'] = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
    return plan


def require_digest(plan: dict, approved: str) -> None:
    if not approved or plan['digest'] != approved:
        raise ValueError('cleanup plan changed or missing approval; preview again')


def apply_plan(release_dir: Path, keep_tags: list[str], approved: str) -> dict:
    import fcntl

    with open(LOCK_PATH, 'a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        plan = build_plan(*snapshot(release_dir), keep_tags, time.time())
        require_digest(plan, approved)
        for ref in plan['image_tags']:
            current = build_plan(*snapshot(release_dir), keep_tags, time.time())
            if ref not in current['image_tags']:
                raise RuntimeError(f'image became protected: {ref}')
            docker('image', 'rm', ref)
        for item in plan['archives']:
            path = release_dir / item['name']
            info = path.lstat()
            if (not stat.S_ISREG(info.st_mode) or info.st_mtime_ns != item['mtime_ns']
                    or info.st_size != item['size']):
                raise RuntimeError('archive changed; stop and preview again')
            path.unlink()
        return plan


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--release-dir', default='/opt/cameltv-release')
    parser.add_argument('--keep-tag', action='append', required=True)
    parser.add_argument('--apply-digest', default='')
    args = parser.parse_args()
    try:
        release_dir = Path(args.release_dir).resolve(strict=True)
        if release_dir != Path('/opt/cameltv-release'):
            raise ValueError('cleanup is restricted to /opt/cameltv-release')
        free_before = shutil.disk_usage(release_dir).free
        if args.apply_digest:
            plan = apply_plan(release_dir, args.keep_tag, args.apply_digest)
        else:
            plan = build_plan(*snapshot(release_dir), args.keep_tag, time.time())
        plan.update(applied=bool(args.apply_digest), free_before=free_before,
                    free_after=shutil.disk_usage(release_dir).free)
        print(json.dumps(plan, indent=2, sort_keys=True))
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as exc:
        sys.exit(f'cleanup stopped: {exc}')


if __name__ == '__main__':
    main()
