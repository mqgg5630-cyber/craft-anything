"""Actions-only public carousel acquisition. No credentials, no login bypass."""
import hashlib, io, json, os, re, tempfile, urllib.request
from pathlib import Path
from urllib.parse import urlparse, unquote
from PIL import Image

ROOT=Path('deliveries/newyear-blessings-3kQq76Fee2O')
SHARE='https://xhslink.cn/o/3kQq76Fee2O'
LIMIT=12*1024*1024

def public_url(url):
    p=urlparse(url)
    return p.scheme=='https' and not p.username and not p.password and any(p.hostname==h or (p.hostname or '').endswith('.'+h) for h in ['xhscdn.com','rednotecdn.com','xiaohongshu.com'])

def decode(data):
    if len(data)>LIMIT: raise ValueError('Image exceeds size cap')
    with Image.open(io.BytesIO(data)) as im: im.verify()
    with Image.open(io.BytesIO(data)) as im:
        im.load();w,h=im.size;fmt=im.format.lower()
    if min(w,h)<300 or fmt not in ['png','jpeg','webp']:raise ValueError('Unexpected image dimensions or format')
    return dict(width=w,height=h,format=fmt,bytes=len(data),md5=hashlib.md5(data).hexdigest(),sha256=hashlib.sha256(data).hexdigest())

def request(url,limit):
    req=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0','Referer':'https://www.xiaohongshu.com/'})
    with urllib.request.urlopen(req,timeout=40) as r:
        data=r.read(limit+1);final=r.url
    if len(data)>limit:raise ValueError('Response exceeds cap')
    return data,final

def extract(html):
    match=re.search(r'window\.__INITIAL_STATE__\s*=\s*(.*?)</script>',html,re.S)
    if not match:raise ValueError('No public initial state; do not bypass login')
    state=json.loads(re.sub(r'\bundefined\b','null',match.group(1).strip().rstrip(';')))
    notes=[v.get('note',{}) for v in state.get('note',{}).get('noteDetailMap',{}).values()]
    notes=[v for v in notes if v.get('imageList')]
    if len(notes)!=1:raise ValueError('No unambiguous public carousel')
    return notes[0]

def main():
    if os.environ.get('GITHUB_ACTIONS')!='true':raise RuntimeError('Actions only')
    ROOT.mkdir(parents=True,exist_ok=True)
    html,final=request(SHARE,8*1024*1024)
    parsed=urlparse(final)
    note_ids=re.findall(r'/item/([0-9a-f]{24})',unquote(final))
    diagnostic=dict(share_url=SHARE,final_url=parsed.scheme+'://'+parsed.netloc+parsed.path,note_id=note_ids[0] if len(set(note_ids))==1 else None,page_bytes=len(html),run_id=os.environ.get('GITHUB_RUN_ID'),query_retained=False)
    (ROOT/'page-diagnostic.json').write_text(json.dumps(diagnostic,indent=2)+'\n')
    note=extract(html.decode('utf-8'))
    images=note['imageList']
    if not 1<=len(images)<=20:raise ValueError('Unexpected carousel size')
    records=[];total=0;seen=set()
    with tempfile.TemporaryDirectory() as folder:
        stage=Path(folder)
        for item in images:
            urls=list(dict.fromkeys([item.get('urlDefault','')]+[i.get('url','') for i in item.get('infoList',[])]))
            candidates=[]
            for url in urls:
                if not public_url(url):continue
                try:
                    data,redirect=request(url,LIMIT)
                    if not public_url(redirect):raise ValueError('Unexpected image redirect')
                    a=decode(data);candidates.append((a['width']*a['height'],len(data),data,a,url))
                except (OSError,ValueError):print('One public image candidate unavailable',flush=True)
            if not candidates:raise ValueError('No decodable public candidate')
            _,_,data,a,url=max(candidates,key=lambda c:c[:2])
            if a['sha256'] in seen:continue
            seen.add(a['sha256']);total+=len(data)
            if total>75*1024*1024:raise ValueError('Total exceeds cap')
            name=f'{len(records)+1:02d}.{a["format"]}'
            (stage/name).write_bytes(data);records.append(dict(a,file='source/'+name,source_url=url))
        dest=ROOT/'source'
        for p in stage.iterdir():
            if (dest/p.name).exists() and (dest/p.name).read_bytes()!=p.read_bytes():raise ValueError('Refuse overwrite')
        dest.mkdir(exist_ok=True)
        for p in stage.iterdir():(dest/p.name).write_bytes(p.read_bytes())
    manifest=dict(share_url=SHARE,note_id=note.get('noteId'),title=note.get('title'),description=note.get('desc'),author=note.get('user',{}).get('nickname'),final_url=diagnostic['final_url'],run_id=os.environ.get('GITHUB_RUN_ID'),source_quality='Public CDN display files, not confirmed author masters',status='downloaded_pending_visual_review',images=records)
    (ROOT/'source-manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    (ROOT/'download-status.json').write_text(json.dumps(dict(status='downloaded_pending_visual_review',count=len(records),all_decoded=True),indent=2)+'\n')
    print('Verified',len(records),'originals')

if __name__=='__main__':
    try:main()
    except Exception as e:
        if os.environ.get('GITHUB_ACTIONS')=='true':
            ROOT.mkdir(parents=True,exist_ok=True)
            (ROOT/'download-status.json').write_text(json.dumps(dict(status='blocked_source_download',error_type=type(e).__name__,error=str(e),run_id=os.environ.get('GITHUB_RUN_ID')),indent=2)+'\n')
        raise
