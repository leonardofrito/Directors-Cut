import asyncio
import ipaddress
import json
import logging
import os
import re
import secrets
import uuid
from pathlib import Path
from urllib.parse import urlsplit

import aiohttp
from aiohttp import web

from .provider import CAMERAS, RATIOS, STYLE, OPTICS, LIGHTING, FILM, GRADE, ComfyProvider, GenerationCancelled, build_graph, image_dimensions
from .presets import F_STOPS, FILM_PALETTES, LENS_TYPES, SENSORS, FOCAL_LENGTHS, LIGHT_COLORS, PALETTES, FRAMING, legacy_camera
from .enhancer import availability as enhancer_availability
from .loras import availability as lora_availability, validate_loras
from .storage import Store, now, write_json
from .catalog import describe, entry, EDITABLE
from .assets import add_asset, resolve_references, merge_assets, delete_asset, rename_asset, sync_asset_studies, fork_asset_study, edit_reference, MAX_UPLOAD
from .presets import snap_focal_length
from .characters import CATEGORIES, validate_traits
from .asset_presets import ASSET_CATEGORIES, validate_choices, asset_prompt, preview_images
from . import video
from .model_install import import_video_file
from . import model_downloads, engine_config, engine_connection
from . import reference_uploads, motion_reference, audio_reference, project_cover, edit_presets, rtx_upscale
from . import app_control
from .paths import DATA_ROOT

ROOT = Path(__file__).resolve().parent.parent
LOG = logging.getLogger('openframe')
ACTIVE = {'queued', 'submitting', 'running', 'pending', 'downloading'}


def allowed_host(authority):
    try:
        host = urlsplit('//'+authority).hostname
        if host in ('localhost', '127.0.0.1', '::1'):
            return True
        if os.environ.get('OPENFRAME_HOST', '127.0.0.1') in ('127.0.0.1', 'localhost', '::1'):
            return False
        address = ipaddress.ip_address(host)
        # Accept LAN and Tailscale IPs without trusting arbitrary DNS names.
        return not (address.is_unspecified or address.is_multicast) and (
            address.is_private or address in ipaddress.ip_network('100.64.0.0/10'))
    except ValueError:
        return False


@web.middleware
async def errors(request, handler):
    # Network mode keeps Host validation and same-origin writes enabled.
    if not allowed_host(request.host):
        raise web.HTTPForbidden(text='Use the local, LAN or Tailscale IP address.')
    if request.method != 'GET' and request.headers.get('Origin') not in (None, f'http://{request.host}'):
        raise web.HTTPForbidden(text='Cross-origin request refused.')
    try:
        return await handler(request)
    except (ValueError, KeyError, StopIteration, json.JSONDecodeError) as exc:
        return web.json_response({'error': str(exc) or 'Item not found.'}, status=400)
    except FileNotFoundError:
        return web.json_response({'error': 'Project or file not found.'}, status=404)
    except web.HTTPException:
        raise
    except Exception:
        LOG.exception('Request failed')
        return web.json_response({'error': 'Request failed. See the application log.'}, status=500)


class Studio:
    def __init__(self):
        engine_config.apply_environment(engine_config.current())
        self.connection = engine_connection.Connection()
        self.connection_changing = False
        self.store = Store()
        self.queue = asyncio.Queue()
        self.progress = {}
        self.provider = None
        self.queue_serial = 0
        self.audio_locks = {}
        self.upscale_locks = {}
        self.model_downloads = model_downloads.ModelDownloads()

    async def nodes(self):
        base = os.environ.get('OPENFRAME_COMFY_URL', 'http://127.0.0.1:8188')
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
            async with session.get(base + '/object_info') as response:
                response.raise_for_status()
                return await response.json()

    async def gpu_devices(self):
        base = os.environ.get('OPENFRAME_COMFY_URL', 'http://127.0.0.1:8188')
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5)) as session:
            async with session.get(base + '/system_stats') as response:
                response.raise_for_status()
                self.engine_system_stats = await response.json()
                return self.engine_system_stats.get('devices', [])

    async def gpu_memory(self):
        await self.gpu_devices()
        return engine_config.hardware(self.engine_system_stats)['memory_total']

    async def worker(self):
        while True:
            project_id, shot_id, draft_id = await self.queue.get()
            project = self.store.load(project_id)
            shot = self.store.shot(project, shot_id)
            draft = next(d for d in shot['drafts'] if d['id'] == draft_id)
            async def update(**changes):
                # Re-read to preserve edits/approvals made while a job is running.
                current = self.store.load(project_id)
                current_shot = self.store.shot(current, shot_id)
                current_draft = next(d for d in current_shot['drafts'] if d['id'] == draft_id)
                if current_draft.get('cancel_requested') and changes.get('job_id') and not current_draft.get('cancel_sent'):
                    current_draft['job_id'] = changes['job_id']
                    self.store.save(current)
                    try:
                        await self.provider.cancel(changes['job_id'])
                        sent = True
                    except Exception:
                        LOG.exception('Cancellation request failed; generation remains active')
                        sent = False
                    current = self.store.load(project_id)
                    current_shot = self.store.shot(current, shot_id)
                    current_draft = next(d for d in current_shot['drafts'] if d['id'] == draft_id)
                    current_draft['cancel_sent'] = sent
                    if not sent:
                        current_draft['cancel_requested'] = False
                    self.store.save(current)
                self.progress[draft_id] = {**self.progress.get(draft_id, {}), **changes}
                durable = {k: v for k, v in changes.items() if k in ('job_id', 'status', 'error', 'enhanced_prompt', 'full_prompt', 'prompt_note', 'enhancer_output', 'applied_output_audio_id', 'audio_applied_at')}
                if any(current_draft.get(k) != v for k, v in durable.items()):
                    current_draft.update(durable)
                    self.store.save(current)
                    if changes.get('status') == 'succeeded':
                        sync_asset_studies(self.store, current)
            try:
                if draft['status'] == 'cancelled':
                    continue
                target = self.store.file(project_id, draft['file'])
                target.parent.mkdir(parents=True, exist_ok=True)
                graph_path = self.store.file(project_id, draft['workflow'])
                graph = json.loads(graph_path.read_text(encoding='utf-8'))
                await update(status='submitting' if not draft.get('job_id') else 'running')
                await self.provider.generate(graph, target, update, draft.get('job_id'))
                if draft.get('settings', {}).get('output_audio_id'):
                    await update(status='downloading', stage='Applying final audio', sampling=False)
                    ref = draft['settings']['output_audio']
                    await audio_reference.replace_soundtrack(target, self.store.file(project_id, ref['file']))
                    await update(applied_output_audio_id=ref['id'], audio_applied_at=now())
                await update(status='succeeded', progress=1)
            except GenerationCancelled:
                await update(status='cancelled', stage='Cancelled')
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                LOG.exception('Generation failed')
                await update(status='failed', error=str(exc))
            finally:
                self.queue.task_done()

    def restore_queue(self):
        pending = []
        for p in self.store.list():
            changed = False
            for s in p['shots']:
                for index, d in enumerate(s['drafts']):
                    self.queue_serial = max(self.queue_serial, d.get('queue_order', 0))
                    if d['status'] not in ACTIVE:
                        continue
                    if d['status'] != 'queued' and not d.get('job_id'):
                        d.update(status='failed', error='Submission was interrupted. Check the ComfyUI queue before regenerating.')
                        changed = True
                    else:
                        # Resume submitted work first; waiting items retain global FIFO order.
                        pending.append((not bool(d.get('job_id')), d.get('created_at', ''), d.get('queue_order', 0), p['id'], s['id'], index, d['id']))
            if changed:
                self.store.save(p)
        for _, _, _, project_id, shot_id, _, draft_id in sorted(pending):
            self.queue.put_nowait((project_id, shot_id, draft_id))

    async def lifecycle(self, app):
        await self.connection.startup()
        self.provider = ComfyProvider()
        self.restore_queue()
        worker = asyncio.create_task(self.worker())
        yield
        worker.cancel()
        await asyncio.gather(worker, return_exceptions=True)
        await self.provider.close()
        await self.model_downloads.close()
        await self.connection.close()

    def queue_items(self):
        items = []
        for p in self.store.list():
            for s in p['shots']:
                for index, saved in enumerate(s['drafts']):
                    d = {**saved, **self.progress.get(saved['id'], {})}
                    if d['status'] not in ACTIVE:
                        continue
                    settings = d.get('settings', {})
                    items.append(dict(id=d['id'], project_id=p['id'], project_name=p['name'], shot_id=s['id'],
                                      title=settings.get('title', s['title']) + (' Â· RTX Upscale' if d.get('postprocess', {}).get('type') == 'rtx-upscale' else ''), take=d.get('number', index + 1),
                                      status=d['status'], progress=d.get('progress', 0), stage=d.get('stage', ''),
                                      created_at=d.get('created_at', ''), queue_order=d.get('queue_order', 0), workflow_id=settings.get('workflow_id', 'qwen21'),
                                      seed=settings.get('seed'), ratio=settings.get('ratio', ''),
                                      can_cancel=d['status'] == 'queued' and not d.get('job_id')))
        items.sort(key=lambda item: (item['can_cancel'], item['created_at'], item['queue_order'], item['take']))
        position = 0
        for item in items:
            if item['can_cancel']:
                position += 1
                item['position'] = position
            else:
                item['position'] = 0
        return items

    async def preview_status(self, request):
        folder = DATA_ROOT / '.runtime/preset-previews'
        if request.method == 'POST':
            action = (await request.json()).get('action')
            if action not in ('pause', 'resume', 'stop'):
                raise ValueError('Unknown preview action.')
            folder.mkdir(parents=True, exist_ok=True)
            if action == 'pause':
                (folder / 'pause').touch()
            elif action == 'stop':
                (folder / 'stop').touch()
            else:
                (folder / 'pause').unlink(missing_ok=True)
                (folder / 'stop').unlink(missing_ok=True)
        path = folder / 'progress.json'
        status = json.loads(path.read_text(encoding='utf-8')) if path.exists() else dict(status='idle', ready=0, total=0)
        status['pause_requested'] = (folder / 'pause').exists()
        status['stop_requested'] = (folder / 'stop').exists()
        return web.json_response(status)

    async def generation_queue(self, request):
        items = self.queue_items()
        return web.json_response(dict(items=items, waiting=sum(i['can_cancel'] for i in items), running=sum(not i['can_cancel'] for i in items)))

    async def cancel_queued(self, request):
        p = self.store.load(request.match_info['project'])
        shot = self.store.shot(p, request.match_info['shot'])
        draft = next(d for d in shot['drafts'] if d['id'] == request.match_info['draft'])
        if draft['status'] == 'cancelled':
            return web.json_response(dict(cancelled=True))
        if draft['status'] not in ACTIVE:
            raise ValueError('This take has already finished.')
        if draft.get('job_id') or draft['status'] != 'queued':
            draft['cancel_requested'] = True
            self.store.save(p)
            self.progress[draft['id']] = {**self.progress.get(draft['id'], {}), 'stage':'Stoppingâ€¦'}
            if draft.get('job_id'):
                try:
                    await self.provider.cancel(draft['job_id'])
                except Exception:
                    current=self.store.load(p['id']);s=self.store.shot(current,shot['id'])
                    d=next(d for d in s['drafts'] if d['id']==draft['id']);d['cancel_requested']=False;self.store.save(current)
                    self.progress[draft['id']]['stage']='Unable to stop. Try again.'
                    raise
                current=self.store.load(p['id']);s=self.store.shot(current,shot['id'])
                d=next(d for d in s['drafts'] if d['id']==draft['id']);d['cancel_sent']=True;self.store.save(current)
            return web.json_response(dict(cancelled=False, cancel_requested=True))
        draft['status'] = 'cancelled'
        self.progress[draft['id']] = dict(status='cancelled')
        self.store.save(p)
        return web.json_response(dict(cancelled=True))

    async def config(self, request):
        online, detail = False, ''
        nodes = {}
        vram_total = None
        devices = []
        try:
            nodes = await self.nodes()
            devices = await self.gpu_devices()
            vram_total = engine_config.hardware(self.engine_system_stats)['memory_total'] or None
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5)) as session:
                async with session.get(os.environ['COMFY_BASE_URL'] + '/api/v2/jobs?limit=1') as response:
                    response.raise_for_status()
                online = True
        except Exception as exc:
            detail = str(exc)
        return web.json_response(dict(rtx_upscale=rtx_upscale.availability(nodes, devices), styles=list(STYLE), cameras=CAMERAS, ratios=list(RATIOS), lenses=list(OPTICS), lighting=list(LIGHTING), films=list(FILM), grades=list(GRADE), lens_types=list(LENS_TYPES), sensors=list(SENSORS), focal_lengths=FOCAL_LENGTHS, light_colors=list(LIGHT_COLORS), palettes=PALETTES, film_palettes=FILM_PALETTES, f_stops=F_STOPS, legacy_camera_defaults={key: legacy_camera({'lens': key}) for key in OPTICS},
            image_edit_presets=edit_presets.choices(), preset_hints={'style': STYLE, 'camera': FRAMING, 'lens_type': LENS_TYPES, 'sensor': SENSORS, 'lighting': LIGHTING, 'light_color': LIGHT_COLORS, 'film': FILM, 'grade': GRADE}, preview_generation_enabled=False, preview_images=preview_images(), asset_categories=ASSET_CATEGORIES, character_categories=CATEGORIES, enhancer=enhancer_availability(nodes, 'qwen21'), loras=lora_availability(nodes), video=video.availability(nodes, vram_total), workflows=describe(nodes), output_dir=str(self.store.root), online=online, detail=detail))

    async def projects(self, request):
        if request.method == 'POST':
            return web.json_response(self.store.create((await request.json())['name']))
        if request.query.get('summary') == '1':
            return web.json_response([dict(id=p['id'], name=p['name'], updated_at=p['updated_at'],
                cover_image=p.get('cover_image'), cover_revision=p.get('cover_revision'),
                asset_count=sum(s.get('mode') == 'asset' for s in p['shots']),
                shot_count=sum(s.get('mode') == 'video' for s in p['shots'])) for p in self.store.list()])
        return web.json_response(self.store.list())

    async def project(self, request):
        p = self.store.load(request.match_info['project'])
        if request.method == 'DELETE':
            confirmation = await request.json()
            p = self.store.load(request.match_info['project'])
            if confirmation.get('confirm_name') != p['name']:
                raise ValueError('Confirm the project name before deleting it.')
            if any(self.progress.get(d['id'], {}).get('status', d['status']) in ACTIVE
                   for s in p['shots'] for d in s.get('drafts', [])):
                raise ValueError('Finish or cancel this projectâ€™s queued generations before deleting it.')
            self.store.remove(p['id'])
            return web.json_response(dict(deleted=p['id']))
        sync_asset_studies(self.store, p)
        for shot in p['shots']:
            for draft in shot['drafts']:
                draft.update(self.progress.get(draft['id'], {}))
                # An image is usable only after its download has finished.
                if draft['status'] == 'succeeded' and not self.store.file(p['id'], draft['file']).exists():
                    draft['status'] = 'running'
        return web.json_response(p)

    async def shots(self, request):
        p = self.store.load(request.match_info['project'])
        data = await request.json()
        is_video = data.get('mode') == 'video'
        settings = video.settings(data.get('settings', {})) if is_video else self.settings(data['settings']) if 'settings' in data else {}
        shot = self.store.add_shot(p)
        if data.get('mode') == 'asset':
            shot.update(mode='asset', title='New asset', reference_ids=[])
        shot.update(settings)
        shot['mode'] = 'video' if is_video else 'asset' if data.get('mode') == 'asset' else 'storyboard'
        self.store.save(p)
        sync_asset_studies(self.store, p)
        return web.json_response(shot)

    async def assets(self, request):
        pid = request.match_info['project']
        if request.method == 'GET':
            project = self.store.load(pid)
            sync_asset_studies(self.store, project)
            return web.json_response(project.get('assets', []))
        if request.content_type == 'multipart/form-data':
            reader = await request.multipart()
            data, content = {}, bytearray()
            async for part in reader:
                if part.name == 'image':
                    while chunk := await part.read_chunk():
                        content.extend(chunk)
                        if len(content) > MAX_UPLOAD:
                            raise ValueError('Choose an image up to 32 MB.')
                elif part.name in ('name', 'kind', 'description'):
                    value = await part.read(decode=True)
                    if len(value) > 8192:
                        raise ValueError('Asset details are too long.')
                    data[part.name] = value.decode('utf-8')
            content = bytes(content)
        else:
            data = await request.json()
            if data.get('source_asset'):
                source = self.store.load(data['source_project'])
                asset = next((a for a in source.get('assets', []) if a['id'] == data['source_asset']), None)
                if not asset:
                    raise ValueError('Source asset not found.')
                if asset.get('members'):
                    project = self.store.load(pid)
                    originals = {a['id']: a for a in source.get('assets', [])}
                    copied = []
                    for member_id in asset['members']:
                        member = originals.get(member_id)
                        if not member:
                            raise ValueError('The source group contains a removed asset.')
                        copied.append(add_asset(self.store, project, self.store.file(source['id'], member['file']).read_bytes(),
                                                member['name'], member['kind'], member.get('description', ''))['id'])
                    if len(copied) == 1:
                        return web.json_response(next(a for a in project['assets'] if a['id'] == copied[0]), status=201)
                    return web.json_response(merge_assets(self.store, project, copied), status=201)
                content = self.store.file(source['id'], asset['file']).read_bytes()
                data = {**asset, **data}
            else:
                source = self.store.load(pid)
                shot = self.store.shot(source, data['shot_id'])
                draft = next((d for d in shot['drafts'] if d['id'] == data['draft_id'] and d['status'] == 'succeeded'), None)
                if not draft:
                    raise ValueError('Choose a completed image to save as an asset.')
                content = self.store.file(pid, draft['file']).read_bytes()
        project = self.store.load(pid)
        study = next((s for s in project['shots'] if s['id'] == data.get('shot_id') and s.get('mode') == 'asset'), None)
        existing = next((a for a in project.get('assets', []) if study and a['id'] == study.get('asset_id')), None)
        save_as_new = data.get('save_action') == 'new'
        if data.get('save_action') not in (None, 'new', 'overwrite'):
            raise ValueError('Choose overwrite or save as a new asset.')
        if existing and not save_as_new and data.get('name') and data['name'] != existing['name']:
            rename_asset(self.store, project, existing['id'], data['name'])
        asset = add_asset(self.store, project, content, data.get('name', ''), data.get('kind', 'character'), data.get('description', ''), existing=None if save_as_new else existing)
        if data.get('shot_id') and not data.get('source_asset'):
            asset.update(source_shot_id=shot['id'], source_draft_id=draft['id'])
            if save_as_new and study:
                fork_asset_study(self.store, project, study, asset, draft)
            self.store.save(project)
        sync_asset_studies(self.store, project)
        if asset not in project['assets']:
            linked = next((a.get('linked_into') for a in project.get('archived_assets', []) if a['id'] == asset['id']), None)
            asset = next((a for a in project['assets'] if a['id'] == linked), asset)
        return web.json_response(asset, status=201)

    async def upload_references(self, project, references):
        base = os.environ.get('OPENFRAME_COMFY_URL', 'http://127.0.0.1:8188')
        result = []
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=60)) as session:
            for asset in references:
                payload = aiohttp.FormData()
                media = asset.get('media_type', 'image')
                suffix, mime = {'video': ('.mp4', 'video/mp4'), 'audio': ('.wav', 'audio/wav'), 'image': ('.png', 'image/png')}[media]
                payload.add_field('image', self.store.file(project['id'], asset['file']).read_bytes(),
                                  filename=f"{asset['id']}" + suffix, content_type=mime)
                payload.add_field('subfolder', f"DirectorsCut/{project['id']}")
                payload.add_field('overwrite', 'false')
                async with session.post(base + '/upload/image', data=payload) as response:
                    response.raise_for_status()
                    uploaded = await response.json()
                result.append({**asset, 'comfy_image': '/'.join(filter(None, [uploaded.get('subfolder', ''), uploaded['name']]))})
        return result

    async def asset_action(self, request):
        project = self.store.load(request.match_info['project'])
        if request.method == 'DELETE':
            delete_asset(self.store, project, request.match_info['asset'])
            return web.json_response(project)
        data = await request.json()
        rename_asset(self.store, project, request.match_info['asset'], data.get('handle'))
        return web.json_response(project)

    def settings(self, data):
        for key, values in [('style', STYLE), ('camera', CAMERAS), ('ratio', RATIOS)]:
            if data[key] not in values:
                raise ValueError(f'Unknown {key}.')
        prompt = str(data['prompt']).strip()
        megapixels = float(data.get('megapixels', 2))
        image_dimensions(data['ratio'], megapixels)
        if len(prompt) > 20000:
            raise ValueError('Prompt is too long (20,000 characters maximum).')
        steps, seed = int(data['steps']), int(data.get('seed', -1))
        if not 1 <= steps <= 10000 or not -1 <= seed <= 2**53 - 1:
            raise ValueError('Invalid steps or seed.')
        workflow_id = data.get('workflow_id', 'qwen21')
        if workflow_id == 'qwen21-edit':
            workflow_id = 'qwen21'
        if workflow_id != 'qwen21':
            raise ValueError('This studio uses Qwen 2.1 only.')
        entry(workflow_id)
        model_format = data.get('model_format', 'standard')
        if model_format not in ('standard', 'gguf'):
            raise ValueError('Choose Standard or GGUF.')
        files = data.get('model_files', {})
        if not isinstance(files, dict) or not all(isinstance(k, str) and isinstance(v, str) for k, v in files.items()):
            raise ValueError('Invalid model selection.')
        files = {key.removeprefix('459_'): value for key, value in files.items()} if data.get('workflow_id') == 'qwen21-edit' else files
        asset_kind = data.get('asset_kind', 'character')
        if asset_kind not in ('character', 'prop', 'location'):
            raise ValueError('Unknown asset type.')
        character_traits = validate_traits(data.get('character_traits', {}))
        location_traits = validate_choices(data.get('location_traits', {}), 'location')
        prop_traits = validate_choices(data.get('prop_traits', {}), 'prop')
        reference_ids = data.get('reference_ids', [])
        if not isinstance(reference_ids, list) or len(reference_ids) > 10 or not all(isinstance(x, str) for x in reference_ids):
            raise ValueError('Choose up to 10 reference assets.')
        mode = data.get('mode', 'storyboard')
        if mode not in ('storyboard', 'asset'):
            raise ValueError('Unknown creation mode.')
        use_direction = data.get('direction_presets', True)
        if not isinstance(use_direction, bool):
            raise ValueError('Invalid storyboard presets option.')
        upload_ids=data.get('upload_reference_ids',[])
        if not isinstance(upload_ids,list) or len(upload_ids)>10 or not all(isinstance(ident,str) for ident in upload_ids):
            raise ValueError('Choose up to 10 uploaded reference images.')
        direction = {'loras': validate_loras(data.get('loras', [])), 'direction_presets': use_direction,
                     'upload_reference_ids':list(dict.fromkeys(upload_ids))}
        for field, values in [('lens', OPTICS), ('lighting', LIGHTING), ('film', FILM), ('grade', GRADE)]:
            value = data.get(field, next(iter(values)))
            if value not in values:
                raise ValueError(f'Unknown {field}.')
            direction[field] = value
        camera_defaults = legacy_camera(data)
        for field, values in [('lens_type', LENS_TYPES), ('sensor', SENSORS), ('light_color', LIGHT_COLORS)]:
            value = data.get(field, camera_defaults.get(field, next(iter(values))))
            if value not in values:
                raise ValueError(f'Unknown {field}.')
            direction[field] = value
        focal = snap_focal_length(data.get('focal_length', camera_defaults['focal_length']))
        notes = str(data.get('light_notes', '')).strip()
        if len(notes) > 1000:
            raise ValueError('Lighting notes are too long (1,000 characters maximum).')
        enhance = data.get('prompt_enhancer', False)
        if not isinstance(enhance, bool):
            raise ValueError('Invalid prompt enhancer option.')
        enhancer_model = data.get('enhancer_model', '')
        if not isinstance(enhancer_model, str) or len(enhancer_model) > 512:
            raise ValueError('Invalid enhancer model selection.')
        f_stop = str(data.get('f_stop', ''))
        if f_stop and (not 0.7 <= float(f_stop) <= 32):
            raise ValueError('Aperture must be between f/0.7 and f/32.')
        source = data.get('edit_source')
        if source is not None and (not isinstance(source, dict) or set(source) != {'shot_id', 'draft_id'} or
                                   not all(isinstance(v, str) and 0 < len(v) <= 80 for v in source.values())):
            raise ValueError('Invalid image editing source.')
        direction.update(enhancer_model=enhancer_model, f_stop=f_stop, megapixels=megapixels, edit_source=source, edit_preset=edit_presets.validate(data.get('edit_preset', ''), source))
        direction.update(lens='Natural perspective', focal_length=focal, light_notes=notes, prompt_enhancer=enhance)
        return dict(prompt=prompt, style=data['style'], camera=data['camera'], ratio=data['ratio'], steps=steps, seed=seed, title=str(data.get('title', 'Untitled shot'))[:120], workflow_id=workflow_id, model_format=model_format, model_files=files, reference_ids=list(dict.fromkeys(reference_ids)), mode=mode, asset_kind=asset_kind, character_traits=character_traits, location_traits=location_traits, prop_traits=prop_traits, **direction)

    async def shot(self, request):
        p = self.store.load(request.match_info['project'])
        s = self.store.shot(p, request.match_info['shot'])
        if request.method == 'DELETE':
            if any(d['status'] in ACTIVE for d in s.get('drafts', [])):
                raise ValueError('Wait for this item to finish generating before deleting it.')
            if s.get('asset_id') and any(a['id'] == s['asset_id'] for a in p.get('assets', [])):
                delete_asset(self.store, p, s['asset_id'])
            if s in p['shots']:
                p['shots'].remove(s)
                p.setdefault('archived_shots', []).append(s)
            p['storyboard'] = [panel for panel in p.get('storyboard', []) if panel['shot_id'] != s['id']]
            self.store.save(p)
            return web.json_response(p)
        data = await request.json()
        settings = video.settings(data) if s.get('mode') == 'video' else self.settings(data)
        settings['mode'] = s.get('mode', 'storyboard')
        s.update(settings)
        self.store.save(p)
        return web.json_response(s)

    async def attach_reference_image(self, request):
        return web.json_response(await reference_uploads.attach_image(request,self.store),status=201)

    async def attach_project_cover(self, request):
        return web.json_response(await project_cover.attach(request,self.store),status=201)

    async def attach_motion_reference(self, request):
        return web.json_response(await motion_reference.attach(request, self.store), status=201)

    async def attach_audio_reference(self, request):
        return web.json_response(await audio_reference.attach(request, self.store), status=201)

    async def apply_soundtrack(self, request):
        data = await request.json()
        pid, sid, did = (request.match_info[key] for key in ('project', 'shot', 'draft'))
        async with self.audio_locks.setdefault((pid, did), asyncio.Lock()):
            project = self.store.load(pid)
            shot = self.store.shot(project, sid)
            draft = next((d for d in shot['drafts'] if d['id'] == did and d['status'] == 'succeeded'), None)
            if shot.get('mode') != 'video' or draft is None:
                raise ValueError('Choose a completed video take.')
            target = self.store.file(pid, draft['file'])
            ident = data.get('audio_id', '')
            if data.get('restore') is True:
                await audio_reference.restore_soundtrack(target)
                ident = ''
            else:
                ref = audio_reference.resolve(project, dict(output_audio_id=ident), 'output')
                if not ref:
                    raise ValueError('Choose final audio first.')
                await audio_reference.replace_soundtrack(target, self.store.file(pid, ref['file']))
            project = self.store.load(pid)
            draft = next(d for d in self.store.shot(project, sid)['drafts'] if d['id'] == did)
            draft.update(applied_output_audio_id=ident, audio_applied_at=now())
            self.store.save(project)
            return web.json_response(project)

    async def generate(self, request):
        if self.connection_changing:
            raise ValueError("Engine connection is being changed. Try again in a moment.")
        data = await request.json()
        initial_project = self.store.load(request.match_info['project'])
        initial_shot = self.store.shot(initial_project, request.match_info['shot'])
        is_video = initial_shot.get('mode') == 'video'
        settings = video.settings(data) if is_video else self.settings(data)
        count = data.get('count', 1)
        if isinstance(count, bool) or not isinstance(count, int) or not 1 <= count <= 16:
            raise ValueError('Choose between 1 and 16 takes per queue submission.')
        request_id = data.get('request_id', '')
        if not isinstance(request_id, str) or (request_id and not re.fullmatch(r'[A-Za-z0-9_-]{1,80}', request_id)):
            raise ValueError('Invalid queue request identifier.')
        def previous_batch(shot):
            return [d for d in shot['drafts'] if request_id and d.get('request_id') == request_id]
        def result(drafts):
            # Keep the first take's fields for older clients using this endpoint.
            return web.json_response({**drafts[0], 'drafts': drafts, 'count': len(drafts)}, status=202)
        p = self.store.load(request.match_info['project'])
        s = self.store.shot(p, request.match_info['shot'])
        if previous := previous_batch(s):
            return result(previous)
        settings['mode'] = s.get('mode', 'storyboard')
        if not settings['prompt'] and not (not is_video and (asset_prompt(settings) or (settings.get('edit_source') and settings.get('edit_preset')))):
            raise ValueError('Describe your shot or choose asset details first.')
        references = resolve_references(p, settings)
        if not is_video:
            references += reference_uploads.resolve(p,settings)
            if len(references)>10:raise ValueError('Use up to 10 reference images.')
        if settings.get('edit_source'):
            references.insert(0, edit_reference(p, settings['edit_source'], settings['asset_kind']))
            if len(references) > 10:
                raise ValueError('Use up to 10 images, including the editing source.')
        if not is_video and (references or settings['mode'] == 'asset') and settings['workflow_id'] not in EDITABLE:
            raise ValueError('Choose an image model with reference editing support.')
        nodes = await self.nodes()
        video_vram = await self.gpu_memory() if is_video else None
        if is_video and len(references) > 9:
            raise ValueError('Choose up to 9 video image references.')
        uploaded = await self.upload_references(p, references) if references else []
        uploaded_motion = None
        if is_video and (motion := motion_reference.resolve(p, settings)):
            uploaded_motion = (await self.upload_references(p, [{**motion, 'media_type': 'video'}]))[0]
        uploaded_audio = None
        final_audio = None
        if is_video:
            if speech := audio_reference.resolve(p, settings, 'reference'):
                uploaded_audio = (await self.upload_references(p, [{**speech, 'media_type': 'audio'}]))[0]
            final_audio = audio_reference.resolve(p, settings, 'output')
        # Reserve the complete batch without yielding after reading current project data.
        p = self.store.load(request.match_info['project'])
        s = self.store.shot(p, request.match_info['shot'])
        if previous := previous_batch(s):
            return result(previous)
        if is_video:
            ready = video.availability(nodes, video_vram, settings['model_files'])['presets'][settings['video_preset']]
            if not ready['ready']:
                raise ValueError('; '.join(ready['missing']))
            available_loras = lora_availability(nodes)
            for row in settings['loras']:
                if row['enabled'] and row['strength'] != 0 and row['name'] not in available_loras['files']:
                    raise ValueError('LoRA not installed: ' + row['name'])
        else:
            profile = next(w for w in describe(nodes) if w['id'] == settings['workflow_id'])
            availability = profile['formats'][settings['model_format']]
            if not availability['edit_ready' if references else 'ready']:
                raise ValueError('; '.join(availability['edit_missing' if references else 'missing']))
        drafts, workflows, seeds = [], [], set()
        for offset in range(count):
            snapshot = {**settings, 'model_files': dict(settings['model_files'])}
            if uploaded:
                snapshot['references'] = uploaded
            if uploaded_motion:
                snapshot['motion_reference'] = uploaded_motion
            if uploaded_audio:
                snapshot['audio_reference'] = uploaded_audio
            if final_audio:
                snapshot['output_audio'] = final_audio
            if settings['seed'] == -1:
                seed = secrets.randbelow(2**53)
                while seed in seeds:
                    seed = secrets.randbelow(2**53)
            else:
                seed = (settings['seed'] + offset) % (2**53)
            seeds.add(seed)
            snapshot['seed'] = seed
            number = len(s['drafts']) + offset + 1
            stem = f'shots/{s["id"]}/draft_{number:03d}'
            graph, prompt = video.build_graph(snapshot, f'video/DirectorsCut/{p["id"]}/{s["id"]}', nodes) if is_video else build_graph(snapshot, f'DirectorsCut/{p["id"]}/{s["id"]}', nodes)
            self.queue_serial += 1
            draft = dict(id=uuid.uuid4().hex, queue_order=self.queue_serial, number=number, status='queued', file=stem + ('.mp4' if is_video else '.png'),
                         workflow=stem + '.workflow.json', settings=snapshot, full_prompt=prompt, created_at=now(),
                         request_id=request_id, batch_index=offset + 1, batch_count=count)
            drafts.append(draft)
            workflows.append(graph)
        for draft, graph in zip(drafts, workflows):
            write_json(self.store.file(p['id'], draft['workflow']), graph)
        s.update(settings)
        s['drafts'].extend(drafts)
        self.store.save(p)
        for draft in drafts:
            self.queue.put_nowait((p['id'], s['id'], draft['id']))
        return result(drafts)

    async def upscale_video(self, request):
        pid, sid, source_id = (request.match_info[key] for key in ('project', 'shot', 'draft'))
        key = (pid, sid, source_id)
        async with self.upscale_locks.setdefault(key, asyncio.Lock()):
            def source_data():
                p = self.store.load(pid)
                s = self.store.shot(p, sid)
                source = next((d for d in s['drafts'] if d['id'] == source_id), None)
                if s.get('mode') != 'video' or not source or source['status'] != 'succeeded' or not source.get('file'):
                    raise ValueError('Choose a completed video take to upscale.')
                if source.get('postprocess', {}).get('type') == 'rtx-upscale':
                    raise ValueError('This take is already upscaled. Choose its original take.')
                if not self.store.file(pid, source['file']).is_file():
                    raise FileNotFoundError('Source video is missing.')
                return p, s, source
            p, s, source = source_data()
            existing = next((d for d in s['drafts'] if d.get('postprocess', {}).get('source_draft_id') == source_id and d['status'] in ACTIVE), None)
            if existing:
                return web.json_response(existing)
            nodes, devices = await asyncio.gather(self.nodes(), self.gpu_devices())
            if not rtx_upscale.availability(nodes, devices)['ready']:
                raise ValueError('RTX upscale requires a supported NVIDIA RTX GPU and the installed RTX Video Super Resolution node.')
            uploaded = await self.upload_references(p, [dict(id='rtx_' + source_id, file=source['file'], media_type='video')])
            # Reload after upload to preserve any concurrent renames, approvals or takes.
            p, s, source = source_data()
            number = len(s['drafts']) + 1
            stem = f'shots/{sid}/draft_{number:03d}'
            graph = rtx_upscale.build_graph(uploaded[0]['comfy_image'], f'video/DirectorsCut/{pid}/{sid}/RTX', nodes)
            snapshot = dict(source['settings'], title=s['title'], output_audio_id='')
            snapshot.pop('output_audio', None)  # Already present in the source video; do not apply twice.
            self.queue_serial += 1
            draft = dict(id=uuid.uuid4().hex, number=number, queue_order=self.queue_serial,
                         status='queued', file=stem + '.mp4', workflow=stem + '.workflow.json',
                         settings=snapshot, full_prompt=source.get('full_prompt', snapshot.get('prompt', '')),
                         created_at=now(), postprocess=dict(type='rtx-upscale', scale=2, source_draft_id=source_id))
            for field in ('applied_output_audio_id', 'audio_applied_at'):
                if field in source:
                    draft[field] = source[field]
            write_json(self.store.file(pid, draft['workflow']), graph)
            s['drafts'].append(draft)
            self.store.save(p)
            self.queue.put_nowait((pid, sid, draft['id']))
            return web.json_response(draft, status=201)

    async def approve(self, request):
        draft_id = (await request.json())['draft_id']
        p = self.store.load(request.match_info['project'])
        s = self.store.shot(p, request.match_info['shot'])
        if s.get('mode') == 'asset':
            raise ValueError('Save asset studies to the library. Storyboard approval is for shots.')
        self.store.approve(p, s, draft_id)
        return web.json_response(s)

    async def export(self, request):
        columns = int((await request.json()).get('columns', 2))
        p = self.store.load(request.match_info['project'])
        if columns not in (2, 3):
            raise ValueError('Choose a 2 x 2 or 3 x 3 grid.')
        files = await asyncio.to_thread(self.store.export, p, columns)
        download = await asyncio.to_thread(self.store.export_download, p['id'], files, columns)
        return web.json_response({'files': files, 'download': download})

    async def storyboard(self, request):
        data = await request.json()
        project = self.store.load(request.match_info['project'])
        self.store.edit_storyboard(project, data)
        return web.json_response(project)

    async def file(self, request):
        path = self.store.file(request.match_info['project'], request.match_info['file'])
        if path.suffix not in ('.png', '.jpg', '.json', '.zip', '.mp4'):
            raise web.HTTPForbidden()
        headers = {'Cache-Control': 'no-cache'}
        if request.query.get('download') == '1':
            headers['Content-Disposition'] = f'attachment; filename="{path.name}"'
        return web.FileResponse(path, headers=headers)


def create_app(shutdown_event=None):
    studio = Studio()
    app = web.Application(middlewares=[errors], client_max_size=130 * 1024 * 1024)
    app['studio'] = studio
    if shutdown_event is not None:app['shutdown_event']=shutdown_event
    app.cleanup_ctx.append(studio.lifecycle)
    app.router.add_get('/api/app', app_control.info)
    app.router.add_post('/api/app/quit', app_control.quit_app)
    app.router.add_post('/api/app/open-data', app_control.open_data)
    app.router.add_get('/api/app/legal/{document:app|third-party|dependencies}',app_control.license_text)
    app.router.add_get('/api/models/catalog', model_downloads.catalog)
    app.router.add_get('/api/models/downloads', model_downloads.status)
    app.router.add_post('/api/models/downloads', model_downloads.start)
    app.router.add_post('/api/models/downloads/{model}/cancel', model_downloads.cancel)
    app.router.add_get('/api/config', studio.config)
    app.router.add_get('/api/engine', engine_connection.describe)
    app.router.add_get('/api/engine/discover', engine_connection.discover)
    app.router.add_post('/api/engine/test', engine_connection.probe)
    app.router.add_put('/api/engine', engine_connection.save)
    app.router.add_post('/api/video/import/{kind}', import_video_file)
    app.router.add_get('/api/queue', studio.generation_queue)
    app.router.add_get('/api/previews', studio.preview_status)
    app.router.add_post('/api/previews', studio.preview_status)
    app.router.add_route('*', '/api/projects', studio.projects)
    app.router.add_get('/api/projects/{project}', studio.project)
    app.router.add_delete('/api/projects/{project}', studio.project)
    app.router.add_post('/api/projects/{project}/cover', studio.attach_project_cover)
    app.router.add_post('/api/projects/{project}/shots', studio.shots)
    app.router.add_route('GET', '/api/projects/{project}/assets', studio.assets)
    app.router.add_route('POST', '/api/projects/{project}/assets', studio.assets)
    app.router.add_patch('/api/projects/{project}/assets/{asset}', studio.asset_action)
    app.router.add_delete('/api/projects/{project}/assets/{asset}', studio.asset_action)
    app.router.add_put('/api/projects/{project}/shots/{shot}', studio.shot)
    app.router.add_delete('/api/projects/{project}/shots/{shot}', studio.shot)
    app.router.add_post('/api/projects/{project}/shots/{shot}/references', studio.attach_reference_image)
    app.router.add_post('/api/projects/{project}/shots/{shot}/motion-reference', studio.attach_motion_reference)
    app.router.add_post('/api/projects/{project}/shots/{shot}/audio/{kind:reference|output}', studio.attach_audio_reference)
    app.router.add_post('/api/projects/{project}/shots/{shot}/drafts/{draft}/soundtrack', studio.apply_soundtrack)
    app.router.add_post('/api/projects/{project}/shots/{shot}/generate', studio.generate)
    app.router.add_post('/api/projects/{project}/shots/{shot}/approve', studio.approve)
    app.router.add_post('/api/projects/{project}/shots/{shot}/drafts/{draft}/cancel', studio.cancel_queued)
    app.router.add_post('/api/projects/{project}/shots/{shot}/drafts/{draft}/rtx-upscale', studio.upscale_video)
    app.router.add_post('/api/projects/{project}/export', studio.export)
    app.router.add_put('/api/projects/{project}/storyboard', studio.storyboard)
    app.router.add_get('/files/{project}/{file:.*}', studio.file)
    async def static(request):
        return web.FileResponse(ROOT / 'web' / request.match_info.get('asset', 'index.html'))
    app.router.add_get('/', static)
    app.router.add_get('/{asset:app.js|player.js|video.js|workspace-nav.js|dropdowns.js|style.css|icons.js|library.js|polish.js|polish.css|motion.js|motion.css|model-downloads.js|engine-settings.js}', static)
    app.router.add_static('/assets', ROOT / 'web/assets')
    return app


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    web.run_app(create_app(), host=os.environ.get('OPENFRAME_HOST', '127.0.0.1'), port=int(os.environ.get('OPENFRAME_PORT', 7860)))

