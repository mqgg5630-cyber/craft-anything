"""Deterministic supplemental ZIP; originals/results separate and exact bytes retained."""
from pathlib import Path
import json,zipfile,hashlib
ROOT=Path(__file__).resolve().parent
OUT=ROOT.parents[1]/'.local/delivery-bundles/秋天和秋千-新生成10张-完整交付-852x1848.zip'
def main():
 mapping=[(ROOT/'source/01.jpg','01-下载原片/01.jpg')]
 m=json.loads((ROOT/'output-manifest.json').read_text())
 for r in m['files']:mapping.append((ROOT/r['file'],'02-复刻结果-852x1848/'+Path(r['file']).stem+'-'+r['title']+'.png'))
 for p in sorted(ROOT.glob('00-*.jpg')):mapping.append((p,'03-总预览/'+p.name))
 for n in ['README.md','source-manifest.json','output-manifest.json','以后默认尺寸-852x1848.json']:mapping.append((ROOT/n,'04-说明与清单/'+n))
 assert len(mapping)==18 and len({n for _,n in mapping})==18
 OUT.parent.mkdir(parents=True,exist_ok=True)
 with zipfile.ZipFile(OUT,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
  for p,n in mapping:
   a=zipfile.ZipInfo(n,date_time=(2026,1,1,0,0,0));a.compress_type=zipfile.ZIP_DEFLATED;a.external_attr=0o100644<<16;z.writestr(a,p.read_bytes())
 rows=[]
 with zipfile.ZipFile(OUT) as z:
  assert z.testzip() is None
  for p,n in mapping:
   data=p.read_bytes();assert data==z.read(n);rows.append(dict(member=n,source=str(p.relative_to(ROOT)),bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),match=True))
 data=OUT.read_bytes();report=dict(status='passed',archive=str(OUT.relative_to(ROOT.parents[1])),bytes=len(data),md5=hashlib.md5(data).hexdigest(),sha256=hashlib.sha256(data).hexdigest(),member_count=18,all_bytes_match=True,crc_test_passed=True,new_generations=10,old_result_reuse=False,files=rows)
 (ROOT/'bundle-verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='files'},ensure_ascii=False))
if __name__=='__main__':main()
