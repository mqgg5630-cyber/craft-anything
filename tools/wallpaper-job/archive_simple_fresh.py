"""Create an offline-rebuildable ZIP; verify image hashes and every ZIP CRC."""
import hashlib
import json
from pathlib import Path
import shutil
import zipfile

ROOT=Path('deliveries/simple-fresh-first-10')
ARCHIVE=Path('.local/简单清新壁纸-第一张参考-十张祝福完整包.zip')
TOP=Path('简单清新壁纸')

def main():
    res=ROOT/'03-复现资源'
    for name in ('package_simple_fresh.py','test_simple_fresh_package.py','archive_simple_fresh.py','download_simple_fresh_first.py','test_download_simple_fresh_first.py','download_sunset.py'):
        shutil.copyfile(Path('tools/wallpaper-job')/name,res/name)
    shutil.copyfile('.github/workflows/simple-fresh-first-download.yml',res/'simple-fresh-first-download.yml')
    (res/'requirements.txt').write_text('Pillow==11.3.0\n')
    m=json.loads((ROOT/'output-manifest.json').read_text())
    rows=[m['source']]+m['previews']+[r['result'] for r in m['outputs']]
    for row in rows:
        data=(ROOT/row['file']).read_bytes()
        if len(data)!=row['bytes'] or hashlib.sha256(data).hexdigest()!=row['sha256']:
            raise ValueError('Image changed before archive: '+row['file'])
    for row in m['outputs']:
        if hashlib.sha256((res/'底图'/row['raw_file']).read_bytes()).hexdigest()!=row['raw_sha256']:
            raise ValueError('Raw asset changed')
    members=[]
    with zipfile.ZipFile(ARCHIVE,'w',zipfile.ZIP_DEFLATED) as z:
        for p in sorted(ROOT.rglob('*')):
            if p.is_file() and p.name not in ('archive-verification.json','storage-verification.json','standalone-verification.json'):
                name=(TOP/p.relative_to(ROOT)).as_posix();z.write(p,name)
                members.append({'file':name,'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
    with zipfile.ZipFile(ARCHIVE) as z:
        if z.testzip() is not None:raise ValueError('ZIP CRC failure')
        for r in members:
            if hashlib.sha256(z.read(r['file'])).hexdigest()!=r['sha256']:raise ValueError('ZIP member hash mismatch')
    data=ARCHIVE.read_bytes()
    if len(data)>100*1024*1024:raise ValueError('Upload limit exceeded')
    report={'archive':str(ARCHIVE),'bytes':len(data),'md5':hashlib.md5(data).hexdigest(),'sha256':hashlib.sha256(data).hexdigest(),
            'member_count':len(members),'crc_verified':True,'all_member_hashes_verified':True,'members':members,
            'snapshot':'Pre-upload; authoritative later cloud state is storage-verification.json outside ZIP.'}
    (ROOT/'archive-verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
    print(json.dumps({k:v for k,v in report.items() if k!='members'},ensure_ascii=False))

if __name__=='__main__':main()
