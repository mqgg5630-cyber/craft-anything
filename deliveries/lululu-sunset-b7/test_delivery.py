"""Offline delivery regression verification. Run with Python + Pillow."""
import hashlib
import json
from pathlib import Path
import unittest
from PIL import Image

ROOT = Path(__file__).resolve().parent


class DeliveryTests(unittest.TestCase):
    def test_sources_and_outputs(self):
        count = 0
        for filename, key, expected in [('source-manifest.json', 'images', 5), ('output-manifest.json', 'files', 20)]:
            manifest = json.loads((ROOT / filename).read_text())
            self.assertEqual(len(manifest[key]), expected)
            for item in manifest[key]:
                path = ROOT / item['file']; data = path.read_bytes()
                with Image.open(path) as im:
                    im.load()
                    self.assertEqual(im.size, (item['width'], item['height']))
                self.assertEqual(len(data), item['bytes'])
                for algorithm in ('md5', 'sha256'):
                    self.assertEqual(getattr(hashlib, algorithm)(data).hexdigest(), item[algorithm])
                count += 1
        self.assertEqual(count, 25)

    def test_exact_counts_and_unique_clean_outputs(self):
        for folder, count in [('source', 5), ('images', 10), ('ui', 10)]:
            paths = sorted((ROOT / folder).glob('*.png'))
            self.assertEqual([p.name for p in paths], [f'{i:02d}.png' for i in range(1, count + 1)])
            self.assertEqual(len({hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}), count)

    def test_previews(self):
        for name in ('00-总预览.jpg', '00-原片总预览.jpg', '00-无UI总预览.jpg', '00-有UI总预览.jpg'):
            with Image.open(ROOT/name) as im:
                im.load()
                self.assertGreater(im.width, 1000)

    def test_historical_seed_matches_actual_sources(self):
        seed = json.loads((ROOT/'source-seed.json').read_text())
        source = json.loads((ROOT/'source-manifest.json').read_text())
        for expected, actual in zip(seed['images'], source['images']):
            self.assertTrue(actual['historical_hash_match'])
            for key in ('md5','sha256','bytes','width','height','format','source_url'):
                self.assertEqual(expected[key], actual[key])


if __name__ == '__main__':
    unittest.main()
