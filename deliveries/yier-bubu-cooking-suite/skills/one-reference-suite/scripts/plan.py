"""Host-native tool planner; no API keys, external requests or implicit paid calls."""
from pathlib import Path
from PIL import Image
import json,hashlib,argparse
SLOTS=[
 ('01-phone','9:16 portrait phone','full cozy scene, top 40 percent calm clock-safe background'),
 ('02-desktop','16:9 landscape desktop','redraw panoramic room, subjects right, left 40 percent icon-safe negative space'),
 ('03-ipad-landscape','4:3 landscape tablet','redraw full scene, subjects lower right, left half for icons'),
 ('04-ipad-portrait','3:4 portrait tablet','full scene, upper 40 percent clear, whole heads and paws'),
 ('05-watch','1:1 square watch','medium close-up of visible subjects lower 60 percent, top third calm clock-safe area'),
 ('06-avatar-a','1:1 square individual avatar A','native head-and-shoulders close-up, face large, entire ears/head/chin with 12 percent margin, facing right, small affectionate gesture'),
 ('07-avatar-b','1:1 square individual avatar B','native head-and-shoulders close-up, face large, entire ears/head/chin with 12 percent margin, facing left, complementary affectionate gesture'),
 ('08-moments','2:1 panoramic social header','subjects center-left, right bottom quarter free of faces for profile avatar'),
 ('09-qq-profile','16:9 social profile header','subjects right half, left third calm for profile information'),
 ('10-chat','9:16 portrait chat wallpaper','middle and upper 70 percent pale low-contrast, small subjects at bottom right only'),
]
def build(reference,profile,out):
 reference=Path(reference).resolve();out=Path(out).resolve()
 with Image.open(reference) as im:size=list(im.size);im.verify()
 entities=profile.get('visible_entities',[])
 if not entities or any(not e.get('id') or not e.get('locked') for e in entities):raise ValueError('Vision analysis must provide visible_entities with id and locked anchors')
 if not profile.get('style_locked'):raise ValueError('style_locked required from actual image inspection')
 if profile.get('input_kind') not in ['avatar','wallpaper','ui_screenshot','other']:raise ValueError('input_kind must be visually classified')
 if reference.is_relative_to(out):raise ValueError('Output must not contain or overwrite the input')
 out.mkdir(parents=True,exist_ok=True)
 if (out/'tool_jobs.json').exists():raise FileExistsError('New output folder required; refusing to overwrite prior plan')
 jobs=[]
 for key,ratio,layout in SLOTS:
  selected=entities
  if key=='06-avatar-a':selected=[entities[0]]
  if key=='07-avatar-b':selected=[entities[1] if len(entities)>1 else entities[0]]
  anchors='; '.join(e['id']+': '+', '.join(e['locked']) for e in selected)
  prompt=f"ONE standalone {ratio} illustration. Use ONLY attached original as identity/style truth. Preserve: {anchors}. Style: {profile['style_locked']}. Purpose composition: {layout}. Scene/context: {profile.get('scene_adaptation','simple coordinated setting inferred only where not visible')}. Allowed modifications: {profile.get('allowed_changes','pose, framing, minor props appropriate to use')}. No tiny face crop enlargement, no portrait stretched into landscape, no collage, no text or UI. All heads/ears intact. Maximum available native resolution. Unseen details are plausible adaptations, not recovered original facts."
  jobs.append(dict(slot=key,selected_entities=[e['id'] for e in selected],status='planned_not_dispatched',tool='generate_image',arguments=dict(file_path=str(out/'masters'/f'{key}.png'),prompt=prompt,images=[str(reference)],offer_options=False)))
 doc=dict(reference=str(reference),reference_md5=hashlib.md5(reference.read_bytes()).hexdigest(),reference_size=size,profile=profile,call_budget=10,one_subject_pair_policy='Same visible identity twice with complementary poses; never invent unseen partner identity',jobs=jobs)
 (out/'tool_jobs.json').write_text(json.dumps(doc,ensure_ascii=False,indent=2));return doc
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--reference',required=True);p.add_argument('--profile',required=True);p.add_argument('--out',required=True);a=p.parse_args();doc=build(a.reference,json.loads(Path(a.profile).read_text()),a.out);print(f"PLANNED {len(doc['jobs'])} host tool calls; no generation dispatched")
