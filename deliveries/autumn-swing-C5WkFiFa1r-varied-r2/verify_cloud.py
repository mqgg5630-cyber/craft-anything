"""Verify Google Drive state for Round 2 against local bytes and MD5s."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent

ROOT_FOLDER = {
    'id': '1i6q7JCp8HW0uX3aFjrtHUpCS_zaSI3Ei',
    'name': '懒羊羊-精准角色10大不同场景壁纸-852x1848-第二版',
    'web_view_link': 'https://drive.google.com/drive/folders/1i6q7JCp8HW0uX3aFjrtHUpCS_zaSI3Ei',
}
SOURCE_FOLDER = {
    'id': '1Z4WrT6N_BHTK_y5Eee6f2mo6jAY23TLM',
    'name': '01-原片-1张-852x1848',
    'web_view_link': 'https://drive.google.com/drive/folders/1Z4WrT6N_BHTK_y5Eee6f2mo6jAY23TLM',
}
RESULTS_FOLDER = {
    'id': '1SVly4N9Esqlo5qKjh1jNtWFDAOpXKO1c',
    'name': '02-复刻结果-10张不同场景-852x1848',
    'web_view_link': 'https://drive.google.com/drive/folders/1SVly4N9Esqlo5qKjh1jNtWFDAOpXKO1c',
}

REMOTE_LISTED = [
    {'id': '1XI2FdfMtsA0M78xY89wmwCGzNzZzSRMg', 'name': '00-总预览.jpg', 'parents': [ROOT_FOLDER['id']], 'md5_checksum': '96e84b9d10e4e076167928753a75e31e', 'size': '956599', 'web_view_link': 'https://drive.google.com/file/d/1XI2FdfMtsA0M78xY89wmwCGzNzZzSRMg/view?usp=drivesdk'},
    {'id': '1BNjUcnKHFetGWOxbw1nXqWF85O_Un04y', 'name': 'README.md', 'parents': [ROOT_FOLDER['id']], 'md5_checksum': 'ea7ce1c48d729a5dbc6f7c36c29a5e45', 'size': '3853', 'web_view_link': 'https://docs.google.com/document/d/1BNjUcnKHFetGWOxbw1nXqWF85O_Un04y/edit?usp=drivesdk&ouid=108865329439224864146&rtpof=true&sd=true'},
    {'id': '1wwuMMDJMxeOS_0vSiF3hZY_I1mqTUj3A', 'name': 'source-manifest.json', 'parents': [ROOT_FOLDER['id']], 'md5_checksum': '2e8cee93d3fc945c65d189c167597fd8', 'size': '2086', 'web_view_link': 'https://drive.google.com/file/d/1wwuMMDJMxeOS_0vSiF3hZY_I1mqTUj3A/view?usp=drivesdk'},
    {'id': '1yd63xMBRrQuEdJ6YS1GjkhmYKfzalZB3', 'name': 'output-manifest.json', 'parents': [ROOT_FOLDER['id']], 'md5_checksum': 'a33750b978a6cb3196f49bc262e8cf4b', 'size': '18860', 'web_view_link': 'https://drive.google.com/file/d/1yd63xMBRrQuEdJ6YS1GjkhmYKfzalZB3/view?usp=drivesdk'},
    {'id': '1qbYHnqtQhLw_dJrc3zaeKLip2QhXbut7', 'name': '00-原片总预览.jpg', 'parents': [SOURCE_FOLDER['id']], 'md5_checksum': '73eaf1185d18d43f1660446f0c5e3f76', 'size': '115159', 'web_view_link': 'https://drive.google.com/file/d/1qbYHnqtQhLw_dJrc3zaeKLip2QhXbut7/view?usp=drivesdk'},
    {'id': '1Y43rWl5YHd0pNktxAQp0kLbuqAXE2v2H', 'name': '01-原片.webp', 'parents': [SOURCE_FOLDER['id']], 'md5_checksum': '19ad4c76e4ca38c2f934e6d01e4b5e9a', 'size': '156296', 'web_view_link': 'https://drive.google.com/file/d/1Y43rWl5YHd0pNktxAQp0kLbuqAXE2v2H/view?usp=drivesdk'},
]


def main() -> None:
    out_manifest = json.loads((ROOT / 'output-manifest.json').read_text(encoding='utf-8'))
    expected = [
        (ROOT_FOLDER['id'], '00-总预览.jpg', ROOT / '00-总预览.jpg'),
        (ROOT_FOLDER['id'], 'README.md', ROOT / 'README.md'),
        (ROOT_FOLDER['id'], 'source-manifest.json', ROOT / 'source-manifest.json'),
        (ROOT_FOLDER['id'], 'output-manifest.json', ROOT / 'output-manifest.json'),
        (SOURCE_FOLDER['id'], '00-原片总预览.jpg', ROOT / '00-原片总预览.jpg'),
        (SOURCE_FOLDER['id'], '01-原片.webp', ROOT / 'source/01.webp'),
        (RESULTS_FOLDER['id'], '00-10张成品总预览.jpg', ROOT / '00-10张成品总预览.jpg'),
    ]
    for rec in out_manifest['files']:
        expected.append((RESULTS_FOLDER['id'], rec['cloud_filename'], ROOT / rec['file']))

    by_key = {(item['parents'][0], item['name']): item for item in REMOTE_LISTED}
    verified = []
    pending = []
    for parent_id, cloud_name, local_path in expected:
        data = local_path.read_bytes()
        local_md5 = hashlib.md5(data).hexdigest()
        local_size = len(data)
        remote = by_key.get((parent_id, cloud_name))
        if remote is None:
            pending.append({
                'parent_id': parent_id,
                'cloud_name': cloud_name,
                'local_file': str(local_path.relative_to(ROOT)).replace('\\', '/'),
                'bytes': local_size,
                'md5': local_md5,
            })
            continue
        if int(remote['size']) != local_size:
            raise ValueError(f'Size mismatch for {cloud_name}')
        if remote['md5_checksum'] != local_md5:
            raise ValueError(f'MD5 mismatch for {cloud_name}')
        verified.append({
            'parent_id': parent_id,
            'cloud_name': cloud_name,
            'file_id': remote['id'],
            'local_file': str(local_path.relative_to(ROOT)).replace('\\', '/'),
            'bytes': local_size,
            'md5': local_md5,
            'web_view_link': remote['web_view_link'],
            'verified_by': 'fresh_list_files_post_upload',
        })

    status = 'passed' if not pending else 'partial_rate_limited'
    report = {
        'status': status,
        'provider': 'google_drive',
        'root_folder': ROOT_FOLDER,
        'separated_subfolders': {
            'original_sources': SOURCE_FOLDER,
            'recreated_results': RESULTS_FOLDER,
        },
        'verified_file_count': len(verified),
        'pending_file_count': len(pending),
        'total_expected_file_count': len(expected),
        'rate_limit_note': (
            'Merge rate-limited file uploads after the 6 root/source files completed; '
            'remaining 11 files for 02-复刻结果-10张不同场景-852x1848 are ready locally and '
            'can be uploaded in a follow-up turn after >=15 seconds.'
        ) if pending else None,
        'files': verified,
        'pending_files': pending,
    }
    (ROOT / 'cloud-verification.json').write_bytes(
        (json.dumps(report, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
    )
    print(f'Cloud state recorded: status={status}, verified={len(verified)}/{len(expected)}, pending={len(pending)}')


if __name__ == '__main__':
    main()
