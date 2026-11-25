"""Compare fresh Drive listings captured after all uploads with local deliverables."""
from pathlib import Path
import json,hashlib
ROOT=Path(__file__).resolve().parent
ROWS='''source/01.webp|1Ky9BWyVvlgMGHFpsEtPdsaKeSWIJoUpE|98690e291254d4fe752af505f42ae66f|75728
images/01.png|1aPFXeY5AhV6_ilgSgnJll2pNrFNYJG6u|4e8c4af865cfefa6a292c9b46e605655|1594759
images/02.png|1SXu0mnQ_oFcC7KEBnlQCoeYZJNbPCKcB|af36e48f83a822e3468468d8b216ed6d|1669980
images/03.png|1O5N9oQubu19NxfSMy26mNSBAJb-Isg9K|539ac9899d51947e069f7ecd3d1b5e8f|1575999
images/04.png|1kncXXDCVDpMW6GIMHVgS8Y3_wRqS-JL6|09c33eadbae25e93456dcfd05d8da54d|1582640
images/05.png|1r1eq_ZP7aEzRwKcu-94fnKd0OhbJIC_c|ff67e701cb4dd24eb22f6f9986e4c53f|1571982
images/06.png|15R8yOowxafxg14rYn8EzD-ZfXApUZoy1|19eb932ab77dd39955cf4a918d91141e|1716174
images/07.png|1hBEcn3qtoBNuE-8QouIg0LSP3OQ0DWBN|025f6fd35bd495f591c9001e57c94485|1594616
images/08.png|1OeAiScHG8QMvZOQGsgr2AIHnhl0M0tB6|13ec6e57a00722af0e3ccbd0adc31898|1568503
images/09.png|1ZBMbw6fIP67A4xIj-ZCNjFhHX-JKC9Lr|c9078d74f280a33ca1665866cb8d4ae8|2100370
images/10.png|1m-E_y6iGJxeJyI_jvVgMQg1YkOwaHQa1|86c58ac72310dcd7a7e862b362828f05|1720594
00-10张成品总预览.jpg|1W1PKBimivxEJfpeRCANSQvuaE2WIKtn7|b0a0535a22df194663213f9d3d5635f5|296370
00-原片与成品总预览.jpg|1PXCtrH5snVb_5sBX9esKGPsh0fCalggY|d56876e21e89fb6e0a0dbda85794bf6b|333318
source-manifest.json|1puqZxyOBBSGYU0fYP6QSriJofJPoe8vP|743de0a5efd4f385c7293418e0cb47cf|1740
output-manifest.json|1Fy-7qMo2TxTn2rU9hATMkLTWw3CZGCa6|e776ab0848ca9a61f5a1a92823b6e4c4|19543
README.md|1bDJbSC49w2lKykrC4m1HpToALdUkrnjL|8f454f92488bfc595c33e1c083e90d41|6368'''
def main():
 m=json.loads((ROOT/'output-manifest.json').read_text());phrases={r['file']:r['phrase'] for r in m['files']};records=[]
 for row in ROWS.splitlines():
  file,drive_id,expected,size=row.split('|');data=(ROOT/file).read_bytes();actual=hashlib.md5(data).hexdigest();size=int(size)
  assert actual==expected and len(data)==size,file
  cloud_name=(Path(file).stem+'-'+phrases[file]+'.png') if file.startswith('images/') else ('01-唯一参考原片.webp' if file.startswith('source/') else Path(file).name)
  records.append(dict(file=file,cloud_name=cloud_name,drive_id=drive_id,local_md5=actual,cloud_md5=expected,local_bytes=len(data),cloud_bytes=size,match=True))
 assert len(records)==16
 audit=dict(status='verified_complete_requested_deliverables',verification_basis='Fresh search_files listings of all 3 Drive folders after all uploads; not upload acknowledgements',root_folder_id='1nXnOZFiEQ5-QJ7koRsBUNEtE6DaSBESS',folder_ids=dict(source='1hndd8tksnb1vqxg-VVtuGDN522aV42HG',images='14FVICWAs3M1BN8g6NoLlfhFD0G2qP3Dt'),fresh_counts=dict(root_items=7,root_files=5,root_subfolders=2,source_files=1,final_files=10,total_files=16),next_page_tokens=[None]*3,incomplete_search=False,all_match=True,scope='First original, 10 final exact-size quote wallpapers, 2 previews, 2 manifests and README; native artwork/code/font/audit local-repository only',files=records)
 (ROOT/'cloud-verification.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2)+'\n');print('PASS: all 16 freshly listed Drive deliverables match local bytes and MD5')
if __name__=='__main__':main()
