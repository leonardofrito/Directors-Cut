"""Shot-owned motion clips, normalized on CPU before H3 reference conditioning."""
import asyncio
import os
from pathlib import Path
import shutil
import uuid
import logging

from .storage import now

MAX_VIDEO = 128 * 1024 * 1024


def ffmpeg_path():
    configured = os.environ.get('OPENFRAME_FFMPEG') or shutil.which('ffmpeg')
    if configured:
        return str(configured)
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        from .engine_config import current
        root = Path(current().get('comfy_root') or '.')
        candidates=[]
        for environment in [root/'.venv',root.parent/'.venv',root/'venv',root.parent/'python_embeded']:
            for pattern in ['Lib/site-packages/imageio_ffmpeg/binaries/ffmpeg*','lib/python*/site-packages/imageio_ffmpeg/binaries/ffmpeg*']:
                candidates.extend(p for p in sorted(environment.glob(pattern)) if p.is_file() and (os.name=='nt' and p.suffix=='.exe' or os.name!='nt' and os.access(p,os.X_OK)))
        if candidates:
            return str(candidates[0])
    raise ValueError('Install FFmpeg or set OPENFRAME_FFMPEG to import a motion video.')


async def run_ffmpeg(*arguments, error_message='Could not read this video. Choose a valid MP4, MOV or WebM file.'):
    options = {'creationflags': 0x08000000} if os.name == 'nt' else {}
    environment=os.environ.copy()
    if getattr(__import__('sys'),'frozen',False):
        if 'LD_LIBRARY_PATH_ORIG' in environment:environment['LD_LIBRARY_PATH']=environment['LD_LIBRARY_PATH_ORIG']
        else:environment.pop('LD_LIBRARY_PATH',None)
    process = await asyncio.create_subprocess_exec(ffmpeg_path(), '-hide_banner', '-loglevel', 'error', '-nostdin',
        *map(str, arguments), stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE, env=environment, **options)
    try:
        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=120)
    except (asyncio.TimeoutError, asyncio.CancelledError):
        process.kill()
        await process.wait()
        raise
    if process.returncode:
        logging.getLogger(__name__).warning('FFmpeg rejected media: %s', stderr.decode('utf-8', errors='replace')[-1200:].strip())
        raise ValueError(error_message)
    return stdout.decode('utf-8', errors='replace')


async def attach(request, store):
    project = store.load(request.match_info['project'])
    shot = store.shot(project, request.match_info['shot'])
    if shot.get('mode') != 'video':
        raise ValueError('Motion videos belong to video shots.')
    reader = await request.multipart()
    part = await reader.next()
    if part is None or part.name != 'video' or not part.filename:
        raise ValueError('Choose a motion video.')
    suffix = Path(part.filename).suffix.lower()
    if suffix not in ('.mp4', '.mov', '.webm', '.mkv', '.m4v'):
        raise ValueError('Choose an MP4, MOV or WebM video.')
    ident = uuid.uuid4().hex
    folder = store.file(project['id'], 'references/motion')
    folder.mkdir(parents=True, exist_ok=True)
    original, target, poster = folder / (ident + '.upload' + suffix), folder / (ident + '.mp4'), folder / (ident + '.jpg')
    complete = False
    try:
        size = 0
        with original.open('xb') as output:
            while chunk := await part.read_chunk(1024 * 1024):
                size += len(chunk)
                if size > MAX_VIDEO:
                    raise ValueError('Choose a motion video up to 128 MB.')
                await asyncio.to_thread(output.write, chunk)
        # Bound decoding memory: 24 fps, at most 15 seconds, no source soundtrack.
        progress = await run_ffmpeg('-threads', '2', '-i', original, '-t', '15', '-an', '-vf',
            "fps=24,scale=w='min(512,iw)':h='min(512,ih)':force_original_aspect_ratio=decrease:force_divisible_by=2",
            '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '21', '-threads', '2', '-movflags', '+faststart',
            '-progress', 'pipe:1', '-y', target)
        frames = max((int(line.split('=')[1]) for line in progress.splitlines() if line.startswith('frame=')), default=0)
        if frames < 48:
            raise ValueError('Choose a motion video at least 2 seconds long.')
        await run_ffmpeg('-i', target, '-frames:v', '1', '-threads', '1', '-y', poster)
        project = store.load(project['id'])
        shot = store.shot(project, shot['id'])
        ref = dict(id=ident, name=Path(part.filename).name[:120], file=f'references/motion/{ident}.mp4',
            thumbnail=f'references/motion/{ident}.jpg', duration=round(frames/24, 2), fps=24, created_at=now())
        project.setdefault('motion_references', []).append(ref)
        shot['motion_reference_id'] = ident
        store.save(project)
        complete = True
        return project
    finally:
        original.unlink(missing_ok=True)
        if not complete:
            target.unlink(missing_ok=True)
            poster.unlink(missing_ok=True)


def resolve(project, settings):
    ident = settings.get('motion_reference_id', '')
    if not ident:
        return None
    ref = next((r for r in project.get('motion_references', []) if r['id'] == ident), None)
    if ref is None:
        raise ValueError('This motion reference is no longer available.')
    return dict(ref)
