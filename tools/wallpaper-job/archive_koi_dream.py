"""Create a folder-preserving Koi Dream bundle with offline reproduction assets.

No network or uploads. The generated archive is an ignored rebuildable cache;
versioned reports and individual pictures remain in the delivery directory.
"""
import hashlib
import json
from pathlib import Path
import zipfile

ROOT=Path('deliveries/koi-dream-10')
ARCHIVE=Path('.local/锦鲤入梦-原片与十张复刻完整包.zip')
TOP=Path('锦鲤入梦')
RESOURCES={
    'package_koi_dream.py':Path('tools/wallpaper-job/package_koi_dream.py'),
    'archive_koi_dream.py':Path('tools/wallpaper-job/archive_koi_dream.py'),
    'test_koi_dream_package.py':Path('tools/wallpaper-job/test_koi_dream_package.py'),
    'download_koi_dream.py':Path('tools/wallpaper-job/download_koi_dream.py'),
    'test_download_koi_dream.py':Path('tools/wallpaper-job/test_download_koi_dream.py'),
    'download_sunset.py':Path('tools/wallpaper-job/download_sunset.py'),
    'koi-dream-download.yml':Path('.github/workflows/koi-dream-download.yml'),
    'NotoSansCJKsc-Regular.otf':Path('assets/fonts/cjk/NotoSansCJKsc-Regular.otf'),
    'CJK-LICENSE.txt':Path('assets/fonts/cjk/LICENSE.txt'),
    'DMSans-Regular.ttf':Path('assets/fonts/DMSans-Regular.ttf'),
    'DMSans-LICENSE.txt':Path('assets/fonts/OFL-DMSans.txt'),
}


def main():
    m=json.loads((ROOT/'output-manifest.json').read_text())
    images=m['sources']+m['previews']+[p[k] for p in m['pairs'] for k in ('clean','simulated_ui')]
    if len(images)!=27:
        raise ValueError('Expected 27 images including sources and previews')
    for row in images:
        data=(ROOT/row['file']).read_bytes()
        if len(data)!=row['bytes'] or hashlib.sha256(data).hexdigest()!=row['sha256']:
            raise ValueError('File changed before archiving: '+row['file'])
    # Preflight all assets and license files before creating any archive.
    for p in RESOURCES.values():
        if not p.is_file():
            raise ValueError('Missing reproduction resource: '+str(p))
    ARCHIVE.parent.mkdir(parents=True,exist_ok=True)
    members=[];resource_rows=[]
    with zipfile.ZipFile(ARCHIVE,'w',compression=zipfile.ZIP_DEFLATED) as z:
        for p in sorted(ROOT.rglob('*')):
            if not p.is_file() or p.name in ('archive-verification.json','storage-verification.json'):
                continue
            if '04-复现资源' in p.relative_to(ROOT).parts:
                raise ValueError('Do not duplicate repository resources in the delivery tree')
            name=(TOP/p.relative_to(ROOT)).as_posix()
            z.write(p,name);members.append(name)
        for name,p in RESOURCES.items():
            archive_path=(TOP/'04-复现资源'/name).as_posix()
            data=p.read_bytes();z.writestr(archive_path,data);members.append(archive_path)
            resource_rows.append({'file':archive_path,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()})
        name=(TOP/'04-复现资源/requirements.txt').as_posix()
        z.writestr(name,'Pillow==11.3.0\n');members.append(name)
    with zipfile.ZipFile(ARCHIVE) as z:
        if z.testzip() is not None:
            raise ValueError('ZIP CRC verification failed')
        for row in images:
            if hashlib.sha256(z.read((TOP/row['file']).as_posix())).hexdigest()!=row['sha256']:
                raise ValueError('Archived image hash mismatch')
        for row in resource_rows:
            if hashlib.sha256(z.read(row['file'])).hexdigest()!=row['sha256']:
                raise ValueError('Archived reproduction asset hash mismatch')
    data=ARCHIVE.read_bytes()
    if len(data)>100*1024*1024:
        raise ValueError('ZIP exceeds connector upload limit')
    result={'schema_version':1,'archive':ARCHIVE.as_posix(),'bytes':len(data),
            'md5':hashlib.md5(data).hexdigest(),'sha256':hashlib.sha256(data).hexdigest(),
            'crc_verified':True,'all_27_image_hashes_verified':True,'resource_hashes_verified':True,
            'member_count':len(members),'members':members,'resources':resource_rows,
            'documentation_snapshot':'Pre-upload snapshot; external storage-verification.json is authoritative for later cloud state.'}
    (ROOT/'archive-verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k not in ('members','resources')},ensure_ascii=False))


if __name__=='__main__':
    main()
