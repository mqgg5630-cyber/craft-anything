"""Actions-only public carousel acquisition. No credentials, no login bypass."""
import hashlib, io, json, os, re, tempfile, urllib.request
from pathlib import Path
from urllib.parse import urlparse, unquote
import urllib.parse
from PIL import Image

ROOT=Path('deliveries/autumn-swing-C5WkFiFa1r')
SHARE='https://xhslink.cn/o/C5WkFiFa1r'
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

def parse_note(html, final_url, title_hint='秋'):
    match = re.search(r'window\.__INITIAL_STATE__\s*=\s*(.*?)</script>', html, re.S)
    if not match:
        raise ValueError('Public note state unavailable; may require app/login')
    # Undefined is emitted as a JS literal by this public page. Do not eval JS.
    raw = match.group(1).strip().rstrip(';')
    raw = re.sub(r'(?<=[,:\[])\s*undefined\s*(?=[,}\]])', 'null', raw)
    state = json.loads(raw)
    details = state.get('note', {}).get('noteDetailMap', {})
    note_id_match = re.search(r'/(?:explore|discovery/item)/([a-f0-9]{24})', final_url)
    notes = [v.get('note', {}) for v in details.values() if isinstance(v, dict)]
    if note_id_match:
        notes = [n for n in notes if n.get('noteId', note_id_match.group(1)) == note_id_match.group(1)]
    if not notes:
        # The official international web page uses a different state layout.
        # Inspect data only, with bounded traversal; never execute page scripts.
        stack, visited = [(state, 0)], 0
        while stack:
            value, depth = stack.pop()
            visited += 1
            if visited > 100_000 or depth > 30:
                raise ValueError('Public note state exceeds traversal cap')
            if isinstance(value, dict):
                if (isinstance(value.get('imageList'), list)
                        and title_hint in str(value.get('title', ''))
                        and (not note_id_match or value.get('noteId', note_id_match.group(1)) == note_id_match.group(1))):
                    if value not in notes:
                        notes.append(value)
                stack.extend((v, depth + 1) for v in value.values() if isinstance(v, (dict, list)))
            elif isinstance(value, list):
                stack.extend((v, depth + 1) for v in value if isinstance(v, (dict, list)))
    if len(notes) != 1:
        keys = ','.join(str(k) for k in state)[:90]
        note_keys = ','.join(str(k) for k in state.get('note', {}))[:90]
        raise ValueError(f'Cannot identify note: count={len(notes)}; state={keys}; note={note_keys}')
    note = notes[0]
    if note_id_match:
        note.setdefault('noteId', note_id_match.group(1))
    if title_hint not in note.get('title', ''):
        raise ValueError('Resolved note title does not match requested note')
    images = note.get('imageList', [])
    if not 1 <= len(images) <= 20:
        raise ValueError('Unexpected carousel image count')
    return note


def main():
    if os.environ.get('GITHUB_ACTIONS')!='true':raise RuntimeError('Actions only')
    ROOT.mkdir(parents=True,exist_ok=True)
    html,final=request(SHARE,8*1024*1024)
    parsed=urlparse(final)
    note_ids=re.findall(r'/item/([0-9a-f]{24})',unquote(final))
    diagnostic=dict(share_url=SHARE,final_url=parsed.scheme+'://'+parsed.netloc+parsed.path,note_id=note_ids[0] if len(set(note_ids))==1 else None,page_bytes=len(html),run_id=os.environ.get('GITHUB_RUN_ID'),query_retained=False)
    (ROOT/'page-diagnostic.json').write_text(json.dumps(diagnostic,indent=2)+'\n')
    note=parse_note(html.decode('utf-8'),final)
    if note.get('noteId') != '6abdb5a9000000001802f193':raise ValueError('Wrong note identity')
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
