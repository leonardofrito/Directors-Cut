"""Second Take: source performance plus replacement identity, through local H3."""
import hashlib
import math
import re
import copy
import shutil
import uuid
from pathlib import Path

from .storage import now
from .motion_reference import MAX_VIDEO, run_ffmpeg

APP = 'second-take'
LORA = 'minimax_h3_motion_transfer_tara_v1.0_ref2va.safetensors'
MODES = {
    'motion':dict(code='M',label='Motion Transfer',lora=LORA),
    'character-1':dict(code='C1',label='Character Swap 1',lora='h3_character_swap_v1.5.safetensors'),
    'character-2':dict(code='C2',label='Character Swap 2',lora='minimax_h3_character_swap_v1.1_ref2va_fro.safetensors'),
}

def mode(data):
    selected=data.get('swap_mode')
    if not selected:
        selected=next((key for key,row in MODES.items() if key!='motion' and any(l.get('name')==row['lora'] for l in data.get('loras',[]) if isinstance(l,dict))),'motion')
    if selected not in MODES:raise ValueError('Choose Motion Transfer, Character Swap 1 or Character Swap 2.')
    return selected

def modes():
    return [dict(id=key,**row) for key,row in MODES.items()]
WORKSPACE = '_SecondTake'
MAX_REFERENCES=6
PROMPT_TAIL=("Preserve the source performance, timing, camera and all unassigned scene elements. "
    "Use each assigned reference for its replacement identity and complete three-dimensional design; ignore unassigned photo backgrounds and collage layouts. "
    "Replace the entire requested target, including its silhouette and structure, not only its color or texture. "
    "Requested replacements override preservation of the original target. Keep each replacement stable from the first frame to the last.")

def default_direction(project,refs,mapping=None,people=()):
    assets={a['id']:a for a in project.get('assets',[])};lines=[]
    pairs=list((mapping or {}).items()) or [(f'p{i+1}',ident) for i,ident in enumerate(refs)]
    for person_id,ident in pairs:
        asset=assets.get(ident)
        if not asset:continue
        person=next((p for p in people if p['id']==person_id),{})
        label=re.sub(r'^<Subject\s*\d+>\s*[-:]?\s*','',person.get('label',''),flags=re.I).strip() if person.get('matched') else ''
        if asset.get('kind')=='character':
            label=label or ('main foreground person' if len(lines)==0 else 'selected person '+person_id.lstrip('pu'))
            lines.append(f"Replace the original {label} in @video1 with @{asset['handle']}, including their face, hair, body and complete outfit.")
        else:
            lines.append(f"Replace the corresponding source object in @video1 with @{asset['handle']}, using its full shape, proportions, materials and structure. Use the original object only for its motion and placement.")
    return '\n'.join([*lines,PROMPT_TAIL])


def session(store):
    """An application-owned workspace, never a user-visible project."""
    if store.file(WORKSPACE, 'project.json').exists():
        return store.load(WORKSPACE)
    target = dict(id=WORKSPACE, name='Second Take', system_workspace=APP,
                  created_at=now(), shots=[], assets=[], swap_sources=[], storyboard=[])
    # Preserve trials from the previous project-scoped UI. Originals are untouched.
    for source in store.list():
        shots = [s for s in source['shots'] if s.get('studio_app') == APP]
        if not shots:
            continue
        if any(d['status'] in ('queued','submitting','running','pending','downloading') for s in shots for d in s['drafts']):
            raise ValueError('Finish the existing character-swap queue before opening Second Take.')
        def preserve(value):
            if isinstance(value, list):
                return [preserve(v) for v in value]
            if not isinstance(value, dict):
                return value
            result = {}
            for key, item in value.items():
                if key in ('file','thumbnail','workflow') and isinstance(item, str) and store.file(source['id'], item).is_file():
                    relative = f"imported/{source['id']}/{item}"
                    destination = store.file(WORKSPACE, relative)
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(store.file(source['id'], item), destination)
                    result[key] = relative
                else:
                    result[key] = preserve(item)
            return result
        ids = {i for shot in shots for i in shot.get('reference_ids', [])}
        ids.update(i for shot in shots for d in shot['drafts'] for i in d.get('settings',{}).get('reference_ids',[]))
        target['assets'].extend(preserve(a) for a in source.get('assets',[]) if a['id'] in ids)
        target['swap_sources'].extend(preserve(s) for s in source.get('swap_sources',[]))
        for shot in shots:
            saved = preserve(copy.deepcopy(shot))
            saved['id'] = f"shot_{len(target['shots'])+1:03d}"
            target['shots'].append(saved)
    store.save(target)
    return target


def all_assets(store):
    return [dict(a, source_project=p['id'], project_name=p['name']) for p in store.list()
            if not p.get('system_workspace') for a in p.get('assets', []) if a.get('file') and not a.get('members')]


def select_asset(store, source_id, asset_id):
    """Copy a chosen revision, keeping old takes independent of later edits/deletes."""
    from .assets import add_asset
    source = store.load(source_id)
    asset = next((a for a in source.get('assets',[]) if a['id'] == asset_id and a.get('file') and not a.get('members')), None)
    if source.get('system_workspace') or asset is None:
        raise ValueError('Choose an asset from Asset Creation.')
    content = store.file(source_id, asset['file']).read_bytes()
    digest = hashlib.sha256(content).hexdigest()
    project = session(store)
    origin = dict(project=source_id, asset=asset_id, digest=digest)
    cached = next((a for a in project['assets'] if a.get('swap_origin') == origin), None)
    if cached is None:
        cached = add_asset(store, project, content, asset['name'], asset['kind'], asset.get('description',''))
        cached['swap_origin'] = origin
        store.save(project)
    return dict(asset=cached, project=project)


def prompt(accessory=False):
    text = ('Replace the main foreground person in <Video 1> with the character in <Picture 1>. '
            'Keep the reference character identity, face, hair, body proportions and clothing. '
            'Follow the original performer pose, gestures, expression, gaze and movement throughout the video. '
            'Preserve the original scene, other people, objects, lighting, camera movement, framing, timing and cuts. '
            'Replace only this one person. Do not add another copy of the character. '
            'The studio background of <Picture 1> is not part of the scene.')
    if accessory:
        text += (' Add the accessory from <Picture 2> to the replacement character, preserving its design '
                 'and attaching it naturally to the character. Its image background is not part of the scene.')
    return text


def settings(data):
    from . import video
    selected_mode=mode(data)
    if video.model_preset(data)=='hyperflow':
        raise ValueError('HyperFlow does not support Character Swap. Choose Base or OmniRef.')
    refs = data.get('reference_ids', [])
    if not isinstance(refs, list) or not all(isinstance(r,str) for r in refs) or len(refs) > MAX_REFERENCES or len(refs) != len(set(refs)):
        raise ValueError('Choose up to six character, product or clothing references.')
    roles=data.get('swap_roles', (['character']+['accessory']*(len(refs)-1)) if refs else [])
    enabled=data.get('swap_direction_enabled',False)
    direction=data.get('swap_direction','')
    if not isinstance(roles,list) or len(roles)!=len(refs) or any(r not in ('character','product','clothes','accessory','background') for r in roles) or roles.count('background')>1:
        raise ValueError('Choose a role for each reference.')
    if isinstance(roles,list) and 'background' in roles:
        keep=[i for i,role in enumerate(roles) if role!='background']
        refs=[refs[i] for i in keep];roles=[roles[i] for i in keep]
        data={**data,'reference_ids':refs};direction='';enabled=False
    if not isinstance(enabled,bool) or not isinstance(direction,str) or len(direction)>20000:
        raise ValueError('Direction must be at most 20,000 characters.')
    source = data.get('swap_source_id', '')
    if not isinstance(source, str) or source and not re.fullmatch('[a-f0-9]{32}', source):
        raise ValueError('Choose a source video.')
    full = data.get('swap_full_duration', True)
    start, end = data.get('swap_start', 0), data.get('swap_end', 5)
    if not isinstance(full, bool) or any(isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x) for x in (start, end)) or start < 0 or end <= start:
        raise ValueError('Choose a valid video range.')
    base = {**data, 'duration': 5, 'prompt': prompt(len(refs) == 2),
            'selflift': data.get('selflift', True), 'prompt_enhancer': data.get('prompt_enhancer',False), 'video_direction': {},
            'motion_reference_id': '', 'audio_reference_id': '', 'output_audio_id': '',
            'loras': [dict(name=MODES[selected_mode]['lora'], strength=1, enabled=True)]}
    base.pop('studio_app', None)
    result = video.settings(base)
    result['swap_mode']=selected_mode
    reviewed=data.get('swap_cuts_reviewed',False)
    candidates=data.get('swap_cut_candidates',[])
    if not isinstance(reviewed,bool) or not isinstance(candidates,list) or len(candidates)>720:
        raise ValueError('Invalid reviewed video cuts.')
    for cut in candidates:
        if not isinstance(cut,dict) or set(cut)!={'frame','accepted'} or type(cut['frame']) is not int or cut['frame']<0 or not isinstance(cut['accepted'],bool):
            raise ValueError('Invalid reviewed cut marker.')
    if len({c['frame'] for c in candidates})!=len(candidates):raise ValueError('Duplicate video cut marker.')
    review_start,review_end=data.get('swap_cut_review_start'),data.get('swap_cut_review_end')
    if reviewed and (type(review_start) is not int or type(review_end) is not int or review_start<0 or review_end<=review_start):
        raise ValueError('Review cuts for the selected trim range.')
    if reviewed and any(not review_start<c['frame']<review_end for c in candidates):raise ValueError('Cut marker outside the reviewed trim.')
    result.update(swap_cuts_reviewed=reviewed,swap_cut_candidates=sorted(candidates,key=lambda c:c['frame']),
                  swap_cut_review_start=review_start,swap_cut_review_end=review_end)
    # New TARA edits use the source clip directly, without person detection.
    analysis='';mapping={}
    if not isinstance(analysis,str) or analysis and not re.fullmatch('[a-f0-9]{32}',analysis) or not isinstance(mapping,dict) or len(mapping)>MAX_REFERENCES or any(not isinstance(k,str) or not re.fullmatch('[pu][0-9]+',k) or v not in refs for k,v in mapping.items()):raise ValueError('Invalid person mapping.')
    ignored=[]
    if not isinstance(ignored,list) or len(ignored)>100 or any(not isinstance(i,str) or not re.fullmatch(r'[pu][0-9]+',i) for i in ignored):raise ValueError('Invalid ignored detections.')
    if any(i in mapping for i in ignored):raise ValueError('An ignored detection cannot have a replacement.')
    if data.get('swap_manual_targets'):raise ValueError('Object replacement has been removed. Select people again before generating.')
    result.update(swap_ignored_people=list(dict.fromkeys(ignored)))
    # Old take snapshots may request neutralization. New generations always use
    # the original source video, including after Reuse Settings.
    result.update(swap_analysis_id=analysis,swap_people_map=mapping,swap_neutralize=False)
    result.update(studio_app=APP, swap_source_id=source, swap_full_duration=full,
                  swap_start=float(start), swap_end=float(end),swap_roles=roles,swap_direction_enabled=enabled,swap_direction=direction)
    return result


def resolve(project, settings, store=None):
    source = next((r for r in project.get('swap_sources', []) if r['id'] == settings['swap_source_id']), None)
    if not source:
        raise ValueError('Add a source video first.')
    refs = settings['reference_ids']
    if not refs or not any(a['id'] == refs[0] and a.get('file') for a in project.get('assets', [])):
        raise ValueError('Choose a replacement character first.')
    start = 0 if settings['swap_full_duration'] else settings['swap_start']
    end = source['duration'] if settings['swap_full_duration'] else settings['swap_end']
    validate_range(source['duration'],start,end)
    duration = round((min(end, source['duration']) - start) * 24) / 24
    settings.update(duration=duration, swap_start=start, swap_end=start+duration,
                    swap_source=dict(source), swap_ratio=f"{source['width']}:{source['height']}")
    if settings.get('swap_cuts_reviewed') and (settings['swap_cut_review_start']!=round(start*24) or settings['swap_cut_review_end']!=round((start+duration)*24)):
        raise ValueError('The trim changed. Open Adjust Trim and review its cuts again.')
    roles=settings['swap_roles']
    assets={a['id']:a for a in project.get('assets',[])}
    if any(ident not in assets or not assets[ident].get('file') for ident in refs):
        raise ValueError('A selected reference is no longer available.')
    bindings={assets[ident]['handle'].casefold():f'<Picture {i+1}>' for i,ident in enumerate(refs)}
    mapping=settings.get('swap_people_map',{});people=[]
    if settings.get('swap_analysis_id'):
        from .swap_people import selected_manifest
        from .storage import Store
        manifest=selected_manifest(store or Store(),project['id'],settings);people=manifest['people']
        valid={p['id'] for p in people}
        if not mapping or any(k not in valid for k in mapping):raise ValueError('Choose a person and a replacement image.')
    automatic_direction=default_direction(project,refs,mapping,people)
    direction=settings['swap_direction'] if settings['swap_direction_enabled'] and settings['swap_direction'].strip() else automatic_direction
    if not settings['swap_direction_enabled'] or not settings['swap_direction'].strip() or direction==automatic_direction:
        if mode(settings)!='motion':
            direction+=' Match the reference clothing colors, patterns and materials exactly; do not retain the source person\'s outfit or replace it with a generic dark outfit.'
        settings['swap_direction']=direction;settings['swap_direction_enabled']=True
    settings['prompt']=re.sub(r'(?<![\w@])@([a-zA-Z0-9_]+)',lambda m:'<Video 1>' if m[1].casefold()=='video1' else bindings.get(m[1].casefold(),m[0]),direction)
    return source


def validate_range(duration,start,end):
    if any(isinstance(n,bool) or not isinstance(n,(int,float)) or not math.isfinite(n) for n in (duration,start,end)) or start<0 or end>duration+1/24 or not 4-1e-6<=end-start<=30+1e-6:
        raise ValueError('Choose a 4–30 second range within the source video.')


def generated_videos(store):
    return [dict(project_id=p['id'],project_name=p['name'],shot_id=s['id'],draft_id=d['id'],
                 title=s['title'],take=d.get('number',i+1),file=d['file'],duration=d.get('settings',{}).get('duration'),
                 approved=d['id']==(s.get('approved') or {}).get('draft_id'))
            for p in store.list() for s in p['shots'] if s.get('mode')=='video'
            for i,d in enumerate(s.get('drafts',[])) if d.get('status')=='succeeded' and d.get('file')
            and store.file(p['id'],d['file']).is_file()]


async def choose_source(store,data):
    from .sequence import probe
    project=session(store)
    shot=store.shot(project,data['shot_id'])
    if shot.get('studio_app')!=APP:raise ValueError('Choose a Second Take shot.')
    start,end=data.get('start'),data.get('end')
    if data.get('source_id'):
        row=next((r for r in project.get('swap_sources',[]) if r['id']==data['source_id']),None)
        if not row:raise ValueError('Source video is no longer available.')
        validate_range(row['duration'],start,end)
    else:
        original=store.load(data['project_id'])
        source_shot=store.shot(original,data['source_shot_id'])
        draft=next((d for d in source_shot.get('drafts',[]) if d['id']==data['draft_id'] and d.get('status')=='succeeded'),None)
        if source_shot.get('mode')!='video' or not draft:raise ValueError('Choose a completed video take.')
        path=store.file(original['id'],draft['file']);info=await probe(path)
        validate_range(info['duration'],start,end)
        ident=uuid.uuid4().hex;folder=store.file(WORKSPACE,'references/swap');folder.mkdir(parents=True,exist_ok=True)
        target,poster=folder/(ident+'.mp4'),folder/(ident+'.jpg')
        try:
            shutil.copy2(path,target)
            await run_ffmpeg('-i',target,'-frames:v','1','-vf','scale=384:-2','-threads','1','-y',poster)
            row=dict(id=ident,name=source_shot['title']+'.mp4',file=f'references/swap/{ident}.mp4',thumbnail=f'references/swap/{ident}.jpg',
                     duration=info['duration'],width=info['width'],height=info['height'],audio=info['audio'],created_at=now())
            project=store.load(WORKSPACE);shot=store.shot(project,data['shot_id']);project.setdefault('swap_sources',[]).append(row)
        except BaseException:
            target.unlink(missing_ok=True);poster.unlink(missing_ok=True);raise
    shot.update(swap_source_id=row['id'],swap_full_duration=start==0 and abs(end-row['duration'])<1/24,swap_start=start,swap_end=end,
                swap_cuts_reviewed=False,swap_cut_candidates=[],swap_cut_review_start=None,swap_cut_review_end=None)
    store.save(project)
    return project


async def attach(request, store):
    from .sequence import probe
    pid, sid = request.match_info['project'], request.match_info['shot']
    project = store.load(pid)
    shot = store.shot(project, sid)
    if shot.get('studio_app') != APP:
        raise ValueError('Choose a Second Take shot before uploading.')
    reader = await request.multipart()
    part = await reader.next()
    if part is None or part.name != 'video' or not part.filename:
        raise ValueError('Choose a source video.')
    suffix = Path(part.filename).suffix.lower()
    if suffix not in ('.mp4', '.mov', '.webm', '.mkv', '.m4v'):
        raise ValueError('Choose an MP4, MOV, MKV or WebM video.')
    ident = uuid.uuid4().hex
    folder = store.file(pid, 'references/swap')
    folder.mkdir(parents=True, exist_ok=True)
    target, poster = folder/(ident+suffix), folder/(ident+'.jpg')
    complete = False
    try:
        size = 0
        with target.open('xb') as output:
            while chunk := await part.read_chunk(1024*1024):
                size += len(chunk)
                if size > MAX_VIDEO:
                    raise ValueError('Choose a source video up to 128 MB.')
                output.write(chunk)
        info = await probe(target)
        if not math.isfinite(info['duration']) or info['duration'] < 4:
            raise ValueError('Choose a source video at least four seconds long.')
        await run_ffmpeg('-i', target, '-frames:v', '1', '-vf', 'scale=384:-2', '-threads', '1', '-y', poster)
        fields={}
        async for field in reader:
            if field.name in ('start','end'):
                value=await field.read(decode=True)
                if len(value)>32:raise ValueError('Invalid video range.')
                fields[field.name]=float(value.decode())
        start,end=fields.get('start',0),fields.get('end',min(30,info['duration']))
        validate_range(info['duration'],start,end)
        project = store.load(pid)
        shot = store.shot(project, sid)
        row = dict(id=ident, name=Path(part.filename).name[:120], file=f'references/swap/{target.name}',
                   thumbnail=f'references/swap/{poster.name}', duration=info['duration'], width=info['width'],
                   height=info['height'], audio=info['audio'], created_at=now())
        project.setdefault('swap_sources', []).append(row)
        shot.update(swap_source_id=ident, swap_full_duration=start==0 and abs(end-info['duration'])<1/24, swap_start=start, swap_end=end,
                    swap_cuts_reviewed=False,swap_cut_candidates=[],swap_cut_review_start=None,swap_cut_review_end=None)
        store.save(project)
        complete = True
        return project
    finally:
        if not complete:
            target.unlink(missing_ok=True)
            poster.unlink(missing_ok=True)


async def prepare(store, project, settings):
    """Trim/normalize only the selected range; retain original soundtrack on CPU."""
    source = settings['swap_source']
    key = hashlib.sha256(f"{source['id']}:{settings['swap_start']}:{settings['duration']}".encode()).hexdigest()[:24]
    relative = f'references/swap/{key}-prepared.mp4'
    target = store.file(project['id'], relative)
    if not target.is_file():
        temporary = target.with_name(key+'-preparing-'+uuid.uuid4().hex+'.mp4')
        try:
            await run_ffmpeg('-threads', '2', '-ss', settings['swap_start'], '-i', store.file(project['id'], source['file']),
                '-t', settings['duration'], '-map', '0:v:0', '-map', '0:a:0?', '-vf',
                "fps=24,scale=w='min(512,iw)':h='min(512,ih)':force_original_aspect_ratio=decrease:force_divisible_by=2",
                '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '20', '-c:a', 'aac', '-threads', '2',
                '-movflags', '+faststart', '-y', temporary)
            temporary.replace(target)
        finally:
            temporary.unlink(missing_ok=True)
    return dict(source, file=relative, duration=settings['duration'], fps=24)


async def finish(target, source_path, settings):
    """Remove H3 frame-grid padding and restore the selected source audio."""
    temporary = target.with_name(target.stem+'.swap-finish.mp4')
    try:
        await run_ffmpeg('-i', target, '-i', source_path, '-map', '0:v:0', '-map', '1:a:0?',
            '-t', settings['duration'], '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '18', '-threads', '2', '-c:a', 'aac', '-movflags', '+faststart', '-y', temporary)
        temporary.replace(target)
    finally:
        temporary.unlink(missing_ok=True)
