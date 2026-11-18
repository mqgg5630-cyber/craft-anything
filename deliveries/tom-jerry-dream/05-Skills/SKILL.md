---
name: tom-jerry-healing-dream-world
description: 猫和老鼠治愈梦境10新场景，纸感赛璐璐角色与柔光水彩背景，双版本及同目录预览，真实文件夹验收。
---

# 猫和老鼠 · 温柔梦境

本轮要求：更好看、更治愈、更梦幻，10张不同场景，继续历史ZIP转真实文件夹。沿用既有已下载参考，不虚构新来源或新母版。

## 视觉改进

保留经典手绘角色比例、细墨线、柔和平涂赛璐璐与纸感；把旧日常蜂蜜黄背景升级为柔雾长春花蓝、灰粉紫、月金和浅青。梦幻来自柔光、水彩云雾与童话空间，不换成写实或3D。强调“陪伴、照顾、分享”，无追打惊吓。上方约1/3留安静空间，角色下半部，背景装饰克制。

10场景：月亮花园分享星花、云海木舟、星光温室、观景台看梦鲸、森林茶会、极光雪毯、月牙云朵邮局、繁花星轨秋千、珍珠贝壳梦、晚安流星车站。动作道具构图与前两轮不同，不裁切换色旧图凑数。

## 已执行配方

1. 参考本地deliveries/tom-jerry-remix/02-复刻无手机UI/01-毛线小帮手.png，只作STYLE ONLY。每次generate_image独立一张全幅约9:20竖图，真实10次调用成功。prompts.json是成功调用摘要，不是逐字日志。
2. 角色：Tom灰猫黄眼白嘴粉耳，Jerry棕鼠浅腹粉耳；二维细线与纸感；禁止文字、数字、UI、设备边框、水印、标志、签名、拼图。生成阶段保留干净图。
3. 用render.py生成10同名UI示意和两版同目录总预览。固定09:41及日期为设计示意，不是真机或实时截图。脚本只做渲染，不自行调用生图模型。原生尺寸以验收记录为准，未插值冒充高清。
4. 人工检查无UI/UI总预览；确认10场景不同、角色正常、留白可用。哈希不能证明视觉差异，需另人工比对前两轮。
5. 上传Drive实际图片与Skills，重新列目录核对路径、数量、MD5；若工具明确限流停止，当前回复不得再上传或换方式绕过，保存缺失清单。历史ZIP完整匹配后才可恢复回收。

## 重跑

```sh
pip install -r 05-Skills/requirements.txt
python 05-Skills/render.py
python 05-Skills/test_delivery.py
```

系统需DejaVuSans字体。重复渲染不应改变干净图字节。UI为示意，非官方授权素材或动画原画。

原片：https://drive.google.com/drive/folders/1MIjIATl-lKbquKJd1owNTVuxI5XDLqc6
上一轮：https://drive.google.com/drive/folders/1mpts0ySAOoSEQx-c-Qz0GgI_m_VEMlT_
对话：https://arena.ai/agent/01a1e233-191b-7343-97c4-5f1ae134e8d7
