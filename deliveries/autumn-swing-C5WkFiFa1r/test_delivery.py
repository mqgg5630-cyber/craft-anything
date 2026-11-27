"""Offline acceptance tests for autumn-swing (C5WkFiFa1r) delivery."""
import hashlib
import json
from pathlib import Path
import sys
import unittest

from PIL import Image, ImageChops

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
import package_delivery as pkg  # noqa: E402


class AutumnSwingDeliveryTests(unittest.TestCase):
    def test_source_untouched_and_matches_manifest(self):
        manifest = json.loads((pkg.ROOT / 'source-manifest.json').read_text(encoding='utf-8'))
        self.assertEqual(manifest['reference_count_downloaded'], 1)
        self.assertEqual(len(manifest['images']), 1)
        entry = manifest['images'][0]
        actual = pkg.file_info(pkg.ROOT / entry['file'])
        for key in ('width', 'height', 'format', 'bytes', 'md5', 'sha256'):
            self.assertEqual(actual[key], entry[key])
        self.assertEqual((actual['width'], actual['height']), (852, 1848))

    def test_ten_unique_native_and_ten_unique_exact_finals(self):
        out_manifest = json.loads((pkg.ROOT / 'output-manifest.json').read_text(encoding='utf-8'))
        self.assertEqual(out_manifest['generated_count'], 10)
        self.assertEqual(len(out_manifest['files']), 10)
        final_paths = sorted((pkg.ROOT / 'images').glob('*.png'))
        native_paths = sorted((pkg.ROOT / 'artwork').glob('*.png'))
        self.assertEqual([p.name for p in final_paths], [f'{i:02d}.png' for i in range(1, 11)])
        self.assertEqual([p.name for p in native_paths], [f'{i:02d}.png' for i in range(1, 11)])
        self.assertEqual(len({hashlib.sha256(p.read_bytes()).hexdigest() for p in final_paths}), 10)
        self.assertEqual(len({hashlib.sha256(p.read_bytes()).hexdigest() for p in native_paths}), 10)
        for record in out_manifest['files']:
            actual = pkg.file_info(pkg.ROOT / record['file'])
            for key in ('width', 'height', 'format', 'bytes', 'md5', 'sha256'):
                self.assertEqual(actual[key], record[key])
            self.assertEqual((actual['width'], actual['height']), (852, 1848))
            self.assertEqual(record['references'], ['source/01.webp'])
            self.assertFalse(record['ui_overlay'])

    def test_pixel_identical_reproduction_from_native_artwork(self):
        for idx in range(1, 11):
            with Image.open(pkg.ROOT / f'artwork/{idx:02d}.png') as raw, Image.open(
                pkg.ROOT / f'images/{idx:02d}.png'
            ) as actual:
                expected = pkg.adapt_to_target(raw)
                diff = ImageChops.difference(expected, actual.convert('RGB'))
                self.assertIsNone(diff.getbbox(), f'Mismatch on {idx:02d}.png')

    def test_three_previews_decodable(self):
        names = ('00-总预览.jpg', '00-原片总预览.jpg', '00-10张成品总预览.jpg')
        for name in names:
            path = pkg.ROOT / name
            self.assertTrue(path.exists(), name)
            with Image.open(path) as im:
                im.load()
                self.assertGreater(im.width, 500)
                self.assertGreater(im.height, 600)

    def test_persisted_skill_defaults_match_reference_size(self):
        defaults_path = pkg.REPO / 'skills/xhs-link-recreate-10/references/delivery-defaults.json'
        defaults = json.loads(defaults_path.read_text(encoding='utf-8'))
        self.assertEqual(defaults['default_output_dimensions'], [852, 1848])
        self.assertTrue(defaults['delivery_layout']['separate_originals_and_results'])

    def test_cloud_verification_matches_local_bytes(self):
        cloud_path = pkg.ROOT / 'cloud-verification.json'
        self.assertTrue(cloud_path.exists())
        report = json.loads(cloud_path.read_text(encoding='utf-8'))
        self.assertTrue(report['all_match'])
        self.assertTrue(report['originals_and_results_separated'])
        self.assertEqual(report['fresh_listing_counts']['total_verified_files'], 17)
        self.assertEqual(len(report['files']), 17)
        for row in report['files']:
            data = (pkg.ROOT / row['local_file']).read_bytes()
            self.assertEqual(len(data), row['cloud_bytes'])
            self.assertEqual(hashlib.md5(data).hexdigest(), row['cloud_md5'])


if __name__ == '__main__':
    unittest.main()
