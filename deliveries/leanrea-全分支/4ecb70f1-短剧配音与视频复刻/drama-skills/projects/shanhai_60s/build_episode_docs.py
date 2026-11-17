#!/usr/bin/env python3
"""
生成《山海寻光记：赴一场四季星河》（v2 正版形象还原精制版 · EP001 · 60.00s 治愈系 3D AI 漫剧）
全套五份 zenstory-ai/drama-skills 规范文档，并通过 creator_markdown_check.py 跨文档一致性锁与真实资产引用校验。
"""
import json
from pathlib import Path

PROJ = Path(__file__).resolve().parent
EP = PROJ / "剧集" / "EP001"
EP.mkdir(parents=True, exist_ok=True)

LOCK_LULU = (
    "canonical DuoAi 3D smooth matte golden-yellow vinyl-clay capybara-hippo boy Lulu "
    "with smooth rounded orange-blushed snout (zero nostrils), small glossy black eyes, "
    "tiny orange tangerine with green leaf on head, and warm brown shorts"
)
LOCK_LUMEI = (
    "canonical DuoAi 3D smooth matte sunny-yellow vinyl-clay capybara-hippo girl Lumei "
    "with smooth rounded rosy-cheeked snout (zero nostrils), expressive glossy black eyes, "
    "white scalloped ruffle trim around head with flat pancake-hat topped by two green sprout leaves, "
    "and pastel pink short-sleeve collared dress"
)

SHOTS = [
    {
        "idx": 1, "id": "SHOT-EP001-001", "motion_id": "MOTION-EP001-001", "scene_id": "EP001-SC001",
        "chapter": 1, "act": "第一章·破晓云海列车", "title": "云海石拱桥与晨光列车",
        "kind": "landscape", "scene_key": "L1", "speaker": "噜妹", "voice_mode": "VO",
        "line": "山海尽头，藏着星河呢。", "sub_display": "噜妹（独白）：山海尽头，藏着星河呢",
        "place": "破晓云海石拱桥",
        "purpose": "以吉卜力式壮阔破晓云海与复古小火车大远景开篇，瞬间立住山海寻光的世界观与温暖晨光色温。",
        "camera": "高空俯瞰大远景缓推，越过翠绿松谷推向驶过石拱桥的晨光列车。",
        "start_state": "朝霞刺破翻涌的金色云海，复古小火车稳稳驶上高架石拱桥。",
        "action": "列车沿石拱桥平稳前行，洁白蒸汽随山风飘散，云海翻涌流淌。",
        "end_state": "金色晨光洒满整座云谷，自然叠化切入温暖木质车厢。",
        "kf_prompt": "9:16 vertical cinematic 3D animated film grand landscape establishing shot: golden sunrise rays break through a glowing sea of pink and gold morning clouds in an emerald pine valley, an arched stone viaduct spans the canyon as a vintage cream-and-green train crosses smoothly, volumetric sunbeams, no text, no logo.",
        "motion_prompt": "In a 9:16 vertical 3D animated mountain valley at sunrise, a vintage train glides smoothly across the stone viaduct bridge above rolling golden clouds as white steam drifts in the breeze and camera gently pushes in, no text, no logo.",
    },
    {
        "idx": 2, "id": "SHOT-EP001-002", "motion_id": "MOTION-EP001-002", "scene_id": "EP001-SC001",
        "chapter": 1, "act": "第一章·破晓云海列车", "title": "暖阳木车厢·递出星河车票",
        "kind": "char_pair", "scene_key": "C1", "beat": "A", "speaker": "噜噜", "voice_mode": "DIALOGUE",
        "line": "给，专属于噜妹的车票。", "sub_display": "噜噜：给，专属于噜妹的车票",
        "place": "复古暖阳木质车厢",
        "purpose": "首次正版 3D 形象亮相：噜噜在晨光木车厢中把发光金色星河车票递给噜妹，唇形、眨眼与递票动作精准同步。",
        "camera": "车厢双人中近景微推，窗外金色云海缓缓向后流动。",
        "start_state": "噜噜坐在左排木椅手持发光星河车票，噜妹坐在右侧伸出双手期待接票。",
        "action": "窗外云海流动，星光微粒自金色车票升起，噜噜温柔开口说话、自然眨眼并将车票递向噜妹手中。",
        "end_state": "金色车票递至噜妹手边，无缝切入下一镜接票欢呼。",
        "kf_prompt": f"9:16 vertical 3D smooth matte vinyl animation inside a sunlit wooden train cabin overlooking golden clouds: on left {LOCK_LULU} hands a glowing golden star ticket toward {LOCK_LUMEI} on right, warm sunrise rim light, no text, no logo.",
        "motion_prompt": f"Inside a sunlit wooden train cabin, {LOCK_LULU} speaks with synchronized 3D lip motion, blinks naturally, and extends a glowing golden ticket toward {LOCK_LUMEI} while clouds drift past outside the window, no text, no logo.",
    },
    {
        "idx": 3, "id": "SHOT-EP001-003", "motion_id": "MOTION-EP001-003", "scene_id": "EP001-SC001",
        "chapter": 1, "act": "第一章·破晓云海列车", "title": "手捧星河车票·开心出发",
        "kind": "char_pair", "scene_key": "C1", "beat": "B", "speaker": "噜妹", "voice_mode": "DIALOGUE",
        "line": "好耶，和噜噜出发喽！", "sub_display": "噜妹：好耶，和噜噜出发喽！",
        "place": "复古暖阳木质车厢",
        "purpose": "承接上一镜递票动作：噜妹双手捧起发光车票雀跃欢呼，完成第一章启程情感闭环。",
        "camera": "双人中近景柔和跟拍，星光粒子萦绕车票。",
        "start_state": "噜妹双手捧住发光的金色星河车票，噜噜在左侧笑眼弯弯注视着她。",
        "action": "噜妹开心晃动身体并清晰说出对白，金色星点自车票冉冉升起，窗外云海流淌。",
        "end_state": "两人相视灿烂微笑，柔和叠化进入第二章风车花海。",
        "kf_prompt": f"9:16 vertical 3D smooth matte vinyl animation inside sunlit wooden train cabin: {LOCK_LUMEI} joyfully holds up the glowing golden star ticket with both hands as {LOCK_LULU} watches with happy curved eyes, no text, no logo.",
        "motion_prompt": f"Inside the sunlit wooden train cabin, {LOCK_LUMEI} holds the glowing golden star ticket and cheers with crisp 3D lip-sync and joyful head bounce while {LOCK_LULU} smiles warmly beside her, no text, no logo.",
    },
    {
        "idx": 4, "id": "SHOT-EP001-004", "motion_id": "MOTION-EP001-004", "scene_id": "EP001-SC002",
        "chapter": 2, "act": "第二章·晴空风车花海", "title": "雪峰白风车与格桑花海",
        "kind": "landscape", "scene_key": "L2", "speaker": "噜噜", "voice_mode": "VO",
        "line": "春风一吹，花海都醒啦。", "sub_display": "噜噜（独白）：春风一吹，花海都醒啦",
        "place": "雪峰白风车花海步道",
        "purpose": "展现湛蓝晴空下皑皑雪山、旋转白色木风车与漫山粉色格桑花海的治愈画卷。",
        "camera": "低机位掠过摇曳花海向远方白色大风车与雪峰缓推。",
        "start_state": "晴空万里，雪峰脚下白色风车悠然转动，粉白格桑花铺满山坡。",
        "action": "春风拂过无边花海掀起层层花浪，风车叶片匀速旋转，蒲公英绒絮随风轻舞。",
        "end_state": "阳光洒满花海石径，顺畅切入双人吹蒲公英近景。",
        "kf_prompt": "9:16 vertical 3D animated scenic meadow under crisp blue sky with snow-capped peaks, spinning white wooden windmills, and endless pink-and-white cosmos flowers swaying in spring breeze, no text, no logo.",
        "motion_prompt": "Across a sunlit alpine flower meadow in 9:16 vertical 3D animation, pink cosmos flowers sway in waves and white windmill blades turn gently under snow peaks as camera glides forward, no text, no logo.",
    },
    {
        "idx": 5, "id": "SHOT-EP001-005", "motion_id": "MOTION-EP001-005", "scene_id": "EP001-SC002",
        "chapter": 2, "act": "第二章·晴空风车花海", "title": "风车花径·吹起蒲公英许愿",
        "kind": "char_pair", "scene_key": "C2", "beat": "A", "speaker": "噜妹", "voice_mode": "DIALOGUE",
        "line": "我把小愿望吹出去啦！", "sub_display": "噜妹：我把小愿望吹出去啦！",
        "place": "雪峰白风车花海步道",
        "purpose": "核心物理互动亮点：噜妹说完许愿台词后轻轻一吹，手中白色蒲公英绒球逐层散作漫天飞舞的伞状种子。",
        "camera": "花径双人全身近中景微推，景深分层展现远方雪峰风车。",
        "start_state": "花海石径上噜妹举着一朵饱满洁白的蒲公英绒球，噜噜在左侧温柔凝望。",
        "action": "噜妹清晰说出对白后轻吹一口气，洁白蒲公英绒球由右向左逐瓣消散，化作数十颗精致白色伞状种子迎风飞起。",
        "end_state": "蒲公英种子漫天飘散，仅留翠绿花托细茎，无缝接下一镜。",
        "kf_prompt": f"9:16 vertical 3D smooth matte vinyl animation on a stone garden path in a cosmos flower meadow with white windmills: {LOCK_LUMEI} holds a fluffy white dandelion puffball near her smiling mouth while {LOCK_LULU} watches lovingly, no text, no logo.",
        "motion_prompt": f"On a sunlit flower path, {LOCK_LUMEI} speaks with 3D lip-sync and blows the white dandelion puffball so dozens of delicate white parachute seeds detach and float into the breeze toward {LOCK_LULU}, no text, no logo.",
    },
    {
        "idx": 6, "id": "SHOT-EP001-006", "motion_id": "MOTION-EP001-006", "scene_id": "EP001-SC002",
        "chapter": 2, "act": "第二章·晴空风车花海", "title": "漫天蒲公英·替你记着心愿",
        "kind": "char_pair", "scene_key": "C2", "beat": "B", "speaker": "噜噜", "voice_mode": "DIALOGUE",
        "line": "你的愿望，我都替你记着。", "sub_display": "噜噜：你的愿望，我都替你记着",
        "place": "雪峰白风车花海步道",
        "purpose": "严格物理连续性衔接：噜妹手中已是吹空的花茎，漫天蒲公英绒毛继续飘过画面，噜噜温柔回应。",
        "camera": "双人中景微推，飘浮的蒲公英种子掠过前景。",
        "start_state": "蒲公英绒球已吹散只剩绿茎，洁白种子在两人周围晴空中轻盈飘浮。",
        "action": "噜噜望着噜妹温柔开口回应，唇形随字音自然张合，蒲公英绒籽在春风中缓缓升腾。",
        "end_state": "两人沐浴在花海暖阳中相视微笑，叠化转入第三章晴雨彩虹谷。",
        "kf_prompt": f"9:16 vertical 3D smooth matte vinyl animation in the windmill flower meadow: white dandelion seeds drift through sunlit air around {LOCK_LULU} speaking warmly and {LOCK_LUMEI} holding the bare green dandelion stem, no text, no logo.",
        "motion_prompt": f"White dandelion seeds float gracefully across the sunlit flower meadow as {LOCK_LULU} speaks affectionately with synchronized 3D lip motion to {LOCK_LUMEI}, no text, no logo.",
    },
    {
        "idx": 7, "id": "SHOT-EP001-007", "motion_id": "MOTION-EP001-007", "scene_id": "EP001-SC003",
        "chapter": 3, "act": "第三章·林涧太阳雨与彩虹", "title": "雨霁山谷瀑布与彩虹桥",
        "kind": "landscape", "scene_key": "L3", "speaker": "噜妹", "voice_mode": "VO",
        "line": "太阳雨后，会有彩虹桥。", "sub_display": "噜妹（独白）：太阳雨后，会有彩虹桥",
        "place": "雨霁彩虹瀑布山谷",
        "purpose": "新海诚/吉卜力式清新雨后峡谷大远景：双道白练飞瀑汇入碧蓝溪流，七彩长虹横跨云谷。",
        "camera": "峡谷高处三维视差缓推，展现前景山花、中景飞瀑碧溪与远景彩虹云朵的纵深感。",
        "start_state": "太阳雨初歇，阳光穿透积云在翠绿峡谷上方架起一道绚丽彩虹，双瀑奔流而下。",
        "action": "洁白瀑布水花飞流直下，碧绿溪水泛起粼粼波光，金色雨雾微粒冉冉升腾，白云轻移。",
        "end_state": "彩虹光晕温润闪耀，自然切入林涧石桥撑伞双人镜。",
        "kf_prompt": "9:16 vertical Makoto Shinkai and Studio Ghibli inspired scenic anime painting of a lush emerald mountain valley right after a sun-shower: twin white waterfalls cascade into a turquoise river, wildflowers on foreground slope, luminous rainbow arching across blue sky and fluffy clouds, no text, no logo.",
        "motion_prompt": "In a lush sunlit mountain canyon after a sun-shower, twin white waterfalls cascade downward into a shimmering turquoise river under a glowing rainbow while clouds drift slowly and camera pushes in, no text, no logo.",
    },
    {
        "idx": 8, "id": "SHOT-EP001-008", "motion_id": "MOTION-EP001-008", "scene_id": "EP001-SC003",
        "chapter": 3, "act": "第三章·林涧太阳雨与彩虹", "title": "林涧石桥·雨伞偏向你头顶",
        "kind": "char_pair", "scene_key": "C3", "beat": "A", "speaker": "噜噜", "voice_mode": "DIALOGUE",
        "line": "下雨啦，快往我怀里躲。", "sub_display": "噜噜：下雨啦，快往我怀里躲",
        "place": "林涧青苔古石桥",
        "purpose": "细节动作还原：金色丁达尔光束穿过太阳雨丝，噜噜撑起透明雨伞特意偏向噜妹头顶，唤她往怀里躲雨。",
        "camera": "石桥双人近中景缓推，逆光太阳雨丝晶莹划过林间。",
        "start_state": "青苔小石桥上落下晶莹太阳雨，噜噜右手举着透明雨伞偏向右侧的噜妹。",
        "action": "纤细雨丝在伞外晶莹飘落，噜噜自然眨眼并温柔开口说话，噜妹闻言开心地向噜噜身旁靠拢。",
        "end_state": "噜妹靠近噜噜伞下怀抱，顺畅切入下一镜温暖依偎。",
        "kf_prompt": f"9:16 vertical 3D smooth matte vinyl animation on a mossy stone footbridge in an emerald forest during a golden sun-shower: {LOCK_LULU} holds a clear transparent umbrella tilted generously over {LOCK_LUMEI}, sunlit raindrops sparkling, no text, no logo.",
        "motion_prompt": f"Under golden sunbeams and sparkling sun-shower raindrops on a forest stone bridge, {LOCK_LULU} holds a clear umbrella over {LOCK_LUMEI}, blinks naturally, and speaks gently as she leans closer, no text, no logo.",
    },
    {
        "idx": 9, "id": "SHOT-EP001-009", "motion_id": "MOTION-EP001-009", "scene_id": "EP001-SC003",
        "chapter": 3, "act": "第三章·林涧太阳雨与彩虹", "title": "伞下依偎·怀里最暖和",
        "kind": "char_pair", "scene_key": "C3", "beat": "B", "speaker": "噜妹", "voice_mode": "DIALOGUE",
        "line": "嘻嘻，噜噜怀里最暖和！", "sub_display": "噜妹：嘻嘻，噜噜怀里最暖和！",
        "place": "林涧青苔古石桥",
        "purpose": "承接躲雨动作：两人共握伞柄依偎在一起，太阳雨渐停化作金色光斑，噜妹笑眼弯弯撒娇回应。",
        "camera": "伞下双人亲密近中景微推，金色暖光包裹两人。",
        "start_state": "同一把透明雨伞下，噜妹亲昵依偎在噜噜肩头，雨势渐疏。",
        "action": "林间飘起温暖金色水雾光斑，噜妹仰起笑脸清晰说出台词，两人轻轻摇晃倍感温馨。",
        "end_state": "雨停晴透、暖意融融，柔和叠化进入第四章橘子海黄昏。",
        "kf_prompt": f"9:16 vertical 3D smooth matte vinyl animation under a clear umbrella on a sunlit forest bridge: {LOCK_LUMEI} snuggles happily against {LOCK_LULU}'s warm shoulder as golden sun-shower mist sparkles around them, no text, no logo.",
        "motion_prompt": f"Under a clear umbrella in golden forest sunlight, {LOCK_LUMEI} snuggles against {LOCK_LULU} and laughs with crisp 3D lip-sync as warm golden bokeh droplets float upward, no text, no logo.",
    },
    {
        "idx": 10, "id": "SHOT-EP001-010", "motion_id": "MOTION-EP001-010", "scene_id": "EP001-SC004",
        "chapter": 4, "act": "第四章·橘子海落日栈道", "title": "橘子海夕阳与木栈道",
        "kind": "landscape", "scene_key": "L4", "speaker": "噜噜", "voice_mode": "VO",
        "line": "晚风带着我们到了海边。", "sub_display": "噜噜（独白）：晚风带着我们到了海边",
        "place": "落日橘子海木栈道",
        "purpose": "全片暖色高潮空镜：漫天橙红晚霞将整片大海染成温柔的橘子汽水色，海浪轻拍海岸。",
        "camera": "顺着海滨木栈道向天际线落日与金色海浪平稳推进。",
        "start_state": "夕阳悬于海天交界，万顷碧波被晚霞染成璀璨金橘色。",
        "action": "金色海浪层层涌向沙滩泛起碎金波光，海鸟掠过晚霞天空。",
        "end_state": "橘色余晖铺满木栈道栏杆，自然切入看海双人镜。",
        "kf_prompt": "9:16 vertical 3D animated golden-hour coastal landscape: a glowing tangerine sunset reflects across gentle ocean waves beside a warm wooden seaside boardwalk, seagulls gliding in amber sky, no text, no logo.",
        "motion_prompt": "Along a sunlit wooden seaside boardwalk at golden sunset in 9:16 vertical 3D animation, tangerine-orange ocean waves roll gently with sparkling golden reflections as camera glides forward, no text, no logo.",
    },
    {
        "idx": 11, "id": "SHOT-EP001-011", "motion_id": "MOTION-EP001-011", "scene_id": "EP001-SC004",
        "chapter": 4, "act": "第四章·橘子海落日栈道", "title": "凭栏远眺·大海变橘子味啦",
        "kind": "char_pair", "scene_key": "C4", "beat": "A", "speaker": "噜妹", "voice_mode": "DIALOGUE",
        "line": "快看，大海变橘子味啦！", "sub_display": "噜妹：快看，大海变橘子味啦！",
        "place": "落日橘子海木栈道",
        "purpose": "趣味台词与动作呼应：噜妹兴奋伸手指着金灿灿的夕阳海面（呼应噜噜头顶的小橘子！），海面碎金闪烁。",
        "camera": "木栈道栏杆双人近中景，逆光金橘色海面波光粼粼。",
        "start_state": "海边木栏杆前，噜妹兴奋地伸出手臂指向远方金橘色大海，噜噜在身旁温柔注视。",
        "action": "背后橘子海波光跃动、晚风拂起金色微尘，噜妹手指海面雀跃开口说出台词。",
        "end_state": "两人沐浴在金色夕阳里笑意盈盈，切入下一镜揽肩承诺。",
        "kf_prompt": f"9:16 vertical 3D smooth matte vinyl animation on a wooden seaside boardwalk at golden tangerine sunset: {LOCK_LUMEI} points excitedly toward the shimmering orange ocean while {LOCK_LULU} smiles warmly beside her, no text, no logo.",
        "motion_prompt": f"At a golden tangerine sunset boardwalk, {LOCK_LUMEI} points joyfully at the sparkling orange sea and speaks with 3D lip-sync while warm sea-breeze light motes drift past {LOCK_LULU}, no text, no logo.",
    },
    {
        "idx": 12, "id": "SHOT-EP001-012", "motion_id": "MOTION-EP001-012", "scene_id": "EP001-SC004",
        "chapter": 4, "act": "第四章·橘子海落日栈道", "title": "夕阳揽肩·每个黄昏陪你看海",
        "kind": "char_pair", "scene_key": "C4", "beat": "B", "speaker": "噜噜", "voice_mode": "DIALOGUE",
        "line": "每个黄昏，都陪你看海。", "sub_display": "噜噜：每个黄昏，都陪你看海",
        "place": "落日橘子海木栈道",
        "purpose": "第四章温情收束：噜噜伸手轻轻揽住噜妹肩膀并肩看海，许下陪伴诺言。",
        "camera": "夕阳逆光双人近景微推，金色轮廓光温暖柔和。",
        "start_state": "橘色落日余晖里，噜噜温暖地揽着噜妹的肩膀并肩站在木栈道旁。",
        "action": "海面碎金闪烁，噜噜自然眨眼并温柔说出承诺台词，噜妹闭眼幸福微笑。",
        "end_state": "暮色渐深，橘红晚霞柔和过渡至第五章璀璨星夜灯火。",
        "kf_prompt": f"9:16 vertical 3D smooth matte vinyl animation at golden sunset by the sea: {LOCK_LULU} wraps his arm gently around {LOCK_LUMEI}'s shoulder as they watch the glowing tangerine ocean together, warm rim light, no text, no logo.",
        "motion_prompt": f"By the glowing sunset sea, {LOCK_LULU} holds {LOCK_LUMEI} warmly around the shoulder, blinks naturally, and speaks affectionately with 3D lip-sync as ocean glints shimmer behind them, no text, no logo.",
    },
    {
        "idx": 13, "id": "SHOT-EP001-013", "motion_id": "MOTION-EP001-013", "scene_id": "EP001-SC005",
        "chapter": 5, "act": "第五章·万灯星河与烟花收束", "title": "千盏水灯汇入璀璨星河",
        "kind": "landscape", "scene_key": "L5", "speaker": "噜妹", "voice_mode": "VO",
        "line": "万千灯火，都飘向星河啦。", "sub_display": "噜妹（独白）：万千灯火，都飘向星河啦",
        "place": "星夜千灯河谷与观星露台",
        "purpose": "入夜仪式感大远景：无数温暖金色河灯与孔明灯汇成流淌在地上的星河，与第一章首尾呼应。",
        "camera": "贴近暖金灯河缓推并微仰，展现万灯升空与璀璨银河相连。",
        "start_state": "夜幕降临，水面上千盏暖金色莲花河灯与升空的孔明灯交相辉映。",
        "action": "盏盏明灯随清波缓缓漂流、冉冉升向繁星夜空，水中金色倒影荡漾。",
        "end_state": "灯火与银河融为一体，切入山顶观星木露台碰杯。",
        "kf_prompt": "9:16 vertical 3D animated magical night landscape: thousands of glowing golden river lanterns drift along a calm waterway while sky lanterns rise toward a starry Milky Way sky, warm reflections, no text, no logo.",
        "motion_prompt": "Under a starry Milky Way night sky in 9:16 vertical 3D animation, glowing golden river lanterns float gently along the water and sky lanterns drift upward into the stars, no text, no logo.",
    },
    {
        "idx": 14, "id": "SHOT-EP001-014", "motion_id": "MOTION-EP001-014", "scene_id": "EP001-SC005",
        "chapter": 5, "act": "第五章·万灯星河与烟花收束", "title": "星夜木露台·热可可碰杯",
        "kind": "char_pair", "scene_key": "C5", "beat": "A", "speaker": "噜妹", "voice_mode": "DIALOGUE",
        "line": "敬我们一起走过的山海！", "sub_display": "噜妹：敬我们一起走过的山海！",
        "place": "星夜千灯河谷与观星露台",
        "purpose": "终章仪式互动（户外串灯观星木露台，清爽温馨）：两人手捧冒着袅袅白气的棉花糖热可可举杯相庆。",
        "camera": "璀璨银河与暖黄串灯木露台双人中景缓推至近景碰杯。",
        "start_state": "繁星银河下的串灯木露台上，噜噜与噜妹各自端着温暖的棉花糖热可可马克杯相视而立。",
        "action": "杯口升起袅袅白色热气，噜妹自然眨眼、开心说出祝酒词并轻轻举高马克杯与噜噜相碰。",
        "end_state": "两只马克杯温暖相碰发出清脆瓷响，顺势推进终章烟花特写。",
        "kf_prompt": f"9:16 vertical 3D smooth matte vinyl animation on a fairy-lit wooden mountain terrace under a vivid Milky Way starry sky: {LOCK_LULU} and {LOCK_LUMEI} toast warm ceramic mugs of marshmallow hot cocoa with rising steam, no text, no logo.",
        "motion_prompt": f"On a fairy-lit wooden terrace under the Milky Way, {LOCK_LUMEI} speaks cheerfully with 3D lip-sync, blinks, and raises her steaming hot cocoa mug to clink with {LOCK_LULU}, no text, no logo.",
    },
    {
        "idx": 15, "id": "SHOT-EP001-015", "motion_id": "MOTION-EP001-015", "scene_id": "EP001-SC005",
        "chapter": 5, "act": "第五章·万灯星河与烟花收束", "title": "璀璨烟花·岁岁年年在你身边",
        "kind": "char_pair", "scene_key": "C5", "beat": "B", "speaker": "噜噜", "voice_mode": "DIALOGUE",
        "line": "岁岁年年，都在你身边。", "sub_display": "噜噜：岁岁年年，都在你身边",
        "place": "星夜千灯河谷与观星露台",
        "purpose": "全片 60.00s 圆满情感收官：漫天金色烟花在夜空绽放，两人脸贴脸依偎许下岁岁年年的陪伴。",
        "camera": "双人温馨近景稳稳推近定格，夜空烟花绚烂绽放后柔和渐暗收束。",
        "start_state": "串灯露台夜空中第一簇金色烟花绚丽绽放，噜噜与噜妹亲昵依偎在一起。",
        "action": "漫天暖金色烟花依次升空绽放点亮星空，热可可余温袅袅，噜噜眉眼弯弯说出收官台词，噜妹闭眼幸福依偎。",
        "end_state": "60.00 秒星河烟花余晖温柔包裹两人，圆满渐隐。",
        "kf_prompt": f"9:16 vertical 3D smooth matte vinyl animation heartwarming close-up finale on a fairy-lit wooden terrace with golden fireworks blooming across the starry sky: {LOCK_LULU} laughs warmly with his arm around {LOCK_LUMEI} cuddling happily, no text, no logo.",
        "motion_prompt": f"Under blooming golden fireworks on a starry wooden terrace, {LOCK_LULU} speaks affectionately with synchronized 3D lip motion while cuddling {LOCK_LUMEI} before a gentle cinema fade-out, no text, no logo.",
    },
]

scenes_meta = [
    ("EP001-SC001", "外/内 · 破晓云海石拱桥与复古暖阳木车厢 · 晨", [1, 2, 3]),
    ("EP001-SC002", "外 · 雪峰白风车与格桑花海步道 · 日", [4, 5, 6]),
    ("EP001-SC003", "外 · 雨霁彩虹瀑布山谷与林涧青苔古石桥 · 午后晴雨", [7, 8, 9]),
    ("EP001-SC004", "外 · 落日橘子海木栈道 · 黄昏", [10, 11, 12]),
    ("EP001-SC005", "外 · 星夜千灯河谷与观星木露台 · 星夜", [13, 14, 15]),
]

script_lines = ["# EP001 · 山海寻光记：赴一场四季星河\n"]
for sc_id, sc_title, s_nums in scenes_meta:
    script_lines.append(f"## {sc_id} {sc_title}\n")
    for n in s_nums:
        s = SHOTS[n - 1]
        script_lines.append(f"{s['start_state']}{s['action']}\n")
        if s["voice_mode"] == "VO":
            script_lines.append(f"[VO] {s['speaker']}：{s['line']}\n")
        else:
            script_lines.append(f"{s['speaker']}：{s['line']}\n")
(EP / "剧本.md").write_text("\n".join(script_lines), encoding="utf-8")

char_shot_ids = "、".join(s["id"] for s in SHOTS if s["kind"] == "char_pair")
places = []
for s in SHOTS:
    if s["place"] not in places:
        places.append(s["place"])

vis_lines = [
    "# EP001 视觉设定\n",
    "- 制作形态：正版多爱 3D 搪胶黏土质感治愈系动态漫剧，竖屏 9:16（1080×1920 · 24fps）。",
    "- 视觉世界观：电影级自然风景（破晓云海 → 雪峰风车花海 → 雨霁彩虹飞瀑 → 橘子海落日 → 星夜千灯烟花）与 100% 还原正版多爱 3D 哑光圆润水豚角色无缝融合。\n",
    "## 人物 · 噜噜\n",
    "- 正版多爱 3D 哑光金黄色圆润水豚男孩，面部极其光滑饱满（无鼻孔），乌黑发亮的小圆豆眼，吻部泛着温暖橘色红晕，头顶稳稳顶着一颗带绿叶的小巧橙色橘子。",
    "- 本集造型：经典暖棕色短裤，体态敦实憨厚，说话时唇形、点头与眨眼自然生动。",
    "- 识别锚点：金黄哑光搪胶圆脸（无鼻孔）、暖橘色吻部晕染、头顶带叶小橘子、暖棕色短裤。",
    "- 画面代称：Lulu",
    "- 声音参考：设定集/voices/ref_lulu_clean.flac（纯净无伴奏干声切片 + 5-Seed F5-TTS + 48-Step Seed-VC 双模式优选）",
    f"- 连续性锁：LOCK-LULU-DUOAI《噜噜正版3D金黄橘子造型》（镜头：{char_shot_ids}；图片提示词项：IMG-LULU-SHEET）· 锁面：{LOCK_LULU}\n",
    "## 人物 · 噜妹\n",
    "- 正版多爱 3D 哑光奶黄色圆润水豚女孩，比噜噜略娇小，面部光滑圆润（无鼻孔）配粉嫩圆腮红，乌黑灵动圆眼。",
    "- 本集造型：环绕头部的白色荷叶花边软帽、头顶扁圆暖黄小饼帽长出两片嫩绿小芽，身穿浅樱花粉翻领短袖连衣裙。",
    "- 识别锚点：奶黄哑光圆脸（无鼻孔）、白色荷叶花边双叶嫩芽小饼帽、浅粉色翻领连衣裙。",
    "- 画面代称：Lumei",
    "- 声音参考：设定集/voices/ref_lumei_clean.flac（纯净无伴奏干声切片 + 5-Seed F5-TTS + 48-Step Seed-VC 双模式优选）",
    f"- 连续性锁：LOCK-LUMEI-DUOAI《噜妹正版3D嫩芽粉裙造型》（镜头：{char_shot_ids}；图片提示词项：IMG-LUMEI-SHEET）· 锁面：{LOCK_LUMEI}\n",
]
for pl in places:
    vis_lines.append(f"## 地点 · {pl}\n")
    vis_lines.append(f"- 3D 电影级治愈风景与温馨旅途空间锚点：{pl}，保持细腻体积光与统一色温递进。")
    vis_lines.append(f"- 识别锚点：{pl}标志性地貌/光影与当章情绪色温严格一致。\n")
(EP / "视觉设定.md").write_text("\n".join(vis_lines), encoding="utf-8")

img_lines = [
    "# EP001 图片提示词\n",
    "## IMG-LULU-SHEET · 噜噜角色设定板\n",
    "- 用途：100% 锁定噜噜跨全片 10 个角色镜头的正版多爱 3D 哑光搪胶脸型（无鼻孔）、头顶小橘子与棕色短裤。",
    "- 参考：REF-CHAR-SHEET（顺序：1）· 设定集/characters/canonical_duoai_sheet.png《多爱噜噜噜妹正版3D官方基准图》（用途：身份；控制：精确五官、无鼻孔圆吻部、头饰与服饰；不得控制：背景）。\n",
    "### 可复制提示词",
    f"> Canonical 3D turnaround sheet of {LOCK_LULU}, clean studio lighting, smooth matte vinyl-clay surface, no nostrils, no text, no logo.\n",
    "## IMG-LUMEI-SHEET · 噜妹角色设定板\n",
    "- 用途：100% 锁定噜妹跨全片 10 个角色镜头的正版多爱 3D 奶黄圆脸（无鼻孔）、白色荷叶边双叶嫩芽帽与粉色连衣裙。",
    "- 参考：REF-CHAR-SHEET（顺序：1）· 设定集/characters/canonical_duoai_sheet.png《多爱噜噜噜妹正版3D官方基准图》（用途：身份；控制：精确五官、无鼻孔圆吻部、荷叶边嫩芽帽与粉裙；不得控制：背景）。\n",
    "### 可复制提示词",
    f"> Canonical 3D turnaround sheet of {LOCK_LUMEI}, clean studio lighting, smooth matte vinyl-clay surface, no nostrils, no text, no logo.\n",
]
for s in SHOTS:
    img_id = f"IMG-S{s['idx']:02d}-PLATE"
    img_lines.append(f"## {img_id} · {s['title']}关键帧母版\n")
    img_lines.append(f"- 用途：作为 {s['id']} 的 9:16 冻结起始帧与空间光色锚点。")
    if s["kind"] == "char_pair":
        img_lines.append("- 参考：REF-CHAR-SHEET（顺序：1）· 设定集/characters/canonical_duoai_sheet.png《多爱噜噜噜妹正版3D官方基准图》（用途：身份；控制：双人正版3D角色外观与比例；不得控制：自然场景地貌）。\n")
    else:
        img_lines.append("- 参考：无外部参考；保持全片统一高画质治愈系动画风景美学。\n")
    img_lines.append("### 可复制提示词")
    img_lines.append(f"> {s['kf_prompt']}\n")
(EP / "图片提示词.md").write_text("\n".join(img_lines), encoding="utf-8")

sb_lines = ["# EP001 分镜\n"]
for sc_id, sc_title, s_nums in scenes_meta:
    sb_lines.append(f"## 场景站位 · {sc_id} · {sc_title}")
    sb_lines.append("- 固定锚点：自然远景天际线与主光源方向恒定；双人同框时噜噜居左、噜妹居右，轴线严格恒定不跳轴")
    sb_lines.append("- 人物：噜噜居左护持位，噜妹居右互动位；每章首镜为纯风景空镜建立空间与呼吸感")
    sb_lines.append("- 轴线：噜噜（左） ↔ 噜妹（右）双人正面微弧机位；working side：朝向镜头受光面")
    sb_lines.append("- 变化：随破晓金云、晴昼花海、午后晴雨彩虹、落日橘海至星夜烟花平滑递进\n")

for s in SHOTS:
    img_id = f"IMG-S{s['idx']:02d}-PLATE"
    kf_rel = f"设定集/keyframes/s{s['idx']:02d}.jpg"
    sb_lines.append(f"## {s['id']} · {s['title']}\n")
    sb_lines.append(f"- 来源：{s['scene_id']}")
    sb_lines.append("- 时长：4s")
    sb_lines.append(f"- 目的：{s['purpose']}")
    sb_lines.append(f"- 景别/机位：9:16 竖屏{'大远景纯风景镜头' if s['kind'] != 'char_pair' else '双人正版3D互动中近景'}。")
    sb_lines.append(f"- 运镜：{s['camera']}")
    sb_lines.append(f"- 起点：{s['start_state']}")
    sb_lines.append(f"- 唯一动作：{s['action']}")
    sb_lines.append(f"- 终点：{s['end_state']}")
    if s["kind"] == "char_pair":
        sb_lines.append(f"- 图片提示词项：IMG-LULU-SHEET《噜噜角色设定板》（控制：身份、造型）；IMG-LUMEI-SHEET《噜妹角色设定板》（控制：身份、造型）；{img_id}《{s['title']}关键帧母版》（控制：构图、光色）。")
        sb_lines.append(f"- 视觉依据：《视觉设定.md》·人物「噜噜」（控制：身份、本集造型）；人物「噜妹」（控制：身份、本集造型）；地点「{s['place']}」（控制：空间地理与光色）。")
    else:
        sb_lines.append(f"- 图片提示词项：{img_id}《{s['title']}关键帧母版》（控制：地貌构图、大气光效）。")
        sb_lines.append(f"- 视觉依据：《视觉设定.md》·地点「{s['place']}」（控制：自然地貌、光影氛围）。")
    sb_lines.append(f"- 输入参考图：REF-KF-{s['idx']:02d}（顺序：1）· {kf_rel}《{s['title']}起始帧》（用途：起始帧；控制：构图、地理、造型状态；不得控制：无）。")
    sb_lines.append(f"- 声音：{'画外独白' if s['voice_mode'] == 'VO' else '角色同期对白'}（{s['speaker']}）配自然环境声与治愈配乐铺底。\n")
    sb_lines.append("### 冻结关键帧提示词")
    sb_lines.append(f"> {s['kf_prompt']}\n")
(EP / "分镜.md").write_text("\n".join(sb_lines), encoding="utf-8")

vp_lines = ["# EP001 视频提示词\n"]
for s in SHOTS:
    kf_rel = f"设定集/keyframes/s{s['idx']:02d}.jpg"
    ref_line = f"REF-KF-{s['idx']:02d}（顺序：1）· {kf_rel}《{s['title']}起始帧》（用途：起始帧；控制：构图、地理、造型状态；不得控制：无）。"
    vp_lines.append(f"## {s['motion_id']} · {s['title']}\n")
    vp_lines.append(f"- 分镜：{s['id']}")
    vp_lines.append("- 时长：4s")
    vp_lines.append("- 生成方式：图生视频")
    vp_lines.append(f"- 输入参考图：{ref_line}")
    vp_lines.append(f"- 静态视觉锚点：{s['kf_prompt']}")
    vp_lines.append(f"- 起始帧：{s['start_state']}")
    vp_lines.append(f"- 状态链：{s['start_state']} → {s['action']} → {s['end_state']}")
    vp_lines.append(f"- 终点：{s['end_state']}\n")
    vp_lines.append("### 可复制提示词")
    vp_lines.append(f"> {s['motion_prompt']} No subtitles, captions or text overlays at any moment, no watermark.\n")
(EP / "视频提示词.md").write_text("\n".join(vp_lines), encoding="utf-8")

manifest = {
    "project_id": "SD-19E24D7D9AE8",
    "title": "山海寻光记：赴一场四季星河（正版形象还原精制版）",
    "episode": "EP001",
    "target_seconds": 60.0,
    "fps": 24,
    "total_frames": 1440,
    "width": 1080,
    "height": 1920,
    "shots": SHOTS,
}
(PROJ / "episode_manifest_60s.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
print("Generated all 5 v2 Creator-First documents + episode_manifest_60s.json!")
