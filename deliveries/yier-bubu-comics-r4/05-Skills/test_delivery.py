import unittest,json,hashlib
from pathlib import Path
from PIL import Image
R=Path(__file__).resolve().parents[1]
class Delivery(unittest.TestCase):
 def test_rule(self):
  d=json.loads((R/'05-Skills/配方与验收.json').read_text());f=d['files']
  self.assertEqual(len(f),10);self.assertEqual(len({x['headwear_left'] for x in f}),10)
  for x in f:self.assertEqual(x['headwear_left'],x['headwear_right'])
 def test_images(self):
  d=json.loads((R/'05-Skills/配方与验收.json').read_text())
  for x in d['files']:
   p=R/'02-新漫画10张'/x['file'];self.assertEqual(hashlib.md5(p.read_bytes()).hexdigest(),x['md5'])
   with Image.open(p) as im:im.load();self.assertEqual(list(im.size),x['size'])
 def test_overview(self):
  with Image.open(R/'02-新漫画10张/总预览.jpg') as im:self.assertEqual(im.size,(1600,900))
if __name__=='__main__':unittest.main()
