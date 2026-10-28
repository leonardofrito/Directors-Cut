"""CPU-only connection, platform discovery and real tiny HTTP-download checks."""
import asyncio,hashlib,json,os,sys,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock,patch
import aiohttp
from aiohttp import web
from aiohttp.test_utils import TestClient,TestServer
from openframe import engine_config as cfg,engine_connection as ec,model_downloads as md

class EngineTests(unittest.IsolatedAsyncioTestCase):
 async def asyncSetUp(self):
  self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name).resolve();self.models=self.root/'ComfyUI/models';self.models.mkdir(parents=True)
  self.environment=patch.dict(os.environ,{k:v for k,v in os.environ.items() if k not in ('OPENFRAME_COMFY_ROOT','OPENFRAME_MODELS_DIR','OPENFRAME_COMFY_URL','COMFY_BASE_URL')},clear=True);self.environment.start()
  self.config=patch.object(cfg,'CONFIG',self.root/'engine.json');self.config.start()
 async def asyncTearDown(self):self.config.stop();self.environment.stop();self.temp.cleanup()

 async def test_first_run_uses_managed_proxy_but_preserves_explicit_external(self):
  with patch.object(cfg,'discover_paths',return_value=[]):
   self.assertTrue(cfg.current()['proxy_managed'])
   cfg.CONFIG.write_text(json.dumps({'proxy_managed':False,'proxy_url':'http://localhost:9191'}))
   self.assertFalse(cfg.current()['proxy_managed'])

 async def test_quoted_portable_path_with_spaces_is_normalized(self):
  portable=self.root/'Real Documents'/'Portable'
  models=portable/'ComfyUI/models';models.mkdir(parents=True)
  data=cfg.validate_folders({'comfy_root':'"'+str(portable)+'"','models_dir':'"'+str(models)+'"'})
  self.assertEqual(Path(data['models_dir']),models)
  self.assertEqual(Path(data['comfy_root']),models.parent)

 async def test_folder_save_survives_bad_external_proxy_without_engine_access(self):
  connection=ec.Connection();connection.proxy_ready=AsyncMock(return_value=False)
  studio=SimpleNamespace(connection=connection,connection_changing=False,queue_items=lambda:[],queue=asyncio.Queue(),model_downloads=SimpleNamespace(snapshot=lambda:[]))
  app=web.Application();app['studio']=studio;app.router.add_put('/engine/folders',ec.save_folders)
  cfg.apply_environment({'comfy_url':'http://127.0.0.1:1'})
  settings={'comfy_url':'http://127.0.0.1:1','comfy_root':str(self.models.parent),'models_dir':str(self.models),'proxy_mode':'external','proxy_url':'http://127.0.0.1:1'}
  async with TestClient(TestServer(app)) as client:
   response=await client.put('/engine/folders',json=settings)
   self.assertEqual(response.status,200)
   self.assertEqual(cfg.downloads_directory(),self.models)
   request=SimpleNamespace(app={'studio':studio},json=AsyncMock(return_value=settings))
   with patch.object(cfg,'probe',new=AsyncMock(return_value={'online':True})),self.assertRaisesRegex(ValueError,'Turn off'):
    await ec.save(request)
  self.assertEqual(Path(cfg.load()['models_dir']),self.models)
  # Simulate relaunch: the saved path does not depend on this process environment.
  for key in ('OPENFRAME_MODELS_DIR','OPENFRAME_COMFY_ROOT'):os.environ.pop(key,None)
  self.assertEqual(cfg.downloads_directory(),self.models)
  connection.proxy_ready.assert_any_await(settings['proxy_url'])

 async def test_folder_only_save_preserves_remote_and_active_download_guards(self):
  studio=SimpleNamespace(connection=ec.Connection(),queue_items=lambda:[],queue=asyncio.Queue(),model_downloads=SimpleNamespace(snapshot=lambda:[]))
  data={'comfy_url':'http://192.168.1.2:8188','models_dir':str(self.models)}
  request=SimpleNamespace(app={'studio':studio},json=AsyncMock(return_value=data))
  with self.assertRaisesRegex(ValueError,'shared models folder'):await ec.save_folders(request)
  self.assertEqual(cfg.load(),{})
  studio.model_downloads.snapshot=lambda:[{'status':'downloading'}]
  with self.assertRaisesRegex(ValueError,'Pause model downloads'):await ec.save_folders(request)

 async def test_portable_manual_and_desktop_on_three_platforms(self):
  for system in ('Windows','Darwin','Linux'):
   with self.subTest(system=system):
    home=self.root/system;home.mkdir();env={'APPDATA':str(home/'roaming'),'XDG_CONFIG_HOME':str(home/'config')}
    data=home/'installed/ComfyUI';(data/'models').mkdir(parents=True);shared=home/'shared models';shared.mkdir()
    folder=cfg.desktop_dirs(home,system,env)[2];folder.mkdir(parents=True)
    (folder/'installations.json').write_text(json.dumps({'installations':[{'installPath':str(data.parent),'name':'Test Desktop','modelDirsPrimary':str(shared),'sourceId':'local'}]}))
    legacy=cfg.desktop_dirs(home,system,env)[0];legacy.mkdir(parents=True)
    old=home/'legacy';(old/'models').mkdir(parents=True);(legacy/'config.json').write_text(json.dumps({'basePath':str(old)}))
    found=cfg.discover_paths(home,system,env)
    self.assertTrue(any(Path(p['root'])==data.resolve() and Path(p['models_dir'])==shared.resolve() for p in found))
    self.assertTrue(any(Path(p['root'])==old.resolve() for p in found))
  self.assertEqual(cfg.normalize_root(self.root),self.models.parent)
  self.assertEqual(cfg.normalize_root(self.models),self.models.parent)

 async def test_paths_validate_without_executing_or_creating(self):
  data=cfg.validate({'comfy_url':'http://localhost:9000','comfy_root':str(self.root),'models_dir':str(self.models)})
  self.assertEqual(data['comfy_root'],str(self.models.parent));self.assertTrue(data['proxy_managed'])
  exe=self.root/'ComfyUI.exe';exe.write_bytes(b'')
  with self.assertRaises(ValueError):cfg.normalize_root(exe)
  with self.assertRaises(ValueError):cfg.validate({'models_dir':str(self.root/'missing')})
  self.assertFalse((self.root/'missing').exists())

 async def test_custom_urls_and_remote_download_guard(self):
  self.assertEqual(cfg.url('https://example.org:9443/comfy/'),'https://example.org:9443/comfy')
  for url in ('file:///tmp/x','http://user:pass@localhost:80','http://localhost:bad','http://localhost/?token=x'):
   with self.assertRaises(ValueError):cfg.url(url)
  settings={'comfy_url':'http://192.168.1.2:9000','models_dir':str(self.models),'shared_filesystem':False}
  with self.assertRaises(ValueError):cfg.downloads_directory(settings)
  settings['shared_filesystem']=True;self.assertEqual(cfg.downloads_directory(settings),self.models)
  settings.update(comfy_url='http://[::1]:9000',shared_filesystem=False);self.assertEqual(cfg.downloads_directory(settings),self.models)

 async def test_backend_memory_is_not_cuda_only(self):
  for kind,name,backend in [('cuda','NVIDIA RTX','cuda'),('cuda','AMD Radeon','rocm'),('xpu','Intel Arc','xpu'),('privateuseone','AMD','directml'),('mps','Apple M4','mps')]:
   with self.subTest(kind=kind,name=name):
    result=cfg.hardware({'system':{'ram_total':64},'devices':[{'type':kind,'name':name,'vram_total':0 if kind=='mps' else 12}]})
    self.assertEqual(result['devices'][0]['backend'],backend);self.assertEqual(result['memory_total'],64 if kind=='mps' else 12)
  self.assertFalse(cfg.hardware({'devices':[{'type':'cpu','name':'CPU','vram_total':64}]})['accelerated'])

 async def test_discovery_uses_detected_custom_port(self):
  seen=[]
  async def probe(base):seen.append(base);return {'online':base.endswith(':9234')}
  with patch.object(cfg,'discover_paths',return_value=[]),patch.object(cfg,'process_hints',return_value=([],{9234})),patch.object(cfg,'probe',side_effect=probe):
   result=await cfg.discover()
  self.assertEqual([s['url'] for s in result['servers']],['http://127.0.0.1:9234']);self.assertIn('http://127.0.0.1:9234',seen)

 async def test_proxy_launch_targets_engine_without_touching_existing_process(self):
  process=SimpleNamespace(returncode=None,terminate=lambda:None,wait=AsyncMock(),kill=lambda:None)
  connection=ec.Connection()
  with patch.object(cfg,'ROOT',self.root),patch.object(ec.asyncio,'create_subprocess_exec',new=AsyncMock(return_value=process)) as spawn,patch.object(connection,'proxy_ready',new=AsyncMock(return_value=True)):
   connection.process,connection.log,base=await connection.start_proxy({'comfy_url':'http://localhost:9234'})
   args=spawn.call_args.args;self.assertIn('http://localhost:9234',args);self.assertIn('127.0.0.1',args);self.assertEqual(args[0],sys.executable)
   self.assertEqual(spawn.call_args.kwargs.get('creationflags'),0x08000000 if os.name=='nt' else None)
   self.assertTrue(base.startswith('http://127.0.0.1:'))
  await connection.close()

 async def test_http_probe_and_save_reuses_external_proxy_and_blocks_busy_queue(self):
  engine=web.Application();engine.router.add_get('/system_stats',lambda _:web.json_response({'system':{'os':'test'},'devices':[]}));engine.router.add_get('/queue',lambda _:web.json_response({'queue_running':[],'queue_pending':[]}))
  async with TestServer(engine) as source:
   address=str(source.make_url('')).rstrip('/');settings={'comfy_url':address,'proxy_url':address,'comfy_root':str(self.models.parent),'models_dir':str(self.models),'proxy_managed':False,'shared_filesystem':False};cfg.apply_environment(settings)
   self.assertTrue((await cfg.probe(address))['online'])
   connection=ec.Connection();connection.proxy_ready=AsyncMock(return_value=True)
   studio=SimpleNamespace(connection=connection,connection_changing=False,queue_items=lambda:[],queue=asyncio.Queue(),model_downloads=SimpleNamespace(snapshot=lambda:[]),provider=SimpleNamespace(close=AsyncMock()))
   app=web.Application();app['studio']=studio;app.router.add_put('/engine',ec.save)
   new=SimpleNamespace(close=AsyncMock())
   async with TestClient(TestServer(app)) as client, self.provider_patch(new):
    response=await client.put('/engine',json={**settings,'proxy_mode':'external'});self.assertEqual(response.status,200);self.assertIs(studio.provider,new);self.assertFalse(studio.connection_changing)
    studio.queue_items=lambda:[{'id':'busy'}]
    # Test direct busy handling without the production ValueError middleware.
    request=SimpleNamespace(app={'studio':studio},json=AsyncMock(return_value=settings))
    with self.assertRaisesRegex(ValueError,'queue is idle'):await ec.save(request)
    self.assertFalse(studio.connection_changing)
  self.assertEqual(cfg.load()['comfy_url'],address)

 class provider_patch:
  def __init__(self,value):self.patch=patch('openframe.provider.ComfyProvider',return_value=value)
  async def __aenter__(self):self.patch.start()
  async def __aexit__(self,*_):self.patch.stop()

 async def test_real_http_resume_hash_and_install_to_selected_models_folder(self):
  payload=b'tiny model\n'*20;seen=[]
  async def download(request):
   seen.append(request.headers.get('Range'));offset=int(request.headers.get('Range','bytes=0-').split('=')[1].split('-')[0]);return web.Response(body=payload[offset:],status=206,headers={'Content-Range':f'bytes {offset}-{len(payload)-1}/{len(payload)}'})
  app=web.Application();app.router.add_get('/tiny',download)
  row={'id':'test-live','filename':'tiny.safetensors','folder':'diffusion_models','repo':'Comfy-Org/test','path':'tiny','size':len(payload),'sha256':hashlib.sha256(payload).hexdigest()}
  cfg.apply_environment({'comfy_url':'http://127.0.0.1:8188','models_dir':str(self.models)})
  manager=md.ModelDownloads();real_session=aiohttp.ClientSession
  async with TestServer(app) as source:
   class Session:
    def __init__(self,**kw):self.session=real_session(**kw)
    async def __aenter__(self):await self.session.__aenter__();return self
    async def __aexit__(self,*args):return await self.session.__aexit__(*args)
    def get(self,url,headers):return self.session.get(source.make_url('/tiny'),headers=headers)
   target=md.destination(row);target.parent.mkdir();partial=target.with_name('.'+target.name+'.download.part');partial.write_bytes(payload[:7])
   with patch.dict(md.BY_ID,{row['id']:row}),patch.object(md.aiohttp,'ClientSession',Session):
    await manager.start(row['id']);await manager.tasks[row['id']]
   self.assertEqual(manager.jobs[row['id']]['status'],'installed');self.assertEqual(target.read_bytes(),payload);self.assertEqual(seen,['bytes=7-']);self.assertFalse(partial.exists())
  await manager.close()
