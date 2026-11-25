"""Offline tests proving that no carousel image except the first is fetched."""
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from PIL import Image
import download_sunset as engine
import download_simple_fresh_first as job


def page(note):
    return '<script>window.__INITIAL_STATE__='+json.dumps({'noteData':{'data':note}})+'</script>'


class FreshFirstDownloadTests(unittest.TestCase):
    def test_only_first_selected(self):
        note={'noteId':'a'*24,'title':'简单清新壁纸','imageList':[{'urlDefault':'https://sns-webpic-qc.xhscdn.com/first'},{'urlDefault':'https://sns-webpic-qc.xhscdn.com/never-fetch'}]}
        actual=job.parse_note(page(note),'https://www.xiaohongshu.com/explore/'+'a'*24)
        self.assertEqual(len(actual['imageList']),1)
        self.assertEqual(actual['imageList'][0],note['imageList'][0])
        self.assertEqual(job._selection['observed_carousel_count'],2)

    def test_local_network_prohibited_and_configuration_restored(self):
        before=(engine.ROOT,engine.SHARE_URL,engine.parse_note,engine.PUBLIC_NOTE_URLS[:])
        with patch.dict(os.environ,{},clear=True),patch.object(engine,'read_url') as read:
            with self.assertRaises(RuntimeError):job.main()
            read.assert_not_called()
        self.assertEqual((engine.ROOT,engine.SHARE_URL,engine.parse_note,engine.PUBLIC_NOTE_URLS),before)

    def test_download_first_only_and_record_its_exact_size(self):
        buffer=io.BytesIO();Image.new('RGB',(450,977),'#ebf5f0').save(buffer,'PNG')
        data=buffer.getvalue();url='https://www.xiaohongshu.com/explore/'+'a'*24
        first='https://sns-webpic-qc.xhscdn.com/first'
        note={'noteId':'a'*24,'title':'简单清新壁纸','imageList':[{'urlDefault':first},{'urlDefault':'https://sns-webpic-qc.xhscdn.com/never-fetch'}]}
        def read(address,limit):
            if address==job.SHARE_URL:return page(note).encode(),url
            if address==first:return data,first
            raise AssertionError('Non-first source image requested')
        with tempfile.TemporaryDirectory() as tmp,patch.dict(os.environ,{'GITHUB_ACTIONS':'true'}):
            root=Path(tmp)/'delivery'
            with patch.object(job,'ROOT',root),patch.object(engine,'read_url',side_effect=read) as fetch:
                job.main()
            m=json.loads((root/'source-manifest.json').read_text())
            self.assertEqual((m['images'][0]['width'],m['images'][0]['height']),(450,977))
            self.assertEqual(m['observed_carousel_count'],2)
            self.assertEqual(m['source_count'],1)
            self.assertFalse(m['other_carousel_images_downloaded'])
            self.assertEqual((root/'01-下载原片/01.png').read_bytes(),data)
            self.assertEqual(fetch.call_count,2)


if __name__=='__main__':unittest.main()
