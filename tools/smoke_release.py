"""Exercise a real native bundle with a fake ComfyUI: no GPU or model downloads."""
import argparse,asyncio,json,os,platform,socket,sys,tempfile,zipfile
from pathlib import Path
import aiohttp
from aiohttp import web
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from openframe.version import VERSION

def free_port():
 with socket.socket() as s:s.bind(('127.0.0.1',0));return s.getsockname()[1]

async def main():
 parser=argparse.ArgumentParser();parser.add_argument('--source',action='store_true');parser.add_argument('--artifacts',type=Path);args=parser.parse_args()
 output=args.artifacts.resolve() if args.artifacts else ROOT/'release'/VERSION;output.mkdir(parents=True,exist_ok=True)
 if args.source:command=[sys.executable,str(ROOT/'app_entry.py')]
 else:
  files=list(output.glob('*.exe')) if platform.system()=='Windows' else list(output.glob('*.app/Contents/MacOS/*')) if platform.system()=='Darwin' else [p for p in output.glob('DirectorsCut-*-linux-*') if p.is_file()]
  if len(files)!=1:raise RuntimeError('Expected one native artifact, got '+str(files))
  command=[str(files[0])]
 with tempfile.TemporaryDirectory(prefix='directors-cut-package-') as tmp:
  data=Path(tmp).resolve()/'persistent';data.mkdir();models=Path(tmp).resolve()/'ComfyUI/models';models.mkdir(parents=True)
  async def stats(_):return web.json_response({'system':{'os':'package-test','ram_total':8*1024**3},'devices':[{'name':'CPU packaging fixture','type':'cpu','vram_total':0}]})
  async def empty_nodes(_):return web.json_response({})
  async def queue(_):return web.json_response({'queue_running':[],'queue_pending':[]})
  async def websocket(request):
   ws=web.WebSocketResponse();await ws.prepare(request)
   async for _ in ws:pass
   return ws
  fake=web.Application();fake.router.add_get('/system_stats',stats);fake.router.add_get('/object_info',empty_nodes);fake.router.add_get('/queue',queue);fake.router.add_get('/ws',websocket)
  runner=web.AppRunner(fake);await runner.setup();engine_port=free_port();await web.TCPSite(runner,'127.0.0.1',engine_port).start()
  port=free_port();base=f'http://127.0.0.1:{port}'
  environment={k:v for k,v in os.environ.items() if not k.startswith(('OPENFRAME_','COMFY_'))}
  environment.update(OPENFRAME_COMFY_URL=f'http://127.0.0.1:{engine_port}',OPENFRAME_COMFY_ROOT=str(models.parent),OPENFRAME_MODELS_DIR=str(models),COMFY_BASE_URL='http://127.0.0.1:1')
  log_dir=ROOT/'.runtime/release-smoke';log_dir.mkdir(parents=True,exist_ok=True)
  log=(log_dir/'smoke-run.log').open('wb');process=None
  async def launch(client):
   process=await asyncio.create_subprocess_exec(*command,'--no-browser','--port',str(port),'--data',str(data),env=environment,stdout=log,stderr=log,**({'creationflags':0x08000000} if os.name=='nt' else {}))
   for _ in range(160):
    if process.returncode is not None:raise RuntimeError('Native app exited: '+str(process.returncode))
    try:
     async with client.get(base+'/api/app') as response:
      info=await response.json()
      if info.get('application')=="Director's Cut":return process,info
    except (aiohttp.ClientError,asyncio.TimeoutError):pass
    await asyncio.sleep(.25)
   process.terminate();await process.wait();raise RuntimeError('Native app startup timed out')
  try:
   async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=6)) as client:
    process,info=await launch(client)
    assert Path(info['data_dir'])==data and info['can_quit']
    async with client.get(base+'/') as r:assert r.status==200 and 'Director' in await r.text()
    async with client.get(base+'/api/engine') as r:engine=await r.json();assert engine['online']
    async with client.get(engine['settings']['proxy_url']+'/api/v2/jobs?limit=1') as r:assert r.status==200
    for path in ['/api/config','/api/models/catalog','/assets/previews/index.json','/api/app/legal/app']:
     async with client.get(base+path) as r:assert r.status==200,(path,r.status)
    async with client.post(base+'/api/projects',json={'name':'Package persistence check'}) as r:project=await r.json();assert r.status==200
    async with client.post(base+'/api/app/quit',json={}) as r:assert r.status==200
    await asyncio.wait_for(process.wait(),20);assert process.returncode==0
    process,_=await launch(client)
    async with client.get(base+'/api/projects') as r:projects=await r.json();assert any(p['id']==project['id'] for p in projects)
    async with client.post(base+'/api/app/quit',json={}) as r:assert r.status==200
    await asyncio.wait_for(process.wait(),20);assert process.returncode==0
   self_report=output/'native-self-test.json'
   process=await asyncio.create_subprocess_exec(*command,'--self-test','--data',str(data),'--report',str(self_report),env=environment,stdout=log,stderr=log,**({'creationflags':0x08000000} if os.name=='nt' else {}))
   await asyncio.wait_for(process.wait(),50);assert process.returncode==0;self_data=json.loads(self_report.read_text(encoding='utf-8'));assert self_data['ok']
   source=output/f'DirectorsCut-{VERSION}-source.zip'
   if source.exists():
    with zipfile.ZipFile(source) as z:
     forbidden={'projects','.runtime','.venv','Preset Catalog - Black Studio','commercial'}
     assert not any(forbidden.intersection(Path(name).parts) for name in z.namelist())
     assert not any(Path(name).suffix in ('.safetensors','.gguf','.mp4') for name in z.namelist())
   self_data['data_dir']='isolated test data';self_report.write_text(json.dumps(self_data,indent=2),encoding='utf-8')
   result={'ok':True,'source_mode':args.source,'platform':platform.platform(),'version':VERSION,'managed_proxy':True,'persistent_projects':True,'web_resources':True,'verified_catalog':True,'self_test':self_data,'gpu_generation':False,'model_download':False}
   (output/'smoke-report.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result))
   from tools import build_release
   build_release.OUTPUT=output;build_release.checksums()
  finally:
   if process and process.returncode is None:process.terminate();await process.wait()
   log.close();await runner.cleanup()
   if sys.exc_info()[0] is not None:
    print((log_dir/'smoke-run.log').read_text(encoding='utf-8',errors='replace')[-12000:],file=sys.stderr)
    for diagnostic in (data/'.runtime').glob('*.log'):
     print(diagnostic.name+'\n'+diagnostic.read_text(encoding='utf-8',errors='replace')[-6000:],file=sys.stderr)
if __name__=='__main__':asyncio.run(main())
