# GitHub相似Skills调研（2026-11-16）
通过 gh search repos 查询 `image generation agent skills` 和 `character consistency skill`，用GitHub API读取以下SKILL.md正文。未安装执行第三方代码，未使用外部付费API，也没有验证仓库广告里的质量/成本承诺。

|项目|读取版本|真实相似点|与目标的差距|采用方式|
|---|---|---|---|---|
|[ShotPilot](https://github.com/ma-nucho-pro/shotpilot/blob/bb4291acdcaf8bbdb2216e154f0a0320c165c0bd/skills/shotpilot/SKILL.md)|bb4291acdcaf8bbdb2216e154f0a0320c165c0bd|自动分类、身份/画风参考角色、内部JSON规格、宿主生图派发、结构校验|默认单张，不自带壁纸/情头全套规格和Drive验收|借鉴“用户给图、内部规划、不让用户复制提示词”；未声称运行其validator或多Agent流程|
|[image-craft](https://github.com/jide/jide-skills/blob/4db67a45fc50b400b966adf83a912f9d707a9876/skills/image-craft/SKILL.md)|4db67a45fc50b400b966adf83a912f9d707a9876|全分辨率参考、变体/编辑分支、避免纯AI串行漂移、生成后看图|通用图像制作，不是全套用途自动路由；其CLI有模型/API依赖|采用“每张回到同一原始参考”和视觉验收，不安装CLI|
|[Geying Character](https://github.com/baicuya/geying-character-skill/blob/209c384a9e99af6c1f9014c2fe1ad08731d398e8/SKILL.md)|209c384a9e99af6c1f9014c2fe1ad08731d398e8|Character DNA，身份锚点与叙事变量分开，参考条件与漂移报告|偏漫画/视频连续性，不含设备壁纸比例、UI、安全区和云端交付|最适合情头用途化改造的身份约束方法，转成profile结构|
|[character-consistency](https://github.com/divolleggett/character-consistency-skill/blob/f77c2734afbda6f2cac539ff408f8682d5061b59/SKILL.md)|f77c2734afbda6f2cac539ff408f8682d5061b59|参考优先，先检验角色一致性|主要是拼图分镜→Seedance视频，依赖AtlasCloud，非静态全套，分镜拼图不符合独立原画需求|不采用其视频流水线；仅作近似方案对比|

结论：本次有限检索没有找到可原封不动完成“任意套图单张输入→十用途原生构图→UI→独立文件→Drive哈希验收”的完整Skill。推荐将前三者的思想组合为本目录one-reference-suite；不能说GitHub不存在其它方案，也不能说这些仓库已经被本机完整集成/验证。
