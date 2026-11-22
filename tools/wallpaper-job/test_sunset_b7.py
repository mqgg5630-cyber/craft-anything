"""Offline regression tests: never access Xiaohongshu from the sandbox."""
import hashlib
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image
import download_sunset_b7 as job


class DownloadTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / 'delivery'
        self.root.mkdir()
        buf = io.BytesIO()
        Image.new('RGB', (320, 480), 'orange').save(buf, 'PNG')
        self.data = buf.getvalue()
        record = {'source_url': 'https://sns-img-bd.xhscdn.com/notes_pre_post/test',
                  'width': 320, 'height': 480, 'format': 'png', 'bytes': len(self.data),
                  'md5': hashlib.md5(self.data).hexdigest(), 'sha256': hashlib.sha256(self.data).hexdigest()}
        seed = {'share_url': job.SHARE_URL, 'note_id': job.NOTE_ID, 'title': 'test',
                'author': 'test', 'provenance': {}, 'images': [record.copy() for _ in range(5)]}
        (self.root / 'source-seed.json').write_text(json.dumps(seed))
        self.patches = [patch.object(job, 'ROOT', self.root), patch.dict(os.environ, {'GITHUB_ACTIONS': 'true'})]
        for p in self.patches:
            p.start(); self.addCleanup(p.stop)

    def test_actions_gate(self):
        with patch.dict(os.environ, {'GITHUB_ACTIONS': 'false'}), patch.object(job, 'fetch') as fetch:
            with self.assertRaises(RuntimeError): job.main()
            fetch.assert_not_called()

    def test_all_five_verified(self):
        with patch.object(job, 'fetch', return_value=(self.data, 320, 480, 'png')):
            job.main()
        self.assertEqual(len(list((self.root / 'source').glob('*.png'))), 5)
        manifest = json.loads((self.root / 'source-manifest.json').read_text())
        self.assertTrue(all(x['historical_hash_match'] for x in manifest['images']))

    def test_last_image_failure_writes_no_sources(self):
        good = (self.data, 320, 480, 'png')
        with patch.object(job, 'fetch', side_effect=[good] * 4 + [ValueError('failure')]):
            with self.assertRaises(ValueError): job.main()
        self.assertFalse((self.root / 'source').exists())
        self.assertFalse((self.root / 'source-manifest.json').exists())

    def test_wrong_historical_hash_rejected(self):
        seed_path = self.root / 'source-seed.json'
        seed = json.loads(seed_path.read_text()); seed['images'][0]['sha256'] = '0' * 64
        seed_path.write_text(json.dumps(seed))
        with patch.object(job, 'fetch', return_value=(self.data, 320, 480, 'png')):
            with self.assertRaisesRegex(ValueError, 'sha256'): job.main()
        self.assertFalse((self.root / 'source').exists())

    def test_corrupt_bytes_rejected(self):
        with patch.object(job, 'fetch', return_value=(b'not an image', 320, 480, 'png')):
            with self.assertRaises(OSError): job.main()
        self.assertFalse((self.root / 'source').exists())

    def test_existing_different_source_not_overwritten(self):
        (self.root / 'source').mkdir()
        target = self.root / 'source/01.png'; target.write_bytes(b'preserve')
        with patch.object(job, 'fetch', return_value=(self.data, 320, 480, 'png')):
            with self.assertRaises(RuntimeError): job.main()
        self.assertEqual(target.read_bytes(), b'preserve')


if __name__ == '__main__':
    unittest.main()
