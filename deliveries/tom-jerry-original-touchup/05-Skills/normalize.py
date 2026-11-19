from pathlib import Path
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
for p in sorted((ROOT/'04-生成原尺寸').glob('*.png')):
 im=Image.open(p).convert('RGB');w,h=im.size;e=round(w*20/9)-h
 if e<1: raise ValueError('Unexpected source aspect ratio')
 out=Image.new('RGB',(w,h+e));out.paste(im.crop((0,0,w,32)).resize((w,e)),(0,0));out.paste(im,(0,e));out.save(ROOT/'02-复刻无手机UI'/p.name)
