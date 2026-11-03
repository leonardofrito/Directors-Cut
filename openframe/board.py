"""Small on-demand image thumbnails; full-resolution originals stay untouched."""
import asyncio
from pathlib import Path
from aiohttp import web
from PIL import Image, ImageOps

_slots = asyncio.Semaphore(2)


async def thumbnail(request, store):
    project = store.load(request.match_info['project'])
    shot = store.shot(project, request.match_info['shot'])
    draft = next((d for d in shot['drafts'] if d['id'] == request.match_info['draft'] and d['status']=='succeeded'), None)
    if not draft or shot.get('mode')!='asset':
        raise ValueError('Choose a completed asset image.')
    source = store.file(project['id'], draft['file'])
    stamp = source.stat().st_mtime_ns
    target = store.file(project['id'], f'.thumbnails/{draft["id"]}-{stamp}.jpg')
    def make():
        target.parent.mkdir(parents=True, exist_ok=True)
        with Image.open(source) as original:
            if original.width*original.height>40_000_000:
                raise ValueError('Image is too large to preview.')
            image = ImageOps.exif_transpose(original)
            image.thumbnail((512,512))
            if image.mode=='RGBA':
                background=Image.new('RGB',image.size,'#080808');background.paste(image,mask=image.getchannel('A'));image=background
            image.convert('RGB').save(target,'JPEG',quality=75,optimize=True)
    if not target.exists():
        async with _slots:
            if not target.exists():await asyncio.to_thread(make)
    return web.FileResponse(target,headers={'Cache-Control':'private, max-age=86400'})
