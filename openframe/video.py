"""MiniMax H3 video generation derived from Leonardo's H3 REF2VA workflow."""
import json
import re
from pathlib import Path

from .catalog import names, prune
from .provider import image_dimensions
from .presets import RATIOS
from .loras import validate_loras, attach_loras, availability as lora_availability
from . import video_prompt, selflift
from .video_mentions import bind_media_mentions

ROOT = Path(__file__).resolve().parent.parent / 'workflows/video'
PRESETS = {'original': 'DC_original_Normal.api.json', 'fast-omni': 'DC_fast-omni_Normal.api.json',
           'hyperflow': 'DC_hyperflow_Normal.api.json', 'vsa': 'H3_REF2VA_8step_VSA.api.json'}
TARA_PRESETS = {'original':'DC_original_TARA.api.json','fast-omni':'DC_fast-omni_TARA.api.json'}
TARA_LORA = 'minimax_h3_motion_transfer_tara_v1.0_ref2va.safetensors'
MODEL_FIELDS = {
    '127': ('Video model', 'unet_name', r'minimax.*h3.*ref2va.*\.safetensors$'),
    '128': ('H3 text encoder', 'clip_name', r'qwen3vl[_-]32b.*minimax.*h3.*\.(?:safetensors|gguf)$'),
    '119': ('Video VAE', 'vae_name', r'minimax.*h3.*video_vae.*\.safetensors$'),
    '120': ('Audio VAE', 'vae_name', r'minimax.*h3.*audio_vae.*\.safetensors$'),
    '145': ('8-step acceleration LoRA', 'lora_name', r'minimax.*h3.*ref2v.*8step.*\.safetensors$'),
    '156': ('VSA gate', 'gate_file', r'.*vsa.*gate.*\.safetensors$'),
}


def model_pattern(key, preset):
    if key == '127' and preset == 'hyperflow':
        return r'^(?=.*hyperflow)(?=.*ref2va).*\.(?:safetensors|gguf)$'
    if key == '127' and preset == 'fast-omni':
        return r'fast[-_]?h3.*omni(?:ref)?.*\.(?:safetensors|gguf)$'
    if key == '127':
        return r'^(?!.*(?:hyperflow|omni)).*minimax[-_].*h3.*ref2va.*\.(?:safetensors|gguf)$'
    return MODEL_FIELDS[key][2]


def model_preset(data):
    filename = data.get('model_files', {}).get('127', '') if isinstance(data.get('model_files', {}), dict) else ''
    if isinstance(filename, str) and filename:
        if 'hyperflow' in filename.lower():return 'hyperflow'
        return 'fast-omni' if re.search(model_pattern('127', 'fast-omni'), filename, re.I) else 'vsa' if data.get('video_preset') == 'vsa' else 'original'
    return data.get('video_preset', 'fast-omni')


def model_files(data):
    files = data.get('model_files', {})
    preset = model_preset(data)
    if not isinstance(files, dict) or any(key not in MODEL_FIELDS or not isinstance(value, str) or
            (preset in ('fast-omni','hyperflow') and key in ('145', '156')) or
            len(value) > 512 or not re.search(model_pattern(key, preset), value, re.I) for key, value in files.items()):
        raise ValueError('Choose compatible H3 Ref2VA model files.')
    return dict(files)


def settings(data):
    if data.get('studio_app') == 'second-take':
        from . import character_swap
        return character_swap.settings(data)
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
    if preset=='hyperflow' and any('tara' in row.get('name','').lower() or 'character_swap' in row.get('name','').lower() for row in data.get('loras',[]) if isinstance(row,dict)):
        raise ValueError('HyperFlow does not support Character Swap or TARA. Choose Base or OmniRef.')
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
    audio_ids = {key: data.get(key, '') for key in ('audio_reference_id', 'output_audio_id', 'output_audio_selection_id')}
    if any(not isinstance(ident, str) or ident and not re.fullmatch(r'[a-f0-9]{32}', ident) for ident in audio_ids.values()):
        raise ValueError('Choose an uploaded audio file.')
    enhance = data.get('prompt_enhancer', False)
    lift = data.get('selflift', False)
    if not isinstance(lift, bool):
        raise ValueError('SelfLift must be on or off.')
    enhancer_model = data.get('enhancer_model', '')
    if not isinstance(enhance, bool) or not isinstance(enhancer_model, str) or len(enhancer_model) > 512:
        raise ValueError('Invalid video prompt enhancer selection.')
    return dict(title=str(data.get('title', 'New shot'))[:120], prompt=prompt, mode='video',
                workflow_id='h3-ref2va', model_files=files, model_format='gguf' if files.get('127', '').lower().endswith('.gguf') else 'standard', steps=8,
                ratio=ratio, megapixels=mp, duration=duration, fps=24, seed=seed,
                video_preset=preset, reference_ids=list(dict.fromkeys(refs)), motion_reference_id=motion_id, **audio_ids, prompt_enhancer=enhance,enhancer_model=enhancer_model,
                selflift=lift, video_direction=video_prompt.validate(data.get('video_direction', {})),
                loras=validate_loras(data.get('loras', [])))


def template(preset, swap=False):
    if swap and preset not in TARA_PRESETS:
        raise ValueError('HyperFlow does not support Character Swap. Choose Base or OmniRef.')
    return json.loads((ROOT / (TARA_PRESETS if swap else PRESETS)[preset]).read_text(encoding='utf-8'))


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
                if key == '127' and preset!='hyperflow':
                    all_files += names(nodes, 'UnetLoaderGGUF', 'unet_name')
                if key == '128':
                    all_files += names(nodes, 'CLIPLoaderGGUF', 'clip_name')
                options = list(dict.fromkeys(name for name in all_files if re.search(pattern, name, re.I)))
                default = inputs[field]
                chosen = (selected or {}).get(key, default)
                if key == '127' and chosen.lower().endswith('.gguf') and 'UnetLoaderGGUF' not in nodes:
                    fixed_missing.append('Node: UnetLoaderGGUF (H3-compatible version)')
                    missing.append(fixed_missing[-1])
                if key == '128' and chosen.lower().endswith('.gguf') and 'CLIPLoaderGGUF' not in nodes:
                    fixed_missing.append('Node: CLIPLoaderGGUF (H3-compatible version)')
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
                     for preset in ('fast-omni', 'original','hyperflow') for loader in result[preset]['loaders']
                     if loader['node'] == '127' for file in loader['options']]
    return dict(presets=result, models=model_choices, selflift=selflift.availability(nodes),loras=lora_availability(nodes),prompt_presets=video_prompt.catalog(),enhancer=video_prompt.availability(nodes),
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


def validate_graph_links(graph,nodes):
    """Reject invalid output slots before SDK submission, with a useful error."""
    if nodes is None:return
    for target,node in graph.items():
        for field,value in node['inputs'].items():
            if not (isinstance(value,list) and len(value)==2 and isinstance(value[0],str) and isinstance(value[1],int)):continue
            source,slot=value
            if source not in graph:raise ValueError(f'Workflow connection missing: {target}.{field} → {source}.')
            kind=graph[source]['class_type'];schema=nodes.get(kind)
            if schema is not None and not 0<=slot<len(schema.get('output',[])):
                raise ValueError(f'Workflow connection invalid: {kind} ({source}) has no output {slot}; required by {node["class_type"]} ({target}).{field}.')


def build_graph(saved, prefix, nodes=None):
    swap=saved.get('studio_app')=='second-take'
    from . import character_swap
    swap_mode=character_swap.mode(saved) if swap else None
    graph = template(model_preset(saved),swap and swap_mode=='motion')
    if swap and model_preset(saved)=='hyperflow':raise ValueError('HyperFlow does not support Character Swap. Choose Base or OmniRef.')
    required_lora=character_swap.MODES[swap_mode]['lora'] if swap else None
    if swap and nodes is not None:
        if required_lora not in lora_availability(nodes)['files']:
            raise ValueError('Second Take LoRA not installed: '+required_lora)
        if swap_mode=='motion' and 'BFSMiniMaxH3NativeTemporal' not in nodes:
            raise ValueError('Motion Transfer requires BFS native TARA.')
    for key, filename in model_files(saved).items():
        if key in graph:
            graph[key]['inputs'][MODEL_FIELDS[key][1]] = filename
    if graph['127']['class_type']!='HyperFlowLoader' and graph['127']['inputs']['unet_name'].lower().endswith('.gguf'):
        graph['127'] = dict(class_type='UnetLoaderGGUF', inputs=dict(unet_name=graph['127']['inputs']['unet_name']))
    if graph['128']['inputs']['clip_name'].lower().endswith('.gguf'):
        inputs = graph['128']['inputs']
        graph['128'] = dict(class_type='CLIPLoaderGGUF', inputs=dict(clip_name=inputs['clip_name'], type=inputs['type']))
    if swap and swap_mode!='motion':
        parent=graph['142']['inputs']['model']
        graph['dc_swap_lora']=dict(class_type='LoraLoaderModelOnly',inputs=dict(model=parent,lora_name=required_lora,strength_model=1.))
        graph['142']['inputs']['model']=['dc_swap_lora',0]
        if swap_mode=='character-1':
            graph['124']['inputs']['scheduler']='normal'
            graph['123']['inputs']['sampler_name']='er_sde'
            if model_preset(saved)=='original':
                turbo='minimax_h3_fl2v_turbo_8step_v1.0_768p_comfyui_bf16.safetensors'
                if nodes is not None and turbo not in lora_availability(nodes)['files']:raise ValueError('Character Swap 1 acceleration LoRA not installed: '+turbo)
                graph['145']['inputs']['lora_name']=turbo
    adapter_loras={row['lora'] for row in character_swap.MODES.values()}
    attach_loras(graph, [r for r in saved.get('loras', []) if not swap or r['name'] not in adapter_loras])
    refs = saved.get('references', [])
    if len(refs) > 9:
        raise ValueError('H3 accepts up to 9 image references.')
    prompt = saved['prompt'] if saved.get('studio_app') == 'second-take' else reference_prompt(saved['prompt'], refs, saved)
    if swap:
        prompt=re.sub(r'^\s*(?:body_swap|motion_transfer):\s*','',prompt,count=1)
        if swap_mode=='motion':prompt='motion_transfer:\n'+prompt
    prompt = video_prompt.apply_direction(prompt, video_prompt.validate(saved.get('video_direction', {})))
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
        if swap and swap_mode=='motion':
            dims=image_dimensions(saved.get('swap_ratio',saved['ratio']),saved['megapixels'],minimum=.2)
            graph['dc_tara_guide'] = dict(class_type='ImageScale',inputs=dict(image=['dc_motion_frames',0],upscale_method='lanczos',width=max(32,dims['width']//64*32),height=max(32,dims['height']//64*32),crop='disabled'))
            encoder['ref_videos.ref_video_0']=['dc_tara_guide',0]
        if saved.get('studio_app') == 'second-take' and saved.get('swap_source', {}).get('audio'):
            schema = (nodes or {}).get('MiniMaxH3ReferenceToVideo', {}).get('input', {})
            if nodes is None or any('ref_video_audios' in fields for fields in schema.values() if isinstance(fields, dict)):
                encoder['ref_video_audios.ref_video_audio_0'] = ['dc_motion_frames', 1]
        if saved.get('studio_app') != 'second-take':
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
        if saved.get('studio_app') != 'second-take':prompt += ('\n\nAudio reference: <Audio 1> supplies the speaking character’s vocal timbre, delivery and speech timing. '
            'Preserve the character identity from the image references. Match mouth articulation and pauses to the speech performance. '
            'Use the words from <Audio 1> when the scene does not specify dialogue; otherwise preserve the scripted dialogue. '
            'Do not copy unrelated background music or environmental noise from the reference audio.')
    frames = round(saved['duration'] * 24)
    frames += (5 - frames) % 17
    encoder.update(prompt=prompt, **image_dimensions(saved.get('swap_ratio', saved['ratio']), saved['megapixels'], minimum=.2), length=frames, ref_image_size='match')
    if swap and swap_mode=='character-2':
        if not saved.get('motion_reference'):raise ValueError('Character Swap 2 needs the source video.')
        if nodes is not None and 'MiniMaxH3AddGuide' not in nodes:raise ValueError('Character Swap 2 requires MiniMax H3 Add Guide.')
        encoder.pop('ref_videos.ref_video_0',None)
        paired=encoder.pop('ref_video_audios.ref_video_audio_0',None)
        if paired is not None:encoder.setdefault('ref_audios.ref_audio_0',paired)
        graph['dc_swap_guide']=dict(class_type='ImageScale',inputs=dict(image=['dc_motion_frames',0],upscale_method='lanczos',width=encoder['width'],height=encoder['height'],crop='disabled'))
        graph['dc_swap_addguide']=dict(class_type='MiniMaxH3AddGuide',inputs=dict(positive=['136',0],latent=['136',1],vae=['119',0],image=['dc_swap_guide',0],frame_idx=0))
        graph['126']['inputs']['conditioning']=['dc_swap_addguide',0]
        # Add Guide returns CONDITIONING only; the AV latent stays at ReferenceToVideo.
        graph['125']['inputs']['latent_image']=['136',1]
        prompt=prompt.replace('<Video 1>','the guide video')
        if not prompt.lstrip().startswith('body_swap:'):prompt='body_swap:\n'+prompt
        encoder['prompt']=prompt
    graph['129']['inputs']['noise_seed'] = saved['seed']
    graph['124']['inputs']['steps'] = 8
    selflift.attach(graph,saved,nodes)
    graph['92']['inputs']['filename_prefix'] = prefix
    if saved.get('prompt_enhancer'):
        video_prompt.attach(graph,prompt,saved.get('enhancer_model',''),saved['seed'],saved['duration'],nodes or {},[f'h3_reference_{i}' for i in range(len(refs))])
    result=prune(graph,'92')
    result.update({key:node for key,node in graph.items() if node['class_type']=='PreviewAny' and key.startswith('dc_')})
    validate_graph_links(result,nodes)
    return result, prompt
