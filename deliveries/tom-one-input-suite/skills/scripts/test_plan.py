import unittest,tempfile
from pathlib import Path
from PIL import Image
from plan import build
class PlannerTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.r=Path(self.temp.name);self.ref=self.r/'avatar.png';Image.new('RGB',(1024,1024),'gray').save(self.ref)
 def tearDown(self):self.temp.cleanup()
 def profile(self,n):return dict(input_kind='avatar',style_locked='clean ink',visible_entities=[dict(id=str(k),locked=['visible silhouette']) for k in range(n)])
 def test_avatar_no_invented_partner(self):
  m=build(self.ref,self.profile(1),self.r/'run');self.assertEqual(len(m['jobs']),10);self.assertEqual(m['jobs'][5]['selected_entities'],m['jobs'][6]['selected_entities']);self.assertTrue(all(j['arguments']['images']==[str(self.ref.resolve())] for j in m['jobs']))
 def test_two_visible_entities_make_pair(self):
  m=build(self.ref,self.profile(2),self.r/'run');self.assertNotEqual(m['jobs'][5]['selected_entities'],m['jobs'][6]['selected_entities'])
 def test_refuse_overwrite(self):
  build(self.ref,self.profile(1),self.r/'run')
  with self.assertRaises(FileExistsError):build(self.ref,self.profile(1),self.r/'run')
 def test_require_visual_contract(self):
  with self.assertRaises(ValueError):build(self.ref,{},self.r/'run')
if __name__=='__main__':unittest.main()
