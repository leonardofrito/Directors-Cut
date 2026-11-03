"""Cached local SAM tracks + visual role matching for Second Take."""
import asyncio, base64, hashlib, io, json, re, zipfile, time
from pathlib import Path
from urllib.parse import urlencode
import aiohttp
from PIL import Image
from . import character_swap, engine_config, model_downloads
from .storage import write_json

SAM='sam3.1_multiplex_fp16.safetensors'
ACTIVE={'preparing','running','downloading'}
PHASES={'1':'Reading source video','2':'Reading source frames','3':'Loading person tracker','4':'Preparing person tracker','5':'Tracking people','6':'Selecting recognition frames','7':'Loading visual recognition model','8':'Identifying the cast','9':'Preparing person crops','10':'Matching people across shots','11':'Saving person tracks','12':'Saving cast descriptions','13':'Preparing cast descriptions'}

def update_progress(state,event):
    """Expose actual node work; never invent a whole-analysis percentage."""
    node=str(getattr(event,'current_node','') or '')
    if not node:return
    step,steps=getattr(event,'step',None),getattr(event,'steps',None)
    previous=(state.get('current_node'),state.get('step'),state.get('steps'),state.get('work_value'))
    state.update(current_node=node,stage=PHASES.get(node,'Processing source video'),
                 step=step if steps else None,steps=steps or None,work_value=getattr(event,'value',None))
    if previous!=(node,state['step'],state['steps'],state['work_value']):state['last_progress_at']=time.time()

def analysis_folder(store,pid,ident):
    if not re.fullmatch(r'[a-f0-9]{32}',ident):raise ValueError('Invalid person analysis.')
    return store.file(pid,f'references/swap/people/{ident}')

def selected_manifest(store,pid,settings):
    ident=settings.get('swap_analysis_id','')
    if not ident:return None
    path=analysis_folder(store,pid,ident)/'manifest.json'
    if not path.is_file():raise ValueError('Find people in this video first.')
    m=json.loads(path.read_text(encoding='utf-8'))
    if m['source_id']!=settings['swap_source_id'] or abs(m['start']-settings['swap_start'])>1/48 or abs(m['end']-settings['swap_end'])>1/48:raise ValueError('The video range changed. Find people again.')
    if m.get('status')!='succeeded':raise ValueError('Wait for person identification to finish.')
    return m

def graph(video,model):
    people='List the distinct people in these frames from one video, up to four. Give each original person one stable identity across camera cuts, never treat a changed screen position as a new person. Most screen time first. Use exactly one line per person starting with <Subject 1>, <Subject 2>, etc. Then a short role, then " - ", then their original hair, face and complete clothing that identify them. Output only that list.'
    return {
      '1':{'class_type':'LoadVideo','inputs':{'file':video}},
      '2':{'class_type':'GetVideoComponents','inputs':{'video':['1',0]}},
      '3':{'class_type':'CheckpointLoaderSimple','inputs':{'ckpt_name':SAM}},
      '4':{'class_type':'CLIPTextEncode','inputs':{'text':'person','clip':['3',1]}},
      '5':{'class_type':'SAM3_VideoTrack','_meta':{'title':'Tracking people'},'inputs':{'images':['2',0],'model':['3',0],'conditioning':['4',0],'detection_threshold':.35,'max_objects':8,'detect_interval':1}},
      '6':{'class_type':'VHS_SelectEveryNthImage','inputs':{'images':['2',0],'select_every_nth':48,'skip_first_images':0}},
      '7':{'class_type':'CLIPLoader','inputs':{'clip_name':model,'type':'stable_diffusion','device':'default'}},
      '8':{'class_type':'TextGenerate','_meta':{'title':'Identifying the cast'},'inputs':{'clip':['7',0],'image':['6',0],'prompt':people,'max_length':256,'sampling_mode':'off','thinking':False,'use_default_template':True,'mtp':'off'}},
      '9':{'class_type':'H3TrackCrops','inputs':{'track_data':['5',0],'images':['2',0],'people':['13',0],'cut_threshold':40,'max_crops':32}},
      '10':{'class_type':'H3TrackRoles','_meta':{'title':'Matching people across shots'},'inputs':{'clip':['7',0],'crops':['9',0],'segments':['9',1]}},
      '11':{'class_type':'H3MontagePeople','inputs':{'track_data':['5',0],'crops':['9',0],'labels':['10',0],'source_frames':['2',0]}},
      '12':{'class_type':'PreviewAny','inputs':{'source':['13',0]}},
      '13':{'class_type':'RegexReplace','inputs':{'string':['8',0],'regex_pattern':r'^\s*(?:<\s*Subject\s*|Subject\s*)?([1-4])\s*(?:>|[.):\-])\s*','replace':r'<Subject \1> ','case_insensitive':True,'multiline':True,'dotall':False,'count':0}}}

def unpack(packed):
    import numpy as np
    return np.unpackbits(packed,axis=-1,bitorder='little')

def read_tracks(folder):
    import numpy as np,cv2
    path=folder/'tracks.npz'
    with zipfile.ZipFile(path) as archive:
        if sum(e.file_size for e in archive.infolist())>2*1024**3:raise ValueError('Tracking data exceeds its limit.')
        with archive.open('packed_masks.npy') as data:
            version=np.lib.format.read_magic(data)
            shape,order,dtype=(np.lib.format.read_array_header_1_0 if version==(1,0) else np.lib.format.read_array_header_2_0)(data)
            if dtype!=np.uint8 or len(shape)!=4 or order or not 1<=shape[0]<=721 or not 1<=shape[1]<=16 or shape[2]>1024 or shape[3]>128:raise ValueError('Invalid track dimensions.')
            if shape[2]>384 or shape[3]>48:
                # SAM returns 1008px masks regardless of its input. Compact one frame at a time.
                compact=np.empty((shape[0],shape[1],256,32),dtype=np.uint8)
                size=shape[1]*shape[2]*shape[3]
                for frame in range(shape[0]):
                    raw=data.read(size)
                    if len(raw)!=size:raise ValueError('Incomplete tracking data.')
                    masks=unpack(np.frombuffer(raw,dtype=np.uint8).reshape(shape[1:]))
                    for track in range(shape[1]):compact[frame,track]=np.packbits(cv2.resize(masks[track],(256,256),interpolation=cv2.INTER_NEAREST),axis=-1,bitorder='little')
                temp=folder/'tracks.compact.npz';np.savez_compressed(temp,packed_masks=compact)
            else:compact=None
    if compact is not None:temp.replace(path);return compact
    z=np.load(path,allow_pickle=False);m=z['packed_masks']
    if m.nbytes>128*1024**2:raise ValueError('Tracking data exceeds its limit.')
    return m

def make_manifest(store,pid,ident,raw,descriptions,prepared,source_id,start,end):
    import cv2, numpy as np
    from .swap_cuts import detect_cuts
    folder=analysis_folder(store,pid,ident);packed=read_tracks(folder)
    entries=[];groups={};lines=[x.strip() for x in descriptions.splitlines() if x.strip()]
    for i,item in enumerate(raw.get('people',[])[:64]):
        track=item.get('track');a=item.get('start');b=item.get('end');role=item.get('role',0)
        if not all(type(v) is int for v in [track,a,b,role]) or not 0<=track<packed.shape[1] or not 0<=a<b<=packed.shape[0] or not 0<=role<=4:continue
        if not item.get('on') or item.get('area',0)<.002:continue
        key=f'p{role}' if role else f'u{i}'
        entry=dict(group=key,track=track,start=a,end=b,role=role)
        entries.append(entry)
        if key not in groups or item['area']>groups[key]['area']:
            image=item.get('image','')
            if not image.startswith('data:image/jpeg;base64,') or len(image)>4*1024**2:continue
            photo=Image.open(io.BytesIO(base64.b64decode(image.split(',',1)[1],validate=True)));photo.thumbnail((440,300));photo.convert('RGB').save(folder/f'{key}.jpg',quality=80)
            label=lines[role-1] if 0<role<=len(lines) else 'Unmatched person'
            groups[key]=dict(id=key,label=label,area=item['area'],thumbnail=f'references/swap/people/{ident}/{key}.jpg',matched=bool(role))
    path=store.file(pid,prepared['file']);ranges=detect_cuts(path,packed.shape[0]);video=cv2.VideoCapture(str(path));shots=[]
    try:
        for i,(a,b) in enumerate(ranges):
            f=a+min(12,max(0,(b-a)//2));video.set(cv2.CAP_PROP_POS_FRAMES,f);ok,frame=video.read()
            if not ok:continue
            cv2.imwrite(str(folder/f'shot{i+1}.jpg'),frame,[cv2.IMWRITE_JPEG_QUALITY,82]);boxes=[]
            for key in groups:
                masks=[unpack(packed[f,e['track']]) for e in entries if e['group']==key and e['start']<=f<e['end']]
                if not masks:continue
                ys,xs=np.nonzero(np.maximum.reduce(masks))
                if not len(xs):continue
                h,w=masks[0].shape
                boxes.append(dict(person=key,x=float(xs.min()/w),y=float(ys.min()/h),width=float((xs.max()-xs.min()+1)/w),height=float((ys.max()-ys.min()+1)/h)))
            shots.append(dict(index=i+1,start_frame=a,end_frame=b,frame=f,image=f'references/swap/people/{ident}/shot{i+1}.jpg',boxes=boxes))
    finally:video.release()
    m=dict(id=ident,status='succeeded',source_id=source_id,start=start,end=end,prepared=prepared,frames=int(packed.shape[0]),people=list(groups.values()),appearances=entries,shots=shots)
    write_json(folder/'manifest.json',m);return m

class People:
    def __init__(self,studio):self.studio=studio;self.tasks={};self.jobs={}
    @property
    def running(self):return any(not t.done() for t in self.tasks.values())
    async def close(self):
        for t in self.tasks.values():t.cancel()
        await asyncio.gather(*self.tasks.values(),return_exceptions=True)
    async def start(self,pid,sid,data):
        p=self.studio.store.load(pid);src=next((x for x in p.get('swap_sources',[]) if x['id']==data.get('swap_source_id')),None)
        if not src:raise ValueError('Choose a source video.')
        a=0 if data.get('swap_full_duration',True) else data.get('swap_start',0);b=src['duration'] if data.get('swap_full_duration',True) else data.get('swap_end',0)
        character_swap.validate_range(src['duration'],a,b);b=a+round((b-a)*24)/24
        nodes=await self.studio.nodes()
        files=nodes.get('CLIPLoader',{}).get('input',{}).get('required',{}).get('clip_name',[[]])[0]
        model=next((x for x in ['qwen3vl_8b_w4a8.safetensors','qwen3vl_8b_int8_convrot.safetensors','qwen3.5_4b_int8_convrot.safetensors','qwen3vl_4b_int8_convrot.safetensors'] if x in files),None)
        if not model:raise ValueError('Install a vision-capable Qwen prompt enhancer first.')
        ident=hashlib.sha256(f'{src["id"]}:{a}:{b}:{model}:v2'.encode()).hexdigest()[:32]
        folder=analysis_folder(self.studio.store,pid,ident);folder.mkdir(parents=True,exist_ok=True)
        if (folder/'manifest.json').is_file():return json.loads((folder/'manifest.json').read_text(encoding='utf-8'))
        if ident in self.tasks and not self.tasks[ident].done():return self.jobs[ident]
        if self.studio.queue_items() or self.studio.queue.qsize():
            raise ValueError('A generation is running or waiting in another workspace. Wait for the queue to finish before identifying people.')
        await self.studio.node_setup.ensure_idle()
        if self.running:raise ValueError('Another video is being identified. Wait for it to finish.')
        state=dict(id=ident,status='preparing',stage='Preparing person identification',project_id=pid,shot_id=sid,source_id=src['id'],started_at=time.time())
        previous=folder/'job.json'
        if previous.is_file():state['job_id']=json.loads(previous.read_text(encoding='utf-8')).get('job_id')
        self.jobs[ident]=state;self.tasks[ident]=asyncio.create_task(self.run(p,state,src,a,b,model,nodes));return state
    def status(self,pid,ident):
        if ident in self.jobs:
            if self.jobs[ident]['project_id']!=pid:raise ValueError('Wrong project.')
            return self.jobs[ident]
        path=analysis_folder(self.studio.store,pid,ident)/'manifest.json'
        if not path.is_file():raise ValueError('Person analysis not found. Try again.')
        return json.loads(path.read_text(encoding='utf-8'))
    async def cancel(self,pid,ident):
        state=self.jobs.get(ident)
        if not state or state['project_id']!=pid:return
        state['cancel_requested']=True
        if state.get('owns_download'):await self.studio.model_downloads.cancel('sam31-people')
        if state.get('job_id'):await self.studio.provider.cancel(state['job_id'])
    async def run(self,p,state,src,a,b,model,nodes):
        stream=None;folder=analysis_folder(self.studio.store,p['id'],state['id'])
        try:
            required=['SAM3_VideoTrack','H3TrackCrops','H3TrackRoles','H3MontagePeople','VHS_SelectEveryNthImage']
            if any(k not in nodes for k in required):
                await self.studio.node_setup.start(['swap-tracking'])
                if self.studio.node_setup.task:await self.studio.node_setup.task
                raise ValueError('Person-tracking nodes are installed. Restart ComfyUI once, then choose People again.')
            row=model_downloads.BY_ID['sam31-people']
            if not model_downloads.destination(row).is_file():
                existing=self.studio.model_downloads.tasks.get('sam31-people')
                state['owns_download']=not existing or existing.done()
                state['stage']='Downloading SAM 3.1';await self.studio.model_downloads.start('sam31-people')
                task=self.studio.model_downloads.tasks.get('sam31-people')
                if task:await task
                if not model_downloads.destination(row).is_file():raise ValueError('SAM download did not complete. Check Engine settings.')
            if state.get('cancel_requested'):raise asyncio.CancelledError()
            prepared=await character_swap.prepare(self.studio.store,p,dict(swap_source=src,swap_start=a,duration=b-a))
            if state.get('cancel_requested'):raise asyncio.CancelledError()
            uploaded=(await self.studio.upload_references(p,[{**prepared,'media_type':'video'}]))[0]
            if state.get('cancel_requested'):raise asyncio.CancelledError()
            g=graph(uploaded['comfy_image'],model)
            old_id=hashlib.sha256(f'{src["id"]}:{a}:{b}:{model}:v1'.encode()).hexdigest()[:32]
            old_graph=analysis_folder(self.studio.store,p['id'],old_id)/'workflow.json'
            if old_graph.is_file():g['1']['inputs']['file']=json.loads(old_graph.read_text(encoding='utf-8'))['1']['inputs']['file']
            write_json(folder/'workflow.json',g)
            job=await self.studio.provider.client.jobs.get(state['job_id']) if state.get('job_id') else None
            if job:await job.refresh()
            if state.get('cancel_requested'):raise asyncio.CancelledError()
            if not job or job.status in ('failed','cancelled','canceled'):job=await self.studio.provider.client.submit(self.studio.provider.client.workflows.from_json(g))
            state.update(status='running',job_id=job.id,stage='Tracking and identifying people');write_json(folder/'job.json',state)
            async def events():
                try:
                    async for e in job.events():
                        update_progress(state,e)
                except Exception:pass
            stream=asyncio.create_task(events())
            while True:
                if state.get('cancel_requested'):await self.studio.provider.cancel(job.id);raise asyncio.CancelledError()
                await job.refresh()
                state.update(checked_at=time.time(),engine_status=job.status)
                if job.status in ('succeeded','failed','cancelled','canceled'):break
                await asyncio.sleep(2)
            if job.status!='succeeded':raise ValueError(str(job.error or 'Person detection cancelled.'))
            state.update(stage='Collecting detected people',step=None,steps=None,last_progress_at=time.time())
            base=engine_config.current()['comfy_url']
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=60)) as session:
                async with session.get(base+'/history/'+job.id) as response:response.raise_for_status();h=await response.json()
                outputs=h[job.id]['outputs'];descriptor=outputs['11']['files'][0]
                async def fetch(name,limit):
                    if Path(name).name!=name or not re.fullmatch(r'h3_montage_people_\d+_\.(json|npz)',name):raise ValueError('Invalid tracking output.')
                    async with session.get(base+'/view?'+urlencode(dict(filename=name,type='temp',subfolder=descriptor.get('subfolder','')))) as response:
                        response.raise_for_status();chunks=[];size=0
                        async for chunk in response.content.iter_chunked(1024**2):
                            size+=len(chunk)
                            if size>limit:raise ValueError('Tracking output too large.')
                            chunks.append(chunk)
                        return b''.join(chunks)
                raw=json.loads(await fetch(descriptor['filename'],12*1024**2))
                if not raw.get('tracks'):raise ValueError('No people found. Choose a shot where the person is visible.')
                (folder/'tracks.npz').write_bytes(await fetch(raw['tracks'],64*1024**2))
            text=outputs.get('12',{}).get('text',[''])[0]
            state.update(stage='Building person selections',last_progress_at=time.time())
            result=await asyncio.to_thread(make_manifest,self.studio.store,p['id'],state['id'],raw,text,prepared,src['id'],a,b)
            if state.get('cancel_requested'):
                (folder/'manifest.json').unlink(missing_ok=True)
                raise asyncio.CancelledError()
            state.update(result)
        except asyncio.CancelledError:state.update(status='cancelled',stage='Cancelled')
        except Exception as e:state.update(status='failed',error=str(e),stage='Person identification failed')
        finally:
            if stream:stream.cancel();await asyncio.gather(stream,return_exceptions=True)

async def start(request):
    return aiohttp.web.json_response(await request.app['studio'].people.start(request.match_info['project'],request.match_info['shot'],await request.json()),status=202)
async def status(request):return aiohttp.web.json_response(request.app['studio'].people.status(request.match_info['project'],request.match_info['analysis']))
async def cancel(request):
    await request.app['studio'].people.cancel(request.match_info['project'],request.match_info['analysis'])
    return aiohttp.web.json_response({'cancel_requested':True})


def mask_for_frame(packed,appearances,groups,frame):
    import numpy as np
    masks=[unpack(packed[frame,e['track']]) for e in appearances if e['group'] in groups and e['start']<=frame<e['end']]
    return np.maximum.reduce(masks) if masks else np.zeros((packed.shape[2],packed.shape[3]*8),dtype=np.uint8)

def position_text(store,pid,manifest,mapping,a,b,reference_ids,neutralized=True,compact=False):
    import numpy as np
    packed=read_tracks(analysis_folder(store,pid,manifest['id']));lines=[]
    for i,(group,ref) in enumerate(mapping.items()):
        frame=a+min(12,max(0,(b-a)//2));mask=mask_for_frame(packed,manifest['appearances'],{group},frame)
        ys,xs=np.nonzero(mask)
        if not len(xs):
            visible=next((e for e in manifest['appearances'] if e['group']==group and e['start']<b and e['end']>a),None)
            if visible:mask=mask_for_frame(packed,manifest['appearances'],{group},max(a,visible['start']));ys,xs=np.nonzero(mask)
        if not len(xs):lines.append(f'<Subject {i+1}> is not visible in this shot; do not add them.');continue
        h,w=mask.shape;x=float(xs.mean()/w);share=(ys.max()-ys.min()+1)/h
        horizontal='left' if x<.4 else 'right' if x>.6 else 'centre'
        depth='large foreground' if share>.65 else 'smaller background' if share<.45 else 'midground'
        figure='grey figure' if neutralized else 'original performer'
        if compact:
            lines.append(f'<Subject {i+1}> (<Picture {reference_ids.index(ref)+1}>) replaces the {depth} original performer at {horizontal}; follow that person as they move.')
            continue
        lines.append(f'<Subject {i+1}> from <Picture {reference_ids.index(ref)+1}> replaces the {depth} {figure} in the {horizontal} of the source shot. Its body is centred around x={x:.2f} of frame width. Follow that same performer throughout the shot, including later movement. Do not leave their old face, hair or outfit.')
    return '\n'.join(lines)

async def masked_motion(store,project,prepared,settings):
    import asyncio,hashlib
    from .motion_reference import run_ffmpeg
    manifest=selected_manifest(store,project['id'],settings)
    if not manifest:return prepared,None
    groups=set(settings['swap_people_map']);folder=analysis_folder(store,project['id'],manifest['id'])
    # Version the cached conditioning when the matte construction changes.
    key=hashlib.sha256(('matte-v2:'+','.join(sorted(groups))).encode()).hexdigest()[:12]
    motion=folder/f'motion-{key}.mp4';maskfile=folder/f'mask-{key}.mkv'
    if not motion.is_file() or not maskfile.is_file():
        def render():
            import cv2,numpy as np,tempfile
            cv2.setNumThreads(2);packed=read_tracks(folder);video=cv2.VideoCapture(str(store.file(project['id'],prepared['file'])))
            ok,frame=video.read()
            if not ok:raise ValueError('Source video cannot be decoded.')
            h,w=frame.shape[:2]
            with tempfile.TemporaryDirectory(prefix='mask-render-',dir=folder) as temporary:
                tmp=Path(temporary);writer=cv2.VideoWriter(str(tmp/'motion.avi'),cv2.VideoWriter_fourcc(*'MJPG'),24,(w,h));mw=cv2.VideoWriter(str(tmp/'mask.mkv'),cv2.VideoWriter_fourcc(*'FFV1'),24,(w,h),False)
                try:
                    if not writer.isOpened() or not mw.isOpened():raise ValueError('Video mask encoder unavailable.')
                    for n in range(packed.shape[0]):
                        if n:ok,frame=video.read()
                        if not ok:raise ValueError('Tracking and source video frame counts differ.')
                        m=mask_for_frame(packed,manifest['appearances'],groups,n)
                        m=cv2.resize(m,(w,h),interpolation=cv2.INTER_NEAREST)*255
                        ys,xs=np.nonzero(m)
                        composite=m
                        if len(xs):
                            height=ys.max()-ys.min()+1
                            # The composite must extend beyond the grey conditioning edge,
                            # otherwise any remaining grey pixels appear as a visible halo.
                            inner=max(1,min(8,round(height*.015)))
                            outer=max(inner+10,min(48,round(height*.10)))
                            m=cv2.dilate(m,cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(inner*2+1,inner*2+1)))
                            composite=cv2.dilate(composite,cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(outer*2+1,outer*2+1)))
                        luma=cv2.GaussianBlur(cv2.cvtColor(frame,cv2.COLOR_BGR2GRAY),(5,5),1.0)
                        grey=np.repeat((115+luma.astype(np.float32)*.45).clip(0,255).astype(np.uint8)[...,None],3,axis=2)
                        output=np.where(m[...,None]>0,grey,frame)
                        writer.write(output);mw.write(composite)
                finally:video.release();writer.release();mw.release()
                import shutil
                shutil.copy2(tmp/'motion.avi',folder/f'motion-{key}.avi');shutil.copy2(tmp/'mask.mkv',maskfile)
        await asyncio.to_thread(render)
        temporary=motion.with_suffix('.encoding.mp4')
        try:
            await run_ffmpeg('-threads','2','-i',folder/f'motion-{key}.avi','-an','-c:v','libx264','-preset','veryfast','-crf','18','-threads','2','-y',temporary)
            temporary.replace(motion)
        finally:
            temporary.unlink(missing_ok=True);(folder/f'motion-{key}.avi').unlink(missing_ok=True)
    relative=motion.relative_to(store.folder(project['id'])).as_posix()
    return {**prepared,'file':relative,'audio':False},maskfile.relative_to(store.folder(project['id'])).as_posix()
