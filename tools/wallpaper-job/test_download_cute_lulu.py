"""Offline tests: this job does not fetch any image in the agent sandbox."""
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from PIL import Image
import download_sunset as engine
import download_cute_lulu as job


def page(note):
    return '<script>window.__INITIAL_STATE__=' + json.dumps({'noteData': {'data': note}}) + '</script>'


class CuteLuluDownloadTests(unittest.TestCase):
    def test_correct_note_title(self):
        note = {'noteId': 'a'*24, 'title': '今天是谁家的可爱噜啊', 'imageList': [{}]}
        url = 'https://www.xiaohongshu.com/explore/' + 'a'*24
        self.assertEqual(job.parse_note(page(note), url)['noteId'], 'a'*24)
        note['title'] = '和你一起奔夕阳'
        with self.assertRaises(ValueError):
            job.parse_note(page(note), url)

    def test_cannot_download_locally(self):
        with patch.dict(os.environ, {}, clear=True), patch.object(engine, 'read_url') as read:
            with self.assertRaises(RuntimeError):
                job.main()
            read.assert_not_called()

    def test_atomic_success_and_duplicate_rollback(self):
        buf = io.BytesIO()
        Image.new('RGB', (400, 800), '#abcdee').save(buf, 'PNG')
        data = buf.getvalue()
        url = 'https://www.xiaohongshu.com/explore/' + 'a'*24
        note = {'noteId': 'a'*24, 'title': '今天是谁家的可爱噜啊',
                'imageList': [{'urlDefault':'https://sns-webpic-qc.xhscdn.com/test'}]}
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {'GITHUB_ACTIONS':'true'}):
            root = Path(tmp)/'valid'
            with patch.object(job, 'ROOT', root), patch.object(engine, 'read_url', side_effect=[(page(note).encode(),url), (data,url)]):
                job.main()
            self.assertEqual((root/'01-下载原片/01.png').read_bytes(), data)
            self.assertTrue((root/'source-manifest.json').exists())
            self.assertTrue((root/'原片总预览.jpg').exists())
            root = Path(tmp)/'duplicate'
            note['imageList'] *= 2
            with patch.object(job, 'ROOT', root), patch.object(engine, 'read_url', side_effect=[(page(note).encode(),url), (data,url), (data,url)]):
                with self.assertRaises(ValueError):
                    job.main()
            self.assertFalse(root.exists())
            self.assertEqual(sorted(p.name for p in Path(tmp).iterdir()), ['valid'])


if __name__ == '__main__':
    unittest.main()
