import subprocess,json,base64,concurrent.futures
from pathlib import Path
r=Path('deliveries/yier-bubu-comics/03-找回的漫画预览');r.mkdir(exist_ok=True)
def api(p):return json.loads(subprocess.check_output(['gh','api',p]))
b='arena/6467c7b2-leanrea';t=api('repos/hukeying85-ux/leanrea/git/trees/'+b.replace('/','%2F')+'?recursive=1')['tree']
sel=[x for x in t if x['path'].endswith('/preview.jpg') and x['path'].startswith('healing-comic/examples/')]
def get(x):
 d=api('repos/hukeying85-ux/leanrea/git/blobs/'+x['sha']);n=x['path'].split('/')[-2]+'.jpg';(r/n).write_bytes(base64.b64decode(d['content']));return {'local':n,'branch':b,'path':x['path'],'sha':x['sha']}
with concurrent.futures.ThreadPoolExecutor(max_workers=5) as e:a=list(e.map(get,sel))
(r/'索引.json').write_text(json.dumps(a,ensure_ascii=False,indent=2));print(len(a))
