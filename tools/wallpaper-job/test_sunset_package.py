"""Offline delivery acceptance tests for the sunset source/result separation."""
import hashlib
import json
import unittest
from PIL import Image, ImageChops
import package_sunset as job


class SunsetDeliveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = json.loads((job.ROOT/'output-manifest.json').read_text())

    def test_counts_and_reference_mapping(self):
        m = self.manifest
        self.assertEqual((m['source_count'], m['clean_count'], m['simulated_ui_count']), (5, 10, 10))
        self.assertEqual(len(m['pairs']), 10)
        for i, pair in enumerate(m['pairs']):
            self.assertEqual(pair['references'], job.REFERENCES[i])
            self.assertEqual(pair['kind'], 'reference_redraw' if i < 5 else 'new_scene_same_series')

    def test_all_image_hashes_dimensions_and_decodes(self):
        m = self.manifest
        rows = m['sources'] + m['previews']
        rows += [p[k] for p in m['pairs'] for k in ['clean', 'simulated_ui']]
        for row in rows:
            path = job.ROOT/row['file']
            with self.subTest(file=row['file']):
                data = path.read_bytes()
                self.assertEqual(len(data), row['bytes'])
                self.assertEqual(hashlib.sha256(data).hexdigest(), row['sha256'])
                self.assertEqual(hashlib.md5(data).hexdigest(), row['md5'])
                with Image.open(path) as im:
                    im.load()
                    self.assertEqual(im.size, (row['width'], row['height']))

    def test_original_bytes_preserved_from_actions(self):
        source = json.loads((job.ROOT/'source-manifest.json').read_text())
        self.assertEqual(source['source_count'], 5)
        for row in source['images']:
            self.assertEqual(job.sha(job.ROOT/row['file']), row['sha256'])
        self.assertEqual(len(list((job.ROOT/'01-下载原片').iterdir())), 5)

    def test_ten_unique_clean_and_ui_images(self):
        pairs = self.manifest['pairs']
        self.assertEqual(len({p['clean']['sha256'] for p in pairs}), 10)
        self.assertEqual(len({p['simulated_ui']['sha256'] for p in pairs}), 10)
        for pair in pairs:
            self.assertNotEqual(pair['clean']['sha256'], pair['simulated_ui']['sha256'])
            self.assertEqual((pair['clean']['width'], pair['clean']['height']), (768, 1376))
            self.assertEqual((pair['simulated_ui']['width'], pair['simulated_ui']['height']), (768, 1376))

    def test_overlay_is_nonmutating_and_leaves_middle_untouched(self):
        image = Image.new('RGB', (768, 1376), '#deac76')
        before = image.tobytes()
        result = job.overlay(image)
        self.assertEqual(image.tobytes(), before)
        self.assertIsNone(ImageChops.difference(image.crop((0, 500, 768, 1050)), result.crop((0, 500, 768, 1050))).getbbox())
        self.assertIsNotNone(ImageChops.difference(image, result).getbbox())


if __name__ == '__main__':
    unittest.main()
