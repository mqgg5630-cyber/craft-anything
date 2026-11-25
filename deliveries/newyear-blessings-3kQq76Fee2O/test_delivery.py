"""Local acceptance tests. pip install Pillow fonttools"""
import unittest,json,hashlib
from PIL import Image,ImageChops
from fontTools.ttLib import TTFont
import package_delivery as p
class DeliveryTests(unittest.TestCase):
 def test_originals_match_runner_and_history(self):
  m=json.loads((p.ROOT/'source-manifest.json').read_text());seed=json.loads((p.ROOT/'source-seed.json').read_text());self.assertEqual(len(m['images']),4)
  for r,e in zip(m['images'],seed['images']):
   a=p.info(p.ROOT/r['file'])
   for k in ['width','height','bytes','md5','sha256']:self.assertEqual(a[k],r[k]);self.assertEqual(a[k],e[k])
   self.assertEqual((a['width'],a['height']),p.SIZE)
 def test_exact_sizes_and_manifests(self):
  m=json.loads((p.ROOT/'output-manifest.json').read_text());self.assertEqual(len(m['files']),10)
  self.assertEqual(len(list((p.ROOT/'images').glob('*.png'))),10)
  for r in m['files']:
   a=p.info(p.ROOT/r['file'])
   for k in a:self.assertEqual(a[k],r[k])
   self.assertEqual((a['width'],a['height']),p.SIZE);self.assertFalse(r['ui'])
   self.assertEqual(len(r['reference']),1);self.assertTrue((p.ROOT/r['reference'][0]).exists())
 def test_all_copy_new_and_font_covered(self):
  new=[s for row in p.COPY for s in row[:2]];self.assertEqual(len(set(new)),20)
  # Normalize both traditional forbidden and simplified source strings explicitly.
  old=p.FORBIDDEN+['万稳万当','不如一默','欢喜由心','自在如风','爱财爱己','风生水起','安康如意','顺遂福来']
  self.assertFalse(set(new)&set(old));cmap=TTFont(p.BRUSH).getBestCmap()
  for row in p.COPY:
   for s in row:self.assertEqual(len(s),4);self.assertTrue(all(ord(c) in cmap for c in s))
 def test_unique_background_and_final(self):
  for folder in ['artwork','images']:
   paths=list((p.ROOT/folder).glob('*.png'));self.assertEqual(len(paths),10);self.assertEqual(len({hashlib.sha256(x.read_bytes()).hexdigest() for x in paths}),10)
 def test_pixel_identical_reproduction_and_glyph_in_slip(self):
  for i in range(10):
   with Image.open(p.ROOT/f'artwork/{i+1:02}.png') as raw,Image.open(p.ROOT/f'images/{i+1:02}.png') as actual:
    expected,cols=p.typeset(p.fit(raw),i);self.assertIsNone(ImageChops.difference(expected,actual.convert('RGB')).getbbox())
    for col in cols:
     x0,y0,x1,y1=col['box_normalized'];fs=col['font_px']
     for x,y in col['glyph_centers']:
      self.assertGreater(x-fs/2,x0*p.SIZE[0]);self.assertLess(x+fs/2,x1*p.SIZE[0]);self.assertGreater(y-fs/2,y0*p.SIZE[1]);self.assertLess(y+fs/2,y1*p.SIZE[1])
 def test_previews(self):
  boards=list(p.ROOT.glob('00-*.jpg'));self.assertEqual(len(boards),2)
  for path in boards:
   with Image.open(path) as im:im.load();self.assertEqual(im.width,1400)
if __name__=='__main__':unittest.main()
