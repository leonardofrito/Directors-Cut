"""Engine connection endpoints and an app-owned loopback Comfy API proxy."""
import asyncio,hashlib,logging,os,socket,sys,time
from pathlib import Path
from aiohttp import web,ClientSession,ClientTimeout,ClientError
from . import engine_config as cfg
from .storage import write_json
class Connection:
 def __init__(self):self.process=None;self.log=None;self.lock=asyncio.Lock()
 async def close(self):
  if self.process and self.process.returncode is None:
   self.process.terminate()
   try:await asyncio.wait_for(self.process.wait(),8)
   except asyncio.TimeoutError:self.process.kill();await self.process.wait()
  self.process=None
  if self.log:self.log.close();self.log=None
 async def proxy_ready(self,base):
  try:
   async with ClientSession(timeout=ClientTimeout(total=2)) as s:
    async with s.get(base+'/api/v2/jobs?limit=1') as r:
     data=await r.json();return r.status==200 and isinstance(data,(dict,list))
  except (ClientError,asyncio.TimeoutError,ValueError):return False
 async def start_proxy(self,settings):
  with socket.socket() as listener:listener.bind(('127.0.0.1',0));port=listener.getsockname()[1]
  folder=cfg.ROOT/'.runtime/proxy-connections'/hashlib.sha256(settings['comfy_url'].encode()).hexdigest()[:12];folder.mkdir(parents=True,exist_ok=True)
  log=(folder/'proxy.log').open('ab')
  args=[sys.executable,'-c','from comfy_api_proxy.cli import main; raise SystemExit(main())','run','--host','127.0.0.1','--port',str(port),'--comfyui',settings['comfy_url'],'--state-dir',str(folder)]
  if getattr(sys,'frozen',False):args=[sys.executable,'--internal-proxy',*args[3:]]
  options={'creationflags':0x08000000} if os.name=='nt' else {}
  process=await asyncio.create_subprocess_exec(*args,stdout=log,stderr=log,**options)
  base=f'http://127.0.0.1:{port}'
  for _ in range(60):
   if process.returncode is not None:break
   if await self.proxy_ready(base):return process,log,base
   await asyncio.sleep(.15)
  if process.returncode is None:process.terminate();await process.wait()
  log.close();raise ValueError('Could not start the Comfy SDK proxy. See '+str(folder/'proxy.log'))
 async def startup(self):
  settings=cfg.current();cfg.apply_environment(settings)
  if settings['proxy_managed'] or (cfg.local(settings['proxy_url']) and not await self.proxy_ready(settings['proxy_url'])):
   if (await cfg.probe(settings['comfy_url']))['online']:
    try:
     self.process,self.log,base=await self.start_proxy(settings);settings.update(proxy_url=base,proxy_managed=True);cfg.apply_environment(settings);write_json(cfg.CONFIG,settings)
    except (ValueError,OSError):
     # Keep Settings available so the user can repair an offline/misconfigured proxy.
     logging.getLogger(__name__).exception('SDK proxy startup failed; connection settings remain available.')

async def describe(request):
 settings=cfg.current();result=await cfg.probe(settings['comfy_url'])
 try:models=str(cfg.downloads_directory(settings));download_error=''
 except ValueError as exc:models='';download_error=str(exc)
 return web.json_response({'settings':settings,**result,'downloads_allowed':bool(models),'download_error':download_error,'host_os':os.name})
async def discover(request):return web.json_response(await cfg.discover())
async def probe(request):
 data=await request.json();return web.json_response(await cfg.probe(cfg.url(data.get('comfy_url',''))))
async def save_folders(request):
 studio=request.app['studio'];data=await request.json()
 if getattr(studio,'node_setup',None) and studio.node_setup.running:raise ValueError('Wait until node installation finishes before changing folders.')
 async with studio.connection.lock:
  if studio.queue_items() or studio.queue.qsize():raise ValueError('Wait until the generation queue is idle before changing folders.')
  if any(j['status'] in ('queued','downloading','verifying') for j in studio.model_downloads.snapshot()):raise ValueError('Pause model downloads before changing their destination.')
  settings=cfg.validate_folders(data)
  # A failed remote connection must not enable unconfirmed local downloads.
  if settings['models_dir']:
   cfg.downloads_directory({**settings,'comfy_url':cfg.url(data.get('comfy_url',settings['comfy_url']))})
  write_json(cfg.CONFIG,settings);cfg.apply_environment(settings)
  return web.json_response({'settings':settings,'folders_saved':True})
async def save(request):
 studio=request.app['studio'];data=await request.json();settings=cfg.validate(data)
 if getattr(studio,'node_setup',None) and studio.node_setup.running:raise ValueError('Wait until node installation finishes before changing the engine.')
 async with studio.connection.lock:
  studio.connection_changing=True;new_process=None;new_log=None
  try:
   if studio.queue_items() or studio.queue.qsize():raise ValueError('Wait until the generation queue is idle before changing the engine.')
   if any(j['status'] in ('queued','downloading','verifying') for j in studio.model_downloads.snapshot()):raise ValueError('Pause model downloads before changing their destination.')
   old=cfg.current()
   try:
    async with ClientSession(timeout=ClientTimeout(total=3)) as session:
     async with session.get(old['comfy_url']+'/queue') as response:
      if response.status==200:
       q=await response.json()
       if q.get('queue_running') or q.get('queue_pending'):raise ValueError('ComfyUI is generating. Wait before changing its connection.')
   except (ClientError,asyncio.TimeoutError):pass
   check=await cfg.probe(settings['comfy_url'])
   if not check['online']:raise ValueError('Could not connect to ComfyUI: '+check.get('error',''))
   reuse=settings['comfy_url']==old['comfy_url'] and await studio.connection.proxy_ready(old['proxy_url'])
   if data.get('proxy_mode','managed')=='external':
    if not await studio.connection.proxy_ready(settings['proxy_url']):raise ValueError('The SDK proxy address is not a Comfy SDK v2 endpoint. A normal ComfyUI address belongs in ComfyUI address. Turn off "Use an existing SDK proxy" so Director\'s Cut starts its official local proxy.')
   elif reuse:settings.update(proxy_url=old['proxy_url'],proxy_managed=old['proxy_managed'])
   else:new_process,new_log,base=await studio.connection.start_proxy(settings);settings.update(proxy_url=base,proxy_managed=True)
   from .provider import ComfyProvider
   provider=None;cfg.apply_environment(settings)
   try:
    provider=ComfyProvider();write_json(cfg.CONFIG,settings)
   except BaseException:
    cfg.apply_environment(old)
    if provider:await provider.close()
    raise
   previous=studio.provider;studio.provider=provider
   await previous.close()
   if new_process or not (reuse and settings['proxy_url']==old['proxy_url']):
    await studio.connection.close();studio.connection.process=new_process;studio.connection.log=new_log
   return web.json_response({'settings':settings,**check})
  except BaseException:
   if new_process and new_process.returncode is None:new_process.terminate();await new_process.wait()
   if new_log:new_log.close()
   raise
  finally:studio.connection_changing=False
