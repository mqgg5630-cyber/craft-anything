import subprocess,json,concurrent.futures,base64,hashlib
from pathlib import Path
R=Path('deliveries/comic-history-archive');R.mkdir(exist_ok=True)
def api(p):return json.loads(subprocess.check_output(['gh','api',p]))
scan=json.load(open('deliveries/yier-bubu-comics/00-检索记录/第二账号全仓库扫描.json'));repo=next(x for x in scan if x['repo']=='hukeying85-ux/leanrea')
def tree(b):return b,api('repos/hukeying85-ux/leanrea/git/trees/'+b['sha']+'?recursive=1')
items={}
with concurrent.futures.ThreadPoolExecutor(max_workers=6) as ex:
 for b,t in ex.map(tree,repo['branches']):
  for x in t.get('tree',[]):
   p=x['path']
   if x['type']=='blob' and p.startswith('healing-comic/') and '/pages' in p and p.endswith('.png'):
    key=x['sha'];v=items.setdefault(key,{'sha':key,'bytes':x.get('size'), 'origins':[]});v['origins'].append({'repo':repo['repo'],'branch':b['branch'],'path':p})
print('UNIQUE PAGES',len(items),'bytes',sum(v['bytes'] for v in items.values()),flush=True)
def get(v):
 origin=v['origins'][0];p=origin['path'];group=p.rsplit('/',2)[-2];dest=R/'单张成品'/group/Path(p).name
 if dest.exists() and hashlib.sha1(b'blob '+str(dest.stat().st_size).encode()+b'\0'+dest.read_bytes()).hexdigest()!=v['sha']:dest=dest.with_name(dest.stem+'-'+v['sha'][:8]+dest.suffix)
 dest.parent.mkdir(parents=True,exist_ok=True)
 if not dest.exists():dest.write_bytes(base64.b64decode(api('repos/hukeying85-ux/leanrea/git/blobs/'+v['sha'])['content']))
 data=dest.read_bytes();assert hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()==v['sha']
 v['local']=str(dest);v['md5']=hashlib.md5(data).hexdigest();return v
with concurrent.futures.ThreadPoolExecutor(max_workers=6) as ex:out=list(ex.map(get,items.values()))
(R/'单张文件清单.json').write_text(json.dumps(out,ensure_ascii=False,indent=2));print('downloaded verified',len(out),flush=True)
