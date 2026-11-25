"""Offline contracts for the first-image-only wallpaper delivery."""
import hashlib
import json
import os
from pathlib import Path
import unittest
from PIL import Image
import package_simple_fresh as p

ROOT=Path(os.environ.get('FRESH_DELIVERY_ROOT','deliveries/simple-fresh-first-10'))

class DeliveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m=json.loads((ROOT/'output-manifest.json').read_text())
    def test_first_reference_only(self):
        self.assertTrue(self.m['only_first_reference'])
        self.assertFalse(self.m['other_carousel_images_downloaded_or_used'])
        self.assertEqual(self.m['source']['sha256'],'312d1ffbcbf63aa7690706f0c6c9af2f3a521ef619a6fcdff350b6460e7f3ea7')
    def test_exact_ten(self):
        self.assertEqual(len(self.m['outputs']),10)
        self.assertEqual(len(list((ROOT/'02-同尺寸四字祝福').glob('*.png'))),10)
        self.assertEqual(len({r['result']['sha256'] for r in self.m['outputs']}),10)
    def test_images_and_hashes(self):
        for row in [self.m['source']]+self.m['previews']+[r['result'] for r in self.m['outputs']]:
            f=ROOT/row['file'];data=f.read_bytes()
            self.assertEqual(len(data),row['bytes'])
            self.assertEqual(hashlib.sha256(data).hexdigest(),row['sha256'])
            with Image.open(f) as im:
                im.load();self.assertEqual(list(im.size),[row['width'],row['height']])
    def test_exact_size_wishes_and_fit(self):
        for r in self.m['outputs']:
            self.assertEqual([r['result']['width'],r['result']['height']],[884,1845])
            self.assertEqual(len(r['wish']),4)
            self.assertEqual(r['reference_image_index'],1)
            self.assertIn('no axis stretch',r['sizing']['method'])
        self.assertFalse(self.m['mobile_ui_added'])
    def test_raw_inputs_preserved(self):
        for r in self.m['outputs']:
            f=ROOT/'03-复现资源/底图'/r['raw_file']
            self.assertEqual(hashlib.sha256(f.read_bytes()).hexdigest(),r['raw_sha256'])
    def test_mask_components(self):
        im=Image.new('L',(12,12));im.putpixel((0,0),255)
        for x,y in [(8,8),(8,9),(9,9)]:im.putpixel((x,y),255)
        result=p.largest_components(im,1)
        self.assertEqual(result.getpixel((0,0)),0)
        self.assertEqual(result.getpixel((9,9)),255)

if __name__=='__main__':unittest.main()
