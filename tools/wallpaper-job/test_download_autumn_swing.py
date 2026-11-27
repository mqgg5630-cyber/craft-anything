"""Offline checks; no requests to note hosts from the local environment."""
import io,json,os,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from PIL import Image
import download_sunset as engine
import download_autumn_swing as job

class DownloadTests(unittest.TestCase):
    def test_local_network_forbidden(self):
        old=(engine.ROOT,engine.SHARE_URL,engine.parse_note,engine.PUBLIC_NOTE_URLS[:])
        with patch.dict(os.environ,{},clear=True),patch.object(engine,'read_url') as read:
            with self.assertRaises(RuntimeError):job.main()
            read.assert_not_called()
        self.assertEqual((engine.ROOT,engine.SHARE_URL,engine.parse_note,engine.PUBLIC_NOTE_URLS),old)
    def test_note_and_all_images(self):
        note={'noteId':'a'*24,'title':'秋天和秋千很配哦～','imageList':[{'urlDefault':'https://sns-webpic-qc.xhscdn.com/one'},{'urlDefault':'https://sns-webpic-qc.xhscdn.com/two'}]}
        html='<script>window.__INITIAL_STATE__='+json.dumps({'noteData':{'data':note}})+'</script>'
        data=[]
        for color in ('red','white'):
            b=io.BytesIO();Image.new('RGB',(450,977),color).save(b,'PNG');data.append(b.getvalue())
        def read(url,limit):
            if url==job.SHARE_URL:return html.encode(),'https://www.xiaohongshu.com/explore/'+'a'*24
            return data[0 if url.endswith('one') else 1],url
        with tempfile.TemporaryDirectory() as tmp,patch.dict(os.environ,{'GITHUB_ACTIONS':'true'}),patch.object(job,'ROOT',Path(tmp)/'out'),patch.object(engine,'read_url',side_effect=read):
            job.main();m=json.loads((job.ROOT/'source-manifest.json').read_text())
            self.assertEqual(m['source_count'],2)
            for row in m['images']:self.assertEqual((row['width'],row['height']),(450,977))
    def test_wrong_title_rejected(self):
        html='<script>window.__INITIAL_STATE__='+json.dumps({'noteData':{'data':{'title':'other','imageList':[{}]}}})+'</script>'
        with self.assertRaises(ValueError):job.parse_note(html,'https://www.xiaohongshu.com/')

if __name__=='__main__':unittest.main()
