from pathlib import Path
import json,hashlib,subprocess
from PIL import Image
import imageio_ffmpeg
R=Path(__file__).resolve().parents[1];m=json.loads((R/'素材清单.json').read_text())
assert m['generation_calls']==10 and len(m['native_dimensions'])==10
assert len(m['files'])==33
for rec in m['files']:
 p=R/'images'/rec['file'];assert p.stat().st_size==rec['bytes'];assert hashlib.md5(p.read_bytes()).hexdigest()==rec['md5'],p
 if p.suffix=='.mp4':subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(),'-v','error','-i',str(p),'-f','null','-'],check=True)
 else:
  with Image.open(p) as im:assert list(im.size)==rec['size'];im.load()
for k in ['06-avatar-sakura','07-avatar-syaoran']:
 assert m['native_dimensions'][k]==[1024,1024]
 clean=[v for v in m['files'] if v['source']==k and v['process']=='native_full_canvas_no_crop'];assert len(clean)==1
 with Image.open(R/'masters'/f'{k}.png') as a,Image.open(R/'images'/clean[0]['file']) as b:assert a.convert('RGB').tobytes()==b.convert('RGB').tobytes()
assert not list(R.rglob('*.html'))
print('PASS: 33 independent assets hash/size/decode; 10 purpose sources; two 1024 avatars pixel-identical to native; no HTML')
