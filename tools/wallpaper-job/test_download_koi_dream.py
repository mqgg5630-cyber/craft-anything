"""Offline Koi Dream job tests. Requests are mocked; no live network calls."""
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from PIL import Image
import download_sunset as engine
import download_koi_dream as job


def page(note):
    return '<script>window.__INITIAL_STATE__='+json.dumps({'noteData':{'data':note}})+'</script>'


class KoiDreamDownloadTests(unittest.TestCase):
    def test_title_and_note_identity(self):
        url='https://www.xiaohongshu.com/explore/'+'a'*24
        note={'noteId':'a'*24,'title':'锦鲤入梦｜锁屏壁纸','imageList':[{}]}
        self.assertEqual(job.parse_note(page(note),url)['noteId'],'a'*24)
        with self.assertRaises(ValueError):
            job.parse_note(page(note),url.replace('a'*24,'b'*24))
        note['title']='今天是谁家的可爱噜啊'
        with self.assertRaises(ValueError):
            job.parse_note(page(note),url)

    def test_no_local_download_or_global_config_leak(self):
        original=(engine.ROOT,engine.SHARE_URL,engine.parse_note,engine.PUBLIC_NOTE_URLS[:])
        with patch.dict(os.environ,{},clear=True),patch.object(engine,'read_url') as read:
            with self.assertRaises(RuntimeError):
                job.main()
            read.assert_not_called()
        self.assertEqual((engine.ROOT,engine.SHARE_URL,engine.parse_note,engine.PUBLIC_NOTE_URLS),original)

    def test_success_then_atomic_duplicate_rollback(self):
        buffer=io.BytesIO();Image.new('RGB',(450,800),'#042c3d').save(buffer,'PNG')
        data=buffer.getvalue()
        url='https://www.xiaohongshu.com/explore/'+'a'*24
        note={'noteId':'a'*24,'title':'锦鲤入梦｜锁屏壁纸',
              'imageList':[{'urlDefault':'https://sns-webpic-qc.xhscdn.com/test'}]}
        with tempfile.TemporaryDirectory() as tmp,patch.dict(os.environ,{'GITHUB_ACTIONS':'true'}):
            root=Path(tmp)/'valid'
            with patch.object(job,'ROOT',root),patch.object(engine,'read_url',side_effect=[(page(note).encode(),url),(data,url)]):
                job.main()
            self.assertEqual((root/'01-下载原片/01.png').read_bytes(),data)
            self.assertEqual(json.loads((root/'source-manifest.json').read_text())['source_count'],1)
            note['imageList']*=2;root=Path(tmp)/'duplicate'
            with patch.object(job,'ROOT',root),patch.object(engine,'read_url',side_effect=[(page(note).encode(),url),(data,url),(data,url)]):
                with self.assertRaises(ValueError):
                    job.main()
            self.assertFalse(root.exists())
            self.assertEqual(sorted(p.name for p in Path(tmp).iterdir()),['valid'])


if __name__=='__main__':
    unittest.main()
