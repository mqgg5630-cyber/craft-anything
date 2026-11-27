"""Offline acquisition regression; never request XHS/CDN from the sandbox."""
import io,json,os,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from PIL import Image
import download_autumn_swing_b7 as job
class Tests(unittest.TestCase):
 def test_actions_only(self):
  with patch.dict(os.environ,{'GITHUB_ACTIONS':'false'}),patch.object(job,'read_url') as read:
   with self.assertRaises(RuntimeError):job.main()
   read.assert_not_called()
 def test_bounded_international_note(self):
  note={'noteId':'6abdb5a9000000001802f193','title':'秋天和秋千很配哦～','imageList':[{'urlDefault':'https://sns-webpic-qc.xhscdn.com/test'}]}
  html='<script>window.__INITIAL_STATE__='+json.dumps({'noteData':{'data':note}})+'</script>'
  self.assertEqual(job.parse_note(html,'https://www.rednote.com/discovery/item/'+note['noteId']),note)
 def test_wrong_title(self):
  html='<script>window.__INITIAL_STATE__='+json.dumps({'data':{'title':'other','imageList':[{}]}})+'</script>'
  with self.assertRaises(ValueError):job.parse_note(html,'https://www.rednote.com/')
 def test_host_allowlist(self):
  for bad in ['http://example.com/a','https://example.com/a','https://xhscdn.com.evil.test/a','https://user:pass@xhscdn.com/a']:
   with self.assertRaises(ValueError):job.check_url(bad)
 def test_public_candidate_validation(self):
  b=io.BytesIO();Image.new('RGB',(852,1848),'orange').save(b,'JPEG');self.assertEqual(job.validate(b.getvalue()),(852,1848,'jpg'))
  with self.assertRaises(OSError):job.validate(b'not an image')
 def test_transactional_download(self):
  b=io.BytesIO();Image.new('RGB',(852,1848),'orange').save(b,'JPEG');data=b.getvalue();note={'noteId':'6abdb5a9000000001802f193','title':'秋天和秋千很配哦～','imageList':[{'urlDefault':'https://sns-webpic-qc.xhscdn.com/test'}]}
  html='<script>window.__INITIAL_STATE__='+json.dumps({'noteData':{'data':note}})+'</script>'
  def read(url,limit):return (html.encode(),'https://www.rednote.com/discovery/item/'+note['noteId']) if url==job.SHARE_URL else (data,url)
  with tempfile.TemporaryDirectory() as tmp,patch.object(job,'ROOT',Path(tmp)/'delivery'),patch.dict(os.environ,{'GITHUB_ACTIONS':'true'}),patch.object(job,'read_url',side_effect=read):
   job.main();m=json.loads((job.ROOT/'source-manifest.json').read_text());self.assertEqual(len(m['images']),1);self.assertEqual((job.ROOT/m['images'][0]['file']).read_bytes(),data)
if __name__=='__main__':unittest.main()
