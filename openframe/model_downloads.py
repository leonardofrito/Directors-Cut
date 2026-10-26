"""User-triggered, resumable model downloads from a pinned allowlist. No inference."""
import asyncio,hashlib,json,os,re,shutil,time
from pathlib import Path
from urllib.parse import quote
import aiohttp
from aiohttp import web
from .catalog import names
CATALOG=json.loads(Path(__file__).with_name('model_download_catalog.json').read_text(encoding='utf-8'))
BY_ID={x['id']:x for x in CATALOG['models']}
ACTIVE={'queued','downloading','verifying'}
def model_root():
 from .engine_config import downloads_directory
 return downloads_directory()

def destination(row,root=None):
 root=Path(root or model_root()).resolve();folder=root/row['folder'];target=(folder/row['filename']).resolve()
 if not target.is_relative_to(folder.resolve()) or Path(row['filename']).name!=row['filename'] or row['folder'] not in ('diffusion_models','text_encoders','vae','loras'):
  raise ValueError('Invalid model destination.')
 return target

def installed(row,nodes):
 kind,field={'diffusion_models':('UNETLoader','unet_name'),'text_encoders':('CLIPLoader','clip_name'),'vae':('VAELoader','vae_name'),'loras':('LoraLoaderModelOnly','lora_name')}[row['folder']]
 files=names(nodes,kind,field)
 if row['folder']=='diffusion_models':files+=names(nodes,'UnetLoaderGGUF',field)
 if row['folder']=='text_encoders':files+=names(nodes,'CLIPLoaderGGUF',field)
 if row['folder']=='loras':files+=names(nodes,'LoraLoader','lora_name')
 aliases={row['filename'],*row.get('aliases',[])}
 return next((f for f in files if f.replace('\\','/').rsplit('/',1)[-1] in aliases),'')

class ModelDownloads:
 def __init__(self):self.jobs={};self.tasks={};self.serial=asyncio.Lock()
 def catalog(self,nodes):
  models=[]
  for row in CATALOG['models']:
   file=installed(row,nodes)
   try:
    path=destination(row);local=path.is_file() and path.stat().st_size==row['size']
   except ValueError:local=False
   
   try:model_root();download_error=''
   except ValueError as exc:download_error=str(exc)
   models.append({**row,'installed':bool(file or local),'installed_file':file or (row['filename'] if local else ''),'download_error':download_error})
  return {'models':models,'unavailable':CATALOG['unavailable'],'verified_on':CATALOG['verified_on'],'jobs':self.snapshot()}
 def snapshot(self):return [dict(x) for x in self.jobs.values()]
 async def start(self,ident):
  if ident not in BY_ID:raise ValueError('Choose a model from the verified catalog.')
  row=BY_ID[ident];target=destination(row)
  if target.exists():
   if target.stat().st_size!=row['size']:raise ValueError('A different file already exists with this name. Existing files are never overwritten.')
   return {'id':ident,'status':'installed','received':row['size'],'total':row['size']}
  if ident in self.tasks and not self.tasks[ident].done():return dict(self.jobs[ident])
  partial=target.with_name('.'+target.name+'.download.part');target.parent.mkdir(parents=True,exist_ok=True)
  remaining=row['size']-(partial.stat().st_size if partial.exists() else 0)
  if shutil.disk_usage(target.parent).free<max(0,remaining)+256*1024**2:raise ValueError('Not enough free disk space for this model.')
  self.jobs[ident]={'id':ident,'status':'queued','received':max(0,row['size']-remaining),'total':row['size'],'error':''}
  self.tasks[ident]=asyncio.create_task(self._download(row,target,partial))
  return dict(self.jobs[ident])
 async def cancel(self,ident):
  task=self.tasks.get(ident)
  if task and not task.done():task.cancel();await asyncio.gather(task,return_exceptions=True)
  return dict(self.jobs.get(ident,{'id':ident,'status':'paused'}))
 async def close(self):
  for task in self.tasks.values():
   if not task.done():task.cancel()
  await asyncio.gather(*self.tasks.values(),return_exceptions=True)
 async def _download(self,row,target,partial):
  job=self.jobs[row['id']]
  try:
   async with self.serial:
    job['status']='downloading'
    timeout=aiohttp.ClientTimeout(total=None,connect=30,sock_read=120)
    async with aiohttp.ClientSession(timeout=timeout) as session:
     for attempt in range(4):
      try:
       offset=partial.stat().st_size if partial.exists() else 0
       if offset>row['size']:raise ValueError('Partial download exceeds the expected file size.')
       if offset<row['size']:
        url='https://huggingface.co/'+row['repo']+'/resolve/'+row.get('revision','main')+'/'+quote(row['path'],safe='/')+'?download=true'
        async with session.get(url,headers={'Range':f'bytes={offset}-'} if offset else {}) as response:
         if response.status in (401,403):raise ValueError('This download requires access on Hugging Face. Open the model source page; no account gates are bypassed.')
         response.raise_for_status()
         if response.status==206:
          match=re.fullmatch(r'bytes (\d+)-(\d+)/(\d+)',response.headers.get('Content-Range',''))
          if not match or int(match[1])!=offset or int(match[3])!=row['size']:raise ValueError('Invalid resume response from model source.')
         elif response.status==200:offset=0
         else:raise ValueError('Unexpected download response.')
         job['received']=offset
         with partial.open('ab' if offset else 'wb') as output:
          async for chunk in response.content.iter_chunked(2*1024**2):
           if job['received']+len(chunk)>row['size']:raise ValueError('Download exceeds the catalog file size.')
           await asyncio.to_thread(output.write,chunk);job['received']+=len(chunk)
       if partial.stat().st_size!=row['size']:raise aiohttp.ClientPayloadError('Incomplete download; retry to resume.')
       break
      except (aiohttp.ClientError,asyncio.TimeoutError):
       if attempt==3:raise
       await asyncio.sleep(2*(attempt+1))
    job['status']='verifying'
    def verify():
     digest=hashlib.sha256()
     with partial.open('rb') as source:
      for chunk in iter(lambda:source.read(8*1024**2),b''):digest.update(chunk)
     if digest.hexdigest()!=row['sha256']:
      # Keep a rejected file for diagnosis, but never resume its corrupt bytes.
      rejected=partial.with_name(partial.name+'.rejected-'+str(time.time_ns()));partial.rename(rejected)
      raise ValueError('SHA-256 does not match the published model. The file was not installed.')
     # Atomic publication refuses overwriting, including concurrent imports.
     os.link(partial,target);partial.unlink()
    await asyncio.to_thread(verify)
    job.update(status='installed',received=row['size'],error='')
  except asyncio.CancelledError:job['status']='paused';raise
  except Exception as exc:job.update(status='failed',error=str(exc))

async def catalog(request):
 studio=request.app['studio']
 try:nodes=await studio.nodes()
 except (aiohttp.ClientError,asyncio.TimeoutError):nodes={}
 return web.json_response(studio.model_downloads.catalog(nodes))
async def status(request):return web.json_response({'jobs':request.app['studio'].model_downloads.snapshot()})
async def start(request):return web.json_response(await request.app['studio'].model_downloads.start((await request.json()).get('id')),status=202)
async def cancel(request):return web.json_response(await request.app['studio'].model_downloads.cancel(request.match_info['model']))
