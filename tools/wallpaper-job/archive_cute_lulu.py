"""Build the folder-preserving cute Lulu ZIP offline; never upload or download.

The archive is a rebuildable local cache; sources/results and hashes stay in Git.
Cloud upload metadata belongs outside the immutable uploaded ZIP to avoid a
self-referential checksum. Re-running this reads the saved final delivery only.
"""
import hashlib
import json
from pathlib import Path
import zipfile

ROOT = Path('deliveries/lulu-cute-10')
ARCHIVE = Path('.local/今天是谁家的可爱噜啊-完整交付.zip')
REPORT = ROOT/'archive-verification.json'


def main():
    manifest=json.loads((ROOT/'output-manifest.json').read_text())
    rows=manifest['sources']+manifest['previews']+[p[k] for p in manifest['pairs'] for k in ('clean','simulated_ui')]
    for row in rows:
        data=(ROOT/row['file']).read_bytes()
        if len(data)!=row['bytes'] or hashlib.sha256(data).hexdigest()!=row['sha256']:
            raise ValueError('File changed before archive creation: '+row['file'])
    members=[]
    ARCHIVE.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(ARCHIVE,'w',compression=zipfile.ZIP_DEFLATED) as z:
        for p in sorted(ROOT.rglob('*')):
            if not p.is_file() or p.name in ('archive-verification.json','storage-verification.json'):
                continue
            name=(Path('今天是谁家的可爱噜啊')/p.relative_to(ROOT)).as_posix()
            z.write(p,name)
            members.append(name)
    with zipfile.ZipFile(ARCHIVE) as z:
        if z.testzip() is not None:
            raise ValueError('ZIP CRC check failed')
        for row in rows:
            data=z.read((Path('今天是谁家的可爱噜啊')/row['file']).as_posix())
            if hashlib.sha256(data).hexdigest()!=row['sha256']:
                raise ValueError('Archived image checksum mismatch')
    data=ARCHIVE.read_bytes()
    if len(data)>100*1024*1024:
        raise ValueError('Archive exceeds connector upload limit')
    result={'schema_version':1,'archive':ARCHIVE.as_posix(),'bytes':len(data),
            'md5':hashlib.md5(data).hexdigest(),'sha256':hashlib.sha256(data).hexdigest(),
            'crc_verified':True,'all_29_archived_image_hashes_verified':True,
            'member_count':len(members),'members':members,
            'cloud_status':'not_uploaded_at_archive_creation'}
    REPORT.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k!='members'},ensure_ascii=False))


if __name__=='__main__':
    main()
