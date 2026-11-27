"""Offline delivery contracts; source unchanged, exact pixels and folder format."""
import hashlib,json,unittest
from pathlib import Path
from PIL import Image
import package_autumn_swing as p

class PackageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.m=json.loads((p.ROOT/'output-manifest.json').read_text())
    def test_ten_distinct(self):
        self.assertEqual(len(self.m['outputs']),10)
        self.assertEqual(len(list((p.ROOT/'02-十张复刻壁纸').glob('*.png'))),10)
        self.assertEqual(len({r['result']['sha256'] for r in self.m['outputs']}),10)
    def test_all_hashes_and_decoding(self):
        for row in self.m['sources']+self.m['previews']+[r['result'] for r in self.m['outputs']]:
            p.check(row)
            self.assertEqual(hashlib.md5((p.ROOT/row['file']).read_bytes()).hexdigest(),row['md5'])
    def test_exact_original_dimensions(self):
        for r in self.m['sources']+[r['result'] for r in self.m['outputs']]:self.assertEqual((r['width'],r['height']),(852,1848))
        self.assertEqual(self.m['sources'][0]['sha256'],'eb4d525baab9308a18681b1c8bda6fb05b9ea8c2cb3890a4b5b6bb0d391c5d8b')
    def test_no_ui_text_or_zip(self):
        self.assertFalse(self.m['added_text']);self.assertFalse(self.m['mobile_ui_added'])
        self.assertFalse(list(p.ROOT.rglob('*.zip')))
    def test_latest_defaults(self):
        policy=json.loads(Path('tools/wallpaper-job/delivery-defaults.json').read_text())
        self.assertEqual(policy['wallpaper_size'],[852,1848]);self.assertEqual(policy['size_basis']['note_id'],self.m['note_id'])
    def test_raw_preservation(self):
        verification=p.ROOT/'storage-verification.json'
        storage=json.loads(verification.read_text()) if verification.is_file() else None
        for row in self.m['outputs']:
            raw=row['raw'];local=p.RAW/Path(raw['file']).name
            if local.is_file():self.assertEqual(hashlib.sha256(local.read_bytes()).hexdigest(),raw['sha256'])
            else:
                self.assertIsNotNone(storage)
                self.assertTrue(any(r['file']==raw['file'] and r['verified'] and r['sha256']==raw['sha256'] for r in storage['raw_backups']))
    def test_no_stretch(self):
        for row in self.m['outputs']:
            s=row['sizing'];w,h=row['raw']['width'],row['raw']['height']
            self.assertAlmostEqual(w-2*s['raw_crop_each_side'][0],852/s['scale'])
            self.assertAlmostEqual(h-2*s['raw_crop_each_side'][1],1848/s['scale'])

if __name__=='__main__':unittest.main()
