"""Bounded CPU-only shot suggestions for the source trim, before generation."""
import asyncio
import json
import re
import time
import uuid
from pathlib import Path

from aiohttp import web
from . import character_swap, swap_cuts
from .motion_reference import MAX_VIDEO, run_ffmpeg
from .sequence import probe


class CutPreviews:
    def __init__(self,store):
        self.store=store
        self.folder=store.root/'.runtime/cut-previews'
        self.folder.mkdir(parents=True,exist_ok=True)
        self.sources={}
        self.results={}
        self.lock=asyncio.Lock()

    def expire(self):
        now=time.time()
        for token,row in list(self.sources.items()):
            if now-row['created']>6*3600:
                if row.get('temporary'):row['path'].unlink(missing_ok=True)
                self.sources.pop(token,None)
                for key in list(self.results):
                    if key[0]==token:self.results.pop(key,None)
        # Old staged uploads from a previous app process, never user source files.
        for file in self.folder.iterdir():
            if file.is_file() and re.fullmatch(r'[a-f0-9]{32}(?:-scan)?\.(mp4|mov|webm|mkv|m4v)',file.name) and now-file.stat().st_mtime>86400:
                if not any(row['path']==file for row in self.sources.values()):file.unlink(missing_ok=True)

    async def register(self,path,temporary=False):
        info=await probe(path)
        if info['duration']<4:raise ValueError('Choose a source video at least four seconds long.')
        token=uuid.uuid4().hex
        self.sources[token]=dict(path=path,temporary=temporary,info=info,created=time.time())
        return token

    async def scan(self,token,start,end):
        if not isinstance(token,str) or token not in self.sources:raise ValueError('Cut preview expired. Reopen the source video.')
        row=self.sources[token]
        character_swap.validate_range(row['info']['duration'],start,end)
        a,b=round(start*24),round(end*24)
        key=(token,a,b)
        async with self.lock:
            if key in self.results:return self.results[key]
            target=self.folder/(uuid.uuid4().hex+'-scan.mp4')
            try:
                await run_ffmpeg('-threads','2','-ss',str(a/24),'-i',row['path'],'-t',str((b-a)/24),
                    '-an','-vf',"fps=24,scale=w='min(512,iw)':h='min(512,ih)':force_original_aspect_ratio=decrease:force_divisible_by=2",
                    '-c:v','libx264','-preset','veryfast','-crf','20','-threads','2','-y',target)
                info=await probe(target)
                ranges=await asyncio.wait_for(asyncio.to_thread(swap_cuts.detect_cuts,target,info['frames']),timeout=60)
                result=dict(token=token,start_frame=a,end_frame=b,
                    cuts=[dict(frame=a+x,time=(a+x)/24) for x,y in ranges if 0<x<info['frames']],
                    duration=row['info']['duration'])
                self.results[key]=result
                return result
            finally:
                try:target.unlink(missing_ok=True)
                except OSError:pass  # A timed-out OpenCV reader may still own the temporary file.


async def preview(request):
    studio=request.app['studio']
    if not hasattr(studio,'cut_previews'):studio.cut_previews=CutPreviews(studio.store)
    service=studio.cut_previews;service.expire()
    temporary=None
    token=None
    try:
        if request.content_type=='multipart/form-data':
            reader=await request.multipart();part=await reader.next()
            if part is None or part.name!='video' or not part.filename:raise ValueError('Choose a source video.')
            suffix=Path(part.filename).suffix.lower()
            if suffix not in ('.mp4','.mov','.webm','.mkv','.m4v'):raise ValueError('Choose a supported video file.')
            temporary=service.folder/(uuid.uuid4().hex+suffix)
            size=0
            with temporary.open('xb') as output:
                while chunk:=await part.read_chunk(1024*1024):
                    size+=len(chunk)
                    if size>MAX_VIDEO:raise ValueError('Choose a video up to 128 MB.')
                    output.write(chunk)
            data={}
            async for field in reader:
                if field.name in ('start','end'):
                    value=await field.read(decode=True)
                    if len(value)>32:raise ValueError('Invalid trim range.')
                    data[field.name]=float(value.decode())
            token=await service.register(temporary,temporary=True)
        else:
            data=await request.json()
            if not isinstance(data,dict):raise ValueError('Invalid cut preview request.')
            token=data.get('token')
            if not token:
                if data.get('source_id'):
                    p=character_swap.session(studio.store)
                    source=next((r for r in p.get('swap_sources',[]) if r['id']==data['source_id']),None)
                    if source is None:raise ValueError('Choose an imported source video.')
                    path=studio.store.file(p['id'],source['file'])
                else:
                    p=studio.store.load(data['project_id']);s=studio.store.shot(p,data['shot_id'])
                    draft=next((d for d in s['drafts'] if d['id']==data['draft_id'] and d['status']=='succeeded' and d.get('file')),None)
                    if draft is None or s.get('mode')!='video':raise ValueError('Choose a completed video.')
                    path=studio.store.file(p['id'],draft['file'])
                token=await service.register(path)
        result=await service.scan(token,data.get('start'),data.get('end'))
        return web.json_response(result)
    except BaseException:
        if temporary is not None and token is None:temporary.unlink(missing_ok=True)
        raise
