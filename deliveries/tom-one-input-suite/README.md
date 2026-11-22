# Tom午睡 · 单参考自动全套测试

## 唯一输入
06-午睡小被角.png，无手机UI版；云端file id `127dCApDxNW-pp1ivc2HYvaM5Mw-FxrII`，父目录02-复刻无手机UI `1O7pU46FghihbqBslwJPvpzcSPYYQxin6`。
本地原图MD5与云端相等：`58aaa9d0a2c6f8b7d0537e83824981c3`。同名有UI文件已排除，没有混用其它图片。

## 做了什么
Agent看这张参考图，提取Tom/Jerry、复古赛璐璐线条、米杏/蓝灰色、沙发午睡、毯子/餐巾。每个用途只附同一原图参考，实际调用宿主generate_image共10次，制作手机、电脑、平板横/竖、手表、Tom情头、Jerry情头、朋友圈、QQ主页、聊天。
情头独立1024方形近景生成，改为相向微笑、抱呼应的小毯角，不是从原图抠小脸放大；睡姿→坐姿属于用途适配而非新增身份。聊天中央留空；电脑和平板重新画横向场景，非裁切竖图。
后期独立导出31张静态图片、720p光点MP4与低清GIF，共33个素材。UI为通用英文模拟，无UI原生图保留；另有总览、来源/尺寸/MD5清单和Skills。无HTML/PDF/ZIP替代素材。

## GitHub结果
参见research/GitHub技能调研.md：实际读取并固定commit的ShotPilot、image-craft、Geying Character、character-consistency。前三者的方法相近但不是现成整套壁纸Skill；视频分镜方案不采用。没有运行第三方安装器/付费API，没有声称已运行ShotPilot校验器或多Agent。
组合技能在仓库`skills/one-reference-suite/`，包含SKILL、GitHub调研、规划器、4项单测。只需给图，Agent内部写profile、生成计划并派发生图；独立CLI规划器**不会**自行生图或自动看图，不是完全离线一键程序。

## 实测与边界
- 本次实际测试为：单张双角色手机壁纸→10用途原画→UI→独立素材；只有头像的分支做了规划单测，未另花10次生成验证，所以不能宣称任意头像必定完美。
- 仅一个主体时默认同一角色的A/B配对，不凭空推断另一位人物；不可见全身/背景是合理延展，不是原图信息还原。
- 规划器工具参数示例是在本轮生图后按同一分析创建，用于验证/复用规划接口，非逐字记录本次10次工具调用的提示词。实际生成已由宿主工具完成；planner-demo里status保留planned_not_dispatched，避免误认CLI派发。
- 4K/1440p导出仍为专用原画整幅适配插值，不是原生4K。人物一致性经过总览人工视觉检查，并非自动识别器评分或像素级同一场景。
- MP4仅光点叠加、无人物动画；GIF只是预览。

新Drive目录：`1KLgxaE1XrMLsZy9Gq0rQ0oOitEHJ0r7f`，不覆盖旧版本。全量上传及核对结果以云端验收.json为准。
