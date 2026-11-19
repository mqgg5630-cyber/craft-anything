from pathlib import Path
import unittest,json,hashlib
from PIL import Image
R=Path(__file__).resolve().parents[1]
class Test(unittest.TestCase):
 def test_ten_images(self):
  ps=sorted((R/'02-新漫画10张').glob('*.png'));self.assertEqual(len(ps),10);self.assertEqual(len({hashlib.md5(p.read_bytes()).hexdigest() for p in ps}),10)
  for p in ps:
   with Image.open(p) as im:self.assertEqual(im.size,(896,1200));im.verify()
 def test_new_dialogue(self):
  jobs=json.loads((R/'05-Skills/配方与对白.json').read_text())['jobs'];self.assertEqual(len(jobs),10)
  lines=[s for j in jobs for s in j['dialogue']];self.assertEqual(len(set(lines)),20)
  self.assertFalse(any(s in ['它太大啦！','够我们吃两天！'] for s in lines))
 def test_preview(self):
  with Image.open(R/'02-新漫画10张/总预览.jpg') as im:im.verify()
if __name__=='__main__':unittest.main()
