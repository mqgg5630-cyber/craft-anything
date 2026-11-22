import importlib.util
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


class FakeResponse:
    def __init__(self, body, url='https://www.xiaohongshu.com/explore/abc123'):
        self._body = body
        self._url = url

    def read(self, *args):
        return self._body

    def geturl(self):
        return self._url

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False
from PIL import Image

spec = importlib.util.spec_from_file_location('download_lululu', Path(__file__).with_name('download_lululu.py'))
job = importlib.util.module_from_spec(spec)
spec.loader.exec_module(job)


def png_bytes(size=(320, 640)):
    data = io.BytesIO()
    Image.new('RGB', size, 'blue').save(data, format='PNG')
    return data.getvalue()


def make_initial_state(images):
    note = {'noteId': 'abc123', 'title': 't', 'user': {'nickname': 'a'}, 'imageList': images}
    return {'note': {'noteDetailMap': {'abc123': {'note': note}}}}


class ParseTests(unittest.TestCase):
    def test_parses_image_list(self):
        html = '<script>window.__INITIAL_STATE__ = ' + __import__('json').dumps(
            make_initial_state([{'urlDefault': 'https://x/1'}])) + ';</script>'
        state = job.parse_initial_state(html)
        found = []
        job.iter_image_lists(state, found)
        self.assertEqual(len(found), 1)
        self.assertEqual(len(found[0]), 1)

    def test_finds_image_list_in_alternate_shape(self):
        alt = {'weird': {'nest': {'imageList': [{'urlDefault': 'https://x/9'}]}}}
        found = []
        job.iter_image_lists(alt, found)
        self.assertEqual(len(found), 1)

    def test_handles_undefined_tokens(self):
        html = '<script>window.__INITIAL_STATE__ = {"note": {"noteDetailMap": {"x": {"note": {"imageList": undefined}}}}};</script>'
        state = job.parse_initial_state(html)
        found = []
        job.iter_image_lists(state, found)
        self.assertEqual(found, [])


class CandidateTests(unittest.TestCase):
    def test_collects_and_dedupes(self):
        image = {'urlDefault': 'https://x/a',
                 'infoList': [{'url': 'https://x/b'}, {'url': 'https://x/a'}]}
        urls = job.candidate_urls(image)
        self.assertEqual(urls, ['https://x/a', 'https://x/b'])

    def test_skips_non_https(self):
        image = {'urlDefault': '/relative/path', 'infoList': [{'url': 'https://x/c'}]}
        self.assertEqual(job.candidate_urls(image), ['https://x/c'])


class DownloadTests(unittest.TestCase):
    def test_writes_manifest_and_files(self):
        images = [
            {'urlDefault': 'https://x/1', 'infoList': [{'url': 'https://x/1b'}]},
            {'urlDefault': 'https://x/2'},
        ]
        html = '<script>window.__INITIAL_STATE__ = ' + __import__('json').dumps(
            make_initial_state(images)) + ';</script>'

        def fake_fetch(url):
            data = png_bytes()
            return data, 320, 640, 'png'

        resp = FakeResponse(html.encode('utf-8'))

        with tempfile.TemporaryDirectory() as directory, \
                patch.object(job, 'ROOT', Path(directory) / 'deliveries' / 'lululu-sunset'), \
                patch.object(job.urllib.request, 'urlopen', return_value=resp), \
                patch.object(job, 'fetch', side_effect=fake_fetch):
            job.main()
            folder = job.ROOT / '01-下载原片'
            self.assertEqual(len(list(folder.glob('*.png'))), 2)
            manifest = __import__('json').loads((folder / '下载记录.json').read_text())
            self.assertEqual(manifest['image_count'], 2)
            self.assertEqual(manifest['images'][0]['file'], '01.png')

    def test_no_manifest_after_total_failure(self):
        with tempfile.TemporaryDirectory() as directory, \
                patch.object(job, 'ROOT', Path(directory) / 'deliveries' / 'lululu-sunset'), \
                patch.object(job.urllib.request, 'urlopen', side_effect=OSError('offline')), \
                patch.object(job, 'fetch', side_effect=OSError('offline')):
            with self.assertRaises(RuntimeError):
                job.main()
            self.assertFalse((job.ROOT / '01-下载原片' / '下载记录.json').exists())


if __name__ == '__main__':
    unittest.main()
