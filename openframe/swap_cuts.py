"""CPU cut detection and sequential REF2VA swaps behind one user-facing take."""
import asyncio
import copy
import json
import uuid
import secrets
import shutil
from .motion_reference import run_ffmpeg
from .sequence import probe

VERSION = 1

def set_sampler_seed(graph,seed):
    targets=[n for n in graph.values() if n.get('class_type')=='SelfLiftH3Sampler']
    key='seed'
    if not targets:
        targets=[n for n in graph.values() if n.get('class_type')=='RandomNoise'];key='noise_seed'
    if not targets:
        raise ValueError('This saved workflow has no supported seed sampler. Choose a SelfLift or standard H3 take.')
    for node in targets:node['inputs'][key]=seed

def family_id(draft, drafts):
    seen=set()
    while draft.get('regenerated_from') in drafts and draft['id'] not in seen:
        seen.add(draft['id']);draft=drafts[draft['regenerated_from']]
    return draft['id']

def revision_id(draft,index,drafts):
    part=draft['swap_segments'][index-1]
    if part.get('revision_id'):return part['revision_id']
    parent=drafts.get(draft.get('regenerated_from'))
    if parent and draft.get('regenerated_cut')!=index:return revision_id(parent,index,drafts)
    return draft['id']

def prompt_handles(store,pid,draft):
    project=store.load(pid);assets={a['id']:a for a in project.get('assets',[])}
    return [assets.get(i,{}).get('handle','') for i in draft.get('settings',{}).get('reference_ids',[])]

def editable_prompt(text,handles):
    for i,handle in enumerate(handles,1):
        if handle:text=text.replace(f'<Picture {i}>','@'+handle)
    return text.replace('<Video 1>','@video1').replace('<Audio 1>','@audio1')

def compiled_prompt(text,handles):
    import re
    bindings={handle:f'<Picture {i}>' for i,handle in enumerate(handles,1) if handle}
    bindings.update(video1='<Video 1>',audio1='<Audio 1>')
    return re.sub(r'(?<![\w@])@([A-Za-z0-9_]+)',lambda m:bindings.get(m[1],m[0]),text)

def legacy_environment_index(draft):
    roles=draft.get('settings',{}).get('swap_roles',[])
    return roles.index('background') if 'background' in roles else None

def original_scene_prompt(graph):
    import re
    old=cut_prompt(graph)
    placement=re.search(r'Per-shot cast placement:\n(.*?)(?=\nThis input|\n\n|$)',old,re.S)
    images=graph.get('136',{}).get('inputs',{})
    count=len([k for k in images if k.startswith('ref_images.')])
    if 'dc_swap_bg_fit' in graph and count>2:count-=1
    definitions='\n'.join(f'<Subject {i+1}> uses the complete face, hair, physique and outfit from <Picture {i+1}>. Keep this identity distinct and stable.' for i in range(count))
    return ('subject_definitions:\n'+definitions+'\n<Video 1> supplies the original performance and camera.\n\nsummary:\nReplace only the selected performers. Preserve the original setting, framing, camera movement, cuts and timing.\n\ndetailed_description:\n'+(placement[1] if placement else '')+'\nCopy the original gestures, expressions, choreography and visible mouth shapes. Keep each replacement outfit consistent. Preserve all other scene content. Add no cuts or dialogue.')

def remove_legacy_environment(graph,index):
    encoder=graph['136']['inputs'];key=f'ref_images.ref_image_{index}'
    if key in encoder:
        encoder.pop(key)
        for old in sorted(int(k.rsplit('_',1)[1]) for k in encoder if k.startswith('ref_images.ref_image_') and int(k.rsplit('_',1)[1])>index):
            encoder[f'ref_images.ref_image_{old-1}']=encoder.pop(f'ref_images.ref_image_{old}')
    encoder['prompt']=original_scene_prompt(graph)
    for key in list(graph):
        if key.startswith('dc_swap_bg_'):del graph[key]
    if '92' in graph:
        from .catalog import prune
        kept=prune(graph,'92');graph.clear();graph.update(kept)

def cut_prompt(graph):
    value=graph.get('136',{}).get('inputs',{}).get('prompt','')
    if isinstance(value,str):return value
    return graph.get('dc_swap_compact_prompt',{}).get('inputs',{}).get('string_b') or graph.get('dc_swap_bg_full',{}).get('inputs',{}).get('string_a','')

async def describe(request):
    from aiohttp import web
    store=request.app['studio'].store;pid=request.match_info['project']
    shot=store.shot(store.load(pid),request.match_info['shot'])
    draft=next(d for d in shot['drafts'] if d['id']==request.match_info['draft'])
    parts=[];drafts={d['id']:d for d in shot['drafts']};root=family_id(draft,drafts);handles=prompt_handles(store,pid,draft);removed=legacy_environment_index(draft)
    for part in draft.get('swap_segments',[]):
        graph=json.loads(store.file(pid,part['workflow']).read_text(encoding='utf-8'))
        variants={}
        for candidate in shot['drafts']:
            if candidate.get('deleted_at') or not candidate.get('swap_segments') or family_id(candidate,drafts)!=root:continue
            other=next((p for p in candidate['swap_segments'] if p['index']==part['index']),None)
            if other and other.get('status')!='succeeded':other={**other,'status':candidate['status']}
            if not other or (other['start_frame'],other['end_frame'])!=(part['start_frame'],part['end_frame']):continue
            revision=revision_id(candidate,part['index'],drafts)
            if revision in variants:continue
            other_graph=json.loads(store.file(pid,other['workflow']).read_text(encoding='utf-8'))
            variants[revision]={**other,'revision_id':revision,'draft_id':candidate['id'],'number':candidate.get('number'),
                'prompt':editable_prompt(original_scene_prompt(other_graph) if legacy_environment_index(candidate) is not None else cut_prompt(other_graph),handles)}
        parts.append({**part,'revision_id':revision_id(draft,part['index'],drafts),'prompt':editable_prompt(original_scene_prompt(graph) if removed is not None else cut_prompt(graph),handles),'versions':list(variants.values())})
    return web.json_response(dict(parts=parts,reference_ids=[ident for i,ident in enumerate(draft.get('settings',{}).get('reference_ids',[])) if i!=removed]))

async def regenerate(request):
    """Create a new take, borrowing no mutable files from the original take."""
    from aiohttp import web
    from .storage import now,write_json
    studio=request.app['studio'];store=studio.store;pid=request.match_info['project'];sid=request.match_info['shot'];data=await request.json()
    project=store.load(pid);shot=store.shot(project,sid)
    if shot.get('studio_app')!='second-take':raise ValueError('Cut regeneration belongs to Second Take.')
    source=next((d for d in shot['drafts'] if d['id']==request.match_info['draft']),None)
    if not source or source['status']!='succeeded' or not source.get('swap_segments'):raise ValueError('Choose a completed swap with saved cuts.')
    if data.get('background_text_only'):raise ValueError('Scene replacement has been removed. Use the original video setting.')
    index=data.get('index');parts=source['swap_segments']
    drafts={d['id']:d for d in shot['drafts']};root=family_id(source,drafts)
    choices=data.get('choices',{})
    if not isinstance(choices,dict):raise ValueError('Invalid cut choices.')
    parts=copy.deepcopy(parts)
    for i,part in enumerate(parts,1):part['revision_id']=revision_id(source,i,drafts)
    for key,ident in choices.items():
        if not str(key).isdigit() or not 1<=int(key)<=len(parts):raise ValueError('Invalid cut choice.')
        candidate=drafts.get(ident);i=int(key)
        if not candidate or family_id(candidate,drafts)!=root:raise ValueError('Choose a version from this swap.')
        part=candidate['swap_segments'][i-1]
        if part['status']!='succeeded' or (part['start_frame'],part['end_frame'])!=(parts[i-1]['start_frame'],parts[i-1]['end_frame']):raise ValueError('This cut version is not ready.')
        parts[i-1]=copy.deepcopy(part);parts[i-1]['revision_id']=revision_id(candidate,i,drafts)
    finishing=data.get('finish') is True
    if not finishing and (type(index) is not int or not 1<=index<=len(parts)):raise ValueError('Choose a valid cut.')
    single_test=data.get('single_cut_test') is True
    if single_test and (finishing or index!=1):raise ValueError('The isolated test uses the opening cut only.')
    prompt=data.get('prompt')
    if prompt is not None and (not isinstance(prompt,str) or not prompt.strip() or len(prompt)>40000):raise ValueError('Enter a cut prompt (up to 40,000 characters).')
    if prompt is not None:prompt=compiled_prompt(prompt,prompt_handles(store,pid,source))
    request_id=data.get('request_id','')
    if not isinstance(request_id,str) or len(request_id)>80:raise ValueError('Invalid cut request.')
    existing=next((d for d in shot['drafts'] if request_id and d.get('request_id')==request_id),None)
    if existing:return web.json_response(existing,status=202)
    seed=data.get('seed',-1)
    if type(seed) is not int or not -1<=seed<2**53:raise ValueError('Invalid cut seed.')
    seed=secrets.randbelow(2**53) if seed==-1 else seed
    for part in parts:
        if part.get('status')!='succeeded' or not store.file(pid,part['output']).is_file():raise ValueError('A saved cut is missing. The original take cannot be rebuilt.')
    number=max((d.get('number',0) for d in shot['drafts']),default=0)+1;stem=f'shots/{sid}/draft_{number:03d}';draft=copy.deepcopy(source)
    for key in ('job_id','cancel_requested','cancel_sent','error','audio_applied_at','applied_output_audio_id'):draft.pop(key,None)
    draft.update(id=uuid.uuid4().hex,number=number,status='queued',file=stem+'.mp4',workflow=stem+'.workflow.json',created_at=now(),request_id=request_id,regenerated_from=source['id'],regenerated_cut=None if finishing else index)
    draft['swap_segments']=copy.deepcopy(parts)
    created=[]
    try:
        shutil.copy2(store.file(pid,source['workflow']),store.file(pid,draft['workflow']));created.append(draft['workflow'])
        for i,part in enumerate(draft['swap_segments'],1):
            original=parts[i-1];prefix=stem+f'.part{i:02}'
            part.update(workflow=prefix+'.workflow.json',output=prefix+'.mp4',generated=prefix+'.generated.mp4');part.pop('job_id',None)
            graph=json.loads(store.file(pid,original['workflow']).read_text(encoding='utf-8'))
            removed=legacy_environment_index(source)
            if removed is not None:remove_legacy_environment(graph,removed)
            if i==index and not finishing:
                part['revision_id']=draft['id']
                set_sampler_seed(graph,seed)
                if prompt is not None:
                    if 'dc_swap_compact_prompt' in graph:
                        graph['dc_swap_compact_prompt']['inputs']['string_b']=prompt
                    elif 'dc_swap_bg_full' in graph:
                        graph['dc_swap_bg_full']['inputs']['string_a']=prompt
                        graph['dc_swap_bg_prompt']['inputs']['on_true']=prompt
                    else:graph['136']['inputs']['prompt']=prompt
                    part['prompt']=prompt
                # Old saved workflows must not retain the automatic vision captions.
                graph['136']['inputs']['prompt']=prompt or cut_prompt(graph)
                for key in list(graph):
                    if key.startswith('dc_swap_look_') or key in ('dc_swap_compact_prompt','dc_enhanced_preview'):
                        del graph[key]
                if '92' in graph:graph['92']['inputs']['filename_prefix']=f'video/DirectorsCut/{pid}/{sid}/take{number}/part{i:02}'
                part.update(status='queued',seed=seed)
                part['composite']=False;part['mask_file']=None
            else:
                for key in ('output','generated'):
                    path=store.file(pid,original[key])
                    if path.is_file():shutil.copy2(path,store.file(pid,part[key]));created.append(part[key])
            write_json(store.file(pid,part['workflow']),graph);created.append(part['workflow'])
            if single_test:break
        if single_test:
            draft['swap_segments']=draft['swap_segments'][:1]
            draft['settings'].update(duration=parts[0]['frames']/24,swap_full_duration=False,swap_start=0,swap_end=parts[0]['frames']/24)
            draft['test_note']='Opening cut only.'
        removed=legacy_environment_index(source)
        if removed is not None:
            draft['settings']['reference_ids']=[r for i,r in enumerate(source['settings']['reference_ids']) if i!=removed]
            draft['settings']['swap_roles']=[r for r in source['settings']['swap_roles'] if r!='background']
            if 'references' in draft['settings']:draft['settings']['references']=[r for i,r in enumerate(draft['settings']['references']) if i!=removed]
            draft['settings']['swap_direction']='';draft['settings']['swap_direction_enabled']=False
        draft['settings'].pop('swap_background_text_only',None)
        if single_test and prompt is not None:draft['full_prompt']=prompt
        studio.queue_serial+=1;draft['queue_order']=studio.queue_serial;shot['drafts'].append(draft);store.save(project)
    except BaseException:
        for path in created:store.file(pid,path).unlink(missing_ok=True)
        raise
    studio.queue.put_nowait((pid,sid,draft['id']))
    return web.json_response(draft,status=202)

def detect_cuts(path, frame_count):
    import cv2
    from scenedetect import detect, AdaptiveDetector
    cv2.setNumThreads(2)
    scenes = detect(str(path), AdaptiveDetector(), show_progress=False, start_in_scene=True)
    # prepare() normalizes source to 24fps. Endpoints are original prepared-source frames.
    cuts = sorted({0, frame_count, *(max(0,min(frame_count,a.frame_num)) for a,b in scenes)})
    return [(a,b) for a,b in zip(cuts,cuts[1:]) if b>a]

async def prepare_parts(store, project, prepared, settings=None):
    maskfile=None
    detection_path=store.file(project['id'],prepared['file'])
    original_info=await probe(detection_path)
    path=store.file(project['id'],prepared['file'])
    info=await probe(path)
    count=info['frames']
    if not 1<=count<=24*30+1:raise ValueError('Cut detection accepts a source range up to 30 seconds.')
    ranges=await asyncio.wait_for(asyncio.to_thread(detect_cuts,detection_path,count),timeout=60)
    # Even a single shot uses this path, so padding and audio behavior stay identical.
    result=[]
    for index,(a,b) in enumerate(ranges):
        frames=b-a
        generation=max(96,frames)
        generation+=(5-generation)%17
        key=path.stem+f'-cuts{VERSION}-{a}-{b}'
        relative=f'references/swap/{key}.mp4'
        target=store.file(project['id'],relative)
        if not target.is_file():
            temporary=target.with_name(target.stem+'.'+uuid.uuid4().hex+'.preparing.mp4')
            try:
                filters=f'trim=start_frame={a}:end_frame={b},setpts=PTS-STARTPTS,tpad=stop_mode=clone:stop_duration={generation/24:.9f}'
                await run_ffmpeg('-threads','2','-i',path,'-an','-vf',filters,'-frames:v',generation,
                    '-c:v','libx264','-preset','veryfast','-crf','20','-threads','2','-movflags','+faststart','-y',temporary)
                temporary.replace(target)
            finally:temporary.unlink(missing_ok=True)
        audio_relative=None
        if original_info.get('audio'):
            audio_relative=f'references/swap/{key}-speech.wav'
            audio_target=store.file(project['id'],audio_relative)
            if not audio_target.is_file():
                temporary=audio_target.with_name(audio_target.stem+'.'+uuid.uuid4().hex+'.wav')
                try:
                    await run_ffmpeg('-threads','2','-ss',str(a/24),'-i',detection_path,
                        '-vn','-af',f'atrim=duration={frames/24:.9f},asetpts=PTS-STARTPTS,apad,atrim=duration={generation/24:.9f}','-ac','2','-ar','48000',
                        '-c:a','pcm_s16le','-y',temporary)
                    temporary.replace(audio_target)
                finally:temporary.unlink(missing_ok=True)
        result.append(dict(id=key,index=index+1,start_frame=a,end_frame=b,frames=frames,generation_frames=generation,
                           mask_file=maskfile,audio_file=audio_relative,file=relative,duration=generation/24,fps=24,media_type='video',audio=False))
    return result

async def cast_map(store, project, prepared):
    source=store.file(project['id'],prepared['file'])
    relative=source.with_name(source.stem+'-cast-map.png').relative_to(store.folder(project['id'])).as_posix()
    target=store.file(project['id'],relative)
    if not target.is_file():
        temporary=target.with_name(target.stem+'.'+uuid.uuid4().hex+'.png')
        try:
            await run_ffmpeg('-threads','2','-i',source,'-frames:v','1','-threads','1','-y',temporary)
            temporary.replace(target)
        finally:temporary.unlink(missing_ok=True)
    return dict(id=source.stem+'-cast-map',file=relative,media_type='image')

async def trim_part(generated,target,frames):
    temporary=target.with_suffix('.finishing.mp4')
    try:
        await run_ffmpeg('-threads','2','-i',generated,'-an','-vf',f'fps=24,trim=end_frame={frames},setpts=PTS-STARTPTS',
            '-frames:v',frames,'-c:v','libx264','-preset','veryfast','-crf','18','-threads','2','-movflags','+faststart','-y',temporary)
        info=await probe(temporary)
        if info['frames']!=frames:raise ValueError('A generated segment is shorter than its source. Assembly stopped.')
        temporary.replace(target)
    finally:temporary.unlink(missing_ok=True)

async def composite_part(source,generated,maskfile,start,frames):
    info=await probe(generated);width,height=info['width'],info['height'];temporary=generated.with_suffix('.composite.mp4')
    try:
        filters=f'[0:v]scale={width}:{height},format=gbrp[b];[1:v]format=gbrp[g];[2:v]scale={width}:{height},format=gray,gblur=sigma=2,format=gbrp[m];[b][g][m]maskedmerge,format=yuv420p[out]'
        await run_ffmpeg('-threads','2','-ss',str(start/24),'-i',source,'-i',generated,'-ss',str(start/24),'-i',maskfile,
            '-filter_complex',filters,'-map','[out]','-frames:v',frames,'-an','-c:v','libx264','-preset','veryfast','-crf','18','-threads','2','-y',temporary)
        if (await probe(temporary))['frames']!=frames:raise ValueError('Masked result does not match source frames.')
        temporary.replace(generated)
    finally:temporary.unlink(missing_ok=True)

async def assemble(parts,source,target,total_frames):
    listing=target.with_suffix('.concat.txt');temporary=target.with_suffix('.assembling.mp4')
    try:
        # Only server-generated local part names, not user text, enter this demuxer list.
        listing.write_text('\n'.join("file '"+p.as_posix().replace("'", "'\\''")+"'" for p in parts),encoding='utf-8')
        await run_ffmpeg('-f','concat','-safe','0','-i',listing,'-i',source,'-map','0:v:0','-map','1:a:0?',
            '-t',f'{total_frames/24:.9f}','-c:v','copy','-c:a','aac','-threads','2','-movflags','+faststart','-y',temporary)
        info=await probe(temporary)
        if info['frames']!=total_frames:raise ValueError('Final cut frame count does not match its source.')
        temporary.replace(target)
    finally:
        listing.unlink(missing_ok=True);temporary.unlink(missing_ok=True)

async def generate(studio,project_id,shot_id,draft,update):
    from .provider import GenerationCancelled
    store=studio.store
    parts=copy.deepcopy(draft['swap_segments'])
    def cancelled():
        p=store.load(project_id);s=store.shot(p,shot_id)
        d=next(d for d in s['drafts'] if d['id']==draft['id'])
        if d.get('cancel_requested') or d['status']=='cancelled':raise GenerationCancelled()
    for i,part in enumerate(parts):
        cancelled()
        target=store.file(project_id,part['output'])
        if part.get('status')=='succeeded' and target.is_file():continue
        await update(job_id=part.get('job_id'),status='running',stage=f'Part {i+1}/{len(parts)} · Preparing',
                     sampling=False,sampling_step=None,sampling_steps=None,segment_number=i+1,segment_count=len(parts))
        graph=json.loads(store.file(project_id,part['workflow']).read_text(encoding='utf-8'))
        async def part_update(**changes):
            if changes.get('job_id'):part['job_id']=changes['job_id']
            if changes.get('full_prompt'):part['executed_prompt']=changes['full_prompt']
            changes['swap_segments']=parts
            changes['segment_number']=i+1;changes['segment_count']=len(parts)
            if 'stage' in changes:changes['stage']=f'Part {i+1}/{len(parts)} · '+changes['stage']
            # A child finishing never marks the complete take finished.
            if changes.get('status') in ('succeeded','downloading'):changes['status']='running'
            await update(**changes)
        generated=store.file(project_id,part['generated'])
        await studio.provider.generate(graph,generated,part_update,part.get('job_id'))
        cancelled()
        await update(stage=f'Part {i+1}/{len(parts)} · Trimming',sampling=False,sampling_step=None,sampling_steps=None)
        await trim_part(generated,target,part['frames'])
        if part.get('mask_file') and part.get('composite',True):
            await composite_part(store.file(project_id,draft['settings']['swap_prepared']['file']),target,store.file(project_id,part['mask_file']),part['start_frame'],part['frames'])
        part['status']='succeeded'
        await update(swap_segments=parts,job_id=None)
    cancelled()
    await update(status='downloading',stage='Assembling cuts and restoring source audio',sampling=False,sampling_step=None,sampling_steps=None)
    source=store.file(project_id,draft['settings']['swap_prepared']['file'])
    await assemble([store.file(project_id,p['output']) for p in parts],source,store.file(project_id,draft['file']),sum(p['frames'] for p in parts))
    cancelled()
