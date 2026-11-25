import importlib.util,io,json,unittest
from pathlib import Path
from PIL import Image
spec=importlib.util.spec_from_file_location('koi',Path(__file__).with_name('download_koi_dream.py'));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class Tests(unittest.TestCase):
 def test_url_gate(self):
  self.assertTrue(m.public_url('https://sns-web-i10.rednotecdn.com/public'))
  for u in ['http://sns-web-i10.rednotecdn.com/a','https://rednotecdn.com.evil.test/a','https://user:pass@rednotecdn.com/a','https://example.com/a']:self.assertFalse(m.public_url(u))
 def test_decode(self):
  b=io.BytesIO();Image.new('RGB',(400,700)).save(b,format='PNG');a=m.decode(b.getvalue());self.assertEqual((a['width'],a['height']),(400,700));self.assertEqual(a['format'],'png')
 def test_invalid(self):
  with self.assertRaises(Exception):m.decode(b'not an image')
 def test_small(self):
  b=io.BytesIO();Image.new('RGB',(20,30)).save(b,format='PNG')
  with self.assertRaises(ValueError):m.decode(b.getvalue())
 def test_extract(self):
  note={'noteId':'test','imageList':[{'urlDefault':'https://rednotecdn.com/a'}]};s={'note':{'noteDetailMap':{'test':{'note':note}}}}
  self.assertEqual(m.extract('<script>window.__INITIAL_STATE__='+json.dumps(s)+'</script>'),note)
 def test_login(self):
  with self.assertRaises(ValueError):m.extract('<html>Login</html>')
if __name__=='__main__':unittest.main()
