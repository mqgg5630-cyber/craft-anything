import json,subprocess,concurrent.futures,re
from pathlib import Path
repos=json.load(open('/tmp/repos.json')); print('repos',len(repos),flush=True)
pat=re.compile(r'布布|一二|治愈|漫画|comic|bubu|dudu|healing|bear',re.I)
def api(p):
 r=subprocess.run(['gh','api',p],capture_output=True,text=True)
 if r.returncode:return {'error':r.stderr[:400]}
 return json.loads(r.stdout)
def scan(repo):
 name=repo['nameWithOwner']; branches=api(f'repos/{name}/branches?per_page=100');out=[]
 if not isinstance(branches,list):return {'repo':name,'error':branches}
 for b in branches:
  tree=api(f"repos/{name}/git/trees/{b['commit']['sha']}?recursive=1")
  hits=[x['path'] for x in tree.get('tree',[]) if pat.search(x['path'])]
  out.append({'branch':b['name'],'sha':b['commit']['sha'],'truncated':tree.get('truncated'),'error':tree.get('error'),'hits':hits})
 if any(x['hits'] for x in out): print(name,[(x['branch'],len(x['hits'])) for x in out if x['hits']],flush=True)
 return {'repo':name,'branches':out,'branch_page_full':len(branches)==100}
with concurrent.futures.ThreadPoolExecutor(max_workers=10) as ex:
 result=list(ex.map(scan,repos))
Path('deliveries/yier-bubu-comics/00-检索记录/仓库扫描.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
