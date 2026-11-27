"""End-to-end verification tests for Round 2 (canonical Lazy Goat + 10 distinct scenes, 852x1848)."""
import hashlib
import json
import unittest
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]


class TestAutumnSwingVariedR2Delivery(unittest.TestCase):
    def test_round1_remains_untouched(self) -> None:
        r1 = REPO / 'deliveries/autumn-swing-C5WkFiFa1r'
        self.assertTrue((r1 / '00-总预览.jpg').is_file())
        self.assertTrue((r1 / 'cloud-verification.json').is_file())
        r1_cloud = json.loads((r1 / 'cloud-verification.json').read_text(encoding='utf-8'))
        self.assertEqual(r1_cloud['status'], 'verified_complete_requested_deliverables')
        self.assertEqual(len(r1_cloud['files']), 17)

    def test_persisted_default_dimensions_852x1848(self) -> None:
        defaults_path = REPO / 'skills/xhs-link-recreate-10/references/delivery-defaults.json'
        defaults = json.loads(defaults_path.read_text(encoding='utf-8'))
        self.assertEqual(defaults['default_output_dimensions'], [852, 1848])
        self.assertTrue(defaults['delivery_layout']['separate_originals_and_results'])

    def test_source_and_results_separated_locally(self) -> None:
        src_files = sorted(p.name for p in (ROOT / 'source').iterdir() if p.is_file())
        out_files = sorted(p.name for p in (ROOT / 'images').iterdir() if p.is_file())
        self.assertEqual(src_files, ['01.webp'])
        self.assertEqual(out_files, [f'{i:02d}.png' for i in range(1, 11)])

    def test_ten_unique_852x1848_wallpapers_with_distinct_scenes(self) -> None:
        out_manifest = json.loads((ROOT / 'output-manifest.json').read_text(encoding='utf-8'))
        self.assertEqual(out_manifest['round'], 2)
        self.assertEqual(out_manifest['generated_count'], 10)
        self.assertEqual(out_manifest['reference_dimensions'], [852, 1848])
        self.assertFalse(out_manifest['ui_overlay'])
        hashes = set()
        titles = set()
        scenes = set()
        for idx, rec in enumerate(out_manifest['files'], start=1):
            p = ROOT / rec['file']
            data = p.read_bytes()
            with Image.open(p) as im:
                im.verify()
            with Image.open(p) as im:
                im.load()
                self.assertEqual(im.size, (852, 1848))
                self.assertEqual(im.format, 'PNG')
            digest = hashlib.sha256(data).hexdigest()
            self.assertEqual(digest, rec['sha256'])
            self.assertEqual(rec['index'], idx)
            hashes.add(digest)
            titles.add(rec['title'])
            scenes.add(rec['scene_description'])
        self.assertEqual(len(hashes), 10)
        self.assertEqual(len(titles), 10)
        self.assertEqual(len(scenes), 10)

    def test_all_three_preview_boards_exist_and_decode(self) -> None:
        for name in ('00-总预览.jpg', '00-原片总预览.jpg', '00-10张成品总预览.jpg'):
            p = ROOT / name
            self.assertTrue(p.is_file(), name)
            with Image.open(p) as im:
                im.verify()
            with Image.open(p) as im:
                im.load()
                self.assertEqual(im.format, 'JPEG')
                self.assertGreater(im.width, 500)
                self.assertGreater(im.height, 600)

    def test_cloud_verification_accurate_and_separated(self) -> None:
        cloud = json.loads((ROOT / 'cloud-verification.json').read_text(encoding='utf-8'))
        self.assertIn(cloud['status'], ('passed', 'partial_rate_limited'))
        src_folder = cloud['separated_subfolders']['original_sources']['id']
        res_folder = cloud['separated_subfolders']['recreated_results']['id']
        self.assertNotEqual(src_folder, res_folder)
        self.assertEqual(
            cloud['verified_file_count'] + cloud['pending_file_count'],
            cloud['total_expected_file_count'],
        )
        self.assertEqual(cloud['total_expected_file_count'], 17)
        for item in cloud['files']:
            local_bytes = (ROOT / item['local_file']).read_bytes()
            self.assertEqual(len(local_bytes), item['bytes'])
            self.assertEqual(hashlib.md5(local_bytes).hexdigest(), item['md5'])


if __name__ == '__main__':
    unittest.main()
