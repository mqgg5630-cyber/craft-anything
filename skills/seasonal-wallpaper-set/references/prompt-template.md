# Prompt 模板（英文，填空即用）

## 通用编辑模板

```
Edit this vertical phone wallpaper <keep the same tall narrow portrait canvas as the reference> into
a <SEASON> version.

KEEP COMPLETELY UNCHANGED: <CHARACTERS> — exact same silhouettes, size, positions, poses, faces,
line art, <PER-CHARACTER DETAILS: the gray horns / bat wings / heart-tipped tail on the right one, the
feathered angel wings on the left one>. Do NOT add hats, scarves, mittens or any clothing to them.
Keep the handwritten "<TEXT>" lettering and its underline exactly as is (same position, same <COLOR>,
same size). Keep the same watercolor paper-grain texture and the same vertical gradient layout with a
large empty middle area.

Only change the season:
- Sky: <SKY LAYER — gradient direction + what is added: snowflakes of mixed sizes / pastel aurora
  ribbons / shooting stars / falling petals / fireflies>; remove all <OLD SEASON PROPS: bats>.
- Keep the <MOON SUN ETC> in the <POSITION> at the same position and size, <plus a soft halo>.
- Bottom third: replace the <OLD PROPS — jack-o'-lanterns, the trick-or-treat ghost, the candies and
  the dry autumn plants> with <NEW SCENE> in the same <PALETTE> tones: <3–5 concrete props>.
  Keep the composition as airy as the original, with the same amount of empty space in the middle.

No extra text, no logos.
```

## 占位符说明

| 占位符 | 填什么 | 例子 |
|---|---|---|
| `<SEASON>` | 目标季节/节日 | `winter`、`early-spring`、`summer night` |
| `<CHARACTERS>` | 角色数量与形态 | `the two chibi characters` |
| `<PER-CHARACTER DETAILS>` | 唯一标识特征，越具体越好 | 犄角颜色、翅膀形状、尾巴末端、腮红、眼睛画法 |
| `<TEXT>` `<COLOR>` | 手写文字与颜色 | `yf ♡ wsh`、`sage-green` |
| `<SKY LAYER>` | 顶层氛围 | 雪、极光、流星、花瓣、萤火 |
| `<OLD SEASON PROPS>` | 原图里必须删掉的季节道具 | 蝙蝠、南瓜、糖果、枯枝 |
| `<NEW SCENE>` `<PALETTE>` | 底部地景与配色 | 雪人+热可可+礼物；`muted lavender-gray` |

## 强化句（按需追加）

- 比例跑偏：`Keep the tall narrow portrait canvas of the reference (roughly 9:16).`
- 画面被填满：`Leave the middle of the image as empty as the original — it is where phone icons go.`
- 角色被"美化"：`Do not redraw the characters in a different style; keep the original line weight,
  eye style and blush.`
- 出现意外的帽子/配饰：`Absolutely no clothing, hats, scarves, earmuffs or mittens on the characters.`
- 文字模糊：`The lettering must stay a clean flat hand-written brush script, not re-rendered or blurred.`

## 提示

- 编辑类模型对"保留"的理解依赖**具体描述**，而不是"keep everything"这种泛泛的话。
- 把"删除旧道具"和"添加新道具"分成两句写，删漏了就是漏在这句。
- 同一个 prompt 骨架跑 10 张时，只替换 `Sky`、`Bottom third` 两段，其余一字不改，这样整套才像一套。
