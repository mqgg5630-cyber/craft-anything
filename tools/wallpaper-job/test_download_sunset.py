"""Offline regression tests: these never request external image or note URLs."""
import io
import json
import unittest
from unittest.mock import patch
from PIL import Image
import download_sunset as job


class SunsetDownloadTests(unittest.TestCase):
    def test_host_restrictions(self):
        for url in ['http://xhslink.cn/a', 'https://xhslink.cn.evil.test/a',
                    'https://localhost/a', 'https://user@xhslink.cn/a',
                    'https://xhslink.cn:444/a']:
            with self.subTest(url=url), self.assertRaises(ValueError):
                job.check_url(url)
        self.assertEqual(job.check_url(job.SHARE_URL), job.SHARE_URL)

    def test_note_selection(self):
        note = {'noteId': 'a' * 24, 'title': '和你一起奔夕阳', 'imageList': [{}]}
        state = {'note': {'noteDetailMap': {'x': {'note': note}}}}
        html = '<script>window.__INITIAL_STATE__=' + json.dumps(state) + '</script>'
        self.assertEqual(job.parse_note(html, 'https://www.xiaohongshu.com/explore/' + 'a'*24), note)
        with self.assertRaises(ValueError):
            job.parse_note(html, 'https://www.xiaohongshu.com/explore/' + 'b'*24)
        with self.assertRaises(ValueError):
            job.parse_note('<html>login required</html>', job.SHARE_URL)

    def test_candidate_dedup_and_https(self):
        url = 'https://sns-webpic-qc.xhscdn.com/test'
        self.assertEqual(job.candidates({'urlDefault': url, 'infoList': [{'url': url}]}), [url])
        self.assertEqual(job.candidates({'urlDefault': url.replace('https:', 'http:')}), [url])

    def test_image_validation_and_truncation(self):
        buf = io.BytesIO()
        Image.new('RGB', (400, 800), 'orange').save(buf, format='PNG')
        self.assertEqual(job.validate(buf.getvalue()), (400, 800, 'png'))
        for data in [b'<html>Error</html>', buf.getvalue()[:100]]:
            with self.assertRaises((ValueError, OSError)):
                job.validate(data)
        buf = io.BytesIO()
        Image.new('RGB', (10, 10)).save(buf, format='PNG')
        with self.assertRaises(ValueError):
            job.validate(buf.getvalue())

    def test_download_not_allowed_locally(self):
        with patch.dict('os.environ', {}, clear=True), patch.object(job, 'read_url') as read:
            with self.assertRaises(RuntimeError):
                job.main()
            read.assert_not_called()


if __name__ == '__main__':
    unittest.main()
