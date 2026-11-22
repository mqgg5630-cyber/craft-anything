"""Offline acceptance tests against this independently delivered cute Lulu set."""
import hashlib
import json
import unittest
from PIL import Image, ImageChops
import package_cute_lulu as job


class CuteLuluPackageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = json.loads((job.ROOT/'output-manifest.json').read_text())

    def test_counts_and_scene_reference_mapping(self):
        m = self.manifest
        self.assertEqual((m['source_count'], m['clean_count'], m['simulated_ui_count']), (5,10,10))
        self.assertEqual(len(m['pairs']),10)
        self.assertEqual(len(set(job.QUOTES)),10)
        for i,pair in enumerate(m['pairs']):
            self.assertEqual(pair['references'],job.REFERENCES[i])
            self.assertEqual(pair['quote'],job.QUOTES[i])
            self.assertEqual(pair['kind'],'reference_redraw' if i<5 else 'new_scene_same_series')

    def test_all_file_bytes_hashes_dimensions_and_decodes(self):
        m = self.manifest
        rows = m['sources']+m['previews']+[p[k] for p in m['pairs'] for k in ('clean','simulated_ui')]
        for row in rows:
            with self.subTest(file=row['file']):
                data=(job.ROOT/row['file']).read_bytes()
                self.assertEqual(len(data),row['bytes'])
                self.assertEqual(hashlib.sha256(data).hexdigest(),row['sha256'])
                self.assertEqual(hashlib.md5(data).hexdigest(),row['md5'])
                with Image.open(job.ROOT/row['file']) as im:
                    im.load()
                    self.assertEqual(im.size,(row['width'],row['height']))

    def test_actions_originals_remain_unchanged(self):
        source=json.loads((job.ROOT/'source-manifest.json').read_text())
        self.assertEqual(source['note_id'],'6a6195240000000001030e32')
        self.assertEqual(source['source_count'],5)
        for row in source['images']:
            self.assertEqual((row['width'],row['height']),(941,1672))
            self.assertEqual(hashlib.sha256((job.ROOT/row['file']).read_bytes()).hexdigest(),row['sha256'])
        self.assertEqual(len(list((job.ROOT/'01-下载原片').iterdir())),5)

    def test_unique_native_portrait_pairs(self):
        pairs=self.manifest['pairs']
        self.assertEqual(len({p['clean']['sha256'] for p in pairs}),10)
        self.assertEqual(len({p['simulated_ui']['sha256'] for p in pairs}),10)
        self.assertEqual(len(list((job.ROOT/'02-复刻无UI').glob('*.png'))),10)
        self.assertEqual(len(list((job.ROOT/'03-复刻模拟UI').glob('*.png'))),10)
        for p in pairs:
            self.assertNotEqual(p['clean']['sha256'],p['simulated_ui']['sha256'])
            for k in ('clean','simulated_ui'):
                self.assertEqual((p[k]['width'],p[k]['height']),(768,1376))

    def test_nonmutating_title_and_ui_rendering(self):
        image=Image.new('RGB',(768,1376),'#f6e1dd')
        before=image.tobytes()
        titled=job.title_image(image,0)
        ui=job.overlay(titled,0)
        self.assertEqual(image.tobytes(),before)
        self.assertIsNotNone(ImageChops.difference(image,titled).getbbox())
        self.assertIsNone(ImageChops.difference(titled.crop((0,440,768,1100)),ui.crop((0,440,768,1100))).getbbox())
        self.assertIsNotNone(ImageChops.difference(titled,ui).getbbox())


if __name__=='__main__':
    unittest.main()
