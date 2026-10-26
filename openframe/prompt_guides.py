"""Shared, inert prompt references for MCP hosts and local enhancer context."""
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent/'docs/prompt-guides'
GUIDES={
    'h3':('h3-ref2va.md',),
    'h3-ref2va':('h3-ref2va.md',),
    'qwen':('qwen-overview.md','qwen-image.md'),
    'qwen-edit':('qwen-overview.md','qwen-image-editing.md'),
    'qwen-presets':('qwen-presets.md',),
    'qwen-examples':('qwen-examples.md',),
    'qwen-text':('qwen-text-rendering.md',),
    'qwen-capabilities':('qwen-capabilities.md',),
}

def guide_text(model):
    if model not in GUIDES:raise ValueError('Choose '+', '.join(GUIDES)+'. H3 uses REF2VA only.')
    return '\n\n'.join((ROOT/name).read_text(encoding='utf-8') for name in GUIDES[model])

def runtime_guidance(model):
    """Small maintained digest, not the entire corpus on a 4B model's context."""
    name='runtime-h3-ref2va.md' if model in ('h3','h3-ref2va') else 'runtime-qwen.md'
    return (ROOT/name).read_text(encoding='utf-8')


def prompt_strategy(model):
    """Project defaults from local tests, not a guarantee that length predicts quality."""
    if model in ('h3', 'h3-ref2va'):
        return dict(model='MiniMax H3 REF2VA', approach='detailed_video_direction',
                    guidance='Describe feasible actions in sequence, reference roles, framing, camera movement, cuts and audio. Use the REF2VA structure; detail must fit the duration. Preserve unusual identities and exact dialogue.',
                    prompt_enhancer='Optional; leave off when the host already writes the final prompt.')
    return dict(model='Qwen-Image 2.1', approach='short_scene_plus_existing_presets',
                guidance='Start with a short direct request and select the existing presets as structured JSON. Do not expand each selected choice into prose: the studio already does that. A preset-only request is valid. Add detail only to resolve missing intent or a specific failed result; do not automatically write a long prompt.',
                prompt_enhancer='Off by default for this path. It is optional, not needed to expand presets.',
                tools=['get_image_presets', 'preview_image_prompt'],
                note='These are project defaults informed by local testing. JSON is the tool settings format, not a claim that the image model needs a JSON caption.')


def image_settings_example():
    return dict(prompt='A cheerful mechanic wearing a red scarf.', asset_kind='character',
                ratio='1:1', megapixels=2, prompt_enhancer=False,
                character_traits={'character_type': {'value': 'Average'},
                                  'gender': {'value': 'Woman'},
                                  'age': {'value': 'Young adult'},
                                  'hairstyle': {'value': 'Bob'},
                                  'render_style': {'value': 'Studio portrait'}})
