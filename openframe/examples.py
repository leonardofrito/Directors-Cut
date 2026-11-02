"""Explicit installation of curated, bundled example projects. Never user uploads."""
import asyncio
import json
import os
import tempfile
import uuid
import zipfile
from pathlib import Path, PurePosixPath
from aiohttp import web
from .paths import RESOURCE_ROOT
from .storage import now, write_json

EXAMPLES = RESOURCE_ROOT / 'examples'


def catalog():
    path = EXAMPLES / 'index.json'
    return json.loads(path.read_text(encoding='utf-8')) if path.is_file() else []


def install(store, example_id):
    entry = next((item for item in catalog() if item['id'] == example_id), None)
    if not entry:
        raise ValueError('Example project not found.')
    existing = next((p for p in store.list() if p.get('example_id') == example_id), None)
    if existing:
        return existing  # Never reset or overwrite someone's changes.
    archive_path = (EXAMPLES / entry['bundle']).resolve()
    if not archive_path.is_relative_to(EXAMPLES.resolve()):
        raise ValueError('Invalid example path.')
    identifier = 'Bank_of_Ideas_demo_' + uuid.uuid4().hex[:10]
    destination = store.folder(identifier)
    if destination.exists():
        raise ValueError('Example destination already exists.')
    with tempfile.TemporaryDirectory(prefix='.example-', dir=store.root) as scratch:
        folder = Path(scratch) / 'project';folder.mkdir()
        with zipfile.ZipFile(archive_path) as archive:
            entries = archive.infolist()
            if len(entries) > 500 or sum(i.file_size for i in entries) > 300*1024*1024:
                raise ValueError('Example archive is too large.')
            seen = set()
            for info in entries:
                relative = PurePosixPath(info.filename)
                if relative.is_absolute() or '..' in relative.parts or '\\' in info.filename or ':' in info.filename or info.filename in seen:
                    raise ValueError('Unsafe example archive path.')
                seen.add(info.filename)
                target = (folder / info.filename).resolve()
                if not target.is_relative_to(folder.resolve()) or info.is_dir():
                    raise ValueError('Invalid example entry.')
                if target.suffix.lower() not in ('.json', '.jpg', '.png', '.mp4', '.webp'):
                    raise ValueError('Unsupported example file.')
                target.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(info) as source, target.open('wb') as output:
                    import shutil
                    shutil.copyfileobj(source, output, 1024*1024)
        project = json.loads((folder/'project.json').read_text(encoding='utf-8'))
        project.update(id=identifier, name=entry['name'], example_id=example_id, created_at=now(), updated_at=now())
        write_json(folder/'project.json', project)
        os.rename(folder, destination)
    return store.load(identifier)


async def list_examples(request):
    return web.json_response([{k:v for k,v in item.items() if k != 'bundle'} for item in catalog()])


async def open_example(request):
    lock = request.app.get('example_import_lock')
    if lock is None:
        lock = asyncio.Lock();request.app['example_import_lock'] = lock
    async with lock:
        project = await asyncio.to_thread(install, request.app['studio'].store, request.match_info['example'])
    return web.json_response(project)
