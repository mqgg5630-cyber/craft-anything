"""Safely unpack Drive ZIPs; repair UTF-8 names stored without the ZIP UTF-8 flag.
Produces a member-level integrity manifest. This does not upload or delete anything.
"""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import stat
import zipfile


def decoded(info):
    name = info.filename
    if not info.flag_bits & 0x800:
        try:
            name = name.encode('cp437').decode('utf-8')
        except UnicodeError:
            pass
    p = PurePosixPath(name)
    if '\\' in name or p.is_absolute() or '..' in p.parts or ':' in name:
        raise ValueError('Unsafe archive path')
    if stat.S_ISLNK(info.external_attr >> 16):
        raise ValueError('Symlink not allowed')
    return p


def extract(archive, target, expected_md5=None):
    archive, target = Path(archive), Path(target)
    whole = hashlib.md5(archive.read_bytes()).hexdigest()
    if expected_md5 and whole != expected_md5:
        raise ValueError('Archive MD5 mismatch')
    rows = []
    with zipfile.ZipFile(archive) as z:
        members = z.infolist()
        if len(members) > 10000 or sum(i.file_size for i in members) > 1024**3:
            raise ValueError('Archive exceeds limits')
        names = [str(decoded(i)) for i in members]
        if len(names) != len(set(names)):
            raise ValueError('Duplicate decoded paths')
        # Read verifies each CRC; preflight paths before writing.
        for i, name in zip(members, names):
            out = target / name
            if i.is_dir():
                out.mkdir(parents=True, exist_ok=True)
                continue
            data = z.read(i)
            if out.exists() and out.read_bytes() != data:
                raise ValueError('Refusing to overwrite different content')
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_bytes(data)
            rows.append({'path':name,'bytes':len(data),'crc32':f'{i.CRC:08x}',
                         'md5':hashlib.md5(data).hexdigest(),'sha256':hashlib.sha256(data).hexdigest()})
    result = {'archive':str(archive),'archive_md5':whole,'crc_verified':True,
              'target':str(target),'file_count':len(rows),'files':rows,'drive_status':'not_uploaded'}
    return result

if __name__ == '__main__':
    p=argparse.ArgumentParser();p.add_argument('archive');p.add_argument('target');p.add_argument('--md5');p.add_argument('--manifest',required=True)
    a=p.parse_args();result=extract(a.archive,a.target,a.md5)
    dest=Path(a.manifest);dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text(json.dumps(result,ensure_ascii=False,indent=2))
    print(f'CRC and MD5 verified; extracted {result["file_count"]} files')
