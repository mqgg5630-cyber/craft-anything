"""Offline acceptance checks for exact first-reference size and faithful typesetting."""
from pathlib import Path
import json,unittest,hashlib
from PIL import Image,ImageChops
import package_delivery as pkg
ROOT=Path(__file__).resolve().parent
class Tests(unittest.TestCase):
 def test_unique_first_source(self):
  m=json.loads((ROOT/'source-manifest.json').read_text());self.assertEqual(len(m['images']),1);self.assertEqual(len(list((ROOT/'source').iterdir())),1)
  a=m['images'][0];b=pkg.details(ROOT/a['file'])
  for k in ['format','width','height','bytes','md5','sha256']:self.assertEqual(a[k],b[k])
  self.assertEqual((a['width'],a['height']),(884,1851))
 def test_all_final_files_exact_size(self):
  m=json.loads((ROOT/'output-manifest.json').read_text());self.assertEqual(len(m['files']),10)
  self.assertEqual([p.name for p in sorted((ROOT/'images').iterdir())],[f'{i:02}.png' for i in range(1,11)])
  for r in m['files']:
   actual=pkg.details(ROOT/r['file']);self.assertEqual((actual['width'],actual['height']),(884,1851));self.assertEqual(r['references'],['source/01.webp'])
   for k in ['file','format','width','height','bytes','md5','sha256']:self.assertEqual(actual[k],r[k])
 def test_ten_independent_artworks(self):
  for folder in ['artwork','images']:
   paths=list((ROOT/folder).glob('*.png'));self.assertEqual(len(paths),10);self.assertEqual(len({hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}),10)
 def test_exact_typography_reproduction(self):
  for i,phrase in enumerate(pkg.PHRASES):
   self.assertEqual(len(phrase),4)
   with Image.open(ROOT/f'artwork/{i+1:02}.png') as base,Image.open(ROOT/f'images/{i+1:02}.png') as actual:
    expected,_=pkg.letter(pkg.sized_art(base,(884,1851)),phrase)
    self.assertIsNone(ImageChops.difference(expected,actual.convert('RGB')).getbbox())
 def test_two_boards(self):
  paths=list(ROOT.glob('00-*.jpg'));self.assertEqual(len(paths),2)
  for p in paths:
   with Image.open(p) as im:im.load();self.assertGreater(im.width,1000)
if __name__=='__main__':unittest.main()
