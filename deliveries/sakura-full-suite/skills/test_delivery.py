from pathlib import Path
import unittest,json,re,base64,hashlib,subprocess,io
from PIL import Image
import imageio_ffmpeg
R=Path(__file__).resolve().parents[1]
class Delivery(unittest.TestCase):
 def test_assets(self):
  data=json.loads((R/'清单.json').read_text());self.assertEqual(len(data),10)
  for i,t in enumerate(data,1):
   self.assertEqual(len(t['files']),33);f=R/'sets'/f"{i:02}-{t['theme']}"
   for x in t['files']:
    p=f/x['file'];self.assertEqual(hashlib.md5(p.read_bytes()).hexdigest(),x['md5'])
    if p.suffix in ['.png','.jpg','.gif']:
     with Image.open(p) as im:im.load();self.assertEqual(list(im.size),x['size'])
 def test_albums(self):
  albums=sorted((R/'albums').glob('*.html'));self.assertEqual(len(albums),10)
  for p in albums:
   text=p.read_text();payload=json.loads(text.split('const assets=',1)[1].split(';function blob',1)[0]);self.assertEqual(len(payload),34)
   i=int(p.name[:2]);theme=json.loads((R/'清单.json').read_text())[i-1]['theme'];folder=R/'sets'/f'{i:02}-{theme}'
   for x in payload:self.assertEqual(base64.b64decode(x['data']),(folder/x['name']).read_bytes())
   script=text.split('<script>')[1].split('</script>')[0];tmp=R/'skills'/'.syntax.js';tmp.write_text(script);result=subprocess.run(['node','--check',str(tmp)],capture_output=True);tmp.unlink();self.assertEqual(result.returncode,0,result.stderr)
 def test_video_decode(self):
  for p in sorted((R/'sets').glob('*/*.mp4')):
   r=subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(),'-v','error','-i',str(p),'-f','null','-'],capture_output=True);self.assertEqual(r.returncode,0,r.stderr)
if __name__=='__main__':unittest.main()
