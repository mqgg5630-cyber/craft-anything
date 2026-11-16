import importlib.util
from pathlib import Path
import unittest
from PIL import Image, ImageChops

spec = importlib.util.spec_from_file_location('wallpaper_package', Path(__file__).with_name('package.py'))
job = importlib.util.module_from_spec(spec)
spec.loader.exec_module(job)


class OverlayTests(unittest.TestCase):
    def test_overlay_preserves_source_and_size(self):
        source = Image.new('RGB', (688, 1536), '#fffaf0')
        original_bytes = source.tobytes()
        result = job.overlay(source)
        self.assertEqual(source.tobytes(), original_bytes)
        self.assertEqual(result.size, source.size)
        self.assertIsNotNone(ImageChops.difference(source, result).getbbox())

    def test_subject_region_remains_unchanged(self):
        source = Image.new('RGB', (688, 1536), '#fffaf0')
        result = job.overlay(source)
        self.assertIsNone(ImageChops.difference(source.crop((0, 500, 688, 1350)),
                                                result.crop((0, 500, 688, 1350))).getbbox())

    def test_overlay_is_deterministic(self):
        source = Image.new('RGB', (688, 1536), '#fffaf0')
        self.assertEqual(job.overlay(source).tobytes(), job.overlay(source).tobytes())


if __name__ == '__main__':
    unittest.main()
