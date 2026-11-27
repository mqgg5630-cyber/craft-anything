"""Verify fresh post-upload Google Drive list_files results against actual local bytes."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent

# Transcribed strictly from fresh post-upload list_files calls across all 3 folders.
FRESH_LISTED_ROWS = [
    ('source/01.webp', '1HiJNmC8evME8i4v18C-1sWr1nkcru8W3', '01.webp', '1KbLuT6K1CPorzJPy1kq2T1Wkwo3OfH31', '19ad4c76e4ca38c2f934e6d01e4b5e9a', 156296),
    ('images/01.png', '1HWDQybUOHIs6yBp3Y_8SmrhNCsDDGshz', '01-树下轻荡.png', '1ERHPjn0TdreVAw8toui4lKAe3-Sbutkz', '1c0d53b8725d08a85afacc0257878d65', 1953060),
    ('images/02.png', '19_u5YvNgBkcI11dUt7yjh8JA83HNUvK0', '02-仰望流云.png', '1ERHPjn0TdreVAw8toui4lKAe3-Sbutkz', '0c35cdb925956e9c4d1728616c78ea4e', 1997085),
    ('images/03.png', '190WiX4718elv7YpXpobU_MH27g5u3Jj8', '03-红枫秋千.png', '1ERHPjn0TdreVAw8toui4lKAe3-Sbutkz', 'fb5544cb9c2e3aa75860bbc5e5496e36', 1930572),
    ('images/04.png', '1QSdGj77AzCbZWjqrQ4hLmJd-8NQtk425', '04-晃脚欢笑.png', '1ERHPjn0TdreVAw8toui4lKAe3-Sbutkz', '38da8d5f7fef918ea8a7241b47f90831', 2014235),
    ('images/05.png', '1nyP9zy8uEgfFbA0FOoVzg28w9hsZhM3P', '05-银杏金雨.png', '1ERHPjn0TdreVAw8toui4lKAe3-Sbutkz', 'fe7484a3902008bc686984f50e8b7113', 2027055),
    ('images/06.png', '1k4gTRo9XGQ2m5djOno-pjfC54V7yeu51', '06-背影看夕阳.png', '1ERHPjn0TdreVAw8toui4lKAe3-Sbutkz', '9ccbf612d974584b838eed078795301e', 1972242),
    ('images/07.png', '1ra833f9V-0Fu3Dow7W6CiR2E4H5ivgc4', '07-秋千野餐篮.png', '1ERHPjn0TdreVAw8toui4lKAe3-Sbutkz', '864f3c146ed50342c2689e69ebfdd8a7', 1965618),
    ('images/08.png', '1gTSSuQoD6uIRWLmouoG7ueRCqCNhGUkU', '08-蒲公英晚风.png', '1ERHPjn0TdreVAw8toui4lKAe3-Sbutkz', 'fec63a5eff440d37f44cf67fb00345d9', 1774399),
    ('images/09.png', '1kNUSf_n9osaJQyUOygEJEukDVMjvZXPt', '09-暮色初星.png', '1ERHPjn0TdreVAw8toui4lKAe3-Sbutkz', '4a694ed5fe4131480b68c79106d1b8d5', 1946561),
    ('images/10.png', '1kh08xrbHrjh7Ce62NcggV9BuJ2JzmIJs', '10-站上秋千望远.png', '1ERHPjn0TdreVAw8toui4lKAe3-Sbutkz', 'c5f355c05997fda8a58c46bb45b75fc8', 2018232),
    ('00-总预览.jpg', '1LMkyDzB2V7l5GE8ok8y2el6BKoPPJ2WW', '00-总预览.jpg', '1onUr7toMeJDQ5jf-xeexgC9L5NjGA9ns', '776166a60aa60b8e94123dc60a242146', 974247),
    ('00-原片总预览.jpg', '1WSnsXHZFPbrEXboBWwCXXLqQbmUGrP4o', '00-原片总预览.jpg', '1onUr7toMeJDQ5jf-xeexgC9L5NjGA9ns', 'cab2e264e20ef374cbd64e7a449a8bcc', 118229),
    ('00-10张成品总预览.jpg', '1noUG-PN7SIbMqbl5QDHP6Y5p6tOxsThw', '00-10张成品总预览.jpg', '1onUr7toMeJDQ5jf-xeexgC9L5NjGA9ns', 'e834180dc0e4b2cfad24ab7a38a0a837', 877989),
    ('source-manifest.json', '13dMv9xqa-bQlL652cQCQcoY-s80Boira', 'source-manifest.json', '1onUr7toMeJDQ5jf-xeexgC9L5NjGA9ns', '2e8cee93d3fc945c65d189c167597fd8', 2086),
    ('output-manifest.json', '1hYr_YJWj5gmSdA8m4vBQpUVST2anIabW', 'output-manifest.json', '1onUr7toMeJDQ5jf-xeexgC9L5NjGA9ns', 'dc6f0dff5b4ff6ba31de6baa5a120b71', 14616),
    ('README.md', '1QYb7-I96ogTeURMj2fAQYXkA5o5AOZib', 'README.md', '1onUr7toMeJDQ5jf-xeexgC9L5NjGA9ns', 'd558dda81d145d9b590f766bc49a01d8', 7195),
]


def main() -> None:
    verified = []
    for local_rel, drive_id, cloud_name, parent_id, cloud_md5, cloud_bytes in FRESH_LISTED_ROWS:
        data = (ROOT / local_rel).read_bytes()
        local_md5 = hashlib.md5(data).hexdigest()
        local_bytes = len(data)
        if local_md5 != cloud_md5 or local_bytes != cloud_bytes:
            raise AssertionError(f'Cloud mismatch for {local_rel}: local=({local_md5},{local_bytes}) cloud=({cloud_md5},{cloud_bytes})')
        verified.append({
            'local_file': local_rel,
            'drive_id': drive_id,
            'cloud_name': cloud_name,
            'parent_folder_id': parent_id,
            'local_md5': local_md5,
            'cloud_md5': cloud_md5,
            'local_bytes': local_bytes,
            'cloud_bytes': cloud_bytes,
            'match': True,
        })

    if len(verified) != 17:
        raise AssertionError(f'Expected 17 verified Drive files, got {len(verified)}')

    report = {
        'status': 'verified_complete_requested_deliverables',
        'basis': 'Fresh post-upload list_files calls on root, source, and results folders; all pages exhausted (next_page_token=null, incomplete_search=false); MD5 and byte size verified against local disk bytes',
        'root_folder': {
            'id': '1onUr7toMeJDQ5jf-xeexgC9L5NjGA9ns',
            'name': '秋天和秋千很配哦-懒羊羊秋千-10张复刻全流程-852x1848',
            'url': 'https://drive.google.com/drive/folders/1onUr7toMeJDQ5jf-xeexgC9L5NjGA9ns',
        },
        'subfolders': {
            'originals': {
                'id': '1KbLuT6K1CPorzJPy1kq2T1Wkwo3OfH31',
                'name': '01-原片-1张-852x1848',
                'url': 'https://drive.google.com/drive/folders/1KbLuT6K1CPorzJPy1kq2T1Wkwo3OfH31',
            },
            'results': {
                'id': '1ERHPjn0TdreVAw8toui4lKAe3-Sbutkz',
                'name': '02-复刻结果-10张-852x1848',
                'url': 'https://drive.google.com/drive/folders/1ERHPjn0TdreVAw8toui4lKAe3-Sbutkz',
            },
        },
        'fresh_listing_counts': {
            'root_total_items': 8,
            'root_subfolders': 2,
            'root_files': 6,
            'source_subfolder_files': 1,
            'results_subfolder_files': 10,
            'total_verified_files': 17,
        },
        'next_page_tokens': [None, None, None],
        'incomplete_search': False,
        'originals_and_results_separated': True,
        'public_permissions_modified': False,
        'all_match': True,
        'files': verified,
    }
    (ROOT / 'cloud-verification.json').write_bytes(
        (json.dumps(report, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
    )
    print('PASS: 17/17 fresh-listed Drive files match local MD5 and byte sizes exactly.')


if __name__ == '__main__':
    main()
