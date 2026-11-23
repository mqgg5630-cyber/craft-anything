"""Compare fresh Drive listing captured in this turn against local bytes. No network."""
from pathlib import Path
import hashlib,json
ROOT=Path(__file__).resolve().parent.parent
# Rows transcribed from fresh search_files listings, not upload acknowledgements.
R2=[
('1fVwSDNmlS99RrQwtYjBy6TvR0cgvuSqN','82782eb8744c0e9aea8dee306e1944ad',2325085),
('1tmziQhJu-nSeUSuY2iYM0m8HuOahDJx8','50068480ac495e7fa4dd4889609eab1c',2208460),
('1-k9XAQmXkcEnxWh55xh2snT1Zsv-AdOS','9a23c508cd3b8636b4c1fadffd575f00',2558473),
('1XhkIHQeSE6sEaVYgcLSOhSxqUPt0IwzA','4b5374d89209630b1e62a5d36dee120d',2665551),
('1T2dxI1d3DBVE1kEqmArsioRYEDdmpUoh','a1d1917444534773006e2a07b541d982',1727735),
('120S98w8z33IwEM9xmpZ15j-oYlAvKltD','03e8f2574c9ddd9f49b1d20e3850a744',2011227),
('1T47T50fkZVYN8RW71-4-WUEyb9vpV13V','08c54744c776de5eed086556c7c634f2',2502503),
('17TQ07S7MVxUHXdPEVHyA4ZthWRZyLZ7K','e9fb9ee99bac7df548a1ca6178eba6f4',2008410),
('1jC-zUMliy-GLKKa0pPSQk9hTQkiecVtw','721985c0ecf9a7783698d312de54ac41',2087116),
('1YaJJF1KioFKEcQNGWlFQWGufBLMEC3IA','efb3374fc6a6d7e40050de00bc549135',2190798),
('1Zqu1wol4ZIynxHwo07o_SZ6q00PX5Csr','1306036e817713486c3980a933b54fdb',459081),
('1Z78k5vkh4nyfW7CCCCh2A15DjmpxQkz1','e608e4dd57f6232e0a23c650aecd960a',5182),
('1US8iw0D7GPteHry-kDiRx-sYKdzc8RwR','4aefe0af1d8e9af41fe9443d52e7e0e6',3937)]
R3=[
('13WKOOvqc68lWJj96mIeIRceGszdylo9Q','b8127980b66c7d71c6f560ae8ce9c6a2',2537441),
('1DT_5komXFp58gZ1ybfY3zXAWTrYqc4vj','97b023c075b47caf602e81ed1553528c',1944745),
('1SBCheNiiaGv4Qf_zCFA6MPdbFnrjKNqJ','17232116ff8eb8c1157b224c29d0884a',2413547),
('17oYlqs-5TN9fknniHPtPjCFtmC7Z2GMx','3830f0091438bacba616952d5cd12a8c',2079348),
('1uAC5Sbn6N2dDvC-mx1RqtLVSTBvfOL44','6327daf3be3037035092f7c391bdd5bf',2102317),
('1CWsru0ucysCM8EwieLWQsdnptpO4I1WG','5f79db2bf20d6be4077c812cdc756b57',2745515),
('1Z6_56IDOAVE98nEufXddmszQHw0oH6Br','1901c5ef5c7155a14fe32f54317ba481',2221109),
('1Kvl0IdbHfBEWrwogy_gOulJprS6um85I','1558eb13d641487d194497c46fc0c072',2257119),
('1G0OgaNvJ66SEqbBqG96sAdjSrzXGb_KW','814b96caaac66cfaa2455e2a22ad15db',2400329),
('1Uz_n-I5F4gTy3Wl-b5NlXPvMIIo3cBLL','22c8be9eea91d811b17be4f285ed9c25',2220277),
('1HSbGdx6llxzdyOKyQOgRLbJTiR9BLmqk','393448a93ce20bd3bd33b00bcc822043',491536),
('11y87Mxx6FACkX0dqJjKyvsOkQiU8cj5j','e0fe621419be20a9b7b1c0e12c0519b0',4833),
('19yWDHZ4pU2AliheOcpzZ10hQH8gf2wIO','872557d68712150e7dff08adf69092e4',3661)]

def check(roundno,rows,folder):
 r=ROOT/f'lululu-cute-round{roundno}-textless'
 paths=[r/'images'/f'{i:02}.png' for i in range(1,11)]+[r/'00-10张新场景总预览.jpg',r/'output-manifest.json',r/'README.md']
 manifest=json.loads((r/'output-manifest.json').read_text())
 records=[]
 for i,(p,(drive_id,cloud_md5,cloud_bytes)) in enumerate(zip(paths,rows)):
  data=p.read_bytes();md5=hashlib.md5(data).hexdigest()
  assert md5==cloud_md5 and len(data)==cloud_bytes,p
  if i<10:
   name=f'{i+1:02}-'+manifest['files'][i]['scene']+('-服装待修' if roundno==2 and i==1 else '')+'.png'
  elif i==10:name=f'00-第{"二" if roundno==2 else "三"}轮10张总预览.jpg'
  else:name=p.name
  records.append(dict(file=str(p.relative_to(r)),cloud_name=name,drive_id=drive_id,local_md5=md5,cloud_md5=cloud_md5,local_bytes=len(data),cloud_bytes=cloud_bytes,match=True))
 assert len(records)==13
 audit=dict(status='verified_uploaded_scope',verification_basis='Fresh Google Drive search_files listing, after all uploads; compared to actual local bytes',folder_id=folder,listed_count=13,png_count=10,preview_count=1,document_count=2,next_page_token=None,incomplete_search=False,all_match=True,scope_note='Round2/3 outputs, preview and two docs only. Original-source and round1 historic pending uploads not included. Audit file itself local/repository only.',files=records)
 (r/'cloud-verification.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2)+'\n')
 print(f'Round{roundno}: all 13 freshly listed files match MD5 and bytes')
if __name__=='__main__':
 check(2,R2,'1qujPZV5GDyO7tnT3gB_ePI81-MdJV9Hw')
 check(3,R3,'1O8pL8493INPy4_7IxBpelq4l24tAIWV2')
