# xhs-replica

把一份小红书图文素材，复刻成 N 张「同角色、同设计语言、换内容」的成品图。

角色（一二／布布）一个像素都不能改，改的只有场景和内容。
输出一律 **1080 × 2280（9:19）** 竖屏手机壁纸。

- 技能本体：[SKILL.md](SKILL.md)
- 后期脚本：[scripts/finish.py](scripts/finish.py) —— 裁切、放大、胶片分级、叠英文小字

```sh
pip install --break-system-packages pillow numpy
python3 scripts/finish.py spec.json
```

`spec.json` 格式见 `SKILL.md` 第 4 节。

它是 leanrea 仓库里第二个「一个文件、不要 MCP」的技能；
`../healing-comic/` 是另一个，做的是把长文转成小红书治愈漫画。
