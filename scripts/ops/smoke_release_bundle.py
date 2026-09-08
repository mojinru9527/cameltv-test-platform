"""Export, verify and reimport actual local split images; never contacts production."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import uuid

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'deploy/release-console'))
from release_artifacts import verify


def docker(*args, timeout=300):
    result = subprocess.run(['docker', *args], capture_output=True, text=True, timeout=timeout)
    if result.returncode:
        raise RuntimeError(f'Docker {args[0]} failed: ' + result.stderr[-1500:])
    return result.stdout.strip()


def main():
    # Keep the strict production tag shape while choosing a collision-checked
    # disposable future release alias. No current/main release tag is modified.
    tag = 'release-20990908-' + str(int(uuid.uuid4().hex[:8], 16) % 10000).zfill(4)
    references = [f'cameltv-tp-{part}:{tag}' for part in ('backend', 'frontend', 'runner')]
    for reference in references:
        exists = subprocess.run(['docker', 'image', 'inspect', reference], capture_output=True)
        if exists.returncode == 0:
            raise RuntimeError('Disposable alias already exists; rerun with a fresh identifier')
    created = []
    with tempfile.TemporaryDirectory(prefix='capacity-bundle-') as temporary:
        root = Path(temporary)
        manifest = {'release_id': tag, 'runtime_mode': 'split'}
        # Config digests from the successful fresh build outputs, not OCI-index IDs.
        expected = {
            'backend': 'c7b78609d47081368e27ea772b76ae00dadadfa2fb1b3eb6e2e5443e16bc86d9',
            'runner': 'fe672bba596c9b76a87eee7d0b79396da1f572a708e052198c04f4a4764487a7',
            'frontend': '7cac66f654c1e06b4ea26daf950bef1287444e6abe7315149385e3d3360aaa6f',
        }
        try:
            for part, reference in zip(('backend', 'frontend', 'runner'), references):
                source = 'api' if part == 'backend' else part
                docker('tag', f'cameltv-tp-{source}:capacity-local', reference)
                created.append(reference)
                docker('save', '-o', str(root / f'{tag}-{part}.tar'), reference)
                manifest[part] = {'image': f'cameltv-tp-{part}', 'digest': 'sha256:' + expected[part]}
            config = root / f'{tag}-execution.yml'
            content = (ROOT / 'test-platform-v2/deploy/docker-compose.execution.yml').read_bytes()
            config.write_bytes(content)
            manifest['execution_config_sha256'] = hashlib.sha256(content).hexdigest()
            verified = verify(str(root), tag, manifest)
            config.write_bytes(content + b'\n# deliberately changed fixture\n')
            try:
                verify(str(root), tag, manifest)
            except ValueError as error:
                assert 'checksum mismatch' in str(error)
            else:
                raise AssertionError('Changed execution configuration was accepted')
            config.write_bytes(content)
            assert verify(str(root), tag, manifest)['ok']
            for part in ('backend', 'frontend', 'runner'):
                docker('load', '-i', str(root / f'{tag}-{part}.tar'))
            print(json.dumps({'result': 'passed', 'verified': verified,
                              'archive_bytes': sum(p.stat().st_size for p in root.glob('*.tar')),
                              'tampered_configuration_rejected': True, 'all_images_reimported': True}))
        finally:
            for reference in reversed(created):
                docker('image', 'rm', reference)


if __name__ == '__main__':
    main()
