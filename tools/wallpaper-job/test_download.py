import importlib.util
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from PIL import Image

spec = importlib.util.spec_from_file_location('download', Path(__file__).with_name('download.py'))
job = importlib.util.module_from_spec(spec)
spec.loader.exec_module(job)


class DownloadTests(unittest.TestCase):
    def png(self, size=(320, 640)):
        data = io.BytesIO()
        Image.new('RGB', size, 'blue').save(data, format='PNG')
        return data.getvalue()

    def test_validates_image_and_preserves_bytes(self):
        data = self.png()
        with patch.object(job.urllib.request, 'urlopen', return_value=io.BytesIO(data)):
            self.assertEqual(job.fetch('https://example.invalid/image'), (data, 320, 640, 'png'))

    def test_rejects_non_image(self):
        with patch.object(job.urllib.request, 'urlopen', return_value=io.BytesIO(b'<html>Login</html>')):
            with self.assertRaises(OSError):
                job.fetch('https://example.invalid/image')

    def test_rejects_small_image(self):
        with patch.object(job.urllib.request, 'urlopen', return_value=io.BytesIO(self.png((20, 20)))):
            with self.assertRaises(ValueError):
                job.fetch('https://example.invalid/image')

    def test_rejects_oversize_response(self):
        with patch.object(job, 'LIMIT', 20), patch.object(
                job.urllib.request, 'urlopen', return_value=io.BytesIO(b'x' * 21)):
            with self.assertRaises(ValueError):
                job.fetch('https://example.invalid/image')

    def test_no_manifest_claiming_success_after_download_failure(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(job, 'ROOT', Path(directory)), patch.object(
                job, 'fetch', side_effect=OSError('offline')):
            with self.assertRaises(RuntimeError):
                job.main()
            self.assertFalse((Path(directory) / '01-下载原图' / '下载记录.json').exists())


if __name__ == '__main__':
    unittest.main()
