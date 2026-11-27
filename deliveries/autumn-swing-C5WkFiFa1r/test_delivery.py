"""Offline checks for ten actually new results and exact source-based dimensions."""
import unittest,json,hashlib
from PIL import Image,ImageChops
import package_delivery as p
class DeliveryTests(unittest.TestCase):
 def test_source_hash_and_size(self):
  m=json.loads((p.ROOT/'source-manifest.json').read_text());self.assertEqual(len(m['images']),1);a=p.info(p.ROOT/'source/01.jpg')
  for k in ['width','height','bytes','md5','sha256']:self.assertEqual(a[k],m['images'][0][k])
  self.assertEqual(a['md5'],'3bca5f33f5d14138709ed324621ddcda');self.assertEqual((a['width'],a['height']),(852,1848))
 def test_exact_ten_final_png(self):
  self.assertEqual([x.name for x in sorted((p.ROOT/'images').iterdir())],[f'{i:02}.png' for i in range(1,11)])
  m=json.loads((p.ROOT/'output-manifest.json').read_text());self.assertEqual(len(m['files']),10);self.assertEqual(m['new_generation_calls'],10);self.assertFalse(m['old_results_reused'])
  for r in m['files']:
   a=p.info(p.ROOT/r['file'])
   for k in a:self.assertEqual(a[k],r[k])
   self.assertEqual((a['width'],a['height']),p.SIZE);self.assertEqual(r['references'],['source/01.jpg']);self.assertFalse(r['ui']);self.assertFalse(r['added_text']);self.assertTrue(r['new_generation'])
 def test_ten_unique_raw_and_final_not_old(self):
  old=p.REPO/'deliveries/newyear-blessings-3kQq76Fee2O';oldhashes={hashlib.sha256(x.read_bytes()).hexdigest() for folder in ['images','artwork'] for x in (old/folder).glob('*.png')}
  for folder in ['artwork','images']:
   paths=list((p.ROOT/folder).glob('*.png'));self.assertEqual(len(paths),10);hashes={hashlib.sha256(x.read_bytes()).hexdigest() for x in paths};self.assertEqual(len(hashes),10);self.assertFalse(hashes&oldhashes)
 def test_exact_reconstruction(self):
  for i in range(1,11):
   with Image.open(p.ROOT/f'artwork/{i:02}.png') as raw,Image.open(p.ROOT/f'images/{i:02}.png') as actual:
    expected=p.adapt(raw);self.assertIsNone(ImageChops.difference(expected,actual.convert('RGB')).getbbox())
 def test_previews(self):
  boards=list(p.ROOT.glob('00-*.jpg'));self.assertEqual(len(boards),3)
  for path in boards:
   with Image.open(path) as im:im.load();self.assertGreaterEqual(im.width,520)
 def test_future_default_updated(self):
  settings=json.loads((p.REPO/'skills/xhs-link-recreate-10/wallpaper-preferences.json').read_text());self.assertEqual((settings['default_final_size']['width'],settings['default_final_size']['height']),p.SIZE);self.assertTrue(settings['separate_source_and_results']);self.assertFalse(settings['reuse_existing_results_as_new_generation'])
if __name__=='__main__':unittest.main()
