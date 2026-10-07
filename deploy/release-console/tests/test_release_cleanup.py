import pathlib
import os
import sys
import tempfile
import unittest
from unittest.mock import mock_open, patch
from types import SimpleNamespace

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import release_cleanup as cleanup


def image(number, tag, extra=()):
    return {'Id': 'sha256:' + str(number) * 64,
            'RepoTags': [f'cameltv-tp-backend:{tag}', *extra]}


class CleanupTests(unittest.TestCase):
    def setUp(self):
        self.keep = ['release-20260907-0001', 'release-20260906-0001']
        self.images = []
        for n, tag in enumerate([*self.keep, 'release-20260903-0001'], 1):
            # 简化后每个发布都带 backend/frontend/runner 三件镜像。
            for repo in ('backend', 'frontend', 'runner'):
                self.images.append({'Id': f'sha256:{n}{repo}',
                                    'RepoTags': [f'cameltv-tp-{repo}:{tag}']})

    def pinned_configs(self):
        """钉扎版本随包的部署 compose（真实发布目录里每个钉扎版本都有一份）。"""
        return [{'name': f'{tag}-deploy.yml', 'size': 100, 'mtime_ns': 1, 'regular': True}
                for tag in self.keep]

    def plan(self, containers=(), archives=None):
        files = self.pinned_configs() if archives is None else list(archives)
        return cleanup.build_plan(self.images, list(containers), files, self.keep, 1788825600)

    def test_only_old_unreferenced_release_is_candidate(self):
        plan = self.plan()
        self.assertEqual(len(plan['image_tags']), 3)
        self.assertTrue(all('20260903' in x for x in plan['image_tags']))

    def test_stopped_container_and_non_release_alias_protect_image(self):
        self.images[-1]['RepoTags'].append('cameltv-tp-frontend:prev-prod')
        plan = self.plan([{'Image': self.images[-3]['Id']}, {'Image': self.images[-2]['Id']}])
        self.assertEqual(plan['image_tags'], [])

    def test_recent_rebuild_with_old_tag_is_protected(self):
        self.images[-1]['Created'] = '2026-09-08T00:00:00Z'
        plan = self.plan()
        self.assertEqual(len(plan['image_tags']), 2)
        self.assertTrue(all('20260903' in x for x in plan['image_tags']))

    def test_missing_rollback_pair_fails_closed(self):
        self.images.pop(5)
        with self.assertRaises(ValueError):
            self.plan()

    def test_at_least_two_pinned_tags_required(self):
        with self.assertRaises(ValueError):
            cleanup.build_plan(self.images, [], [], [self.keep[0]], 1788825600)

    def test_pinned_release_requires_complete_image_set(self):
        """钉扎的回滚锚点必须是完整三件套（缺 runner 即 fail-closed）。"""
        runner = next(i for i in self.images if i['RepoTags'] == [f'cameltv-tp-runner:{self.keep[0]}'])
        self.images.remove(runner)
        with self.assertRaisesRegex(ValueError, 'runner'):
            self.plan()
        self.images.append(runner)
        result = self.plan()
        self.assertNotIn(f'cameltv-tp-runner:{self.keep[0]}', result['image_tags'])

    def test_pinned_release_requires_pinned_compose_artifact(self):
        """钉扎版本必须留有钉扎证据：两种命名至少一份，两份都缺即 fail-closed。"""
        tag = self.keep[0]
        others = [c for c in self.pinned_configs() if not c['name'].startswith(f'{tag}-')]
        for name in (f'{tag}-deploy.yml', f'{tag}-execution.yml'):
            with self.subTest(present=name):
                result = self.plan(archives=[*others, {'name': name, 'size': 100,
                                                       'mtime_ns': 1, 'regular': True}])
                self.assertEqual(result['pinned_configs'][tag], name)
                self.assertNotIn(f'cameltv-tp-backend:{tag}', result['image_tags'])
        with self.assertRaisesRegex(ValueError, 'compose artifact missing'):
            self.plan(archives=others)

    def test_pinned_release_prefers_new_compose_name_when_both_exist(self):
        tag = self.keep[0]
        files = [*self.pinned_configs(), {'name': f'{tag}-execution.yml', 'size': 100,
                                          'mtime_ns': 1, 'regular': True}]
        self.assertEqual(self.plan(archives=files)['pinned_configs'][tag], f'{tag}-deploy.yml')

    def test_pinned_release_with_runner_and_pinned_configuration_is_fully_protected(self):
        """release.ps1 新产物（三件镜像 + -deploy.yml）不得被当成孤儿清理。"""
        tag = self.keep[1]
        files = [*self.pinned_configs(),
                 {'name': f'{tag}-runner.tar', 'size': 100, 'mtime_ns': 1, 'regular': True}]
        result = self.plan(archives=files)
        for pinned in self.keep:
            for part in ('backend', 'frontend', 'runner'):
                self.assertNotIn(f'cameltv-tp-{part}:{pinned}', result['image_tags'])
        self.assertEqual(result['archives'], [])

    def test_old_runner_is_eligible_but_bundled_configuration_is_retained(self):
        tag = 'release-20260903-0001'
        files = [*self.pinned_configs(),
                 dict(name=f'{tag}-runner.tar', size=100, mtime_ns=1, regular=True),
                 dict(name=f'{tag}-deploy.yml', size=100, mtime_ns=1, regular=True)]
        result = self.plan(archives=files)
        self.assertIn(f'cameltv-tp-runner:{tag}', result['image_tags'])
        self.assertEqual(result['archives'], [files[len(self.keep)]])

    def test_recent_archive_backup_and_symlink_not_candidates(self):
        files = [
            *self.pinned_configs(),
            {'name': 'release-20260903-0001-backend.tar', 'size': 100, 'mtime_ns': 1, 'regular': True},
            {'name': 'release-20260903-0001-frontend.tar', 'size': 100, 'mtime_ns': 1, 'regular': False},
            {'name': 'pre_v40_backup.dump', 'size': 100, 'mtime_ns': 1, 'regular': True},
            {'name': 'release-20260902-0001-backend.tar', 'size': 100, 'mtime_ns': 1788825600 * 10**9, 'regular': True},
        ]
        self.assertEqual(len(self.plan(archives=files)['archives']), 1)

    def test_digest_changes_with_container_reference(self):
        first = self.plan()
        second = self.plan([{'Image': self.images[-1]['Id']}])
        self.assertNotEqual(first['digest'], second['digest'])
        with self.assertRaises(ValueError):
            cleanup.require_digest(second, first['digest'])

    def test_stale_apply_performs_no_deletion(self):
        fake_lock = SimpleNamespace(flock=lambda *args: None, LOCK_EX=1, LOCK_NB=2)
        with patch.dict(sys.modules, {'fcntl': fake_lock}), \
                patch('builtins.open', mock_open()), \
                patch.object(cleanup, 'snapshot', return_value=(self.images, [], self.pinned_configs())), \
                patch.object(cleanup, 'docker') as docker:
            with self.assertRaises(ValueError):
                cleanup.apply_plan(pathlib.Path('/unused'), self.keep, 'stale')
        docker.assert_not_called()

    def test_failed_delete_stops_before_archive_removal(self):
        fake_lock = SimpleNamespace(flock=lambda *args: None, LOCK_EX=1, LOCK_NB=2)
        with patch.dict(sys.modules, {'fcntl': fake_lock}), \
                patch('builtins.open', mock_open()), \
                patch.object(cleanup.time, 'time', return_value=1788825600), \
                patch.object(cleanup, 'snapshot', return_value=(self.images, [], self.pinned_configs())), \
                patch.object(cleanup, 'docker', side_effect=RuntimeError('in use')) as docker:
            with self.assertRaises(RuntimeError):
                cleanup.apply_plan(pathlib.Path('/unused'), self.keep, self.plan()['digest'])
        self.assertEqual(docker.call_count, 1)
        self.assertEqual(docker.call_args.args[:2], ('image', 'rm'))
        self.assertNotIn('--force', docker.call_args.args)

    def test_successful_apply_removes_only_reviewed_regular_archive(self):
        fake_lock = SimpleNamespace(flock=lambda *args: None, LOCK_EX=1, LOCK_NB=2)
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            archive = root / 'release-20260903-0001-backend.tar'
            archive.write_bytes(b'old archive')
            os.utime(archive, ns=(1, 1))
            backup = root / 'production.dump'
            backup.write_bytes(b'protected')
            files = [*self.pinned_configs(),
                     {'name': archive.name, 'size': archive.stat().st_size,
                      'mtime_ns': archive.stat().st_mtime_ns, 'regular': True}]
            approved = self.plan(archives=files)['digest']
            with patch.dict(sys.modules, {'fcntl': fake_lock}), \
                    patch('builtins.open', mock_open()), \
                    patch.object(cleanup.time, 'time', return_value=1788825600), \
                    patch.object(cleanup, 'snapshot', return_value=(self.images, [], files)), \
                    patch.object(cleanup, 'docker') as docker:
                cleanup.apply_plan(root, self.keep, approved)
            self.assertFalse(archive.exists())
            self.assertEqual(backup.read_bytes(), b'protected')
            self.assertEqual(docker.call_count, 3)

    def test_new_container_reference_stops_apply_before_image_removal(self):
        fake_lock = SimpleNamespace(flock=lambda *args: None, LOCK_EX=1, LOCK_NB=2)
        states = [(self.images, [], self.pinned_configs()),
                  (self.images, [{'Image': self.images[-3]['Id']}], self.pinned_configs())]
        with patch.dict(sys.modules, {'fcntl': fake_lock}), \
                patch('builtins.open', mock_open()), \
                patch.object(cleanup.time, 'time', return_value=1788825600), \
                patch.object(cleanup, 'snapshot', side_effect=states), \
                patch.object(cleanup, 'docker') as docker:
            with self.assertRaises(RuntimeError):
                cleanup.apply_plan(pathlib.Path('/unused'), self.keep, self.plan()['digest'])
        docker.assert_not_called()


if __name__ == '__main__':
    unittest.main()
