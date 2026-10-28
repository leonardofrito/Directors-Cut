"""Workflow catalog, installed-model discovery, and loader selection."""
import copy
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent.parent
CATALOG = json.loads((ROOT / 'workflows/catalog.json').read_text(encoding='utf-8'))
EDITABLE = {'qwen21', 'flux2-dev', 'flux2-klein', 'flux3-klein'}


def entry(workflow_id='qwen21'):
    return next(item for item in CATALOG if item['id'] == workflow_id)


def template(item):
    return json.loads((ROOT / 'workflows' / item['graph']).read_text(encoding='utf-8'))


def prune(graph, output):
    result = {}
    def visit(node_id):
        if node_id in result:
            return
        result[node_id] = graph[node_id]
        for value in graph[node_id]['inputs'].values():
            if isinstance(value, list) and len(value) == 2 and isinstance(value[0], str):
                visit(value[0])
    visit(output)
    return result


def simplify(graph):
    """Resolve constant workflow switches so inactive models are not required."""
    def constant(value):
        if isinstance(value, list) and len(value) == 2 and isinstance(value[0], str):
            node = graph[value[0]]
            if node['class_type'].startswith('Primitive'):
                return node['inputs'].get('value')
            return None
        return value
    for _ in range(len(graph)):
        replacements = {}
        for node_id, node in graph.items():
            if node['class_type'] == 'ComfySwitchNode':
                switch = constant(node['inputs'].get('switch'))
                if isinstance(switch, bool):
                    replacements[node_id] = node['inputs'].get('on_true' if switch else 'on_false')
        changed = False
        for node in graph.values():
            for key, value in list(node['inputs'].items()):
                if isinstance(value, list) and len(value) == 2 and isinstance(value[0], str) and value[0] in replacements and replacements[value[0]] is not None:
                    node['inputs'][key] = copy.deepcopy(replacements[value[0]])
                    changed = True
        if not changed:
            break
    return graph


def prepared(item):
    graph = template(item)
    if item['id'] == 'flux2-dev':
        # References are attached from project assets, never from sample filenames.
        graph['68_22']['inputs']['conditioning'] = ['68_26', 0]
    # Director controls own the positive prompt. Optional enhancement is attached
    # separately after model selection, leaving imported source workflows intact.
    graph[item['prompt_node']]['inputs'][item['prompt_field']] = ''
    for node in graph.values():
        if node['class_type'] in ('EmptyLatentImage', 'EmptySD3LatentImage', 'EmptyFlux2LatentImage', 'Flux2Scheduler', 'Ideogram4Scheduler'):
            node['inputs'].update(width=1024, height=576)
        if node['class_type'] == 'Ideogram4Scheduler':
            node['inputs'].update(steps=item['default_steps'], mu=0, std=1.75)
    return prune(simplify(graph), item['output'])


def names(nodes, kind, field):
    schema = nodes.get(kind, {}).get('input', {})
    value = {**schema.get('required', {}), **schema.get('optional', {})}.get(field, [[]])[0]
    return value if isinstance(value, list) else []


def family(default, candidate):
    """Restrict choices to the same inspected model family, not every UNet."""
    clean = lambda s: re.sub(r'[^a-z0-9]', '', s.lower())
    a, b = clean(default), clean(candidate)
    if 'mmproj' in b:
        return False
    if 'qwenimage21' in a:
        return 'qwenimage21' in b and 'pe' not in b
    if 'qwen3vl8b' in a:
        return 'qwen3vl8b' in b and 'minimax' not in b
    if 'qwen3vl4b' in a:
        return 'qwen3vl4b' in b
    if 't5xxl' in a:
        return 't5xxl' in b
    if 'flux2klein' in a:
        return 'flux2klein' in b and ('9b' in a) == ('9b' in b) and ('base' in a) == ('base' in b)
    if 'flux3imageklein' in a:
        return 'flux3imageklein' in b and ('kleinsd' in a) == ('kleinsd' in b)
    if 'krea2' in a:
        return 'krea2' in b and ('turbo' in a) == ('turbo' in b)
    for token in ('chroma1', 'flux2klein', 'flux2dev', 'ideogram4', 'krea2', 'mistral3smallflux2', 'qwen38b'):
        if token in a:
            return token in b and (('unconditional' in a) == ('unconditional' in b))
    return default == candidate


def loaders(graph, nodes, model_format):
    result = []
    for node_id, node in graph.items():
        kind = node['class_type']
        if kind not in ('UNETLoader', 'CLIPLoader', 'VAELoader'):
            continue
        field = {'UNETLoader': 'unet_name', 'CLIPLoader': 'clip_name', 'VAELoader': 'vae_name'}[kind]
        default = node['inputs'][field]
        target_kind = 'UnetLoaderGGUF' if kind == 'UNETLoader' and model_format == 'gguf' else kind
        candidates = names(nodes, target_kind, field)
        if kind == 'CLIPLoader':
            candidates = sorted(set(candidates + [n for n in names(nodes, 'CLIPLoaderGGUF', field) if n.lower().endswith('.gguf')]))
        options = [name for name in candidates if family(default, name)]
        result.append(dict(node=node_id, field=field, kind=kind, target_kind=target_kind,
                           role={'UNETLoader': 'Diffusion model', 'CLIPLoader': 'Text encoder', 'VAELoader': 'VAE'}[kind],
                           expected=default, options=options, default=default if default in options else next(iter(options), '')))
    return result


def select_models(graph, item, model_format, selected, nodes):
    if model_format not in ('standard', 'gguf'):
        raise ValueError('Choose Standard or GGUF.')
    for loader in loaders(graph, nodes, model_format):
        chosen = selected.get(loader['node'], loader['default'])
        if chosen not in loader['options']:
            raise ValueError(f'{loader["role"]} is missing: {loader["expected"]}. Open Model setup for download links.')
        node = graph[loader['node']]
        if loader['kind'] == 'UNETLoader':
            node['class_type'] = loader['target_kind']
            node['inputs'] = {loader['field']: chosen}
            if model_format == 'standard':
                node['inputs']['weight_dtype'] = 'default'
        elif loader['kind'] == 'CLIPLoader' and chosen.lower().endswith('.gguf'):
            node['class_type'] = 'CLIPLoaderGGUF'
            node['inputs'] = {'clip_name': chosen, 'type': node['inputs']['type']}
        else:
            node['inputs'][loader['field']] = chosen
    return graph


def describe(nodes):
    result = []
    for item in CATALOG:
        if item['id'] != 'qwen21':
            continue  # Historical workflows stay on disk; the studio now exposes only Qwen 2.1.
        graph = prepared(item)
        formats = {}
        for model_format in ('standard', 'gguf'):
            choices = loaders(graph, nodes, model_format)
            missing = [f'Compatible GGUF diffusion weights for {item["label"]}' if model_format == 'gguf' and l['kind'] == 'UNETLoader' else f'{l["role"]}: {l["expected"]}' for l in choices if not l['options']]
            needed = {n['class_type'] for n in graph.values() if n['class_type'] not in ('UNETLoader', 'CLIPLoader', 'VAELoader')}
            needed.update(l['target_kind'] for l in choices)
            missing.extend(f'Node: {kind}' for kind in sorted(needed) if kind not in nodes)
            edit_nodes = {'LoadImage'} | ({'ReferenceMultiLatent'} if item['id'].startswith('flux') else {'ImageResizeKJv2'})
            edit_missing = [f'Node: {kind}' for kind in sorted(edit_nodes) if kind not in nodes] if item['id'] in EDITABLE else ['This model has no reference editing workflow in the app.']
            formats[model_format] = dict(ready=not missing, missing=missing, loaders=choices, edit_ready=not missing and not edit_missing, edit_missing=missing + edit_missing)
        result.append({**item, 'requires_reference': False, 'supports_editing': item['id'] in EDITABLE, 'max_references': 10 if item['id'] in EDITABLE else 0, 'formats': formats})
    return result


def fit_qwen_reference_canvas(graph, item, references, dimensions, nodes=None):
    """Fill the selected output canvas by center-cropping the first reference, never padding."""
    if item['id'] != 'qwen21' or not references:
        return
    if nodes is not None and 'ImageResizeKJv2' not in nodes:
        raise ValueError('Reference sizing needs ImageResizeKJv2 from ComfyUI-KJNodes.')
    encoder = graph[item['prompt_node']]['inputs']
    for index, _ in enumerate(references):
        key = f'dc_reference_size_{index}'
        graph[key] = dict(class_type='ImageResizeKJv2', inputs=dict(
            image=[f'dc_reference_{index}', 0], **dimensions,
            upscale_method='lanczos', keep_proportion='crop' if index == 0 else 'total_pixels',
            pad_color='0, 0, 0', crop_position='center',
            divisible_by=1 if index == 0 else 32, device='cpu'))
        encoder[f'images.image_{index+1}'] = [key, 0]
    # A positive resolution would resize the canvas again. The first prepared
    # image now supplies the exact user-selected width/height to output latent 2.
    encoder['resolution'] = 0


def attach_references(graph, item, references):
    if not references:
        return
    if item['id'] not in EDITABLE:
        raise ValueError('Choose a model with reference editing support.')
    images = {}
    for index, ref in enumerate(references):
        node_id = f'dc_reference_{index}'
        graph[node_id] = dict(class_type='LoadImage', inputs=dict(image=ref['comfy_image']))
        images[index] = [node_id, 0]
    if item['id'] == 'qwen21':
        encoder = graph[item['prompt_node']]['inputs']
        encoder['vae'] = ['454', 0]
        encoder['resolution'] = 1024
        encoder.update({f'images.image_{i+1}': value for i, value in images.items()})
        # Qwen 2.1 embeds reference latents in its sequence. Sampling must use
        # the encoder's latent size, as required by the native node schema.
        for node in graph.values():
            if node['class_type'] == 'KSampler':
                node['inputs']['latent_image'] = [item['prompt_node'], 2]
    else:
        # Native Comfy multi-reference path, shared by FLUX.2 and FLUX.3.
        sampler = next(n for n in graph.values() if n['class_type'] in ('KSampler', 'CFGGuider', 'BasicGuider'))
        inputs = sampler['inputs']
        positive_key = 'conditioning' if 'conditioning' in inputs else 'positive'
        vae = next(k for k, n in graph.items() if n['class_type'] == 'VAELoader')
        refs = dict(positive=inputs[positive_key], vae=[vae, 0], resolution='resize', **{'resolution.megapixels': 1.0})
        if 'negative' in inputs:
            refs['negative'] = inputs['negative']
            inputs['negative'] = ['dc_reference_conditioning', 1]
        refs.update({f'images.image{i}': value for i, value in images.items()})
        graph['dc_reference_conditioning'] = dict(class_type='ReferenceMultiLatent', inputs=refs)
        inputs[positive_key] = ['dc_reference_conditioning', 0]
