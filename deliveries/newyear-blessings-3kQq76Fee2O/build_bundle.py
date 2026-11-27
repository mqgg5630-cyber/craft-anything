"""Build supplemental ZIP outside Git; preserve all image bytes and verify every member."""
from pathlib import Path
import hashlib,json,zipfile
ROOT=Path(__file__).resolve().parent
REPO=ROOT.parents[1]
OUT=REPO/'.local/delivery-bundles/新年祝福壁纸-完整交付-1080x2343.zip'
def main():
 mapping=[]
 for p in sorted((ROOT/'source').glob('*.webp')):mapping.append((p,'01-原片/'+p.name))
 manifest=json.loads((ROOT/'output-manifest.json').read_text())
 for r in manifest['files']:
  p=ROOT/r['file'];c=r['main_copy'];mapping.append((p,'02-结果-1080x2343/'+p.stem+'-'+c['right']+'-'+c['left']+'.png'))
 for p in sorted(ROOT.glob('00-*.jpg')):mapping.append((p,'03-总预览/'+p.name))
 for name in ['README.md','source-manifest.json','output-manifest.json','全流程与交付索引.md']:mapping.append((ROOT/name,'04-说明与清单/'+name))
 mapping.append((REPO/'skills/xhs-link-recreate-10/wallpaper-preferences.json','04-说明与清单/以后默认尺寸-1080x2343.json'))
 assert len(mapping)==21 and len({n for _,n in mapping})==21
 OUT.parent.mkdir(parents=True,exist_ok=True)
 with zipfile.ZipFile(OUT,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
  for path,name in mapping:
   # Fixed ZIP timestamps make rebuilding deterministic across checkouts.
   entry=zipfile.ZipInfo(name,date_time=(2026,1,1,0,0,0));entry.compress_type=zipfile.ZIP_DEFLATED;entry.external_attr=0o100644<<16;z.writestr(entry,path.read_bytes())
 records=[]
 with zipfile.ZipFile(OUT) as z:
  assert z.testzip() is None
  for path,name in mapping:
   data=path.read_bytes();packed=z.read(name);assert packed==data
   records.append(dict(member=name,source=str(path.relative_to(REPO)),bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),match=True))
 data=OUT.read_bytes();report=dict(status='passed',existing_batch_reused=True,new_generation_count_this_followup=0,archive=str(OUT.relative_to(REPO)),bytes=len(data),md5=hashlib.md5(data).hexdigest(),sha256=hashlib.sha256(data).hexdigest(),crc_test_passed=True,member_count=21,all_member_bytes_match=True,default_final_size=[1080,2343],files=records)
 (ROOT/'bundle-verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='files'},ensure_ascii=False))
if __name__=='__main__':main()
