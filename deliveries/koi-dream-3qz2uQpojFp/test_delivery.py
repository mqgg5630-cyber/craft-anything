"""Offline delivery acceptance checks; never requests network."""
import json,hashlib,unittest
from pathlib import Path
from PIL import Image,ImageChops
import package_delivery as pkg
ROOT=Path(__file__).resolve().parent
class Tests(unittest.TestCase):
 def test_all_files(self):
  for manifest,key,count in [('source-manifest.json','images',3),('output-manifest.json','files',20)]:
   m=json.loads((ROOT/manifest).read_text());self.assertEqual(len(m[key]),count)
   for r in m[key]:
    self.assertEqual(pkg.info(ROOT/r['file']),{k:r[k] for k in ['file','format','width','height','bytes','md5','sha256']})
 def test_exact_counts_and_unique(self):
  for folder,count,ext in [('images',10,'png'),('ui',10,'png'),('source',3,'webp')]:
   paths=sorted((ROOT/folder).iterdir());self.assertEqual([p.name for p in paths],[f'{i:02}.{ext}' for i in range(1,count+1)])
   self.assertEqual(len({hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}),count)
 def test_ui_pixel_pairing(self):
  for i in range(10):
   with Image.open(ROOT/f'images/{i+1:02}.png') as original,Image.open(ROOT/f'ui/{i+1:02}.png') as ui:
    self.assertEqual(original.size,ui.size)
    expected=Image.alpha_composite(original.convert('RGBA'),pkg.ui_layer(original.size,i)).convert('RGB')
    self.assertIsNone(ImageChops.difference(expected,ui.convert('RGB')).getbbox())
    self.assertIsNotNone(ImageChops.difference(original.convert('RGB'),ui.convert('RGB')).getbbox())
 def test_original_hashes_and_reference_links(self):
  seed=json.loads((ROOT/'source-seed.json').read_text());source=json.loads((ROOT/'source-manifest.json').read_text());self.assertEqual(seed['note_id'],source['note_id'])
  for a,b in zip(seed['images'],source['images']):
   for k in ['md5','sha256','width','height','bytes']:self.assertEqual(a[k],b[k])
  for r in json.loads((ROOT/'output-manifest.json').read_text())['files']:
   for ref in r['references']:self.assertTrue((ROOT/ref).exists())
 def test_boards(self):
  paths=list(ROOT.glob('00-*.jpg'));self.assertEqual(len(paths),4)
  for p in paths:
   with Image.open(p) as im:im.load();self.assertGreater(im.width,500)
if __name__=='__main__':unittest.main()
