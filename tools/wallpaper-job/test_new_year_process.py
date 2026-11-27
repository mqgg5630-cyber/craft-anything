"""Offline tests for process supplements and the explicit future size policy."""
import csv,hashlib,json,unittest
from pathlib import Path
from PIL import Image
import complete_new_year_process as p

class ProcessTests(unittest.TestCase):
    def test_future_defaults(self):
        policy=json.loads(p.DEFAULTS.read_text())
        self.assertEqual(policy['wallpaper_size'],policy['size_basis']['all_original_dimensions'])
        self.assertTrue(all(isinstance(v,int) and v>0 for v in policy['wallpaper_size']))
        self.assertTrue(policy['separate_originals_and_results'])
        self.assertIn('no ZIP',policy['delivery_format'])
    def test_supplement_hashes(self):
        report=json.loads((p.EXTRAS/'full-process.json').read_text())
        self.assertTrue(report['originals_and_final_images_unchanged'])
        self.assertEqual(report['new_ai_generations_this_followup'],0)
        self.assertEqual(len(report['generated_supplements']),5)
        for row in report['generated_supplements']:
            data=(p.ROOT/row['file']).read_bytes()
            self.assertEqual(len(data),row['bytes'])
            self.assertEqual(hashlib.sha256(data).hexdigest(),row['sha256'])
            if row['file'].endswith('.jpg'):
                with Image.open(p.ROOT/row['file']) as im:im.load();self.assertEqual([im.width,im.height],[row['width'],row['height']])
    def test_copy_and_dimensions_csv(self):
        with (p.EXTRAS/'十张文案与尺寸表.csv').open(encoding='utf-8-sig') as f:rows=list(csv.DictReader(f))
        self.assertEqual(len(rows),10)
        self.assertEqual(len({r['右列文案'] for r in rows}|{r['左列文案'] for r in rows}),20)
        for row in rows:self.assertEqual((row['宽'],row['高']),('1080','2343'))
    def test_originals_and_results_unchanged(self):
        m=json.loads((p.ROOT/'output-manifest.json').read_text())
        for row in m['sources']+[r['result'] for r in m['outputs']]:p.verify(row)
        corrupt=dict(m['sources'][0],sha256='0'*64)
        with self.assertRaises(ValueError):p.verify(corrupt)

if __name__=='__main__':unittest.main()
