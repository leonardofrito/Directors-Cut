"""Launcher-only process controls; existing direct development servers stay unaffected."""
import asyncio,os,subprocess,sys
from aiohttp import web
from .paths import DATA_ROOT
from .paths import RESOURCE_ROOT
from .version import VERSION

async def info(request):
    return web.json_response(dict(application="Director's Cut",version=VERSION,packaged=bool(getattr(sys,'frozen',False)),can_quit=bool(request.app.get('shutdown_event')),data_dir=str(DATA_ROOT)))

async def quit_app(request):
    stop=request.app.get('shutdown_event')
    if stop is None:raise ValueError('Close the terminal used to launch this development server.')
    studio=request.app['studio']
    if getattr(studio,'node_setup',None) and studio.node_setup.running:raise ValueError('Wait until node installation finishes before quitting.')
    if studio.queue_items() or studio.queue.qsize():raise ValueError('Finish or cancel the generation queue before quitting.')
    if any(j['status'] in ('queued','downloading','verifying') for j in studio.model_downloads.snapshot()):raise ValueError('Pause model downloads before quitting.')
    asyncio.get_running_loop().call_later(.4,stop.set)
    return web.json_response({'stopping':True})

async def open_data(request):
    DATA_ROOT.mkdir(parents=True,exist_ok=True)
    if sys.platform=='win32':os.startfile(str(DATA_ROOT))
    else:subprocess.Popen(['open' if sys.platform=='darwin' else 'xdg-open',str(DATA_ROOT)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    return web.json_response({'opened':True})

async def license_text(request):
    names={'app':'LICENSE','third-party':'THIRD_PARTY_NOTICES.md','dependencies':'DEPENDENCY_NOTICES.txt'}
    return web.FileResponse(RESOURCE_ROOT/names[request.match_info['document']])
