from pathlib import Path
import hashlib,unittest,json
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
class Delivery(unittest.TestCase):
 def test_unique_pairs(self):
  a=sorted((ROOT/'02-复刻无手机UI').glob('*.png'));b=sorted((ROOT/'03-复刻有手机UI').glob('*.png'))
  self.assertEqual(len(a),10);self.assertEqual([p.name for p in a],[p.name for p in b]);self.assertEqual(len({sha(p) for p in a}),10)
  for p,q in zip(a,b):
   with Image.open(p) as im,Image.open(q) as ui:self.assertEqual(im.size,ui.size);self.assertGreaterEqual(im.height,1500);self.assertAlmostEqual(im.width/im.height,9/20,delta=.01)
   self.assertNotEqual(sha(p),sha(q))
 def test_previews(self):
  for folder in ['02-复刻无手机UI','03-复刻有手机UI']:
   with Image.open(ROOT/folder/'总预览.jpg') as im:im.verify()
 def test_recipe(self):
  d=json.loads((ROOT/'05-Skills/prompts.json').read_text());self.assertEqual(len(d['jobs']),10);self.assertIn('ORIGINAL STYLE',d['reference_use'])
if __name__=='__main__':unittest.main()
