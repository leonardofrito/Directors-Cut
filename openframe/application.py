"""Double-click launcher: browser UI, persistent data and graceful local shutdown."""
import argparse,asyncio,json,logging,os,socket,sys,webbrowser
from pathlib import Path
from .version import VERSION

def configure_logging(name='app.log'):
    from .paths import DATA_ROOT
    folder=DATA_ROOT/'.runtime';folder.mkdir(parents=True,exist_ok=True)
    if sys.stdout is None:sys.stdout=(folder/name).open('a',encoding='utf-8',buffering=1)
    if sys.stderr is None:sys.stderr=sys.stdout
    logging.basicConfig(level=logging.INFO,format='%(asctime)s %(levelname)s %(name)s: %(message)s',handlers=[logging.FileHandler(folder/name,encoding='utf-8')])
    logging.getLogger('aiohttp.access').setLevel(logging.WARNING)

def self_test():
    from .paths import RESOURCE_ROOT,DATA_ROOT
    from .provider import build_graph
    from .video import PRESETS,template
    from .prompt_guides import runtime_guidance
    root=RESOURCE_ROOT
    required=['web/index.html','web/assets/theme.css','web/assets/previews/index.json','openframe/model_download_catalog.json','LICENSE','THIRD_PARTY_NOTICES.md']
    for name in required:
        if not (root/name).is_file():raise RuntimeError('Missing bundled resource: '+name)
    previews=json.loads((root/'web/assets/previews/index.json').read_text(encoding='utf-8'))
    images={url for options in previews.values() for url in options.values()}
    for url in images:
        if not (root/'web'/url.lstrip('/')).is_file():raise RuntimeError('Missing preset preview: '+url)
    graph,_=build_graph(dict(mode='asset',asset_kind='character',style='Photorealistic',prompt='A character.',ratio='1:1',seed=1,steps=25),'DirectorsCut/package-self-test')
    for preset in PRESETS:template(preset)
    assert runtime_guidance('h3') and runtime_guidance('qwen')
    DATA_ROOT.mkdir(parents=True,exist_ok=True)
    return dict(ok=True,version=VERSION,packaged=bool(getattr(sys,'frozen',False)),data_dir=str(DATA_ROOT),previews=len(images),image_graph_nodes=len(graph),video_workflows=len(PRESETS),gpu_generation=False)

async def serve(args):
    from aiohttp import web,ClientSession,ClientTimeout,ClientError
    from . import engine_config
    from .server import create_app
    from .paths import DATA_ROOT
    settings=engine_config.current()
    if not engine_config.load().get('comfy_url') and not os.environ.get('OPENFRAME_COMFY_URL'):
        found=await engine_config.discover()
        if found['servers']:settings['comfy_url']=found['servers'][0]['url']
    engine_config.apply_environment(settings)
    explicit_port=args.port is not None;args.port=args.port or 7860
    base=f'http://127.0.0.1:{args.port}'
    # An occupied port is only reused after verifying this application's identity.
    async with ClientSession(timeout=ClientTimeout(total=2)) as client:
        try:
            async with client.get(base+'/api/app') as response:
                data=await response.json()
                if data.get('application')=="Director's Cut" and Path(data.get('data_dir','')).resolve()==DATA_ROOT.resolve():
                    if not args.no_browser:await asyncio.to_thread(webbrowser.open,base)
                    return
        except (ClientError,ValueError,asyncio.TimeoutError):pass
    with socket.socket() as probe:
        # Match aiohttp's POSIX listener so a just-closed connection's TIME_WAIT
        # does not prevent reopening the app on the same port.
        if os.name!='nt':probe.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
        try:probe.bind((args.listen,args.port))
        except OSError:
            if explicit_port:raise
            probe.bind((args.listen,0));args.port=probe.getsockname()[1]
    base=f'http://127.0.0.1:{args.port}'
    os.environ.update(OPENFRAME_HOST=args.listen,OPENFRAME_PORT=str(args.port))
    stop=asyncio.Event();app=create_app(shutdown_event=stop);runner=web.AppRunner(app)
    try:
        await runner.setup();await web.TCPSite(runner,args.listen,args.port).start()
        if not args.no_browser:
            first_run=not app['studio'].store.list()
            await asyncio.to_thread(webbrowser.open,base+('/#setup' if first_run else '/'))
        await stop.wait()
    finally:await runner.cleanup()

def main(argv=None):
    argv=list(sys.argv[1:] if argv is None else argv)
    if argv[:1]==['--internal-proxy']:
        configure_logging('proxy-internal.log')
        from comfy_api_proxy.cli import main as proxy_main
        sys.argv=[sys.argv[0],*argv[1:]]
        return proxy_main()
    parser=argparse.ArgumentParser(description="Director's Cut — local assets and video")
    parser.add_argument('--version',action='version',version=VERSION)
    parser.add_argument('--listen',default='127.0.0.1');parser.add_argument('--port',type=int)
    parser.add_argument('--no-browser',action='store_true');parser.add_argument('--data')
    parser.add_argument('--self-test',action='store_true');parser.add_argument('--report')
    args=parser.parse_args(argv)
    if args.data:os.environ['OPENFRAME_DATA']=str(Path(args.data).expanduser().resolve())
    configure_logging()
    try:
        if args.self_test:
            result=self_test()
            if args.report:Path(args.report).write_text(json.dumps(result,indent=2),encoding='utf-8')
            else:print(json.dumps(result))
            return 0
        asyncio.run(serve(args));return 0
    except KeyboardInterrupt:return 0
    except Exception as exc:
        logging.exception('Application startup failed')
        if args.report:Path(args.report).write_text(json.dumps({'ok':False,'error':str(exc)}),encoding='utf-8')
        if sys.platform=='win32' and getattr(sys,'frozen',False) and not args.self_test:
            import ctypes
            from .paths import DATA_ROOT
            ctypes.windll.user32.MessageBoxW(None,str(exc)+'\n\nLogs: '+str(DATA_ROOT/'.runtime'),"Director's Cut",0x10)
        return 1

if __name__=='__main__':raise SystemExit(main())
