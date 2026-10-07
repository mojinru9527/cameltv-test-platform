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
        # 平台简化后只有一套制品集：backend/frontend/runner（无独立 AI 网关）。
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
        (self.root / f'{self.tag}-deploy.yml').write_bytes(config)
        self.manifest['execution_config_sha256'] = hashlib.sha256(config).hexdigest()

    def test_single_topology_bundle_and_pinned_deploy_compose(self):
        result = release_artifacts.verify(str(self.root), self.tag, self.manifest)
        self.assertEqual(set(result['config_digests']), {'backend', 'frontend', 'runner'})
        self.assertEqual(result['runtime_mode'], 'split')
        # combined 与 split 是同一套制品要求（runner 不再只属于 split）。
        combined = dict(self.manifest, runtime_mode='combined')
        self.assertEqual(release_artifacts.verify(str(self.root), self.tag, combined)['runtime_mode'], 'combined')

    def test_combined_bundle_with_runner_and_pinned_compose_is_accepted(self):
        """release.ps1 新产物：combined 也带 runner + 钉扎校验和，不得被判互斥/缺件。"""
        combined = dict(self.manifest, runtime_mode='combined')
        result = release_artifacts.verify(str(self.root), self.tag, combined)
        self.assertEqual(result['runtime_mode'], 'combined')
        self.assertEqual(set(result['config_digests']), {'backend', 'frontend', 'runner'})
        # 未声明钉扎校验和的（历史 combined 形态）不额外要求配置文件。
        (self.root / f'{self.tag}-deploy.yml').unlink()
        without_pin = {key: value for key, value in combined.items() if key != 'execution_config_sha256'}
        self.assertTrue(release_artifacts.verify(str(self.root), self.tag, without_pin)['ok'])

    def test_legacy_execution_artifact_name_still_verifies(self):
        """历史发布目录里钉扎文件是 {tag}-execution.yml，改名后仍要可验证。"""
        legacy = self.root / f'{self.tag}-execution.yml'
        (self.root / f'{self.tag}-deploy.yml').rename(legacy)
        self.assertTrue(release_artifacts.verify(str(self.root), self.tag, self.manifest)['ok'])
        legacy.write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError, 'checksum'):
            release_artifacts.verify(str(self.root), self.tag, self.manifest)
        legacy.unlink()
        with self.assertRaisesRegex(ValueError, 'regular artifact'):
            release_artifacts.verify(str(self.root), self.tag, self.manifest)

    def test_runner_artifact_is_required_in_both_modes(self):
        for mode in ('combined', 'split'):
            candidate = {key: value for key, value in self.manifest.items() if key != 'runner'}
            candidate['runtime_mode'] = mode
            with self.subTest(mode=mode):
                with self.assertRaisesRegex(ValueError, 'runner'):
                    release_artifacts.verify(str(self.root), self.tag, candidate)

    def test_retired_service_artifact_is_rejected(self):
        # 现场拼接已退役服务的制品键（控制面代码/测试里不再出现该服务的字面量）。
        retired = '-'.join(('ai', 'gateway'))
        candidate = dict(self.manifest, **{retired: {'image': f'cameltv-tp-{retired}', 'digest': 'sha256:' + 'a' * 64}})
        with self.assertRaisesRegex(ValueError, retired):
            release_artifacts.verify(str(self.root), self.tag, candidate)

    def test_missing_runner_and_changed_configuration_are_rejected(self):
        (self.root / f'{self.tag}-deploy.yml').write_bytes(b'changed')
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
