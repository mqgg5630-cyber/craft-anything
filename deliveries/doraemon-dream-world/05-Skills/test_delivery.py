import hashlib
import json
from pathlib import Path
import unittest
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]

class Delivery(unittest.TestCase):
 def test_sources(self):
  record=json.loads((ROOT/'01-下载原图/下载记录.json').read_text())
  self.assertEqual(len(record['images']),4)
  for row in record['images']:
   p=ROOT/'01-下载原图'/row['file']
   self.assertEqual(hashlib.sha256(p.read_bytes()).hexdigest(),row['sha256'])
   with Image.open(p) as im:self.assertEqual(im.size,(row['width'],row['height']))
 def test_pairs(self):
  a=sorted((ROOT/'02-复刻无手机UI').glob('*.png'));b=sorted((ROOT/'03-复刻有手机UI').glob('*.png'))
  self.assertEqual(len(a),10);self.assertEqual([p.name for p in a],[p.name for p in b])
  self.assertEqual(len({hashlib.sha256(p.read_bytes()).hexdigest() for p in a}),10)
  for p,q in zip(a,b):
   with Image.open(p) as im,Image.open(q) as ui:
    self.assertEqual(im.size,ui.size);self.assertGreaterEqual(im.height,1500);self.assertAlmostEqual(im.width/im.height,9/20,delta=0.01)
   self.assertNotEqual(p.read_bytes(),q.read_bytes())
 def test_previews(self):
  for folder in ['02-复刻无手机UI','03-复刻有手机UI']:
   with Image.open(ROOT/folder/'总预览.jpg') as im:im.verify()
 def test_prompt_plan(self):
  plan=json.loads((ROOT/'05-Skills/prompts.json').read_text());self.assertEqual(len(plan['jobs']),10)
  self.assertEqual(sum(x['mode']=='new_scene_same_series' for x in plan['jobs']),9)

if __name__=='__main__':unittest.main()
