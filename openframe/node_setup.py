"""Pinned optional node packs, installed only in the configured local Comfy Python."""
import asyncio, hashlib, io, json, os, shutil, stat, tempfile, zipfile
from pathlib import Path
import aiohttp
from aiohttp import web
from . import engine_config as cfg
from .paths import DATA_ROOT
from .storage import write_json

PACKS=json.loads(Path(__file__).with_name('node_catalog.json').read_text(encoding='utf-8'))
PREFS=DATA_ROOT/'.runtime/node-setup.json'

def preferences():
    try:return json.loads(PREFS.read_text(encoding='utf-8'))
    except (OSError,ValueError):return {'automatic':False,'optional':[]}

def engine_paths():
    settings=cfg.current()
    if not cfg.local(settings['comfy_url']):raise ValueError('Node installation runs on this PC only. Install remote engine nodes on the ComfyUI computer.')
    root=Path(settings['comfy_root']).resolve()
    if not (root/'main.py').is_file():raise ValueError('Choose the ComfyUI folder in Connection first.')
    candidates=[root.parent/'python_embeded/python.exe',root/'.venv/Scripts/python.exe',root/'venv/Scripts/python.exe',root/'.venv/bin/python',root/'venv/bin/python']
    python=next((p for p in candidates if p.is_file()),None)
    if python is None:raise ValueError('ComfyUI Python was not found. Use its Portable/Desktop environment; the app Python will never be substituted.')
    return root,python

def installed_directory(root,pack):
    folder=root/'custom_nodes'
    return next((p for p in folder.iterdir() if p.is_dir() and p.name.lower().replace('_','-')==pack['folder'].lower().replace('_','-')),None) if folder.is_dir() else None

def unpack(data,destination):
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        total=0
        for info in archive.infolist():
            parts=Path(info.filename).parts
            if len(parts)<2:continue
            target=(destination/Path(*parts[1:])).resolve()
            if not target.is_relative_to(destination.resolve()) or stat.S_ISLNK(info.external_attr>>16):raise ValueError('Unsafe node archive.')
            total+=info.file_size
            if total>128*1024**2:raise ValueError('Node archive is too large.')
            if info.is_dir():target.mkdir(parents=True,exist_ok=True)
            else:
                target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(archive.read(info))

class NodeSetup:
    def __init__(self,studio):self.studio=studio;self.task=None;self.job={'status':'idle','message':''}
    @property
    def running(self):return self.task is not None and not self.task.done()
    async def close(self):
        # Let Python package installation finish rather than killing it mid-write.
        if self.running:await self.task
    def describe(self,nodes):
        try:root,python=engine_paths();error=''
        except ValueError as exc:root=None;error=str(exc)
        return {'preferences':preferences(),'job':self.job,'install_error':error,'packs':[
            {**p,'installed':bool(root and installed_directory(root,p)),'loaded':all(n in nodes for n in p['nodes'])} for p in PACKS]}
    async def ensure_idle(self):
        if self.studio.connection_changing or self.studio.queue_items() or self.studio.queue.qsize():raise ValueError('Wait until the generation queue is idle before installing nodes.')
        if any(j['status'] in ('queued','downloading','verifying') for j in self.studio.model_downloads.snapshot()):raise ValueError('Pause model downloads before installing nodes.')
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5)) as session:
            try:
                async with session.get(cfg.current()['comfy_url']+'/queue') as response:
                    response.raise_for_status();data=await response.json()
                    if data.get('queue_running') or data.get('queue_pending'):raise ValueError('ComfyUI is busy. Wait before installing nodes.')
            except (aiohttp.ClientError,asyncio.TimeoutError):
                # Offline engines can safely receive node files before starting.
                pass
    async def start(self,ids):
        if self.running:return self.job
        allowed={p['id'] for p in PACKS}
        if not isinstance(ids,list) or any(not isinstance(x,str) or x not in allowed for x in ids):raise ValueError('Choose nodes from the app catalog.')
        root,_=engine_paths()
        if all(installed_directory(root,p) for p in PACKS if p['id'] in ids):
            self.job={'status':'complete','message':'Selected node packs are already on disk. Start/restart ComfyUI if they are not loaded.'};return self.job
        await self.ensure_idle()
        self.job={'status':'queued','message':'Preparing required nodes…'}
        self.task=asyncio.create_task(self.install(list(dict.fromkeys(ids))));return self.job
    async def command(self,args,root,log):
        options={'creationflags':0x08000000} if os.name=='nt' else {}
        process=await asyncio.create_subprocess_exec(*map(str,args),cwd=root,stdout=log,stderr=log,**options)
        try:code=await asyncio.wait_for(process.wait(),600)
        except asyncio.TimeoutError:process.terminate();await process.wait();raise ValueError('Node dependencies timed out. See the setup log.')
        if code:raise ValueError('Node dependency installation failed. Existing nodes were preserved; see the setup log.')
    async def install(self,ids):
        try:
            async with self.studio.connection.lock:
                await self.ensure_idle();root,python=engine_paths();folder=root/'custom_nodes';folder.mkdir(exist_ok=True)
                logs=DATA_ROOT/'.runtime';logs.mkdir(exist_ok=True,parents=True)
                with (logs/'node-setup.log').open('ab') as log:
                    # Protect the engine's current numerical stack while pip resolves node requirements.
                    freeze="import importlib.metadata as m; print('\\n'.join(d.metadata['Name']+'=='+d.version for d in m.distributions() if d.metadata['Name'].lower() in ('torch','torchvision','torchaudio','numpy')))"
                    for pack in PACKS:
                        if pack['id'] not in ids or installed_directory(root,pack):continue
                        self.job={'status':'installing','message':'Installing '+pack['folder'],'pack':pack['id']}
                        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=120)) as session:
                            async with session.get(pack['url']) as response:
                                response.raise_for_status();data=await response.content.readexactly(pack['size'])
                                if await response.content.read(1):raise ValueError('Node download exceeds the pinned size.')
                        if hashlib.sha256(data).hexdigest()!=pack['sha256']:raise ValueError('Node archive checksum does not match. Nothing was installed.')
                        with tempfile.TemporaryDirectory(prefix='.directorscut-',dir=folder) as stage:
                            stage=Path(stage);payload=stage/'pack';payload.mkdir();unpack(data,payload)
                            requirements=payload/'requirements.txt'
                            if requirements.is_file():
                                process=await asyncio.create_subprocess_exec(str(python),'-I','-c',freeze,stdout=asyncio.subprocess.PIPE,stderr=log,**({'creationflags':0x08000000} if os.name=='nt' else {}))
                                output,_=await asyncio.wait_for(process.communicate(),30)
                                if process.returncode:raise ValueError('Could not inspect the ComfyUI Python environment.')
                                constraints=stage/'constraints.txt';constraints.write_bytes(output)
                                await self.command([python,'-I','-m','pip','install','--disable-pip-version-check','-c',constraints,'-r',requirements],payload,log)
                            target=folder/pack['folder']
                            if target.exists():raise ValueError('Node folder already exists; it was not overwritten.')
                            payload.rename(target)
                self.job={'status':'complete','message':'Nodes ready on disk. Restart ComfyUI to load newly installed nodes. Existing node packs were left unchanged.'}
        except Exception as exc:self.job={'status':'failed','message':str(exc)}

async def describe(request):
    studio=request.app['studio']
    try:nodes=await studio.nodes()
    except (aiohttp.ClientError,asyncio.TimeoutError):nodes={}
    return web.json_response(studio.node_setup.describe(nodes))

async def save(request):
    data=await request.json();automatic=data.get('automatic');optional=data.get('optional',[])
    if not isinstance(automatic,bool) or not isinstance(optional,list) or any(not isinstance(x,str) or x not in ('gguf','vsa','selflift') for x in optional):raise ValueError('Invalid automatic node setup settings.')
    write_json(PREFS,{'automatic':automatic,'optional':list(dict.fromkeys(optional))});return web.json_response(preferences())

async def install(request):
    return web.json_response(await request.app['studio'].node_setup.start((await request.json()).get('packs',[])),status=202)
