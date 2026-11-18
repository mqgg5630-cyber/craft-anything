import hashlib
import json
from pathlib import Path
import unittest
from PIL import Image

ROOT=Path('deliveries/sakura-white-veil')

class SakuraDeliveryTests(unittest.TestCase):
    def test_all_nine_references_match_download(self):
        log=json.loads((ROOT/'01-下载原图/下载记录.json').read_text())
        self.assertEqual(log['note_id'],'6ad8a6ba00000000310375b1')
        self.assertEqual(len(log['images']),9)
        for entry in log['images']:
            self.assertEqual(hashlib.sha256((ROOT/'01-下载原图'/entry['file']).read_bytes()).hexdigest(),entry['sha256'])
    def test_plan_ten_distinct_with_valid_references(self):
        jobs=json.loads((ROOT/'05-Skills/prompts.json').read_text())['jobs']
        self.assertEqual(len(jobs),10)
        self.assertEqual(len({j['file'] for j in jobs}),10)
        for j in jobs:
            self.assertTrue((ROOT/'02-复刻无手机UI'/j['file']).is_file())
            for f in j['reference_files']:self.assertTrue((ROOT/'01-下载原图'/f).is_file())
    def test_pairing_dimensions_and_same_folder_previews(self):
        a=ROOT/'02-复刻无手机UI';b=ROOT/'03-复刻有手机UI'
        files=sorted(a.glob('*.png'))
        self.assertEqual(len(files),10)
        self.assertEqual([p.name for p in files],[p.name for p in sorted(b.glob('*.png'))])
        self.assertEqual(len({hashlib.sha256(p.read_bytes()).hexdigest() for p in files}),10)
        for p in files:
            with Image.open(p) as x,Image.open(b/p.name) as y:
                self.assertEqual(x.size,y.size)
            self.assertNotEqual(p.read_bytes(),(b/p.name).read_bytes())
        for p in [a/'总预览.jpg',b/'总预览.jpg']:
            with Image.open(p) as im:im.verify()
if __name__=='__main__':unittest.main()
