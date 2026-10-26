"""Optional local RTX postprocessing, independent of the H3 generation recipe."""
import re

REQUIRED = ('RTXVideoSuperResolution', 'LoadVideo', 'GetVideoComponents', 'CreateVideo', 'SaveVideo')


def availability(nodes, devices):
    # Use the device selected by Comfy, not the GPU of the browser's computer.
    cuda = next((d for d in devices if d.get('type') == 'cuda'), None)
    supported = bool(cuda and re.search(r'\bRTX\b|\bGB10\b', cuda.get('name', ''), re.I))
    missing = [name for name in REQUIRED if name not in nodes]
    return dict(ready=supported and not missing, scale=2,
                gpu=cuda.get('name', '') if cuda else '', missing=missing)


def build_graph(source, prefix, nodes=None):
    graph = {
        'rtx_load': dict(class_type='LoadVideo', inputs=dict(file=source)),
        'rtx_components': dict(class_type='GetVideoComponents', inputs=dict(video=['rtx_load', 0])),
        'rtx_upscale': dict(class_type='RTXVideoSuperResolution', inputs={
            'images': ['rtx_components', 0], 'resize_type': 'scale by multiplier',
            'resize_type.scale': 2.0, 'quality': 'ULTRA'}),
        'rtx_create': dict(class_type='CreateVideo', inputs=dict(
            images=['rtx_upscale', 0], audio=['rtx_components', 1], fps=['rtx_components', 2])),
        'rtx_save': dict(class_type='SaveVideo', inputs={
            'video': ['rtx_create', 0], 'filename_prefix': prefix,
            'format': 'mp4', 'format.codec': 'h264'}),
    }
    # Newer releases add widgets (strength/encoding); retain their declared defaults.
    schema = (nodes or {}).get('RTXVideoSuperResolution', {}).get('input', {}).get('required', {})
    for name, definition in schema.items():
        options = definition[1] if len(definition) > 1 and isinstance(definition[1], dict) else {}
        if name not in graph['rtx_upscale']['inputs'] and 'default' in options:
            graph['rtx_upscale']['inputs'][name] = options['default']
    return graph
