"""Offline checks for this note only. Requires Pillow, never downloads."""
import hashlib
import json
from pathlib import Path
import unittest
from PIL import Image
ROOT=Path(__file__).resolve().parent


class DeliveryTests(unittest.TestCase):
    def test_all_sources_and_outputs(self):
        for name,key,count in [('source-manifest.json','images',5),('output-manifest.json','files',10)]:
            manifest=json.loads((ROOT/name).read_text())
            self.assertEqual(len(manifest[key]),count)
            for item in manifest[key]:
                p=ROOT/item['file']; data=p.read_bytes()
                with Image.open(p) as im:
                    im.load()
                    self.assertEqual(im.size,(item['width'],item['height']))
                    self.assertEqual(im.format.lower(),item['format'])
                self.assertEqual(len(data),item['bytes'])
                for alg in ['md5','sha256']:
                    self.assertEqual(getattr(hashlib,alg)(data).hexdigest(),item[alg])
                for ref in item.get('references',[]): self.assertTrue((ROOT/ref).is_file())

    def test_exact_number_and_unique_outputs(self):
        for folder,ext,count in [('source','webp',5),('images','png',10)]:
            paths=sorted((ROOT/folder).glob('*'))
            self.assertEqual([p.name for p in paths],[f'{i:02d}.{ext}' for i in range(1,count+1)])
            self.assertEqual(len({hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}),count)

    def test_seed_identity_and_hashes(self):
        seed=json.loads((ROOT/'source-seed.json').read_text())
        source=json.loads((ROOT/'source-manifest.json').read_text())
        self.assertEqual(source['note_id'],'6a6195240000000001030e32')
        self.assertEqual(seed['share_url'],source['share_url'])
        for a,b in zip(seed['images'],source['images']):
            for key in ['source_url','md5','sha256','bytes']:
                self.assertEqual(a[key],b[key])

    def test_previews(self):
        for p in ROOT.glob('00-*.jpg'):
            with Image.open(p) as im:
                im.load()
                self.assertGreater(im.width,1000)
        self.assertEqual(len(list(ROOT.glob('00-*.jpg'))),3)


if __name__=='__main__': unittest.main()
