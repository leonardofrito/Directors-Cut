"""Shot-owned speech guidance and a separate exact final-soundtrack replacement."""
import array
import asyncio
from pathlib import Path
import sys
import uuid
import wave
import shutil

from .motion_reference import run_ffmpeg
from .storage import now

MAX_AUDIO = 64 * 1024 * 1024
MAX_VIDEO = 128 * 1024 * 1024
VIDEO_EXTENSIONS = {'.mp4', '.mov', '.mkv', '.m4v', '.webm'}
SLOTS = {'reference': 'audio_reference_id', 'output': 'output_audio_id'}


def waveform(path):
    with wave.open(str(path), 'rb') as source:
        duration = source.getnframes() / source.getframerate()
        chunk = max(1, source.getnframes() // 48)
        peaks = []
        for _ in range(48):
            samples = array.array('h', source.readframes(chunk))
            if sys.byteorder != 'little':
                samples.byteswap()
            peaks.append(max((abs(n) for n in samples), default=0))
    maximum = max(max(peaks), 1)
    return duration, [round(max(.04, n / maximum), 3) for n in peaks]


async def attach(request, store):
    kind = request.match_info['kind']
    if kind not in SLOTS:
        raise ValueError('Choose reference audio or final audio.')
    project = store.load(request.match_info['project'])
    shot = store.shot(project, request.match_info['shot'])
    if shot.get('mode') != 'video':
        raise ValueError('Audio belongs to video shots.')
    reader = await request.multipart()
    part = await reader.next()
    if part is None or part.name != 'audio' or not part.filename:
        raise ValueError('Choose an audio file.')
    suffix = Path(part.filename).suffix.lower()
    if suffix not in {'.wav', '.mp3', '.flac', '.ogg', '.m4a', '.aac', '.aiff', '.aif', '.opus'} | VIDEO_EXTENSIONS:
        raise ValueError('Choose an audio file or a video with an audio track.')
    limit = MAX_VIDEO if suffix in VIDEO_EXTENSIONS else MAX_AUDIO
    ident = uuid.uuid4().hex
    folder = store.file(project['id'], 'references/audio')
    folder.mkdir(parents=True, exist_ok=True)
    original, target = folder / (ident + '.upload' + suffix), folder / (ident + '.wav')
    complete = False
    try:
        size = 0
        with original.open('xb') as destination:
            while chunk := await part.read_chunk(1024 * 1024):
                size += len(chunk)
                if size > limit:
                    raise ValueError('Choose video up to 128 MB or audio up to 64 MB.')
                await asyncio.to_thread(destination.write, chunk)
        await run_ffmpeg('-threads', '2', '-i', original, '-t', '15' if kind == 'reference' else '30',
            '-vn', '-ac', '2', '-ar', '48000', '-c:a', 'pcm_s16le', '-threads', '2', '-y', target,
            error_message='Could not read an audio track from this file.')
        duration, peaks = await asyncio.to_thread(waveform, target)
        if duration < .25:
            raise ValueError('Choose an audio clip at least a quarter of a second long.')
        project = store.load(project['id'])
        shot = store.shot(project, shot['id'])
        ref = dict(id=ident, kind=kind, name=Path(part.filename).name[:120], file=f'references/audio/{ident}.wav',
            duration=round(duration, 2), waveform=peaks, created_at=now())
        project.setdefault('audio_references', []).append(ref)
        shot[SLOTS[kind]] = ident
        store.save(project)
        complete = True
        return project
    finally:
        original.unlink(missing_ok=True)
        if not complete:
            target.unlink(missing_ok=True)


def resolve(project, settings, slot):
    ident = settings.get(SLOTS[slot], '')
    if not ident:
        return None
    ref = next((r for r in project.get('audio_references', []) if r['id'] == ident), None)
    if ref is None:
        raise ValueError('This audio file is no longer available.')
    return dict(ref)


async def replace_soundtrack(video, audio):
    """Keep the original picture stream. Trim/pad the new audio to that video."""
    temporary = video.with_name(video.stem + '.soundtrack.mp4')
    try:
        original = video.with_name(video.stem + '.generated.mp4')
        if not original.exists():
            await asyncio.to_thread(shutil.copyfile, video, original)
        await run_ffmpeg('-threads', '2', '-i', video, '-threads', '2', '-i', audio,
            '-map', '0:v:0', '-map', '1:a:0', '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k',
            '-af', 'apad', '-shortest', '-movflags', '+faststart', '-threads', '2', '-y', temporary,
            error_message='The video was saved, but the final soundtrack could not be applied.')
        for attempt in range(5):
            try:
                temporary.replace(video)
                break
            except PermissionError:
                if attempt == 4:
                    raise
                await asyncio.sleep(.08)
    finally:
        temporary.unlink(missing_ok=True)


async def restore_soundtrack(video):
    original = video.with_name(video.stem + '.generated.mp4')
    if not original.is_file():
        raise ValueError('There is no original generated soundtrack to restore.')
    temporary = video.with_name(video.stem + '.restore.mp4')
    try:
        await asyncio.to_thread(shutil.copyfile, original, temporary)
        for attempt in range(5):
            try:
                temporary.replace(video)
                break
            except PermissionError:
                if attempt == 4:
                    raise
                await asyncio.sleep(.08)
    finally:
        temporary.unlink(missing_ok=True)
