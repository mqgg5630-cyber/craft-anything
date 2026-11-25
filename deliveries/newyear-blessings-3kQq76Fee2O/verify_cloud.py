"""Compare post-upload fresh search_files listings with actual local bytes."""
from pathlib import Path
import json,hashlib
ROOT=Path(__file__).resolve().parent
# Values below transcribed from fresh three-folder list results, not upload responses.
ROWS='''source/01.webp|1a7BJEGGIa9Bp4jyLrJ-hn-hKfFjn6HKk|37ae8d1775b642644e73eee71983b232|523764
source/02.webp|19u6MSfUOFz_Nf4luuPnngvHtJln3X2eu|468a4090d1bcb544838f1b155a6c4c15|525124
source/03.webp|10G1Z_xvc5XFfILke1ebbkZyHnjxIVOUB|af3ae9c565bb5482d0cf11efcfc08e83|525154
source/04.webp|1s8G7OR8egt0M4MyIJiPAnLX9Nob7WFSP|e8d4f1db8bb09907aeea497c7c73b1ab|525794
images/01.png|1v_t2arwMifiYVY0uJY5hvor_pjfSO3F4|cfb5246ae60d759a57deb6c134973baf|3859305
images/02.png|1KGB5roFu0-36gKWjoQf6kGQZ-cxNp7ti|43af7b430e5e60ae2c6d0cc8b84ab08f|3468492
images/03.png|1nwi89jgERzWR-E2szbDr--XjHWUSNE8d|b20050d73f9d243363ee9205058d813f|3529237
images/04.png|1ZoncuR0eObRdYEMMHh4KXgP7q-CL49fy|add2dd84c935ba8833a50c61359b327f|3468718
images/05.png|1kSPIga6MRnZ71uk5P3CkuQMK3VSfHyGl|2cf1fe426cd451f7f8763d6267e26c3b|3623471
images/06.png|1M1n6T-086wvC13rfl6kljTIgkDKaoaCZ|ea742b902329ede4558c606ce9809317|3600307
images/07.png|11XbKLRkDmiqmhU05xo0B9eCnGA7UHGBK|225086d1e443930e4bff29589e3cf794|3372066
images/08.png|1nVHDDOdzKZ6HZbC-a61B7O90RFoUq7Sg|26344484c3e9a6353020a3e445364a91|3367710
images/09.png|1VYfzqesIIDoZZxQSUpu43HUCtawk2BFN|1ca42597401f822f1a821650e2f5133a|3457204
images/10.png|1eGq4QgVi06XyvF2s8A0PayznjhIbYF3N|7d6d0b0573446c86506073475f288dc2|3594347
00-10張成品總預覽.jpg|1L1-1i1sWs3SWBuMHYrkzb9uOyYvFMF5x|7c606c6577673f16b0476856702946b1|579181
00-原片與成品對照.jpg|1rDcyuwLH8n-WwQNAJp1lNIp2t-23iWrX|18815aaf25bc791736cb90ff629274e7|804323
source-manifest.json|1EMbUivMPZcsChMh0fpKzoykMoAVJKUAL|1fb07ec56a8b2acb24d912ed3d595d79|3285
output-manifest.json|18nC806_4grlUOeEgOBiHX33u7gXw0hXb|af848af041988322949b4567753e3183|28394
README.md|1Xh-akPQe-Dx7TPYOjr_VLKQ1N--xOP6p|f2bf1f23ddcca78a9d38a4528bda5f6f|6280'''
def main():
 manifest=json.loads((ROOT/'output-manifest.json').read_text());copies={r['file']:r['main_copy'] for r in manifest['files']};records=[]
 for row in ROWS.splitlines():
  file,drive_id,expected,size=row.split('|');data=(ROOT/file).read_bytes();actual=hashlib.md5(data).hexdigest();size=int(size)
  assert actual==expected and len(data)==size,file
  copy=copies.get(file);name=(Path(file).stem+'-'+copy['right']+'-'+copy['left']+'.png') if copy else Path(file).name
  records.append(dict(file=file,drive_id=drive_id,cloud_name=name,local_md5=actual,cloud_md5=expected,local_bytes=len(data),cloud_bytes=size,match=True))
 assert len(records)==19
 report=dict(status='verified_complete_requested_deliverables',basis='Fresh post-upload search_files results for root/source/final folders, all pages exhausted; MD5 and size compared against local bytes',root='19pP2tjD9yu-wogvj8Gz06GJa3JFzTxJ6',folders=dict(source='1L7c-XZbXn_bzziexnc1YGxUPX3hSERsr',final='1hUrO6nLTtRVR2klW0dN0XTriHFg6vEVU'),fresh_listing_counts=dict(root_items=7,root_files=5,root_subfolders=2,source_files=4,final_files=10,total_files=19),next_page_tokens=[None,None,None],incomplete_search=False,all_match=True,scope='4 originals, 10 final wallpapers, 2 boards, 2 manifests and README; raw backgrounds, scripts, font and audit repository-only',files=records)
 (ROOT/'cloud-verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print('PASS: 19 fresh-listed Drive files, all MD5 and byte sizes match')
if __name__=='__main__':main()
