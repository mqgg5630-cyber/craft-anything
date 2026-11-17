# deliveries · 双份留存（仓库磁盘 + 云端）

本目录是**仓库磁盘上的实体副本**。云盘（Google Drive / Dropbox）里的每一份交付，
在这里都有一份可浏览的同构文件夹；两者互为备份，任一边丢失都能从另一边还原。

## 为什么需要磁盘副本

- 云盘链接会失效、共享会变权限、配额会满；仓库里的文件夹永久可读、可 diff。
- 传给别人时不用再打包：直接给对方仓库路径或 clone 后打开。
- 每份交付都保留「编号子目录」结构，从 `01-下载原图` 按顺序读到 `05-说明与验收`。

## 目录总表

| 磁盘目录 | 内容 | 云端对应 |
|---|---|---|
| `rainy-note/` | 雨夜壁纸（被窝外正在下雨）：9 张原图、10 张复刻、锁屏/桌面预览各 10、说明与验收 | Drive + Dropbox `06-雨夜壁纸` |
| `butterfly-cats/` | 蝴蝶山猫猫屋：4 张原图与下载记录 | Dropbox `05-蝴蝶山猫猫屋` |
| `ink-bunny-fox-127/` | 水墨兔狐 127：原图、无 UI 复刻、锁屏/桌面预览、说明与验收（`status: partial`，按用户要求不补图） | Drive + Dropbox `02-水墨兔狐 127` |
| `sticker3d-animals/` | 3D 立体破屏动物：原图、复刻、预览、验收 | Drive + Dropbox `04-3D立体破屏动物` |
| `budapest-autumn-563/` | 布达佩斯 563 秋色：原图、复刻、预览、验收 | Drive + Dropbox `01-布达佩斯 563` |
| `blue-kitty/` | 蓝猫系列：原图、无 UI/有 UI 双版复刻、总览与验收 | Drive |
| `bears-261127/` | 261127 熊图：6 张原图与下载记录 | —（仅原片留存） |
| `garden-cats/` | 花园猫：4 张原图与下载记录 | —（仅原片留存） |
| `cloud-town-2n522qk8gxn/` | 梦幻小镇·星空下的钟楼：4 张原片、10 张复刻、锁屏/桌面预览各 10、总览与验收 | Drive `09-梦幻小镇星空钟楼（10张）` + Dropbox 同名目录 |
| `leanrea-全分支/` | leanrea 仓库 15 个 ref 的全部成果，按分支归并去重（见其 README） | Drive `03/07/08-…` + Dropbox 同名目录 |

## 命名约定

- `NN-语义名/`：数字前缀固定阅读顺序。
  - `01-下载原图`：公开 CDN 原始字节 + `下载记录.json`（含 SHA-256）。
  - `02-复刻无手机UI`：干净壁纸，不做任何 UI 叠加。
  - `03-锁屏预览` / `04-桌面预览`：仅用于展示的合成预览。
  - `05-说明与验收`：交付说明、小红书文案、总览图、`验收记录.json`。
- 有 UI / 无 UI 两版必须同时存在；预览图不得覆盖干净壁纸。

## 还原与校验

```bash
# 逐份核对磁盘副本与记录的哈希
python3 - <<'PY'
import json, hashlib, pathlib
for rec in pathlib.Path('deliveries').rglob('下载记录.json'):
    for item in json.loads(rec.read_text()).get('items', []):
        f = rec.parent / item.get('file', '')
        if f.is_file():
            got = hashlib.sha256(f.read_bytes()).hexdigest()
            print('OK ' if got == item.get('sha256') else 'BAD', f)
PY
```

## 云端 → 磁盘的补拉通道

沙箱只放行 github/npm/pypi，云盘直链在沙箱内不可达，因此补拉由仓库的
GitHub Actions 作业 `Pull cloud bundles onto disk` 完成：

1. 用云盘连接器为每个包生成**一次性临时直链**（数小时过期）。
2. 把 `{"url","dest","unzip","flatten"}` 清单写进 `tools/wallpaper-job/cloud-manifest.json` 并 push。
3. 作业下载、解压成文件夹、提交回当前分支；**直链用完即从清单中清空**，
   仓库里永远不保存可长期访问的下载地址。
