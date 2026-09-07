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
            for repo in ('backend', 'frontend'):
                self.images.append({'Id': f'sha256:{n}{repo}',
                                    'RepoTags': [f'cameltv-tp-{repo}:{tag}']})

    def plan(self, containers=(), archives=()):
        return cleanup.build_plan(self.images, list(containers), list(archives), self.keep, 1788825600)

    def test_only_old_unreferenced_release_is_candidate(self):
        plan = self.plan()
        self.assertEqual(len(plan['image_tags']), 2)
        self.assertTrue(all('20260903' in x for x in plan['image_tags']))

    def test_stopped_container_and_non_release_alias_protect_image(self):
        self.images[-1]['RepoTags'].append('cameltv-tp-frontend:prev-prod')
        plan = self.plan([{'Image': self.images[-2]['Id']}])
        self.assertEqual(plan['image_tags'], [])

    def test_recent_rebuild_with_old_tag_is_protected(self):
        self.images[-1]['Created'] = '2026-09-08T00:00:00Z'
        plan = self.plan()
        self.assertEqual(len(plan['image_tags']), 1)
        self.assertIn('backend', plan['image_tags'][0])

    def test_missing_rollback_pair_fails_closed(self):
        self.images.pop(3)
        with self.assertRaises(ValueError):
            self.plan()

    def test_at_least_two_pinned_tags_required(self):
        with self.assertRaises(ValueError):
            cleanup.build_plan(self.images, [], [], [self.keep[0]], 1788825600)

    def test_recent_archive_backup_and_symlink_not_candidates(self):
        files = [
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
                patch.object(cleanup, 'snapshot', return_value=(self.images, [], [])), \
                patch.object(cleanup, 'docker') as docker:
            with self.assertRaises(ValueError):
                cleanup.apply_plan(pathlib.Path('/unused'), self.keep, 'stale')
        docker.assert_not_called()

    def test_failed_delete_stops_before_archive_removal(self):
        fake_lock = SimpleNamespace(flock=lambda *args: None, LOCK_EX=1, LOCK_NB=2)
        with patch.dict(sys.modules, {'fcntl': fake_lock}), \
                patch('builtins.open', mock_open()), \
                patch.object(cleanup.time, 'time', return_value=1788825600), \
                patch.object(cleanup, 'snapshot', return_value=(self.images, [], [])), \
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
            files = [{'name': archive.name, 'size': archive.stat().st_size,
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
            self.assertEqual(docker.call_count, 2)

    def test_new_container_reference_stops_apply_before_image_removal(self):
        fake_lock = SimpleNamespace(flock=lambda *args: None, LOCK_EX=1, LOCK_NB=2)
        states = [(self.images, [], []),
                  (self.images, [{'Image': self.images[-2]['Id']}], [])]
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
