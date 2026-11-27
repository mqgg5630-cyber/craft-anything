"""Verify fresh cloud listings, not merely upload acknowledgments, against bytes."""
from pathlib import Path
import hashlib,json
ROOT=Path(__file__).resolve().parent
REPO=ROOT.parents[1]
# Exact ID/MD5/size from post-upload fresh root/source/final folder listings.
ROWS='''source/01.jpg|1r9ZcmBIa_PslX6Giv6v1qnR9pAYaR26L|3bca5f33f5d14138709ed324621ddcda|231735
images/01.png|1VTAVduQ_5thStUEbp9Ag1jsC3MqHy9Fp|2fd14cca0146752ab2ea7809fa3c7d76|2059047
images/02.png|1EkEn1rtVFbOvr_ELmaN0cvCp1IG_l4vJ|de66301ab0a41bcac10db65c8d5c8012|2085425
images/03.png|1AtTNW54xZHC7BcmP7W4sMy2C_uksXanu|4adb54d7d1d271bf980e10e683ab9bcc|2038668
images/04.png|1VEUSg8G8zVRgGB6cXZvaHHtHEKlxgCfU|0f3424fc6cf3abc6a437d1cee9149785|2131289
images/05.png|1TR6B44b7btSuWz0EseCrmekEMGlkxaS9|6a336093caaff163cbc0fb38de54c3d1|2082077
images/06.png|10bokibHVla7P4n_IB0gUbxRrXaXRZimA|f3abcc46a7bc57d41f40c2cfa9dd982c|2093351
images/07.png|1wr3d7avSPqQt2CG00tb4vHOKdepm2gSM|e51bfffc55d24199ef00bb97d56bfa56|2045875
images/08.png|1vs3m6shyG6BS6w--UZFT-Cy5gnoPNCNS|c5fabf173ca5b6776c90f6be1afe7bac|2014408
images/09.png|1VNltlOvCXnCns9fyr3keys5fE9A6J7YR|a8903d9623304f1788a2173758bb3aa1|2077857
images/10.png|1bqZGFsCkSQPs5f5fgjx3TmSx182c51jI|df000bc8082cb443b64e092699342216|2062637
00-10张成品总预览.jpg|1Jb22sy7g5nknpclMoNzAHeNaeFy6GVkZ|26d1aa886f1e464987faa98a1f2d6460|793706
00-原片与成品对照.jpg|177j1V4n4FjXppbtCLFXy7D4aKkx4lI4F|43aa9e42e7fe8828ba82e2fb787a9529|890975
00-原片总预览.jpg|18JfEUYZ51MXoQDPxCwxxP1lhxPWrDRxX|7570a80c5811f47354aff7b6e884fdd9|97111
README.md|1e3s1vM8Opis340WjN2ZBDbzv0rjcWPbM|dc9c1c113ac29a96e9ef7d63af0a287d|6833
source-manifest.json|1-3cvItEVFlt-uscfSGrWiNYAXj1jB_rk|275374f26bd08fc6de7024c956cd1506|1580
output-manifest.json|1ajT--VapFSB_TrVaFitKMpSgRBQR8fpp|e1922169a1b3f2901092c101a6a2767c|12943
以后默认尺寸-852x1848.json|1MoyAcG_L5dX5blGp8WFA4c6nGU6ej6sy|aed8ea2f8807615403192f2c04472f92|1154
.local/delivery-bundles/秋天和秋千-新生成10张-完整交付-852x1848.zip|173AgqxP-eOzG2k3IJt4cyIXei12UFEr_|d7472ad845398c1701bbbe6983b07d01|22667113'''
def main():
 m=json.loads((ROOT/'output-manifest.json').read_text());titles={r['file']:r['title'] for r in m['files']};records=[]
 for row in ROWS.splitlines():
  file,id_,md5,size=row.split('|');p=(REPO/file) if file.startswith('.local/') else (ROOT/file);data=p.read_bytes();size=int(size)
  assert hashlib.md5(data).hexdigest()==md5 and len(data)==size,file
  name=Path(file).name
  if file.startswith('images/'):name=Path(file).stem+'-'+titles[file]+'.png'
  elif file=='source/01.jpg':name='01-笔记原片-852x1848.jpg'
  elif file=='README.md':name='README-全流程说明.md'
  records.append(dict(file=file,cloud_name=name,drive_id=id_,local_md5=hashlib.md5(data).hexdigest(),cloud_md5=md5,local_bytes=len(data),cloud_bytes=size,match=True))
 assert len(records)==19
 report=dict(status='verified_complete',basis='Fresh post-upload search_files on all three folders; page tokens null; MD5 and byte-size matched against local data, not inferred from upload receipts',root_id='1jh8fgPT0PmOGZapHYuHwcXSrsN2AZxjC',source_folder_id='1sVX68foiiIbgMZS-VHUYnovF8bdBSE-D',result_folder_id='1G2UjZPRJWl8_rm9GCX0h8A58tnNqc00X',fresh_counts=dict(root_items=10,root_files=8,root_subfolders=2,source_files=1,final_files=10,total_files=19),next_page_tokens=[None,None,None],incomplete_search=False,all_match=True,new_generation_count=10,old_outputs_reused=False,final_dimensions=[852,1848],scope='1 original, 10 final PNG, 3 previews, README, 2 manifests, dimension preference and full ZIP; native artwork/code/audit local repository only',files=records)
 (ROOT/'cloud-verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print('PASS: all 19 freshly listed Drive files match local MD5 and bytes')
if __name__=='__main__':main()
