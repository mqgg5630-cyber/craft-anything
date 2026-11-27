"""Offline regression tests for download_lazy_sheep_0ca6: never access network from sandbox."""
import hashlib
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image
import download_lazy_sheep_0ca6 as job


class DownloadLazySheepTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / 'delivery'
        self.root.mkdir()
        buf = io.BytesIO()
        Image.new('RGB', (320, 640), 'orange').save(buf, 'WEBP')
        self.data = buf.getvalue()
        record = {
            'source_url': 'https://sns-web-i10.rednotecdn.com/notes_pre_post/test',
            'width': 320,
            'height': 640,
            'format': 'webp',
            'bytes': len(self.data),
            'md5': hashlib.md5(self.data).hexdigest(),
            'sha256': hashlib.sha256(self.data).hexdigest(),
        }
        seed = {
            'share_url': job.SHARE_URL,
            'note_id': job.NOTE_ID,
            'title': '带着小猫看晚霞的懒羊羊～',
            'author': '🍔',
            'provenance': {},
            'images': [record],
        }
        (self.root / 'source-seed.json').write_text(json.dumps(seed), encoding='utf-8')
        self.patches = [
            patch.object(job, 'ROOT', self.root),
            patch.dict(os.environ, {'GITHUB_ACTIONS': 'true'}),
        ]
        for p in self.patches:
            p.start()
            self.addCleanup(p.stop)

    def test_actions_gate(self):
        with patch.dict(os.environ, {'GITHUB_ACTIONS': 'false'}), patch.object(job, 'fetch') as fetch:
            with self.assertRaises(RuntimeError):
                job.main()
            fetch.assert_not_called()

    def test_single_source_verified(self):
        with patch.object(job, 'fetch', return_value=(self.data, 320, 640, 'webp')):
            job.main()
        self.assertEqual(len(list((self.root / 'source').glob('*.webp'))), 1)
        manifest = json.loads((self.root / 'source-manifest.json').read_text(encoding='utf-8'))
        self.assertEqual(manifest['reference_count_downloaded'], 1)
        self.assertTrue(manifest['images'][0]['historical_hash_match'])

    def test_wrong_hash_rejected(self):
        seed_path = self.root / 'source-seed.json'
        seed = json.loads(seed_path.read_text(encoding='utf-8'))
        seed['images'][0]['sha256'] = '0' * 64
        seed_path.write_text(json.dumps(seed), encoding='utf-8')
        with patch.object(job, 'fetch', return_value=(self.data, 320, 640, 'webp')):
            with self.assertRaisesRegex(ValueError, 'sha256'):
                job.main()
        self.assertFalse((self.root / 'source').exists())

    def test_corrupt_bytes_rejected(self):
        with patch.object(job, 'fetch', return_value=(b'not an image', 320, 640, 'webp')):
            with self.assertRaises(OSError):
                job.main()
        self.assertFalse((self.root / 'source').exists())

    def test_existing_different_source_not_overwritten(self):
        (self.root / 'source').mkdir()
        target = self.root / 'source/01.webp'
        target.write_bytes(b'preserve')
        with patch.object(job, 'fetch', return_value=(self.data, 320, 640, 'webp')):
            with self.assertRaises(RuntimeError):
                job.main()
        self.assertEqual(target.read_bytes(), b'preserve')


if __name__ == '__main__':
    unittest.main()
