"""Ordered model-only LoRA stacks using ComfyUI's native loader."""
import math

from .catalog import names


def validate_loras(value):
    if not isinstance(value, list) or len(value) > 16:
        raise ValueError('Choose up to 16 LoRAs.')
    result = []
    for row in value:
        if not isinstance(row, dict):
            raise ValueError('Invalid LoRA selection.')
        name, enabled = row.get('name', ''), row.get('enabled', True)
        strength = row.get('strength', 1)
        if not isinstance(name, str) or len(name) > 512 or not isinstance(enabled, bool):
            raise ValueError('Invalid LoRA selection.')
        if isinstance(strength, bool) or not isinstance(strength, (int, float)) or not math.isfinite(strength) or not -10 <= strength <= 10:
            raise ValueError('LoRA strength must be between -10 and 10.')
        if enabled and not name:
            raise ValueError('Choose a file for each enabled LoRA.')
        result.append(dict(name=name, strength=float(strength), enabled=enabled))
    return result


def availability(nodes):
    return dict(ready='LoraLoaderModelOnly' in nodes,
                files=names(nodes, 'LoraLoaderModelOnly', 'lora_name'))


def attach_loras(graph, rows, nodes=None):
    active = [row for row in validate_loras(rows) if row['enabled'] and row['strength'] != 0]
    if not active:
        return
    if nodes is not None:
        installed = availability(nodes)
        if not installed['ready']:
            raise ValueError('ComfyUI node missing: LoraLoaderModelOnly.')
        for row in active:
            if row['name'] not in installed['files']:
                raise ValueError('LoRA not installed: ' + row['name'])
    loader = next(key for key, node in graph.items() if node['class_type'] in ('UNETLoader', 'UnetLoaderGGUF'))
    previous = [loader, 0]
    stack = {}
    for index, row in enumerate(active):
        key = f'dc_lora_{index}'
        stack[key] = dict(class_type='LoraLoaderModelOnly', inputs=dict(
            model=previous, lora_name=row['name'], strength_model=row['strength']))
        previous = [key, 0]
    for node in graph.values():
        for key, value in node['inputs'].items():
            if value == [loader, 0]:
                node['inputs'][key] = previous
    graph.update(stack)
