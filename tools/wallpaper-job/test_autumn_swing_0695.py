"""Offline unit tests for download_autumn_swing_0695. Never touches the network."""
import hashlib
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image
import download_autumn_swing_0695 as job


class AutumnSwingDownloadTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / 'delivery'
        self.root.mkdir()
        buf = io.BytesIO()
        Image.new('RGB', (540, 960), '#d9822b').save(buf, 'WEBP')
        self.data = buf.getvalue()
        self.seed = {
            'share_url': job.SHARE_URL,
            'resolved_note_url': 'https://www.rednote.com/discovery/item/' + job.NOTE_ID,
            'note_id': job.NOTE_ID,
            'title': '秋天和秋千很配哦～',
            'author': '🍔',
            'tags': ['懒羊羊', '荡秋千'],
            'carousel_urls': [
                'https://sns-web-i10.rednotecdn.com/202611271640/abcd/notes_pre_post/test!nd_dft_wlteh_webp_3'
            ],
        }
        (self.root / 'source-seed.json').write_bytes(json.dumps(self.seed).encode('utf-8'))
        self.patches = [
            patch.object(job, 'ROOT', self.root),
            patch.dict(os.environ, {'GITHUB_ACTIONS': 'true', 'GITHUB_RUN_ID': '999', 'GITHUB_REF_NAME': 'arena/test'}),
            patch.object(job, 'try_public_page_refresh', return_value=(None, 'no_public_initial_state_used_seed_urls')),
        ]
        for p in self.patches:
            p.start()
            self.addCleanup(p.stop)

    def test_refuses_outside_actions(self):
        with patch.dict(os.environ, {'GITHUB_ACTIONS': 'false'}), patch.object(job, 'fetch') as mock_fetch:
            with self.assertRaises(RuntimeError):
                job.main()
            mock_fetch.assert_not_called()

    def test_single_verified_webp_saved_and_manifested(self):
        with patch.object(job, 'fetch', return_value=(self.data, 540, 960, 'webp')):
            job.main()
        saved = self.root / 'source/01.webp'
        self.assertTrue(saved.exists())
        self.assertEqual(saved.read_bytes(), self.data)
        manifest = json.loads((self.root / 'source-manifest.json').read_text(encoding='utf-8'))
        self.assertEqual(manifest['reference_count_downloaded'], 1)
        self.assertEqual(manifest['images'][0]['md5'], hashlib.md5(self.data).hexdigest())
        self.assertEqual(manifest['images'][0]['sha256'], hashlib.sha256(self.data).hexdigest())
        self.assertEqual((manifest['images'][0]['width'], manifest['images'][0]['height']), (540, 960))

    def test_corrupt_bytes_write_nothing(self):
        with patch.object(job, 'fetch', return_value=(b'not-an-image', 540, 960, 'webp')):
            with self.assertRaises(RuntimeError):
                job.main()
        self.assertFalse((self.root / 'source').exists())
        self.assertFalse((self.root / 'source-manifest.json').exists())

    def test_multi_item_partial_failure_writes_nothing(self):
        two_seed = dict(
            self.seed,
            carousel_urls=self.seed['carousel_urls'] + [
                'https://sns-web-i10.rednotecdn.com/202611271640/abcd/notes_pre_post/test2!nd_dft_wlteh_webp_3'
            ],
        )
        (self.root / 'source-seed.json').write_bytes(json.dumps(two_seed).encode('utf-8'))
        with patch.object(job, 'fetch', side_effect=[(self.data, 540, 960, 'webp'), ValueError('bad second')]):
            with self.assertRaises(RuntimeError):
                job.main()
        self.assertFalse((self.root / 'source').exists())
        self.assertFalse((self.root / 'source-manifest.json').exists())

    def test_disallowed_url_rejected(self):
        bad_seed = dict(self.seed, carousel_urls=['http://example.com/01.webp'])
        (self.root / 'source-seed.json').write_bytes(json.dumps(bad_seed).encode('utf-8'))
        with patch.object(job, 'fetch') as mock_fetch:
            with self.assertRaises(ValueError):
                job.main()
            mock_fetch.assert_not_called()

    def test_refuses_overwriting_different_existing_source(self):
        source_dir = self.root / 'source'
        source_dir.mkdir()
        existing = source_dir / '01.webp'
        existing.write_bytes(b'original-bytes')
        with patch.object(job, 'fetch', return_value=(self.data, 540, 960, 'webp')):
            with self.assertRaises(RuntimeError):
                job.main()
        self.assertEqual(existing.read_bytes(), b'original-bytes')


if __name__ == '__main__':
    unittest.main()
