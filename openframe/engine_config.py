"""Portable/Desktop/manual ComfyUI connection discovery; no driver or GPU installation."""
import asyncio,ipaddress,json,os,platform,re,socket,sys
from pathlib import Path
from urllib.parse import urlsplit,urlunsplit
import aiohttp
from .storage import write_json
from .paths import DATA_ROOT
ROOT=DATA_ROOT
CONFIG=ROOT/'.runtime/engine.json'
def load():
 try:return json.loads(CONFIG.read_text(encoding='utf-8'))
 except (OSError,ValueError):return {}
def url(value):
 value=str(value).strip().rstrip('/');parts=urlsplit(value)
 try:port=parts.port
 except ValueError:raise ValueError('Invalid engine port.')
 if parts.scheme not in ('http','https') or not parts.hostname or parts.username or parts.password or parts.query or parts.fragment:raise ValueError('Use an http(s) ComfyUI address without credentials, query or fragment.')
 return urlunsplit((parts.scheme,parts.netloc,parts.path.rstrip('/'),'',''))
def local(value):
 host=urlsplit(value).hostname
 if host=='localhost':return True
 try:return ipaddress.ip_address(host).is_loopback
 except ValueError:return False
def normalize_root(value):
 path=Path(os.path.expandvars(str(value))).expanduser().resolve()
 if path.is_file():raise ValueError('Choose the ComfyUI data folder, not the Desktop executable.')
 if path.name.lower()=='models' and path.is_dir():path=path.parent
 for candidate in [path,path/'ComfyUI',path/'comfyui']:
  if (candidate/'models').is_dir():return candidate
 raise ValueError('This folder has no models directory. Choose ComfyUI or its Portable parent folder.')
def desktop_dirs(home=None,system=None,environ=None):
 home=Path(home or Path.home());system=system or platform.system();env=environ if environ is not None else os.environ
 base=Path(env.get('APPDATA',home/'AppData/Roaming')) if system=='Windows' else home/'Library/Application Support' if system=='Darwin' else Path(env.get('XDG_CONFIG_HOME',home/'.config'))
 return [base/name for name in ('ComfyUI','comfy-ui-desktop','Comfy Desktop','comfyui-desktop-2')]
def records(data):
 if isinstance(data,list):
  for x in data:yield from records(x)
 elif isinstance(data,dict):
  if any(k in data for k in ('basePath','installPath')):yield data
  for key,value in data.items():
   if isinstance(value,(list,dict)):yield from records(value)
def discover_paths(home=None,system=None,environ=None):
 home=Path(home or Path.home());system=system or platform.system();env=environ if environ is not None else os.environ;result=[];seen=set()
 def add(path,kind,label='',models=''):
  try:root=normalize_root(path)
  except (OSError,ValueError):return
  if str(root) in seen:return
  seen.add(str(root));result.append({'root':str(root),'kind':kind,'name':label or root.name,'models_dir':str(Path(models).expanduser().resolve()) if models and Path(models).expanduser().is_dir() else str(root/'models')})
 if env.get('OPENFRAME_COMFY_ROOT'):add(env['OPENFRAME_COMFY_ROOT'],'configured')
 for folder in desktop_dirs(home,system,env):
  for filename in ('config.json','installations.json'):
   try:
    p=folder/filename
    if p.stat().st_size>2*1024**2:continue
    data=json.loads(p.read_text(encoding='utf-8'))
    for row in records(data):
     if row.get('sourceId')=='cloud':continue
     add(row.get('basePath') or row.get('installPath'),'desktop',row.get('name','Comfy Desktop'),row.get('modelDirsPrimary',''))
   except (OSError,ValueError,TypeError):pass
 for path in [ROOT/'ComfyUI',ROOT.parent/'ComfyUI',Path(sys.executable).parent/'ComfyUI',Path(sys.executable).parent,home/'ComfyUI',home/'Documents/ComfyUI',home/'comfy/ComfyUI']:
  add(path,'manual')
 for parent in [home/'ComfyUI-Installs',home/'Documents/ComfyUI-Installs']:
  if parent.is_dir():
   for path in list(parent.iterdir())[:30]:add(path,'desktop')
 if system=='Windows':
  for parent in [Path('C:/ComfyUI_windows_portable'),home/'ComfyUI_windows_portable',home/'Downloads/ComfyUI_windows_portable']:
   add(parent,'portable')
 return result

def current():
 saved=load();root=os.environ.get('OPENFRAME_COMFY_ROOT',saved.get('comfy_root',''))
 found=[]
 if not root:
  found=discover_paths();root=found[0]['root'] if found else ''
 return {'comfy_url':os.environ.get('OPENFRAME_COMFY_URL',saved.get('comfy_url','http://127.0.0.1:8188')).rstrip('/'),
         'proxy_url':os.environ.get('COMFY_BASE_URL',saved.get('proxy_url','http://127.0.0.1:8189')).rstrip('/'),
         'comfy_root':root,'models_dir':os.environ.get('OPENFRAME_MODELS_DIR',saved.get('models_dir','')) or (found[0]['models_dir'] if found else str(Path(root)/'models') if root else ''),
         'shared_filesystem':bool(saved.get('shared_filesystem',False)),'proxy_managed':bool(saved.get('proxy_managed',False))}
def apply_environment(settings):
 for key,env in [('comfy_url','OPENFRAME_COMFY_URL'),('proxy_url','COMFY_BASE_URL'),('comfy_root','OPENFRAME_COMFY_ROOT'),('models_dir','OPENFRAME_MODELS_DIR')]:
  if settings.get(key):os.environ[env]=settings[key]
  else:os.environ.pop(env,None)
def downloads_directory(settings=None):
 settings=settings or current()
 if not local(settings['comfy_url']) and not settings.get('shared_filesystem'):raise ValueError('Remote engine: configure a mounted shared models folder before downloading. Downloads run on the app server, not in your browser.')
 path=Path(settings['models_dir']).expanduser().resolve() if settings.get('models_dir') else None
 if path is None or not path.is_dir():raise ValueError('Choose an existing ComfyUI models folder in Connection settings.')
 return path

def validate(data):
 cfg=current();cfg['comfy_url']=url(data.get('comfy_url',cfg['comfy_url']));cfg['shared_filesystem']=data.get('shared_filesystem',False) is True
 value=str(data.get('comfy_root','')).strip();cfg['comfy_root']=str(normalize_root(value)) if value else ''
 custom=str(data.get('models_dir','')).strip();cfg['models_dir']=str(Path(custom).expanduser().resolve()) if custom else (str(Path(cfg['comfy_root'])/'models') if cfg['comfy_root'] else '')
 if cfg['models_dir'] and not Path(cfg['models_dir']).is_dir():raise ValueError('The models folder does not exist on the app server.')
 if data.get('proxy_mode','managed')=='external':cfg['proxy_url']=url(data.get('proxy_url',''));cfg['proxy_managed']=False
 else:cfg['proxy_managed']=True
 return cfg
async def probe(base):
 try:
  async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=4)) as session:
   async with session.get(url(base)+'/system_stats') as r:r.raise_for_status();stats=await r.json()
  if not isinstance(stats,dict) or 'system' not in stats or 'devices' not in stats:raise ValueError('The address did not return ComfyUI system stats.')
  return {'online':True,'hardware':hardware(stats),'system':stats.get('system',{})}
 except (aiohttp.ClientError,asyncio.TimeoutError,ValueError) as exc:return {'online':False,'error':str(exc)}
def hardware(stats):
 result=[]
 for device in stats.get('devices',[]):
  kind=str(device.get('type','')).lower();name=device.get('name','');lower=name.lower()
  backend='rocm' if any(x in lower for x in ('amd','radeon')) and kind=='cuda' else 'mps' if kind=='mps' or 'apple' in lower else 'xpu' if kind=='xpu' else 'directml' if kind in ('privateuseone','dml','directml') else kind
  result.append({**device,'backend':backend})
 accelerators=[d for d in result if d.get('backend') not in ('cpu','')]
 memory=max((d.get('vram_total',0) or 0 for d in accelerators),default=0)
 if not memory and any(d['backend']=='mps' for d in accelerators):memory=stats.get('system',{}).get('ram_total',0)
 return {'os':stats.get('system',{}).get('os','unknown'),'devices':result,'memory_total':memory,'accelerated':bool(accelerators),'note':'Hardware is reported by ComfyUI. Quantized kernels and custom nodes must support this backend; detection is not a generation benchmark.'}
def process_hints():
 paths=[];ports=set()
 try:
  import psutil
  pids=set()
  for process in psutil.process_iter(['name','cmdline','cwd']):
   try:
    args=process.info['cmdline'] or [];name=(process.info['name'] or '').lower()
    if not any('main.py' in x for x in args) or not any(x in name for x in ('python','comfy')):continue
    pids.add(process.pid)
    for arg in args:
     if arg.endswith('main.py'):
      p=Path(arg);p=p if p.is_absolute() else Path(process.info['cwd'] or '.')/p
      try:paths.append(str(normalize_root(p.parent)))
      except ValueError:pass
    for i,arg in enumerate(args):
     if arg=='--port' and i+1<len(args) and args[i+1].isdigit():ports.add(int(args[i+1]))
     if arg.startswith('--port=') and arg[7:].isdigit():ports.add(int(arg[7:]))
   except (psutil.Error,OSError):pass
  try:
   for conn in psutil.net_connections(kind='tcp'):
    if conn.pid in pids and conn.status=='LISTEN':ports.add(conn.laddr.port)
  except psutil.Error:pass
 except ImportError:pass
 return paths,ports
async def discover():
 cfg=current();paths=await asyncio.to_thread(discover_paths);process_paths,ports=await asyncio.to_thread(process_hints)
 for p in process_paths:
  if not any(row['root']==p for row in paths):paths.append({'root':p,'models_dir':str(Path(p)/'models'),'kind':'running','name':'Running ComfyUI'})
 bases=list(dict.fromkeys([cfg['comfy_url'],*[f'http://127.0.0.1:{p}' for p in sorted({8188,8000,*ports}) if 0<p<65536]]))[:24]
 results=await asyncio.gather(*(probe(base) for base in bases))
 return {'settings':cfg,'installations':paths,'servers':[{'url':base,**result} for base,result in zip(bases,results) if result['online']],'host_os':platform.system()}
