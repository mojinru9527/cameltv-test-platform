import json
import pathlib
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from fastapi.testclient import TestClient

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import app as console
from tencent_executor import ExecutorCommandFailed


class ConsoleManifestTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        config = SimpleNamespace(release_control_database_path=str(pathlib.Path(self.tmp.name) / 'state.sqlite'), console_token='unit-test')
        self.settings = patch.object(console, 'settings', config)
        self.settings.start()
        self.addCleanup(self.settings.stop)
        self.client = TestClient(console.app, headers={'Authorization': 'Bearer unit-test'})
        self.addCleanup(self.client.close)
        self.executor = Mock()
        self.executor.deploy.return_value = SimpleNamespace(summary='deployed', logs='')
        self.executor.rollback.return_value = SimpleNamespace(summary='rolled back', logs='')
        executor_patch = patch.object(console, '_executor', return_value=self.executor)
        executor_patch.start()
        self.addCleanup(executor_patch.stop)

    def register(self, tag='release-20260908-0001', split=False):
        manifest = dict(schema_version='1.0', release_id=tag, git_sha='a' * 40)
        for part in ('backend', 'frontend', 'runner') if split else ('backend', 'frontend'):
            manifest[part] = dict(image=f'cameltv-tp-{part}', digest='sha256:' + 'b' * 64)
        if split:
            manifest.update(runtime_mode='split', execution_config_sha256='c' * 64)
        body = dict(release_id=tag, image_tag=tag, manifest_json=json.dumps(manifest))
        response = self.client.post('/api/deployments', json=body)
        self.assertEqual(response.status_code, 200, response.text)
        identifier = response.json()['deployment_id']
        self.assertEqual(self.client.post(f'/api/deployments/{identifier}/validate').status_code, 200)
        return identifier, manifest, body

    def state(self, identifier):
        with console._store_conn() as conn:
            return conn.execute('SELECT state FROM deployments WHERE id = ?', (identifier,)).fetchone()[0]

    def test_publish_binds_manifest_and_claims_before_remote_work(self):
        identifier, manifest, body = self.register(split=True)
        def deploy(tag, *, manifest):
            self.assertEqual(self.state(identifier), 'PROD_DEPLOYING')
            duplicate = self.client.post(f'/api/deployments/{identifier}/publish', json={'image_tag': tag})
            self.assertEqual(duplicate.status_code, 409)
            return SimpleNamespace(summary='deployed', logs='')
        self.executor.deploy.side_effect = deploy
        response = self.client.post(f'/api/deployments/{identifier}/publish', json={'image_tag': body['image_tag']})
        self.assertEqual(response.status_code, 200, response.text)
        self.executor.deploy.assert_called_once_with(body['image_tag'], manifest=manifest)
        self.assertEqual(self.state(identifier), 'PROD_OBSERVING')

    def test_tag_mismatch_and_manifest_replacement_rejected(self):
        identifier, manifest, body = self.register()
        response = self.client.post(f'/api/deployments/{identifier}/publish', json={'image_tag': 'release-20260908-0002'})
        self.assertEqual(response.status_code, 422)
        self.executor.deploy.assert_not_called()
        manifest['git_sha'] = 'd' * 40
        body['manifest_json'] = json.dumps(manifest)
        self.assertEqual(self.client.post('/api/deployments', json=body).status_code, 409)

    def test_remote_failure_is_recorded(self):
        identifier, _, body = self.register()
        self.executor.deploy.side_effect = ExecutorCommandFailed('capacity rejected')
        response = self.client.post(f'/api/deployments/{identifier}/publish', json={'image_tag': body['image_tag']})
        self.assertEqual(response.status_code, 500)
        self.assertEqual(self.state(identifier), 'PROD_FAILED')

    def test_other_deployment_cannot_publish_while_observing(self):
        first, _, body = self.register()
        second, _, other = self.register('release-20260908-0002')
        self.assertEqual(self.client.post(f'/api/deployments/{first}/publish', json={'image_tag': body['image_tag']}).status_code, 200)
        self.assertEqual(self.client.post(f'/api/deployments/{second}/publish', json={'image_tag': other['image_tag']}).status_code, 409)
        self.assertEqual(self.executor.deploy.call_count, 1)

    def test_rollback_resolves_target_topology(self):
        _, target, previous = self.register('release-20260907-0001', split=True)
        current, _, body = self.register()
        self.assertEqual(self.client.post(f'/api/deployments/{current}/publish', json={'image_tag': body['image_tag']}).status_code, 200)
        response = self.client.post(f'/api/deployments/{current}/rollback', json={'image_tag': previous['image_tag']})
        self.assertEqual(response.status_code, 200, response.text)
        self.executor.rollback.assert_called_once_with(previous['image_tag'], manifest=target)
        self.assertEqual(self.state(current), 'PROD_ROLLED_BACK')

    def test_unknown_rollback_and_broken_split_rejected(self):
        current, _, body = self.register()
        self.client.post(f'/api/deployments/{current}/publish', json={'image_tag': body['image_tag']})
        self.assertEqual(self.client.post(f'/api/deployments/{current}/rollback', json={'image_tag': 'release-20260901-0001'}).status_code, 404)
        self.executor.rollback.assert_not_called()
        manifest = json.loads(body['manifest_json'])
        manifest['runtime_mode'] = 'split'
        body['manifest_json'] = json.dumps(manifest)
        self.assertEqual(self.client.post('/api/deployments', json=body).status_code, 422)
