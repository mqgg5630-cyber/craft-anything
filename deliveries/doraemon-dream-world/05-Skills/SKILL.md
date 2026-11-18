---
name: doraemon-dream-planet-wallpapers
description: 从公开链接下载参考，视觉确认后重绘1张并扩展9张，交付无UI和锁屏示意各10张及同目录总预览，实传Drive并核验MD5。
---

# 哆啦A梦 · 幻梦星球

来源：https://xhslink.cn/o/4pNl4VJBJjX 。笔记6aedc91f0000000023004ff2，标题《✨哆啦A梦的奇妙世界》，作者“一名努力向上的舞蹈老师”。

成功下载证明：https://github.com/mqgg5630-cyber/craft-anything/actions/runs/44270797413 。公开页面4图：3张设备展示、1张横向壁纸旋转展示；不是4个不同原创场景。实际尺寸见下载记录，网页宣称的8192等文字不是所下载文件真实尺寸。归档是公开CDN WebP，不是作者无损母版，不需要账号Cookie或私信。

## 已成功执行的步骤

1. 工具fetch_page查看用户链接，转至xiaohongshu explore网址后获得4条公开轮播图片签名CDN地址。直接在Actions拉取rednote HTML没有imageList，已记录失败；改用实际页面返回的4条CDN URL下载成功。脚本在tools/wallpaper-job/download_doraemon.py。签名可能过期，优先复用归档字节，不保证永久有效。
2. 9:20竖屏主题不是把设备外壳裁掉就冒充原图。先人工检查原图总预览。参考02.webp用Pillow rotate(90,expand=True)做纯旋转，另存“参考图02-仅旋转校正.png”，不改归档原图。
3. 用图像生成工具逐张独立生成。每次传上述校正参考图、shared_prompt与对应scene，10次调用均成功。01为主题重绘，02—10为同风格新场景。prompts.json为真实成功调用整理的配方，不是逐字日志。不是拼图裁切，不复用旧结果凑数。代理生图步骤并非Python render.py自动完成，不能宣传任意链接无人值守生图服务。
4. 美术：高饱和钴蓝／天蓝宇宙、巨大蓝色星球、粉金边积云、白雏菊粉波斯菊黄花；柔和圆润3D动画材质，金色体积光；上方约25%安静天空给锁屏留白；角色保留哆啦A梦蓝色圆身、白面肚爪、红鼻红项圈与金铃。
5. 每次只生成一张全幅独立竖图；禁手机／平板外框、UI、时间数字、文字、水印与签名。大批量生成选项按工具规则关闭。独立检查总预览与UI预览，异常单图再修，不以文件存在代替画质检查。

## 渲染与测试

在交付根目录执行：

```sh
python -m venv .venv
.venv/bin/pip install -r 05-Skills/requirements.txt
.venv/bin/python 05-Skills/render.py
```

脚本按自身位置定位，读取02-复刻无手机UI的10个PNG，为03-复刻有手机UI生成10张同名示意图，两个目录内各保存总预览.jpg。固定09:41及日期仅设计示意，不是真机截图，不是实时数据。字体依赖系统DejaVuSans。记录实际尺寸与文件哈希，不将插值称原生高清。重跑不得改变干净图字节。

验收：4下载原图SHA256匹配；10个独立干净图哈希互异；10UI同名配对尺寸一致，字节与干净图不同；2预览真实可解码；本轮4项专用测试通过，既有回归测试结果见测试记录。10张原生输出均688×1536，约9:20；未插值伪称1080p。

## 云端交付

根目录：https://drive.google.com/drive/folders/1ObGZquD6fwwgDcOzcgMP2MP12nY3YeuD

原图、无UI、UI、Skills分开放置。每个文件实际upload_file上传，不能只创建空目录或ZIP改名。完成后重新列目录，将路径、数量、MD5与本地逐项比对。上传限流时遵守停止要求，持久化待传清单，不同回复之外不自动后台续传。

## 说明

AI重绘并非官方授权素材或像素级复印。尊重原作者与角色权益，不宣称拥有其版权。公开参考图与AI结果分开归档。

对话：https://arena.ai/agent/01a1e233-191b-7343-97c4-5f1ae134e8d7 （仅保存链接，未导出完整聊天）。
