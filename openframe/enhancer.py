"""Optional local prompt expansion using ComfyUI's native text generator."""
import re

from .catalog import names
from .prompt_guides import runtime_guidance

SYSTEM = (
    'Rewrite the supplied image request as one concrete visual caption. Use one to three sentences for a simple scene; add detail only for complex layouts. '
    'Preserve every explicit subject, count, action, text, composition, camera, lighting, film, '
    'art style and color instruction. Do not invent additional people or change the scene. '
    'If directions conflict, the final explicit direction takes priority. Clarify visual details '
    'only where unspecified. Output only the caption, without headings, commentary or quotation marks '
    'around the caption. Describe a single still image, not a video.'
    ' Do not output thinking tags or reasoning. Exaggerated anatomy does not imply illustration: '
    'preserve the explicitly requested photographic or artistic medium. Do not turn a studio photograph '
    'into concept art unless concept art was requested. Do not invent props, clothing or actions.'
)


UNUSABLE_CAPTION = r"^\s*(?:$|I(?:['’]m| am) sorry\b|Sorry\b|I (?:cannot|can['’]t|am unable)\b|As an? (?:AI|language model)\b)"
THINKING_PATTERN = r'^.*</think\s*>|<think\b[^>]*>.*$|</?think\b[^>]*>'


def clean_caption(text):
    return re.sub(THINKING_PATTERN, '', text, flags=re.IGNORECASE | re.DOTALL).strip()


def usable_caption(text):
    return isinstance(text, str) and re.search(UNUSABLE_CAPTION, text, re.IGNORECASE) is None


PROFILES = (
    dict(key='qwen21-pe-i2i', label='Qwen 2.1 image editing enhancer', kind='dedicated', loader_type='qwen_image',
         expected='qwen3.5_9b_qwen_image_2.1_pe_i2i.int8_convrot.safetensors', workflows=['qwen21'],
         file_prefix='qwen3.5_9b_qwen_image_2.1_pe_i2i', reference_only=True,
         hint='Image-aware editing enhancer. Requires reference images.'),
    dict(key='qwen21-pe-t2i', label='Qwen 2.1 dedicated T2I enhancer', kind='dedicated', loader_type='stable_diffusion',
         expected='qwen3.5_9b_qwen_image_2.1_pe_t2i.int8_convrot.safetensors', workflows=['qwen21'],
         file_prefix='qwen3.5_9b_qwen_image_2.1_pe_t2i',
         hint='Dedicated Qwen 2.1 text-to-image enhancer. Separate weights required.'),
    dict(key='flux3-upsampler', label='FLUX 3 dedicated prompt upsampler', kind='dedicated', loader_type='flux3',
         expected='qwen3.5_9b_flux3_prompt_upsampler_int8_convrot.safetensors', workflows=['flux3-klein'],
         file_prefix='qwen3.5_9b_flux3_prompt_upsampler_',
         hint='Dedicated FLUX 3 text-to-image prompt upsampler. Separate weights required.'),
    dict(key='qwen3vl4b', label='Qwen3-VL 4B · general LLM', kind='general', loader_type='stable_diffusion',
         expected='qwen3vl_4b_int8_convrot.safetensors', workflows=None,
         hint='Reuses the FLUX 3 text encoder as a general LLM. Not a dedicated prompt-enhancer checkpoint.'),
)

DOWNLOADS = (
    dict(label='Qwen 2.1 · image editing enhancer', workflows=['qwen21'], repo='Comfy-Org/Qwen-Image-2.1',
         page='https://huggingface.co/Comfy-Org/Qwen-Image-2.1/tree/main/text_encoders',
         files=[dict(label='INT8', name='qwen3.5_9b_qwen_image_2.1_pe_i2i.int8_convrot.safetensors'),
                dict(label='W4A8', name='qwen3.5_9b_qwen_image_2.1_pe_i2i_w4a8.safetensors')]),
    dict(label='Qwen 2.1 · dedicated T2I enhancer', workflows=['qwen21'], repo='Comfy-Org/Qwen-Image-2.1',
         page='https://huggingface.co/Comfy-Org/Qwen-Image-2.1',
         files=[dict(label='INT8', name='qwen3.5_9b_qwen_image_2.1_pe_t2i.int8_convrot.safetensors'),
                dict(label='W4A8', name='qwen3.5_9b_qwen_image_2.1_pe_t2i_w4a8.safetensors')]),
    dict(label='FLUX 3 · dedicated prompt upsampler', workflows=['flux3-klein'], repo='black-forest-labs/flux-3-image-klein-comfy',
         page='https://huggingface.co/black-forest-labs/flux-3-image-klein-comfy',
         files=[dict(label='INT8', name='qwen3.5_9b_flux3_prompt_upsampler_int8_convrot.safetensors'),
                dict(label='W4A8', name='qwen3.5_9b_flux3_prompt_upsampler_w4a8.safetensors')]),
)


def availability(nodes, workflow_id=None):
    installed = names(nodes, 'CLIPLoader', 'clip_name')
    types = names(nodes, 'CLIPLoader', 'type')
    required = ('TextGenerate', 'CLIPLoader', 'PreviewAny', 'PrimitiveStringMultiline', 'StringConcatenate',
                'StringTrim', 'RegexMatch', 'RegexReplace', 'ComfySwitchNode')
    shared_missing = [f'Node: {kind}' for kind in required if kind not in nodes]
    models = []
    for profile in PROFILES:
        if workflow_id and profile['workflows'] and workflow_id not in profile['workflows']:
            continue
        if profile['kind'] == 'dedicated':
            files = [name for name in installed if name.replace('\\', '/').rsplit('/', 1)[-1].lower().startswith(profile['file_prefix']) and name.lower().endswith('.safetensors')]
        else:
            files = [name for name in installed if name.replace('\\', '/').rsplit('/', 1)[-1].lower().startswith('qwen3vl_4b_') and name.lower().endswith('.safetensors')]
        for filename in files or [profile['expected']]:
            missing = list(shared_missing)
            if profile.get('reference_only') and 'BatchImagesNode' not in nodes:
                missing.append('Node: BatchImagesNode')
            if profile['kind'] == 'general':
                missing.append('Disabled as an enhancer: repeated empty captions or refusals in this app. Choose dedicated enhancer weights below.')
            if not files:
                missing.append('Not installed in ComfyUI/models/text_encoders')
            if profile['loader_type'] not in types:
                missing.append('CLIPLoader type: ' + profile['loader_type'])
            supported = profile['workflows'] is None or workflow_id is None or workflow_id in profile['workflows']
            if not supported:
                missing.append('This dedicated enhancer is configured for ' + ', '.join(profile['workflows']) + ' text-to-image only')
            models.append({**profile, 'id': filename, 'file': filename, 'installed': bool(files), 'ready': not missing, 'missing': missing})
    return dict(ready=any(m['ready'] for m in models), models=models,
                missing=shared_missing, requires_selection=True, downloads=[d for d in DOWNLOADS if not workflow_id or workflow_id in d['workflows']],
                install_folder='ComfyUI/models/text_encoders/')


def attach(graph, item, scene, direction, seed, nodes, selected):
    status = availability(nodes, item['id'])
    model = next((m for m in status['models'] if m['id'] == selected), None)
    if not model:
        raise ValueError('Prompt enhancer needs setup: choose an installed enhancer model explicitly.')
    if not model['ready']:
        raise ValueError('Prompt enhancer needs setup: ' + '; '.join(model['missing']))
    tags = list(dict.fromkeys(re.findall(r'<image\d+>', scene)))
    image_nodes = [key for key in graph if re.fullmatch(r'dc_reference_\d+', key)]
    image_nodes.sort(key=lambda key: int(key.rsplit('_', 1)[-1]))
    if model.get('reference_only') and not image_nodes:
        raise ValueError('The image editing enhancer needs at least one reference image.')
    system = SYSTEM
    unusable = UNUSABLE_CAPTION
    if tags:
        system = ('Rewrite this image editing/compositing instruction as one to three short imperative sentences. Do not pad a simple edit with extra description. '
                  'You cannot see the reference images. Preserve every <imageN> tag exactly, its assigned role, '
                  'subject count, requested change and spatial relationship. Do not describe or invent what the '
                  'images contain. Preserve everything not explicitly changed, including the rendering medium. '
                  'Output only the instruction, without reasoning or commentary.')
        # A rewriter that loses even one image binding falls back to the original.
        unusable += '|' + '|'.join(r'\A(?![\s\S]*' + re.escape(tag) + r')[\s\S]*\Z' for tag in tags)
        if model.get('reference_only'):
            system = system.replace('You cannot see the reference images.', 'The attached images are in tag order. Use them to clarify the requested edit without changing their roles.')
    system+='\n\nModel-specific prompting reference:\n'+runtime_guidance('qwen-edit' if image_nodes else 'qwen')
    graph.update({
        'dc_enhancer_clip': dict(class_type='CLIPLoader', inputs=dict(clip_name=model['file'], type=model['loader_type'], device='default')),
        'dc_enhancer_system': dict(class_type='PrimitiveStringMultiline', inputs=dict(value=system)),
        'dc_enhancer': dict(class_type='TextGenerate', inputs={
            'clip': ['dc_enhancer_clip', 0], 'prompt': scene, 'max_length': 1024,
            'sampling_mode': 'on', 'sampling_mode.temperature': 0.6, 'sampling_mode.top_k': 20,
            'sampling_mode.top_p': 0.9, 'sampling_mode.min_p': 0, 'sampling_mode.repetition_penalty': 1.05,
            'sampling_mode.seed': seed, 'sampling_mode.presence_penalty': 0,
            'thinking': False, 'use_default_template': True, 'mtp': 'off',
            'system_prompt': ['dc_enhancer_system', 0],
        }),
        'dc_enhancer_clean': dict(class_type='RegexReplace', inputs=dict(string=['dc_enhancer', 0], regex_pattern=THINKING_PATTERN, replace='', case_insensitive=True, multiline=False, dotall=True, count=0)),
        'dc_enhancer_trim': dict(class_type='StringTrim', inputs=dict(string=['dc_enhancer_clean', 0], mode='Both')),
        'dc_expansion_preview': dict(class_type='PreviewAny', inputs=dict(source=['dc_enhancer_trim', 0])),
        'dc_enhancer_unusable': dict(class_type='RegexMatch', inputs=dict(string=['dc_enhancer_trim', 0], regex_pattern=unusable, case_insensitive=True, multiline=False, dotall=False)),
        # Generation can terminate without usable text; never send camera cues alone.
        # Select the original scene in the graph, before image conditioning takes place.
        'dc_scene_prompt': dict(class_type='ComfySwitchNode', inputs=dict(switch=['dc_enhancer_unusable', 0], on_true=scene, on_false=['dc_enhancer_trim', 0])),
        'dc_directed_prompt': dict(class_type='StringConcatenate', inputs=dict(string_a=['dc_scene_prompt', 0], string_b=direction, delimiter='\n')),
        'dc_enhanced_preview': dict(class_type='PreviewAny', inputs=dict(source=['dc_directed_prompt', 0])),
    })
    graph[item['prompt_node']]['inputs'][item['prompt_field']] = ['dc_directed_prompt', 0]
    if model.get('reference_only'):
        graph['dc_enhancer_images'] = dict(class_type='BatchImagesNode', inputs={f'images.image{i}': [key, 0] for i, key in enumerate(image_nodes)})
        graph['dc_enhancer']['inputs']['image'] = ['dc_enhancer_images', 0]
