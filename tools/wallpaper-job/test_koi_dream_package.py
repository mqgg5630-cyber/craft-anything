"""Offline acceptance tests: downloaded originals, ten clean/UI pairs, previews."""
import hashlib
import json
import unittest
from PIL import Image, ImageChops
import package_koi_dream as job


class KoiDreamPackageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m=json.loads((job.ROOT/'output-manifest.json').read_text())

    def test_counts_roles_and_reference_mapping(self):
        m=self.m
        self.assertEqual((m['source_count'],m['source_cover_count'],m['source_artwork_count']),(3,1,2))
        self.assertEqual((m['clean_count'],m['simulated_ui_count']),(10,10))
        self.assertEqual(len(m['pairs']),10)
        for i,pair in enumerate(m['pairs']):
            self.assertEqual(pair['reference_files'],job.REFERENCES[i])
            self.assertNotIn(1,pair['reference_files'])
            self.assertEqual(pair['kind'],'reference_redraw' if i<2 else 'new_scene_same_series')
            self.assertEqual(pair['ui_wish'],job.WISHES[i])

    def test_all_image_hashes_bytes_dimensions_and_decoding(self):
        rows=self.m['sources']+self.m['previews']+[p[k] for p in self.m['pairs'] for k in ('clean','simulated_ui')]
        self.assertEqual(len(rows),27)
        for row in rows:
            with self.subTest(file=row['file']):
                p=job.ROOT/row['file'];data=p.read_bytes()
                self.assertEqual(len(data),row['bytes'])
                self.assertEqual(hashlib.sha256(data).hexdigest(),row['sha256'])
                self.assertEqual(hashlib.md5(data).hexdigest(),row['md5'])
                with Image.open(p) as im:
                    im.load();self.assertEqual(im.size,(row['width'],row['height']))

    def test_downloaded_originals_unchanged(self):
        source=json.loads((job.ROOT/'source-manifest.json').read_text())
        self.assertEqual(source['note_id'],'6acb2a3800000000120390ba')
        self.assertEqual(source['source_count'],3)
        self.assertEqual([(r['width'],r['height']) for r in source['images']],[(1080,1440),(853,1844),(853,1844)])
        for row in source['images']:
            self.assertEqual(hashlib.sha256((job.ROOT/row['file']).read_bytes()).hexdigest(),row['sha256'])
        self.assertEqual(len(list((job.ROOT/'01-下载原片').iterdir())),3)

    def test_ten_distinct_native_size_clean_and_ui_files(self):
        pairs=self.m['pairs']
        self.assertEqual(len({p['clean']['sha256'] for p in pairs}),10)
        self.assertEqual(len({p['simulated_ui']['sha256'] for p in pairs}),10)
        self.assertEqual(len(list((job.ROOT/'02-复刻无UI').glob('*.png'))),10)
        self.assertEqual(len(list((job.ROOT/'03-复刻模拟UI').glob('*.png'))),10)
        for p in pairs:
            self.assertNotEqual(p['clean']['sha256'],p['simulated_ui']['sha256'])
            for k in ('clean','simulated_ui'):
                self.assertEqual((p[k]['width'],p[k]['height']),(768,1376))

    def test_ui_nonmutating_and_middle_unmodified(self):
        image=Image.new('RGB',(768,1376),'#f3eedf');before=image.tobytes()
        for i in range(10):
            result=job.overlay(image,i)
            self.assertEqual(image.tobytes(),before)
            self.assertIsNotNone(ImageChops.difference(image,result).getbbox())
            self.assertIsNone(ImageChops.difference(image.crop((0,440,768,1100)),result.crop((0,440,768,1100))).getbbox())


if __name__=='__main__':
    unittest.main()
