import importlib.util
from pathlib import Path
import tempfile
import unittest
import zipfile

spec=importlib.util.spec_from_file_location('extract_verified',Path(__file__).with_name('extract_verified.py'))
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

class ExtractTests(unittest.TestCase):
    def archive(self, folder, names):
        p=Path(folder)/'test.zip'
        with zipfile.ZipFile(p,'w') as z:
            for n in names:z.writestr(n,b'example bytes')
        return p
    def test_extract_crc_and_exact_bytes(self):
        with tempfile.TemporaryDirectory() as t:
            p=self.archive(t,['01-原片/a.jpg']);r=m.extract(p,Path(t)/'out')
            self.assertTrue(r['crc_verified']);self.assertEqual(r['file_count'],1)
            self.assertEqual((Path(t)/'out/01-原片/a.jpg').read_bytes(),b'example bytes')
    def test_reject_traversal(self):
        with tempfile.TemporaryDirectory() as t:
            p=self.archive(t,['../escape'])
            with self.assertRaises(ValueError):m.extract(p,Path(t)/'out')
            self.assertFalse((Path(t)/'out').exists())
    def test_wrong_md5(self):
        with tempfile.TemporaryDirectory() as t:
            p=self.archive(t,['a'])
            with self.assertRaises(ValueError):m.extract(p,Path(t)/'out','0'*32)
    def test_repair_unflagged_utf8(self):
        info=zipfile.ZipInfo('原片'.encode('utf8').decode('cp437')+'/01.jpg')
        self.assertEqual(str(m.decoded(info)),'原片/01.jpg')
    def test_refuse_overwrite_different(self):
        with tempfile.TemporaryDirectory() as t:
            p=self.archive(t,['a']);out=Path(t)/'out';out.mkdir();(out/'a').write_bytes(b'other')
            with self.assertRaises(ValueError):m.extract(p,out)
if __name__=='__main__':unittest.main()
