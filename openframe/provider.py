"""Official Comfy SDK adapter. All inference stays on local ComfyUI."""
import asyncio
import math
import os

from comfy_sdk import AsyncComfy
from comfy_sdk.events import Progress
from .catalog import entry, prepared, select_models, attach_references, fit_qwen_reference_canvas
from .assets import reference_prompt, storyboard_reference_direction
from .asset_presets import asset_prompt
from .edit_presets import prompt as edit_prompt
from .characters import character_render_direction
from .loras import attach_loras

from .presets import aperture_prompt, STYLE, CAMERAS, RATIOS, OPTICS, LIGHTING, FILM, GRADE, FRAMING, LENS_TYPES, SENSORS, LIGHT_COLORS
from .enhancer import attach, usable_caption
import aiohttp


RESOLUTION_RATIOS = {
    '1:1': '1:1 (Square)', '2:3': '2:3 (Portrait Photo)', '3:2': '3:2 (Photo)',
    '3:4': '3:4 (Portrait Standard)', '4:3': '4:3 (Standard)',
    '9:16': '9:16 (Portrait Widescreen)', '16:9': '16:9 (Widescreen)', '21:9': '21:9 (Ultrawide)',
}


def image_dimensions(ratio, megapixels, minimum=0.25):
    megapixels = float(megapixels)
    if not math.isfinite(megapixels) or not minimum <= megapixels <= 8:
        raise ValueError(f'Image size must be between {minimum:g} and 8 megapixels.')
    a, b = map(int, ratio.split(':'))
    scale = math.sqrt(megapixels * 1024 * 1024 / (a * b))
    return dict(width=round(a * scale / 32) * 32, height=round(b * scale / 32) * 32)


def image_prompt_parts(settings, workflow_id='qwen21'):
    """Assemble the same base text used by generation, without nodes or inference."""
    direction = STYLE[settings['style']]
    for field, presets in [('lens', OPTICS), ('lighting', LIGHTING), ('film', FILM), ('grade', GRADE)]:
        value = settings.get(field)
        if value in presets and presets[value]:
            direction += ' ' + presets[value]
    if 'lens_type' in settings:
        direction += ' ' + LENS_TYPES[settings['lens_type']] + ' ' + SENSORS[settings['sensor']]
        direction += f" Focal length: {settings['focal_length']:g}mm."
    if settings.get('light_color') in LIGHT_COLORS:
        direction += ' ' + LIGHT_COLORS[settings['light_color']]
    if settings.get('light_notes'):
        direction += ' Lighting direction: ' + settings['light_notes']
    if settings.get('f_stop'):
        direction += ' ' + aperture_prompt(float(settings['f_stop']))
    if settings.get('mode') == 'asset':
        direction = character_render_direction(settings)
    character = asset_prompt(settings)
    if settings.get('edit_source'):
        direction = 'Keep everything else in the source image unchanged, including identity, composition and rendering medium.'
        if settings.get('edit_preset'):
            direction = 'Preserve the exact source character identity, design, proportions and rendering medium. Change the pose, framing or layout as requested; additional user details override preset defaults.'
        character = ''
    if settings.get('mode', 'storyboard') == 'storyboard' and not settings.get('edit_source'):
        if settings.get('direction_presets', True):
            composition = storyboard_reference_direction(settings)
            if composition:
                direction += '\n' + composition
            direction += ('\nFraming priority — ' + settings['camera'] + ': ' + FRAMING[settings['camera']] +
                          ' Recompose the scene from this camera viewpoint; reference images supply identities and designs, '
                          'not a fixed camera position or crop. This framing takes priority over incidental reference composition.')
        else:
            direction = ''
    base = settings['prompt'] or ('Create an image of a ' + settings.get('asset_kind', 'character') + '.' if character else '')
    if settings.get('edit_source'):
        base = edit_prompt(settings)
    scene = reference_prompt(base, settings.get('references', []), workflow_id)
    if character:
        scene += '\n' + character
    prompt = scene + ('\n' + direction if direction else '')
    return scene, direction, prompt


def build_graph(settings, prefix, nodes=None):
    item = entry(settings.get('workflow_id', 'qwen21'))
    graph = prepared(item)
    scene, direction, prompt = image_prompt_parts(settings, item['id'])
    graph[item['prompt_node']]['inputs'][item['prompt_field']] = prompt
    megapixels = float(settings.get('megapixels', 2))
    dimensions = image_dimensions(settings['ratio'], megapixels)
    custom_ratio = settings['ratio'] in ('5:4', '4:5')
    selector = next((key for key, node in graph.items() if node['class_type'] == 'ResolutionSelector'), None) if not custom_ratio else None
    if not custom_ratio and selector is None and nodes is not None and 'ResolutionSelector' in nodes:
        selector = 'dc_resolution'
        graph[selector] = dict(class_type='ResolutionSelector', inputs={})
    if selector:
        graph[selector]['inputs'].update(aspect_ratio=RESOLUTION_RATIOS[settings['ratio']], megapixels=megapixels, multiple=32)
    graph_dimensions = dict(width=[selector, 0], height=[selector, 1]) if selector else dimensions
    for node in graph.values():
        kind, inputs = node['class_type'], node['inputs']
        if kind in ('EmptyLatentImage', 'EmptySD3LatentImage', 'EmptyFlux2LatentImage', 'Flux2Scheduler', 'Ideogram4Scheduler'):
            inputs.update(graph_dimensions)
        if kind in ('KSampler', 'BasicScheduler', 'Flux2Scheduler', 'Ideogram4Scheduler'):
            inputs['steps'] = settings['steps']
        if kind == 'KSampler':
            inputs['seed'] = settings['seed']
        if kind == 'RandomNoise':
            inputs['noise_seed'] = settings['seed']
    graph[item['output']]['inputs']['filename_prefix'] = prefix
    if nodes is not None:
        graph = select_models(graph, item, settings.get('model_format', 'standard'), settings.get('model_files', {}), nodes)
    attach_loras(graph, settings.get('loras', []), nodes)
    attach_references(graph, item, settings.get('references', []))
    # Match reference conditioning to the selected generation size too.
    for node in graph.values():
        if node['class_type'] == 'TextEncodeQwenImage21':
            node['inputs']['resolution'] = round(math.sqrt(megapixels * 1024 * 1024) / 32) * 32
        elif node['class_type'] == 'ReferenceMultiLatent':
            node['inputs']['resolution.megapixels'] = megapixels
    fit_qwen_reference_canvas(graph, item, settings.get('references', []), dimensions, nodes)
    if settings.get('prompt_enhancer'):
        attach(graph, item, scene, direction, settings['seed'], nodes or {}, settings.get('enhancer_model', ''))
    return graph, prompt


class GenerationCancelled(Exception):
    pass


class ComfyProvider:
    def __init__(self):
        from .engine_config import current, apply_environment
        apply_environment(current())
        self.client = AsyncComfy()

    async def cancel(self, job_id):
        job = await self.client.jobs.get(job_id)
        await job.cancel()

    async def generate(self, graph, target, update, existing_id=None):
        job = await self.client.jobs.get(existing_id) if existing_id else await self.client.submit(self.client.workflows.from_json(graph))
        await update(job_id=job.id, status=job.status)
        # Polling is authoritative; missing live events must never stall a job.
        async def events():
            try:
                async for event in job.events():
                    if isinstance(event, Progress):
                        kind = graph.get(str(event.current_node), {}).get('class_type', '')
                        sampling = (kind.startswith(('KSampler', 'SamplerCustom')) or
                                    not event.current_node and 'sampl' in (event.message or '').lower())
                        changes = dict(progress=event.value, stage=event.message or ('Sampling' if sampling else 'Processing'), sampling=sampling)
                        if sampling and event.step is not None and event.steps:
                            changes.update(sampling_step=event.step, sampling_steps=event.steps)
                        await update(**changes)
            except Exception:
                pass  # Polling below continues if the optional event stream fails.

        stream = asyncio.create_task(events())
        try:
            while True:
                await job.refresh()
                await update(status='downloading' if job.status == 'succeeded' else 'running' if job.status == 'canceling' else job.status)
                if job.status in ('succeeded', 'failed', 'canceled', 'cancelled'):
                    break
                await asyncio.sleep(2)
            if job.status in ('canceled', 'cancelled'):
                raise GenerationCancelled()
            if job.status != 'succeeded':
                raise RuntimeError(f'ComfyUI {job.status}: {job.error}')
            output_id = next(k for k, n in graph.items() if n['class_type'] in ('SaveImage', 'SaveVideo'))
            outputs = job.get_outputs(output_id)
            if not outputs:
                raise RuntimeError('ComfyUI completed without a downloadable output.')
            await outputs[0].to_file(target)
            if 'dc_enhanced_preview' in graph:
                # The local proxy exposes file assets; text previews live in ComfyUI history.
                try:
                    base = os.environ.get('OPENFRAME_COMFY_URL', 'http://127.0.0.1:8188')
                    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
                        async with session.get(base + '/history/' + job.id) as response:
                            response.raise_for_status()
                            history = await response.json()
                    text = history[job.id]['outputs']['dc_enhanced_preview']['text'][0]
                    if not isinstance(text, str) or not text.strip():
                        raise ValueError('Empty expanded caption.')
                    changes = dict(enhanced_prompt=text, full_prompt=text)
                    if 'dc_expansion_preview' in graph:
                        expansion = history[job.id]['outputs']['dc_expansion_preview']['text'][0]
                        if not isinstance(expansion, str):
                            raise ValueError('Invalid enhancer caption.')
                        changes['enhancer_output'] = expansion
                        if not usable_caption(expansion):
                            changes['prompt_note'] = 'The enhancer returned an empty caption or a refusal. Your original scene and camera/style settings were used instead.'
                    await update(**changes)
                except (aiohttp.ClientError, asyncio.TimeoutError, KeyError, IndexError, TypeError, ValueError):
                    await update(prompt_note='Expanded prompt is available in ComfyUI history; its local text preview could not be retrieved.')
        finally:
            stream.cancel()
            await asyncio.gather(stream, return_exceptions=True)

    async def close(self):
        await self.client.aclose()
