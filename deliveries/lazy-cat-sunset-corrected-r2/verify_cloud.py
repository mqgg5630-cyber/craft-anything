"""Compare a recorded fresh Drive listing against local exact bytes, not upload claims."""
from pathlib import Path
import hashlib,json
ROOT=Path(__file__).resolve().parent
REPO=ROOT.parents[1]
# Values transcribed from fresh search_files after all uploads; null next_page_token,
# incomplete_search=false, 22 entries (20 files + 2 subfolders), request below.
LIVE=[
('images/01.png','1upOPG4zG6YPzMIGJ4eX9RC9QpzJKa5DJ',2015230,'151433c5ed43ca8244e526214b6cd5b7'),
('images/02.png','1PMoUM17rKixlty9IjCHuh3MEko0wJ-IE',1912019,'f76cc06567c116a617f030487a057142'),
('images/03.png','1955gpmq6Jqgd-30Ka8z0_we1GfCFmP76',1783935,'2a7bb13efd9811b62f5b6b23cfe25567'),
('images/04.png','1-4-aHBbndwlEE7AiMXxx6MOxtKflUkyT',2053782,'949c9df8c602ba1b7b616dac18569df0'),
('images/05.png','13PumYaGp3iD2pKoDlEhEyESETd637S_x',2316503,'b6734583e330f5b7cec0d10a417db7d7'),
('images/06.png','12eW157l1i1djsvMxyoieoWEeI0_y34Lz',2012627,'e17e829adab3f37c2bf79a0f130bc502'),
('images/07.png','1WyFbuWJKspcqLSuKPC1r8cUcTn7Uizrl',2141598,'30a3692cf71434b99cdd07f2839fed20'),
('images/08.png','1QIyQzDxqTwBvALjWjKQH6gGWPRJkvkIo',1844533,'632ab3de13db66aacc1933bbde545a6d'),
('images/09.png','1T-u92H2YpEO4EqgJdDVbQ3FMJNb2Tlfr',1933533,'ec10f6b6c3eeea6a3e5a7662cab953a8'),
('images/10.png','18D5b7S4xr8jrbMLH4Zx1SA_x5Ldxs4CB',1798653,'4649a546f60ca21ce79d1410e01785c5'),
('reference/source-original.jpg','1V3SvS7RAgFRTmOzGROVlAtqrWgNOMFUH',171975,'92dc7213db39080d626a7f6e0c210cfe'),
('reference/classic-original.png','1OkNa9WOLtWSkgsjaYI6in1qEX_4qN5Xx',119680,'b20cd323491c4e2d67eb76fc2fb06d2f'),
('00-10张成品总预览.jpg','1SeBXXmujG9szLvQXsVfBXJGyxL3NIdkk',719201,'d2fec8360c9e1f25d09e1cdb49e467cd'),
('00-原片与成品对照.jpg','1mblGTIwI66rt0KQVOHBcUyDyfF6L2Pts',800096,'a8e2426d1917781d4d0ace7572c86ff9'),
('00-原片与角色参考.jpg','1R332r3JIERUKuFXStq3CKfXTGiV8R0Wx',106492,'cd8b4d14dc9deb1490a57d08bfb0d94f'),
('README.md','1-KlJjyAXoVggVqt4o5cakwkIVVcw9irg',2582,'3462add10896bca46fd1a08860fd26e2'),
('source-manifest.json','18bRNj22EJDm4HWov_z0GAfgRjQi93NCp',1413,'910b948848ff3743302d635c5a24856b'),
('output-manifest.json','13f9tIJXTlaX6tEf29k5Vuq5-oPSWZ9Fq',8878,'8e9b8e6cbd5fd6d430ecd7225cf1fd22'),
('postprocess-log.json','1sfq4e0NPC8_Y6vURWmyk4_qQUnGX-nuo',1777,'8b390e42f03ffca61ece2f9f38acffc6'),
('../../.local/delivery-bundles/懒羊羊与小猫-身体重做10场景-852x1848.zip','1iD0gYRRYNEZOUofEyuMzPZXdhVbX44G5',21687969,'e43a046301995e1d79c052a14a44a428')]
def main():
 rows=[]
 for name,id_,size,md5 in LIVE:
  data=(ROOT/name).read_bytes();assert len(data)==size,name;assert hashlib.md5(data).hexdigest()==md5,name
  rows.append(dict(file=name,id=id_,bytes=size,md5=md5,match=True))
 report=dict(status='passed',method='Fresh Drive search_files listing across root and two known subfolders; compare sizes and MD5 to local files',live_listing_request='e7c7e749-c3fc-4533-a761-d9e93fdbd079',next_page_token=None,incomplete_search=False,cloud_files=20,subfolders=2,final_count=10,all_bytes_and_md5_match=True,root_id='1Byly8eT2Rhq4EpgodNJxFKLv2MiuJaXP',source_folder_id='1d6dFxR2h1uKWK58aX4CGbz-TCpxGs_yr',result_folder_id='1Tru5WWFwmyWtpf9fPa_JI90yPCrtA2bE',files=rows)
 (ROOT/'cloud-verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print('PASS: all20 live Drive file sizes and MD5 match; 10 final PNGs, originals separate')
if __name__=='__main__':main()
