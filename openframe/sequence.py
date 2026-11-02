"""Ordered, whole-take sequences and CPU-only MP4 / OpenTimelineIO bundles."""
import asyncio
import copy
import json
import math
import os
import re
import shutil
import tempfile
import uuid
import zipfile
from fractions import Fraction
from pathlib import Path
from aiohttp import web
from .motion_reference import ffmpeg_path


def video_shots(project):
    return [s for s in project['shots'] if s.get('mode') == 'video']


def ordered_take(shot):
    completed = [d for d in shot.get('drafts', []) if d.get('status') == 'succeeded' and d.get('file')]
    return next((d for d in completed if d['id'] == (shot.get('approved') or {}).get('draft_id')), completed[-1] if completed else None)


def reorder(project, ids):
    existing = video_shots(project)
    if not isinstance(ids, list) or any(not isinstance(i, str) for i in ids) or len(ids) != len(existing) or set(ids) != {s['id'] for s in existing}:
        raise ValueError('The shot list changed. Refresh the Library and reorder again.')
    mapping = {s['id']: s for s in existing}
    positions = iter(ids)
    project['shots'] = [mapping[next(positions)] if s.get('mode') == 'video' else s for s in project['shots']]


def safe_name(name):
    return re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', str(name)).strip().rstrip('.')[:120] or 'Sequence'


async def command(*args, timeout=1800, check=True):
    options = {'creationflags': 0x08000000} if os.name == 'nt' else {}
    process = await asyncio.create_subprocess_exec(*map(str, args), stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE, **options)
    try:
        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout)
    except BaseException:
        if process.returncode is None:
            process.kill()
            await process.wait()
        raise
    if check and process.returncode:
        raise ValueError('Video export failed: ' + stderr.decode('utf-8', errors='replace')[-700:].strip())
    return stdout, stderr


async def probe(path):
    ffmpeg = Path(ffmpeg_path())
    ffprobe = ffmpeg.with_name('ffprobe.exe' if os.name == 'nt' else 'ffprobe')
    binary = str(ffprobe) if ffprobe.is_file() else shutil.which('ffprobe')
    if binary:
        stdout, _ = await command(binary, '-v', 'error', '-show_streams', '-show_format', '-of', 'json', path, timeout=30)
        data = json.loads(stdout)
        video = next((s for s in data['streams'] if s.get('codec_type') == 'video'), None)
        if not video:
            raise ValueError('A selected take has no video stream.')
        fps = float(Fraction(video.get('avg_frame_rate') or video.get('r_frame_rate') or '24'))
        duration = float(video.get('duration') or data['format']['duration'])
        frames = int(video.get('nb_frames') or round(duration * fps))
        result = dict(width=int(video['width']), height=int(video['height']), fps=fps, duration=frames / fps, frames=frames,
                      audio=any(s.get('codec_type') == 'audio' for s in data['streams']))
    else:
        _, stderr = await command(ffmpeg, '-hide_banner', '-i', path, timeout=30, check=False)
        text = stderr.decode('utf-8', errors='replace')
        duration = re.search(r'Duration: (\d+):(\d+):(\d+(?:\.\d+)?)', text)
        video = re.search(r'Video:.*?\b(\d{2,5})x(\d{2,5})\b.*?([\d.]+) fps', text)
        if not duration or not video:
            raise ValueError('Could not read video timing. Install FFprobe with FFmpeg.')
        fps = float(video[3]); seconds = int(duration[1])*3600 + int(duration[2])*60 + float(duration[3])
        result = dict(width=int(video[1]), height=int(video[2]), fps=fps, duration=seconds, frames=round(seconds*fps), audio='Audio:' in text)
    if not 0 < result['fps'] <= 240 or not 0 < result['duration'] <= 3600:
        raise ValueError('Unsupported video duration or frame rate.')
    return result


def rational(value, rate):
    return {'OTIO_SCHEMA': 'RationalTime.1', 'value': value, 'rate': rate}


def time_range(frames, rate):
    return {'OTIO_SCHEMA': 'TimeRange.1', 'start_time': rational(0, rate), 'duration': rational(frames, rate)}


def otio_timeline(name, rows):
    tracks = []
    for kind in ('Video', 'Audio'):
        children = []
        for row in rows:
            span = time_range(row['frames'], row['fps'])
            if kind == 'Audio' and not row['audio']:
                children.append({'OTIO_SCHEMA': 'Gap.1', 'name': '', 'metadata': {}, 'source_range': span, 'effects': [], 'markers': []})
                continue
            children.append({'OTIO_SCHEMA': 'Clip.1', 'name': row['title'], 'metadata': {'directors_cut': {'shot_id': row['shot_id'], 'take_id': row['take_id']}},
                'source_range': span, 'effects': [], 'markers': [], 'media_reference': {'OTIO_SCHEMA': 'ExternalReference.1', 'name': row['title'],
                'metadata': {}, 'target_url': row['media'], 'available_range': span}})
        tracks.append({'OTIO_SCHEMA': 'Track.1', 'name': 'Shots' if kind == 'Video' else 'Original audio', 'kind': kind,
                       'metadata': {}, 'source_range': None, 'effects': [], 'markers': [], 'children': children})
    return {'OTIO_SCHEMA': 'Timeline.1', 'name': name, 'metadata': {}, 'global_start_time': rational(0, 24),
            'tracks': {'OTIO_SCHEMA': 'Stack.1', 'name': 'Sequence', 'metadata': {}, 'source_range': None, 'effects': [], 'markers': [], 'children': tracks}}


def bundle(destination, name, rows):
    with zipfile.ZipFile(destination, 'w', compression=zipfile.ZIP_STORED, allowZip64=True) as archive:
        archive.writestr('version.txt', '1.0.0')
        archive.writestr('content.otio', json.dumps(otio_timeline(name, rows), ensure_ascii=False, indent=2))
        for row in rows:
            archive.write(row['path'], row['media'])


class Exporter:
    def __init__(self, store):
        self.store = store
        self.jobs = {}
        self.tasks = set()

    async def close(self):
        for task in self.tasks:
            task.cancel()
        await asyncio.gather(*self.tasks, return_exceptions=True)

    def start(self, project, format):
        if format not in ('mp4', 'resolve'):
            raise ValueError('Choose MP4 or DaVinci Resolve.')
        running = next((job for job in self.jobs.values() if job['status'] in ('queued', 'running')), None)
        if running:
            if running['project_id'] == project['id'] and running['format'] == format:
                return running
            raise ValueError('Wait for the current sequence export to finish.')
        shots = [s for s in video_shots(project) if ordered_take(s)]
        if not shots:
            raise ValueError('This project has no completed video takes.')
        if len(shots) > 200:
            raise ValueError('Export up to 200 completed shots at a time.')
        rows = []
        for index, shot in enumerate(shots if project.get('editor_timeline') is None else []):
            take = ordered_take(shot)
            path = self.store.file(project['id'], take['file'])
            if not path.is_file() or path.suffix.lower() != '.mp4':
                raise ValueError('A sequence video is missing.')
            rows.append(dict(path=path, title=shot['title'], shot_id=shot['id'], take_id=take['id'], media=f'media/{index+1:03d} - {safe_name(shot["title"])}.mp4'))
        edit = copy.deepcopy(project.get('editor_timeline'))
        if edit is not None:
            from . import timeline
            rows = timeline.source_rows(self.store, project, edit)
        key = uuid.uuid4().hex
        job = dict(id=key, project_id=project['id'], status='queued', format=format, completed=0, total=len(rows), name=safe_name(project['name']) + ('.mp4' if format == 'mp4' else '.otioz'))
        self.jobs[key] = job
        task = asyncio.create_task(self.run(job, rows, project['name'], edit))
        self.tasks.add(task);task.add_done_callback(self.tasks.discard)
        # Keep bounded in-memory status history; files remain explicit project exports.
        for old in list(self.jobs)[:-30]:
            if self.jobs[old]['status'] not in ('queued', 'running'):
                self.jobs.pop(old, None)
        return job

    async def run(self, job, rows, name, edit=None):
        relative = f'exports/sequence-{job["id"]}/' + job['name']
        destination = self.store.file(job['project_id'], relative)
        destination.parent.mkdir(parents=True, exist_ok=True)
        try:
            job['status'] = 'running'
            for row in rows:
                row.update(await probe(row['path']))
            if edit is not None:
                from . import timeline
                edit = timeline.validate(edit, rows)
                if job['format'] == 'resolve':
                    await asyncio.to_thread(timeline.bundle, destination, name, edit, rows)
                    job['completed'] = job['total']
                else:
                    await timeline.render(destination, edit, rows, job)
                job.update(status='succeeded', download=relative)
                return
            if sum(row['duration'] for row in rows) > 7200:
                raise ValueError('Export sequences up to two hours.')
            if job['format'] == 'resolve':
                await asyncio.to_thread(bundle, destination, name, rows)
                job['completed'] = len(rows)
            else:
                # Normalize one clip at a time on CPU to bound memory, then concatenate.
                with tempfile.TemporaryDirectory(prefix='sequence-', dir=destination.parent) as scratch:
                    folder = Path(scratch)
                    width, height = rows[0]['width']//2*2, rows[0]['height']//2*2
                    width, height = max(2, width), max(2, height)
                    for index, row in enumerate(rows):
                        frames = max(1, round(row['duration'] * 24));seconds = frames / 24
                        args = [ffmpeg_path(), '-hide_banner', '-loglevel', 'error', '-nostdin', '-y', '-threads', '2', '-i', row['path']]
                        if not row['audio']:
                            args += ['-f', 'lavfi', '-i', 'anullsrc=channel_layout=stereo:sample_rate=48000']
                        args += ['-map','0:v:0','-map','0:a:0' if row['audio'] else '1:a:0', '-filter_threads','1',
                                 '-vf', f'scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:color=black,setsar=1,fps=24',
                                 '-af', f'apad,atrim=duration={seconds:.6f},asetpts=PTS-STARTPTS', '-t', f'{seconds:.6f}',
                                 '-c:v','libx264','-preset','veryfast','-crf','18','-pix_fmt','yuv420p','-threads','2','-c:a','aac','-b:a','192k','-ar','48000','-ac','2',folder/f'{index:04d}.mp4']
                        await command(*args);job['completed'] = index+1
                    listing = folder/'list.txt'
                    listing.write_text(''.join(f"file '{i:04d}.mp4'\n" for i in range(len(rows))), encoding='utf-8')
                    await command(ffmpeg_path(), '-hide_banner','-loglevel','error','-nostdin','-y','-f','concat','-safe','1','-i',listing,'-c','copy','-movflags','+faststart',destination)
            job.update(status='succeeded', download=relative)
        except asyncio.CancelledError:
            destination.unlink(missing_ok=True);job.update(status='cancelled');raise
        except Exception as error:
            destination.unlink(missing_ok=True);job.update(status='failed', error=str(error))


async def save_order(request):
    data = await request.json()
    studio = request.app['studio'];project = studio.store.load(request.match_info['project'])
    reorder(project, data.get('ids'));studio.store.save(project)
    return web.json_response(project)


async def start_export(request):
    studio = request.app['studio'];project = studio.store.load(request.match_info['project'])
    return web.json_response(studio.sequence_exports.start(project, (await request.json()).get('format', 'mp4')))


async def export_status(request):
    job = request.app['studio'].sequence_exports.jobs.get(request.match_info['job'])
    if not job or job['project_id'] != request.match_info['project']:
        raise web.HTTPNotFound()
    return web.json_response(job)
