"""Offline compare freshly listed Drive rows to local files, not upload acknowledgements."""
from pathlib import Path
import hashlib,json
ROOT=Path(__file__).resolve().parent
# File path | actual Drive id | fresh-listed MD5 | fresh-listed bytes.
ROWS='''source/01.webp|1nU8Mp2OcCCApRrKcNFZcG76Tuf3VFK1n|91aed9f5b433e2f3a3905e1797c997b9|253386
source/02.webp|1sWmatIhMb-kNMwpfpF_rkwFTW9DzTqkt|7e6426be1ec8b3dbf2deb64880a20b10|178958
source/03.webp|1EfCxs6IEQ7_SAAqWacbaklCObMhlKWK0|92310122a48ba518f1f9480464c9ca47|298916
images/01.png|1HUlx7qxh6dxli0Odk8hxrghYB-MccpoY|8b793644e49622c6f170ccc42acb8e19|2270123
images/02.png|17SDl-XH5Waz88J12NFJ2n1UU8vrR6D6V|4f0bc3a490e1cb9963fb1ed62488ac97|2299603
images/03.png|1q-I3nk-0PlhnFenjpq5cjZVq2PFXaA7Y|777b0fa78899fa82af699196f6612815|1929709
images/04.png|1P9t4t4VY6gphlG_XmWLHHykw15WNLWmQ|972a650751b1ea59bfc5fd04524c56e4|1779951
images/05.png|1sFRCzSspnf3B8N9nFnqh0k5ByztjuKfc|a7b9c68e739de6e4f28b73c9f9a247a5|1708622
images/06.png|1_2foQ2nxE2wpSLy8LkFnkZ1GjNf8aqFz|55ae1c75bae7dc0458083e5e041a6899|1877163
images/07.png|1oks4X5Ta2CejuNQvs3wyU52IBiDtc2Tx|d3606e46a41f8ec205bddca7c836e7fd|2062425
images/08.png|1NXnS_hSFEtTB4rFFRzQ6tF9ThZZYiXKd|2ddeb572732371725179b94b03032902|2220080
images/09.png|1GyAQtxXrywRCLVpT2AaJI5ZptOkwKeeI|70adfd47c65ce3b5f0b955ef276248f0|2197245
images/10.png|1ILoRnvwKFEtEpHW3i4jGsDm3wx_iixPJ|2c6f5dfe76000707c8f888efb7f662b7|2054630
ui/01.png|1cxGRnUv0kTOXKrNKHY9qcnix1AmvpbTj|3d47ea5467796ad9d64ddbd3b9544ede|1781080
ui/02.png|1QQ5EdqmUCNi_Fl8JIA9zYhWoAKl0oBs3|fd1b4e0e4e395f7b3b2fc29cc0e3576b|1781777
ui/03.png|1PcrE1ExjRpS1MhERElKJbyHnNWHcawzI|71c9e8af5f17a6e8e7db738209f83008|1577190
ui/04.png|1O4adegLatRhRzQG5uEZ5cVVKphbcDdY7|0351581ac2ef750bdd46697666cf934f|1778506
ui/05.png|1lIO3SyMId0ucpEr5WxW5Ic-rjhJiDlHv|44cae16bcc2d96081219f49d410fa816|1706163
ui/06.png|1jDYynmBVsB-HOyX-y7LDM5jouDUGS_lh|6554cef884f94bda6b8b0e4f5440f43d|1878154
ui/07.png|1bOzjjQRGyA3b1B0v8O3pEB4ZuDw3Jj1F|71a60b88fe957be40b0b876be6b43a0a|1744202
ui/08.png|1THeJ1PyRo4zSCMr4MSbHMDb1fojrRtxk|fc7d18c691496969fa176d73795dca1b|1848207
ui/09.png|1qsxBt76jEQxhVM_Nm9Sve-jg0HPSwt5d|4c84ce4a6e274626420417800fcf66c2|1879893
ui/10.png|1MKJJct5aFab_8DYv3Xiatk1sesPcWTx9|05f04487514d4c6e07b8b4f2e4453c8f|1758667
00-原片总预览.jpg|1ewsczxvc4Q6f8mx4ysSNwqqgr-StlK5d|059ea02c982628b134462061031a8fac|142922
00-总预览.jpg|1-7i4ApHrTzKfrhG-IBW1zHEJheJGt_jX|cf8d0aec372fe2d192d5e33f2fc86086|1123747
00-无UI总预览.jpg|1pZxSmGOV0e94N3tKY64Zp0BjoDJU5ZK8|6d2c59233df1637ec3fd8ec3779d324a|473034
00-有UI总预览.jpg|110Rm1kpIvPzI6M6j1VYrLwtsn6_eokJF|e8b1ac004d5956c1fb03e61be3069baf|504373
source-manifest.json|1vkteOy_NegUYO6We6oQrPwqs4JsNGXWn|e8ca9cfeca0e830eccc4af73b6e8814b|2597
output-manifest.json|1lmyv9Zg2bzYZbFn4fJQQZ5aeXzXLJJOC|453d6020f4b5e0c80d089c085413c30b|9772
README.md|1UYbnmQDPRL9o2pT_UNdXoQIDbsBXxenC|75f880f7e5a5414a69911fc5ea9f62d6|7136'''

def main():
 records=[]
 for row in ROWS.splitlines():
  file,drive_id,cloud_md5,size=row.split('|');data=(ROOT/file).read_bytes();md5=hashlib.md5(data).hexdigest();size=int(size)
  assert md5==cloud_md5 and len(data)==size,file
  records.append(dict(file=file,drive_id=drive_id,local_md5=md5,cloud_md5=cloud_md5,local_bytes=len(data),cloud_bytes=size,match=True))
 assert len(records)==30 and len({r['drive_id'] for r in records})==30
 audit=dict(status='verified_complete_deliverables',verification_basis='Fresh search_files listings of all four folders after all uploads; locally compared bytes and MD5',root_folder_id='1eDDsVxeCb9i-mzCAIq_lW7e4KXGmcWT7',folder_ids=dict(source='1pjhgD4cTZ0VUpHqxh3xSrX7rmqqGn_Dp',images='1qLdxREXyc9BBB4O32hNUI8wN6bV7hMee',ui='1MDHu-Mk1CZyrYVb4QoEpyyHHhA-t0ngc'),fresh_counts=dict(root_items=10,root_files=7,root_subfolders=3,source_files=3,clean_files=10,ui_files=10,total_files=30),next_page_tokens=[None]*4,incomplete_search=False,all_match=True,scope='3 original WebP, 10 clean PNG, 10 UI PNG, 4 JPEG previews, 2 manifests and README. Audit/code/auxiliary logs repository only.',files=records)
 (ROOT/'cloud-verification.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2)+'\n');print('PASS: all 30 freshly listed Drive files match local MD5 and bytes')
if __name__=='__main__':main()
