"""Offline tests for folder-only, all-new copy and exact-size deliverables."""
import hashlib,json,os
from pathlib import Path
import unittest
from PIL import Image
import package_new_year_blessings as p
ROOT=Path(os.environ.get('NEW_YEAR_DELIVERY_ROOT','deliveries/new-year-blessings-10'))

class PackageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.m=json.loads((ROOT/'output-manifest.json').read_text())
    def test_ten_outputs(self):
        self.assertEqual(len(self.m['outputs']),10)
        self.assertEqual(len(list((ROOT/'02-十张新文案壁纸').glob('*.png'))),10)
        self.assertEqual(len({r['result']['sha256'] for r in self.m['outputs']}),10)
    def test_all_copy_replaced(self):
        phrases=[r[k] for r in self.m['outputs'] for k in ('right_phrase','left_phrase')]
        self.assertEqual(len(set(phrases)),20)
        for phrase in phrases:
            self.assertEqual(len(phrase),4)
            self.assertNotIn(phrase,p.SOURCE_PHRASES)
    def test_all_images_integrity(self):
        for row in self.m['sources']+self.m['previews']+[r['result'] for r in self.m['outputs']]:
            data=(ROOT/row['file']).read_bytes()
            self.assertEqual(len(data),row['bytes'])
            self.assertEqual(hashlib.sha256(data).hexdigest(),row['sha256'])
            self.assertEqual(hashlib.md5(data).hexdigest(),row['md5'])
            with Image.open(ROOT/row['file']) as im:im.load();self.assertEqual(list(im.size),[row['width'],row['height']])
    def test_same_source_size(self):
        for r in self.m['sources']+[r['result'] for r in self.m['outputs']]:self.assertEqual((r['width'],r['height']),(1080,2343))
    def test_folder_only(self):
        self.assertFalse(list(ROOT.rglob('*.zip')))
        self.assertIn('no ZIP',self.m['delivery_format'])
    def test_raw_backup_integrity(self):
        cloudpath=ROOT/'storage-verification.json'
        cloud=json.loads(cloudpath.read_text()) if cloudpath.exists() else None
        for row in self.m['outputs']:
            raw=row['raw'];path=ROOT/raw['file']
            if path.exists():self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(),raw['sha256'])
            else:
                self.assertIsNotNone(cloud,'Raw asset must be local or externally preserved')
                self.assertTrue(any(r['file']==raw['file'] and r['size_and_md5_match'] and r['sha256']==raw['sha256'] and r['bytes']==raw['bytes'] and r['md5']==raw['md5'] for r in cloud['raw_backups']))

if __name__=='__main__':unittest.main()
