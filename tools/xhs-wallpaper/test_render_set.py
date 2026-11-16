import tempfile
import unittest
from pathlib import Path

from PIL import Image

from render_set import build_set


class RenderSetTests(unittest.TestCase):
    def test_builds_separate_ten_image_outputs(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "art"
            source.mkdir()
            for number in range(1, 11):
                Image.new("RGB", (360, 800), (20 * number, 40, 160)).save(source / f"{number:02d}.png")
            result = build_set(source, root / "result", "Monday, November 16", "9:41")
            self.assertEqual(result["count"], 10)
            self.assertEqual(len(list((root / "result/无手机UI").glob("*.png"))), 10)
            self.assertEqual(len(list((root / "result/手机UI预览").glob("*.jpg"))), 10)
            with Image.open(root / "result/无手机UI/01.png") as image:
                self.assertEqual(image.size, (1440, 3200))

    def test_rejects_wrong_art_count_before_creating_outputs(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "art"
            source.mkdir()
            Image.new("RGB", (10, 10)).save(source / "01.png")
            with self.assertRaisesRegex(ValueError, "exactly 10"):
                build_set(source, root / "result", "Monday, November 16", "9:41")


if __name__ == "__main__":
    unittest.main()
