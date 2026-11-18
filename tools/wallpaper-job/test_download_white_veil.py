"""Offline tests for the public white-veil slide retrieval helper."""
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import HTTPError

from PIL import Image
import download_white_veil as job


def png_bytes(width=320, height=640):
    buf = io.BytesIO()
    Image.new('RGB', (width, height), 'white').save(buf, format='PNG')
    return buf.getvalue()


class WhiteVeilDownloadTests(unittest.TestCase):
    def test_known_slide_ids_and_public_url_extraction(self):
        self.assertEqual(len(set(job.TOKENS)), 9)
        token = job.TOKENS[0]
        url = f'https://sns-web-i10.rednotecdn.com/202611181503/abc/notes_pre_post/{token}!nd_dft_wlteh_webp_3'
        page = f'<img src="{url}"><img src="https://example.com/{job.TOKENS[1]}">'
        self.assertEqual(job.page_urls(page), {token: url})
        escaped = page.replace('/', '\\/')
        self.assertEqual(job.page_urls(escaped), {token: url})

    def test_image_is_decoded_and_too_small_rejected(self):
        with patch.object(job.urllib.request, 'urlopen', return_value=io.BytesIO(png_bytes())):
            data, width, height, fmt = job.fetch_image('https://example.com/image')
        self.assertEqual((width, height, fmt), (320, 640, 'png'))
        self.assertEqual(data, png_bytes())
        with patch.object(job.urllib.request, 'urlopen', return_value=io.BytesIO(png_bytes(20, 20))):
            with self.assertRaises(ValueError):
                job.fetch_image('https://example.com/thumbnail')

    def test_saves_exactly_nine_and_records_hashes(self):
        data = png_bytes()
        with tempfile.TemporaryDirectory() as root:
            with patch.object(job, 'OUT', Path(root)), \
                 patch.object(job.urllib.request, 'urlopen', return_value=io.BytesIO(b'<html/>')), \
                 patch.object(job, 'render_public_page', return_value=''), \
                 patch.object(job, 'fetch_image', return_value=(data, 320, 640, 'png')):
                job.main()
            record = json.loads((Path(root) / 'download-record.json').read_text())
            self.assertEqual(len(record['images']), 9)
            self.assertEqual(record['note_id'], job.NOTE_ID)
            self.assertEqual(len(list(Path(root).glob('*.png'))), 9)
            self.assertTrue(all(len(row['sha256']) == 64 for row in record['images']))
            self.assertNotIn('source_url', record['images'][0])

    def test_security_restriction_stops_before_image_requests(self):
        with tempfile.TemporaryDirectory() as root:
            with patch.object(job, 'OUT', Path(root)), \
                 patch.object(job.urllib.request, 'urlopen', return_value=io.BytesIO(b'<html/>')), \
                 patch.object(job, 'render_public_page', return_value='<title>安全限制</title>'), \
                 patch.object(job, 'fetch_image') as get_image:
                with self.assertRaisesRegex(RuntimeError, 'security restriction'):
                    job.main()
            get_image.assert_not_called()

    def test_rate_limit_stops_without_trying_another_host(self):
        error = HTTPError('https://example.com/image', 429, 'rate limited', None, None)
        with tempfile.TemporaryDirectory() as root:
            with patch.object(job, 'OUT', Path(root)), \
                 patch.object(job.urllib.request, 'urlopen', return_value=io.BytesIO(b'<html/>')), \
                 patch.object(job, 'render_public_page', return_value=''), \
                 patch.object(job, 'fetch_image', side_effect=error) as get_image:
                with self.assertRaisesRegex(RuntimeError, 'rate-limited'):
                    job.main()
            self.assertEqual(get_image.call_count, 1)
            self.assertFalse(list(Path(root).glob('*.png')))


if __name__ == '__main__':
    unittest.main()
