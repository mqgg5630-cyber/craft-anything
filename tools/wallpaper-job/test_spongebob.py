"""Offline checks for the spongebob post-processing step: crop maths and preview overlays."""
import importlib.util
from pathlib import Path
import tempfile
import unittest
from PIL import Image, ImageChops, ImageDraw

spec = importlib.util.spec_from_file_location(
    'wallpaper_package_spongebob', Path(__file__).with_name('package_spongebob.py'))
job = importlib.util.module_from_spec(spec)
spec.loader.exec_module(job)


class NormaliseTests(unittest.TestCase):
    def _run(self, image):
        with tempfile.TemporaryDirectory() as folder:
            raw = Path(folder) / 'raw.png'
            out = Path(folder) / 'out.png'
            image.save(raw)
            native = job.normalise(raw, out)
            with Image.open(out) as result:
                return native, result.convert('RGB').copy()

    def test_model_output_is_cropped_not_stretched(self):
        source = Image.new('RGB', (768, 1376), (255, 0, 0))
        ImageDraw.Draw(source).rectangle((0, 0, 767, 10), fill=(0, 0, 255))   # the empty sky band
        native, result = self._run(source)
        self.assertEqual(native, [768, 1376])
        self.assertEqual(result.size, job.TARGET)
        self.assertAlmostEqual(result.size[0] / result.size[1], 768 / 1365, places=3)
        self.assertIsNone(ImageChops.difference(result, Image.new('RGB', result.size, (255, 0, 0))).getbbox(),
                          'the crop must eat the top sky band only, never the artwork')

    def test_overwide_output_is_cropped_from_both_sides(self):
        source = Image.new('RGB', (1000, 1000), (255, 0, 0))
        ImageDraw.Draw(source).rectangle((0, 0, 19, 999), fill=(0, 0, 255))
        ImageDraw.Draw(source).rectangle((980, 0, 999, 999), fill=(0, 0, 255))
        _, result = self._run(source)
        self.assertEqual(result.size, job.TARGET)
        self.assertIsNone(ImageChops.difference(result, Image.new('RGB', result.size, (255, 0, 0))).getbbox())


class OverlayTests(unittest.TestCase):
    def setUp(self):
        self.source = Image.new('RGB', (1080, 1920), '#f6ece0')

    def test_lock_overlay_leaves_the_clean_wallpaper_alone(self):
        original = self.source.tobytes()
        result = job.lock_overlay(self.source)
        self.assertEqual(self.source.tobytes(), original)
        self.assertEqual(result.size, self.source.size)
        self.assertIsNotNone(ImageChops.difference(self.source, result).getbbox())

    def test_lock_overlay_is_deterministic(self):
        self.assertEqual(job.lock_overlay(self.source).tobytes(), job.lock_overlay(self.source).tobytes())
        self.assertEqual(job.home_overlay(self.source).tobytes(), job.home_overlay(self.source).tobytes())

    def test_text_colour_follows_the_top_band(self):
        pale = job.adaptive_ink(Image.new('RGB', (1080, 1920), '#ffffff'))
        dark = job.adaptive_ink(Image.new('RGB', (1080, 1920), '#101018'))
        self.assertLess(sum(pale[:3]), sum(dark[:3]))


if __name__ == '__main__':
    unittest.main()
