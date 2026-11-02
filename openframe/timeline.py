"""Two video/two audio tracks. All edit positions are integer 24 fps frames."""
import asyncio
import copy
import json
import math
import tempfile
import uuid
import zipfile
from pathlib import Path
from aiohttp import web
from . import sequence as seq

RATE=24
TRACKS=('V1','V2','A1','A2')
LIMIT=RATE*7200
_cache={}


async def catalog(store, project):
    used={(c.get('shot_id'),c.get('take_id')) for c in (project.get('editor_timeline') or {}).get('clips',[])}
    result=[]
    for shot in seq.video_shots(project):
        preferred=seq.ordered_take(shot)
        for take in shot.get('drafts',[]):
            if take.get('status')!='succeeded' or not take.get('file') or (take is not preferred and (shot['id'],take['id']) not in used):continue
            path=store.file(project['id'],take['file'])
            if not path.is_file():continue
            stat=path.stat();key=(str(path),stat.st_mtime_ns,stat.st_size)
            if key not in _cache:_cache[key]=await seq.probe(path)
            result.append(dict(_cache[key],key=shot['id']+':'+take['id'],shot_id=shot['id'],take_id=take['id'],title=shot['title'],file=take['file'],preferred=take is preferred))
    if len(_cache)>500:
        for key in list(_cache)[:-250]:_cache.pop(key,None)
    return result


def defaults(sources):
    clips=[];position=0
    for source in sources:
        if not source['preferred']:continue
        duration=max(1,round(source['duration']*RATE));link=uuid.uuid4().hex
        for track in ('V1','A1'):
            if track=='A1' and not source['audio']:continue
            clips.append(dict(id=uuid.uuid4().hex,shot_id=source['shot_id'],take_id=source['take_id'],track=track,start=position,source_in=0,duration=duration,gain=1,link=link))
        position+=duration
    return dict(version=1,revision=0,fps=RATE,clips=clips)


def validate(data,sources):
    if not isinstance(data,dict) or data.get('fps')!=RATE or not isinstance(data.get('clips'),list) or len(data['clips'])>400:raise ValueError('Invalid timeline.')
    mapping={s['key']:s for s in sources};clips=[];seen=set()
    for item in data['clips']:
        if not isinstance(item,dict):raise ValueError('Invalid timeline clip.')
        identifier=item.get('id');track=item.get('track');shot=item.get('shot_id');take=item.get('take_id')
        if not all(isinstance(x,str) and 0<len(x)<=120 for x in (identifier,shot,take)) or identifier in seen or track not in TRACKS:raise ValueError('Invalid timeline clip identity.')
        seen.add(identifier);source=mapping.get(shot+':'+take)
        if not source:raise ValueError('A timeline source take is missing. Remove that clip or restore its shot.')
        start,source_in,duration=(item.get(k) for k in ('start','source_in','duration'))
        if any(isinstance(v,bool) or not isinstance(v,int) for v in (start,source_in,duration)) or min(start,source_in)<0 or duration<1 or start+duration>LIMIT or source_in+duration>round(source['duration']*RATE):raise ValueError('A trim exceeds its source video or timeline limits.')
        if track.startswith('A') and not source['audio']:raise ValueError('This take has no audio.')
        gain=item.get('gain',1)
        if isinstance(gain,bool) or not isinstance(gain,(int,float)) or not math.isfinite(gain) or not 0<=gain<=1:raise ValueError('Use audio volume between 0 and 100%.')
        link=item.get('link','')
        if not isinstance(link,str) or len(link)>120:raise ValueError('Invalid clip link.')
        clips.append(dict(id=identifier,shot_id=shot,take_id=take,track=track,start=start,source_in=source_in,duration=duration,gain=float(gain),link=link))
    for track in TRACKS:
        end=0
        for clip in sorted((c for c in clips if c['track']==track),key=lambda c:c['start']):
            if clip['start']<end:raise ValueError('Clips on the same track cannot overlap. Use V2 or A2 for overlaps.')
            end=clip['start']+clip['duration']
    return dict(version=1,revision=int(data.get('revision',0)),fps=RATE,clips=clips)


def source_rows(store,project,edit):
    if not isinstance(edit,dict) or not isinstance(edit.get('clips'),list) or not edit['clips']:raise ValueError('The timeline is empty.')
    rows=[];seen=set()
    for clip in edit['clips']:
        if not isinstance(clip,dict):raise ValueError('Invalid timeline clip.')
        key=str(clip.get('shot_id'))+':'+str(clip.get('take_id'))
        if key in seen:continue
        seen.add(key)
        shot=next((s for s in seq.video_shots(project) if s['id']==clip.get('shot_id')),None)
        take=next((d for d in (shot or {}).get('drafts',[]) if d['id']==clip.get('take_id') and d.get('status')=='succeeded'),None)
        if not take:raise ValueError('A timeline source is unavailable.')
        path=store.file(project['id'],take['file'])
        if not path.is_file():raise ValueError('A timeline video file is missing.')
        rows.append(dict(key=key,path=path,shot_id=shot['id'],take_id=take['id'],title=shot['title'],media=f'media/{len(rows)+1:03d} - {seq.safe_name(shot["title"])}.mp4'))
    return rows


def span(start,duration):
    return dict(OTIO_SCHEMA='TimeRange.1',start_time=seq.rational(start,RATE),duration=seq.rational(duration,RATE))


def make_otio(name,edit,rows):
    mapping={r['key']:r for r in rows};total=max(c['start']+c['duration'] for c in edit['clips']);tracks=[]
    for track in TRACKS:
        children=[];cursor=0
        for clip in sorted((c for c in edit['clips'] if c['track']==track),key=lambda c:c['start']):
            if clip['start']>cursor:children.append(dict(OTIO_SCHEMA='Gap.1',name='',metadata={},source_range=span(0,clip['start']-cursor),effects=[],markers=[]))
            row=mapping[clip['shot_id']+':'+clip['take_id']]
            effects=[]
            if track.startswith('A') and clip['gain']!=1:
                # Resolve importers may handle audio effect metadata differently; retain exact gain explicitly.
                metadata={'directors_cut':{'gain':clip['gain']}}
            else:metadata={}
            children.append(dict(OTIO_SCHEMA='Clip.1',name=row['title'],metadata=metadata,source_range=span(clip['source_in'],clip['duration']),effects=effects,markers=[],
                media_reference=dict(OTIO_SCHEMA='ExternalReference.1',name=row['title'],metadata={},target_url=row['media'],available_range=seq.time_range(row['frames'],row['fps']))))
            cursor=clip['start']+clip['duration']
        if cursor<total:children.append(dict(OTIO_SCHEMA='Gap.1',name='',metadata={},source_range=span(0,total-cursor),effects=[],markers=[]))
        tracks.append(dict(OTIO_SCHEMA='Track.1',name=track,kind='Video' if track[0]=='V' else 'Audio',metadata={},source_range=None,effects=[],markers=[],children=children))
    return dict(OTIO_SCHEMA='Timeline.1',name=name,metadata={},global_start_time=seq.rational(0,RATE),tracks=dict(OTIO_SCHEMA='Stack.1',name='Timeline',metadata={},source_range=None,effects=[],markers=[],children=tracks))


def bundle(destination,name,edit,rows):
    with zipfile.ZipFile(destination,'w',compression=zipfile.ZIP_STORED,allowZip64=True) as archive:
        archive.writestr('version.txt','1.0.0');archive.writestr('content.otio',json.dumps(make_otio(name,edit,rows),ensure_ascii=False,indent=2))
        for row in rows:archive.write(row['path'],row['media'])


def segments(edit,track=None):
    clips=edit['clips'];total=max(c['start']+c['duration'] for c in clips)
    if track:
        selected=sorted((c for c in clips if c['track']==track),key=lambda c:c['start']);result=[];cursor=0
        for clip in selected:
            if clip['start']>cursor:result.append((cursor,clip['start'],None))
            result.append((clip['start'],clip['start']+clip['duration'],clip));cursor=clip['start']+clip['duration']
        if cursor<total:result.append((cursor,total,None))
        return result
    video=[c for c in clips if c['track'].startswith('V')];edges=sorted({0,total,*[v for c in video for v in (c['start'],c['start']+c['duration'])]});result=[]
    for left,right in zip(edges,edges[1:]):
        choices=[c for c in video if c['start']<=left and c['start']+c['duration']>=right]
        chosen=max(choices,key=lambda c:c['track'],default=None)
        if result and result[-1][2] is chosen:result[-1]=(result[-1][0],right,chosen)
        else:result.append((left,right,chosen))
    return result


async def render(destination,edit,rows,job):
    mapping={r['key']:r for r in rows};video=segments(edit);audio={t:segments(edit,t) for t in ('A1','A2')};total=max(c['start']+c['duration'] for c in edit['clips'])/RATE
    job['total']=len(video)+sum(len(s) for s in audio.values())+2;job['completed']=0
    width,height=rows[0]['width']//2*2,rows[0]['height']//2*2
    with tempfile.TemporaryDirectory(prefix='edit-',dir=destination.parent) as scratch:
        folder=Path(scratch)
        for index,(left,right,clip) in enumerate(video):
            args=[seq.ffmpeg_path(),'-hide_banner','-loglevel','error','-nostdin','-y','-threads','2']
            if clip:
                row=mapping[clip['shot_id']+':'+clip['take_id']];args+=['-ss',str((clip['source_in']+left-clip['start'])/RATE),'-i',row['path']]
            else:args+=['-f','lavfi','-i',f'color=black:size={width}x{height}:rate=24']
            args+=['-t',str((right-left)/RATE),'-an','-filter_threads','1','-vf',f'scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:color=black,setsar=1,fps=24','-c:v','libx264','-preset','veryfast','-crf','18','-pix_fmt','yuv420p','-threads','2',folder/f'v{index:04d}.mp4']
            await seq.command(*args);job['completed']+=1
        listing=folder/'video.txt';listing.write_text(''.join(f"file 'v{i:04d}.mp4'\n" for i in range(len(video))),encoding='utf-8')
        await seq.command(seq.ffmpeg_path(),'-hide_banner','-loglevel','error','-nostdin','-y','-f','concat','-safe','1','-i',listing,'-c','copy',folder/'video.mp4');job['completed']+=1
        for track,pieces in audio.items():
            for index,(left,right,clip) in enumerate(pieces):
                args=[seq.ffmpeg_path(),'-hide_banner','-loglevel','error','-nostdin','-y','-threads','1']
                if clip:
                    row=mapping[clip['shot_id']+':'+clip['take_id']];args+=['-ss',str(clip['source_in']/RATE),'-i',row['path'],'-vn','-map','0:a:0']
                else:args+=['-f','lavfi','-i','anullsrc=channel_layout=stereo:sample_rate=48000']
                duration=(right-left)/RATE
                args+=['-t',str(duration),'-af',f'volume={clip["gain"] if clip else 1},apad,atrim=duration={duration},asetpts=PTS-STARTPTS','-c:a','pcm_s16le','-ar','48000','-ac','2',folder/f'{track}-{index:04d}.wav']
                await seq.command(*args);job['completed']+=1
            listing=folder/(track+'.txt');listing.write_text(''.join(f"file '{track}-{i:04d}.wav'\n" for i in range(len(pieces))),encoding='utf-8')
            await seq.command(seq.ffmpeg_path(),'-hide_banner','-loglevel','error','-nostdin','-y','-f','concat','-safe','1','-i',listing,'-c','copy',folder/(track+'.wav'))
        await seq.command(seq.ffmpeg_path(),'-hide_banner','-loglevel','error','-nostdin','-y','-i',folder/'video.mp4','-i',folder/'A1.wav','-i',folder/'A2.wav','-filter_complex','[1:a][2:a]amix=inputs=2:duration=longest:normalize=0[a]','-map','0:v:0','-map','[a]','-t',str(total),'-c:v','copy','-c:a','aac','-b:a','192k','-movflags','+faststart',destination);job['completed']=job['total']


async def get(request):
    store=request.app['studio'].store;project=store.load(request.match_info['project']);sources=await catalog(store,project)
    return web.json_response(dict(timeline=project.get('editor_timeline') or defaults(sources),sources=sources))


async def save(request):
    data=await request.json();store=request.app['studio'].store;pid=request.match_info['project'];project=store.load(pid)
    sources=await catalog(store,project);validated=validate(data,sources)
    project=store.load(pid);revision=(project.get('editor_timeline') or {}).get('revision',0)
    if validated['revision']!=revision:raise web.HTTPConflict(text=json.dumps({'error':'This timeline changed in another window. Reopen it before saving.'}),content_type='application/json')
    validated['revision']=revision+1;project['editor_timeline']=validated;store.save(project)
    return web.json_response(validated)
