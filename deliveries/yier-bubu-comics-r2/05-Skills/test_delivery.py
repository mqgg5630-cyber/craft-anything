from pathlib import Path
import json,hashlib,unittest
from PIL import Image
R=Path(__file__).resolve().parents[1]
class Delivery(unittest.TestCase):
 def test_ten_native_images(self):
  jobs=json.loads((R/'05-Skills/配方与验收.json').read_text())['jobs'];self.assertEqual(len(jobs),10)
  self.assertEqual(len(list((R/'02-新漫画10张').glob('*.png'))),10)
  for j in jobs:
   p=R/'02-新漫画10张'/j['file'];self.assertEqual(hashlib.md5(p.read_bytes()).hexdigest(),j['md5'])
   with Image.open(p) as im:self.assertEqual(im.size,(896,1200));im.verify()
 def test_unique_hats_and_dialogue(self):
  js=json.loads((R/'05-Skills/配方与验收.json').read_text())['jobs'];self.assertEqual(len({h for j in js for h in j['hats']}),20);self.assertEqual(len({s for j in js for s in j['dialogue']}),20)
 def test_preview(self):
  with Image.open(R/'02-新漫画10张/总预览.jpg') as im:im.verify()
if __name__=='__main__':unittest.main()
