import hashlib
import io
import json
from pathlib import Path
import sys
import tarfile
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import release_artifacts


class ReleaseArtifactsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.tag = 'release-20260908-0001'
        self.manifest = {'release_id': self.tag, 'runtime_mode': 'split'}
        for part in ('backend', 'frontend', 'runner'):
            config = json.dumps({'config': {'Labels': {'part': part}}}).encode()
            descriptor = [{'Config': 'config.json', 'RepoTags': [f'cameltv-tp-{part}:{self.tag}'], 'Layers': []}]
            with tarfile.open(self.root / f'{self.tag}-{part}.tar', 'w') as archive:
                for name, content in [('config.json', config), ('manifest.json', json.dumps(descriptor).encode())]:
                    member = tarfile.TarInfo(name)
                    member.size = len(content)
                    archive.addfile(member, io.BytesIO(content))
            self.manifest[part] = {'image': f'cameltv-tp-{part}', 'digest': 'sha256:' + hashlib.sha256(config).hexdigest()}
        config = b'services: {}\n'
        (self.root / f'{self.tag}-execution.yml').write_bytes(config)
        self.manifest['execution_config_sha256'] = hashlib.sha256(config).hexdigest()

    def test_complete_split_bundle_and_legacy_pair(self):
        result = release_artifacts.verify(str(self.root), self.tag, self.manifest)
        self.assertEqual(set(result['config_digests']), {'backend', 'frontend', 'runner'})
        legacy = {key: value for key, value in self.manifest.items()
                  if key not in ('runner', 'runtime_mode', 'execution_config_sha256')}
        self.assertEqual(release_artifacts.verify(str(self.root), self.tag, legacy)['runtime_mode'], 'combined')

    def test_missing_runner_and_changed_configuration_are_rejected(self):
        (self.root / f'{self.tag}-execution.yml').write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError, 'checksum'):
            release_artifacts.verify(str(self.root), self.tag, self.manifest)
        (self.root / f'{self.tag}-runner.tar').unlink()
        with self.assertRaisesRegex(ValueError, 'regular artifact'):
            release_artifacts.verify(str(self.root), self.tag, self.manifest)

    def test_wrong_digest_repository_and_tag_are_rejected(self):
        for mutation in ('digest', 'image'):
            candidate = json.loads(json.dumps(self.manifest))
            candidate['runner'][mutation] = 'sha256:' + '0' * 64 if mutation == 'digest' else 'unrelated'
            with self.assertRaises(ValueError):
                release_artifacts.verify(str(self.root), self.tag, candidate)
        with self.assertRaises(ValueError):
            release_artifacts.verify(str(self.root), 'release-20260908-0002', self.manifest)

    def test_remote_command_encodes_all_inputs(self):
        command = release_artifacts.remote_verify_command('/tmp/$(not-a-command)', self.tag, self.manifest)
        self.assertNotIn('$(not-a-command)', command)
        self.assertTrue(command.startswith('python3 -c '))


if __name__ == '__main__':
    unittest.main()
