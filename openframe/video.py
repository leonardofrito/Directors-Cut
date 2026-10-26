"""MiniMax H3 video generation derived from Leonardo's H3 REF2VA workflow."""
import json
import re
from pathlib import Path

from .catalog import names, prune
from .provider import image_dimensions
from .presets import RATIOS
from .loras import validate_loras, attach_loras, availability as lora_availability
from . import video_prompt
from .video_mentions import bind_media_mentions

ROOT = Path(__file__).resolve().parent.parent / 'workflows/video'
PRESETS = {'original': 'H3_REF2VA_8step_Original.api.json', 'vsa': 'H3_REF2VA_8step_VSA.api.json',
           'fast-omni': 'FastH3_OmniRef_8step.api.json'}
MODEL_FIELDS = {
    '127': ('Video model', 'unet_name', r'minimax.*h3.*ref2va.*\.safetensors$'),
    '128': ('H3 text encoder', 'clip_name', r'qwen3vl_32b.*minimax.*h3.*\.safetensors$'),
    '119': ('Video VAE', 'vae_name', r'minimax.*h3.*video_vae.*\.safetensors$'),
    '120': ('Audio VAE', 'vae_name', r'minimax.*h3.*audio_vae.*\.safetensors$'),
    '145': ('8-step acceleration LoRA', 'lora_name', r'minimax.*h3.*ref2v.*8step.*\.safetensors$'),
    '156': ('VSA gate', 'gate_file', r'.*vsa.*gate.*\.safetensors$'),
}


def model_pattern(key, preset):
    if key == '127' and preset == 'fast-omni':
        return r'fast[-_]?h3.*omni(?:ref)?.*\.(?:safetensors|gguf)$'
    if key == '127':
        return r'minimax[-_].*h3.*ref2va.*\.(?:safetensors|gguf)$'
    return MODEL_FIELDS[key][2]


def model_preset(data):
    filename = data.get('model_files', {}).get('127', '') if isinstance(data.get('model_files', {}), dict) else ''
    if isinstance(filename, str) and filename:
        return 'fast-omni' if re.search(model_pattern('127', 'fast-omni'), filename, re.I) else 'vsa' if data.get('video_preset') == 'vsa' else 'original'
    return data.get('video_preset', 'fast-omni')


def model_files(data):
    files = data.get('model_files', {})
    preset = model_preset(data)
    if not isinstance(files, dict) or any(key not in MODEL_FIELDS or not isinstance(value, str) or
            (preset == 'fast-omni' and key in ('145', '156')) or
            len(value) > 512 or not re.search(model_pattern(key, preset), value, re.I) for key, value in files.items()):
        raise ValueError('Choose compatible H3 Ref2VA model files.')
    return dict(files)


def settings(data):
    prompt = str(data.get('prompt', '')).strip()
    if len(prompt) > 20000:
        raise ValueError('Video prompt is too long (20,000 characters maximum).')
    ratio = data.get('ratio', '16:9')
    if ratio not in RATIOS:
        raise ValueError('Unknown video aspect ratio.')
    mp = float(data.get('megapixels', .5))
    image_dimensions(ratio, mp, minimum=.2)
    if not .2 <= mp <= 2:
        raise ValueError('Choose between 0.2 and 2 megapixels for video.')
    duration = data.get('duration', 5)
    if isinstance(duration, bool) or not isinstance(duration, int) or not 2 <= duration <= 30:
        raise ValueError('Choose an integer duration between 2 and 30 seconds.')
    preset = model_preset(data)
    if preset not in PRESETS:
        raise ValueError('Choose an installed H3 video workflow.')
    refs = data.get('reference_ids', [])
    if not isinstance(refs, list) or len(refs) > 9 or not all(isinstance(x, str) for x in refs):
        raise ValueError('Choose up to 9 video image references.')
    seed = int(data.get('seed', -1))
    if not -1 <= seed < 2**53:
        raise ValueError('Invalid video seed.')
    files = model_files(data)
    motion_id = data.get('motion_reference_id', '')
    if not isinstance(motion_id, str) or motion_id and not re.fullmatch(r'[a-f0-9]{32}', motion_id):
        raise ValueError('Choose an uploaded motion reference.')
    audio_ids = {key: data.get(key, '') for key in ('audio_reference_id', 'output_audio_id')}
    if any(not isinstance(ident, str) or ident and not re.fullmatch(r'[a-f0-9]{32}', ident) for ident in audio_ids.values()):
        raise ValueError('Choose an uploaded audio file.')
    enhance = data.get('prompt_enhancer', False)
    enhancer_model = data.get('enhancer_model', '')
    if not isinstance(enhance, bool) or not isinstance(enhancer_model, str) or len(enhancer_model) > 512:
        raise ValueError('Invalid video prompt enhancer selection.')
    return dict(title=str(data.get('title', 'New shot'))[:120], prompt=prompt, mode='video',
                workflow_id='h3-ref2va', model_files=files, model_format='gguf' if files.get('127', '').lower().endswith('.gguf') else 'standard', steps=8,
                ratio=ratio, megapixels=mp, duration=duration, fps=24, seed=seed,
                video_preset=preset, reference_ids=list(dict.fromkeys(refs)), motion_reference_id=motion_id, **audio_ids, prompt_enhancer=enhance,enhancer_model=enhancer_model,
                video_direction=video_prompt.validate(data.get('video_direction', {})),
                loras=validate_loras(data.get('loras', [])))


def template(preset):
    return json.loads((ROOT / PRESETS[preset]).read_text(encoding='utf-8'))


def availability(nodes, vram_total=None, selected=None):
    hardware_ok = vram_total is not None and vram_total >= 11 * 1024**3
    result = {}
    for preset in PRESETS:
        missing, fixed_missing, loaders = [], [], []
        for key, node in template(preset).items():
            kind, inputs = node['class_type'], node['inputs']
            if kind not in nodes:
                missing.append('Node: ' + kind)
                fixed_missing.append('Node: ' + kind)
            if key in MODEL_FIELDS:
                role, field, _ = MODEL_FIELDS[key]
                pattern = model_pattern(key, preset)
                all_files = names(nodes, kind, field)
                if key == '127':
                    all_files += names(nodes, 'UnetLoaderGGUF', 'unet_name')
                options = list(dict.fromkeys(name for name in all_files if re.search(pattern, name, re.I)))
                default = inputs[field]
                chosen = (selected or {}).get(key, default)
                if key == '127' and chosen.lower().endswith('.gguf') and 'UnetLoaderGGUF' not in nodes:
                    fixed_missing.append('Node: UnetLoaderGGUF (H3-compatible version)')
                    missing.append(fixed_missing[-1])
                loaders.append(dict(node=key, role=role, options=options, default=default))
                if chosen not in options:
                    missing.append('File: ' + chosen)
                continue
            for field in ('unet_name', 'clip_name', 'vae_name', 'lora_name', 'gate_file'):
                if field in inputs and inputs[field] not in names(nodes, kind, field):
                    missing.append('File: ' + inputs[field])
        if not hardware_ok:
            message = 'Video requires a GPU with at least 12 GB VRAM.' if vram_total is not None else 'Could not verify GPU memory. Connect the local ComfyUI engine.'
            missing.append(message)
            fixed_missing.append(message)
        loaders.sort(key=lambda loader: list(MODEL_FIELDS).index(loader['node']))
        result[preset] = dict(ready=not missing, missing=list(dict.fromkeys(missing)), fixed_missing=list(dict.fromkeys(fixed_missing)), loaders=loaders)
    model_choices = [dict(file=file, preset=preset, recommended=preset == 'fast-omni')
                     for preset in ('fast-omni', 'original') for loader in result[preset]['loaders']
                     if loader['node'] == '127' for file in loader['options']]
    return dict(presets=result, models=model_choices, loras=lora_availability(nodes),prompt_presets=video_prompt.catalog(),enhancer=video_prompt.availability(nodes),
                min_vram_gb=12, vram_total=vram_total, steps=8, max_references=9)


def reference_prompt(prompt, references, settings=None):
    prompt = bind_media_mentions(prompt, settings or {})
    bindings = {ref['handle']: f'<Picture {i+1}>' for i, ref in enumerate(references)}
    prompt = re.sub(r'(?<![\w@])@([a-zA-Z0-9_]+)', lambda m: bindings.get(m[1], m[0]), prompt)
    roles = {'character': 'character identity, proportions and clothing', 'prop': 'object design', 'location': 'location architecture, materials and environment'}
    lines = [f'<Picture {i+1}> supplies {roles[ref["kind"]]}. Its studio background is not part of the scene.'
             if ref['kind'] != 'location' else f'<Picture {i+1}> supplies {roles[ref["kind"]]}; the camera may recompose the location.'
             for i, ref in enumerate(references)]
    return ('Reference bindings, in input order:\n' + '\n'.join(lines) + '\n\n' + prompt) if lines else prompt


def build_graph(saved, prefix, nodes=None):
    graph = template(model_preset(saved))
    for key, filename in model_files(saved).items():
        if key in graph:
            graph[key]['inputs'][MODEL_FIELDS[key][1]] = filename
    if graph['127']['inputs']['unet_name'].lower().endswith('.gguf'):
        graph['127'] = dict(class_type='UnetLoaderGGUF', inputs=dict(unet_name=graph['127']['inputs']['unet_name']))
    attach_loras(graph, saved.get('loras', []))
    refs = saved.get('references', [])
    if len(refs) > 9:
        raise ValueError('H3 accepts up to 9 image references.')
    prompt = reference_prompt(saved['prompt'], refs, saved)
    cues = video_prompt.direction(video_prompt.validate(saved.get('video_direction', {})))
    if cues:
        prompt += '\n\nVideo direction:\n' + cues
    encoder = graph['136']['inputs']
    for key in list(encoder):
        if key.startswith(('ref_images.', 'ref_videos.', 'ref_video_audios.', 'ref_audios.')):
            del encoder[key]
    for i, ref in enumerate(refs):
        key = f'h3_reference_{i}'
        graph[key] = dict(class_type='LoadImage', inputs=dict(image=ref['comfy_image']))
        encoder[f'ref_images.ref_image_{i}'] = [key, 0]
    if motion := saved.get('motion_reference'):
        if nodes is not None and ('LoadVideo' not in nodes or 'GetVideoComponents' not in nodes):
            raise ValueError('Update ComfyUI to load motion reference videos.')
        graph['dc_motion_video'] = dict(class_type='LoadVideo', inputs=dict(file=motion['comfy_image']))
        graph['dc_motion_frames'] = dict(class_type='GetVideoComponents', inputs=dict(video=['dc_motion_video', 0]))
        encoder['ref_videos.ref_video_0'] = ['dc_motion_frames', 0]
        prompt += ('\n\nVideo reference: <Video 1> supplies only the reference roles explicitly requested in the scene. '
            'For camera-only use, follow its camera path, movement direction, viewpoint progression and timing; '
            'do not transfer the source performer’s body movement to the character. '
            'For requested action transfer, use the referenced action while preserving the image-defined identity. '
            'Preserve the requested characters, clothing, rendering style and setting; '
            'do not copy unrequested people, scenery or soundtrack from <Video 1>.')
    if speech := saved.get('audio_reference'):
        if nodes is not None and 'LoadAudio' not in nodes:
            raise ValueError('Update ComfyUI to load reference audio.')
        graph['dc_speech_audio'] = dict(class_type='LoadAudio', inputs=dict(audio=speech['comfy_image']))
        encoder['ref_audios.ref_audio_0'] = ['dc_speech_audio', 0]
        prompt += ('\n\nAudio reference: <Audio 1> supplies the speaking character’s vocal timbre, delivery and speech timing. '
            'Preserve the character identity from the image references. Match mouth articulation and pauses to the speech performance. '
            'Use the words from <Audio 1> when the scene does not specify dialogue; otherwise preserve the scripted dialogue. '
            'Do not copy unrelated background music or environmental noise from the reference audio.')
    frames = round(saved['duration'] * 24)
    frames += (5 - frames) % 17
    encoder.update(prompt=prompt, **image_dimensions(saved['ratio'], saved['megapixels'], minimum=.2), length=frames, ref_image_size='match')
    graph['129']['inputs']['noise_seed'] = saved['seed']
    graph['124']['inputs']['steps'] = 8
    graph['92']['inputs']['filename_prefix'] = prefix
    if saved.get('prompt_enhancer'):
        video_prompt.attach(graph,prompt,saved.get('enhancer_model',''),saved['seed'],saved['duration'],nodes or {},[f'h3_reference_{i}' for i in range(len(refs))])
    result=prune(graph,'92')
    result.update({key:node for key,node in graph.items() if node['class_type']=='PreviewAny' and key.startswith('dc_')})
    return result, prompt
