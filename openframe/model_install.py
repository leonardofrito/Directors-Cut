"""Explicit local model-file imports; files are never downloaded in the background."""
import asyncio
import os
from pathlib import Path
import uuid

from aiohttp import web


async def import_video_file(request):
    kind = request.match_info['kind']
    folders = {'lora': ('loras', '.safetensors', 4 * 1024**3), 'gguf': ('diffusion_models', '.gguf', 64 * 1024**3)}
    if kind not in folders:
        raise ValueError('Choose a LoRA or GGUF file.')
    folder, suffix, limit = folders[kind]
    from .engine_config import downloads_directory
    models = downloads_directory()
    if not models.is_dir():
        raise ValueError('Set OPENFRAME_COMFY_ROOT to your local ComfyUI folder before importing models.')
    reader = await request.multipart()
    part = await reader.next()
    name = part.filename if part is not None else ''
    if not name or '/' in name or '\\' in name or ':' in name or Path(name).suffix.lower() != suffix:
        raise ValueError('Choose a single ' + suffix + ' file.')
    destination = (models / folder / name).resolve()
    if not destination.is_relative_to(models / folder):
        raise ValueError('Invalid model filename.')
    if destination.exists():
        raise ValueError('This file is already installed. Rename it before importing another version.')
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.parent / ('.import-' + uuid.uuid4().hex)
    try:
        size = 0
        with temporary.open('xb') as output:
            while chunk := await part.read_chunk(1024 * 1024):
                size += len(chunk)
                if size > limit:
                    raise ValueError('This model file exceeds the import size limit.')
                await asyncio.to_thread(output.write, chunk)
        with temporary.open('rb') as check:
            magic = check.read(8)
        if kind == 'gguf' and magic[:4] != b'GGUF' or kind == 'lora' and (len(magic) != 8 or not 2 <= int.from_bytes(magic, 'little') <= min(size - 8, 100 * 1024**2)):
            raise ValueError('The file does not have a valid ' + suffix + ' header.')
        # Hard-link publication refuses to overwrite an existing file, including a concurrent import.
        await asyncio.to_thread(os.link, temporary, destination)
        return web.json_response(dict(file=name, folder=folder), status=201)
    finally:
        temporary.unlink(missing_ok=True)
