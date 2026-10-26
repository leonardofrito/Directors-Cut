"""Launch Director's Cut with a discovered/configurable ComfyUI connection on any OS."""
import argparse,asyncio,os,socket,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent

def reachable(port):
 try:
  with socket.create_connection(('127.0.0.1',port),timeout=1):return True
 except OSError:return False

def main():
 from openframe import engine_config
 parser=argparse.ArgumentParser(description="Launch Director's Cut.")
 parser.add_argument('--listen',default=os.environ.get('OPENFRAME_HOST','127.0.0.1'));parser.add_argument('--port',type=int,default=int(os.environ.get('OPENFRAME_PORT',7860)))
 parser.add_argument('--comfy-url');parser.add_argument('--comfy-root');parser.add_argument('--models-dir');parser.add_argument('--proxy-url')
 args=parser.parse_args();os.chdir(ROOT)
 settings=engine_config.current()
 if not args.comfy_url and not engine_config.load().get('comfy_url') and not os.environ.get('OPENFRAME_COMFY_URL'):
  found=asyncio.run(engine_config.discover())
  if found['servers']:settings['comfy_url']=found['servers'][0]['url']
 for key in ('comfy_url','comfy_root','models_dir','proxy_url'):
  value=getattr(args,key)
  if value:
   settings[key]=engine_config.url(value) if key.endswith('_url') else str(Path(value).expanduser().resolve())
 if args.comfy_root:
  settings['comfy_root']=str(engine_config.normalize_root(args.comfy_root))
  if not args.models_dir:settings['models_dir']=str(Path(settings['comfy_root'])/'models')
 if args.proxy_url:settings['proxy_managed']=False
 elif args.comfy_url or settings['comfy_url']!='http://127.0.0.1:8188':settings['proxy_managed']=True
 engine_config.apply_environment(settings)
 # Persist managed intent for the server child; environment carries explicit CLI paths/URLs.
 if settings['proxy_managed']:
  from openframe.storage import write_json
  write_json(engine_config.CONFIG,settings)
 os.environ.update(OPENFRAME_HOST=args.listen,OPENFRAME_PORT=str(args.port))
 if reachable(args.port):print(f'Director’s Cut is already running at http://127.0.0.1:{args.port}');return
 print(f'Director’s Cut: http://127.0.0.1:{args.port}\nComfyUI: {settings["comfy_url"]}',flush=True)
 try:subprocess.run([sys.executable,'-m','openframe.server'],check=True)
 except KeyboardInterrupt:pass
if __name__=='__main__':main()
