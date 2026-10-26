"""Optional MCP bridge. Uses the running studio API, never a second generation queue."""
import argparse
import io
import json
import os
import re
import uuid
from pathlib import Path
from urllib.parse import quote

import aiohttp
from PIL import Image as PillowImage
from mcp.server.fastmcp import FastMCP, Image
from mcp.types import ToolAnnotations, TextContent, ImageContent
from openframe.prompt_guides import GUIDES, guide_text, runtime_guidance, prompt_strategy, image_settings_example
from openframe.provider import image_prompt_parts
from openframe.assets import resolve_references, edit_reference
from openframe.characters import MULTI_TRAITS, EXCLUSIVE_TRAITS
from openframe import reference_uploads

ROOT = Path(__file__).resolve().parent
BASE = os.environ.get('DIRECTORS_CUT_URL', 'http://127.0.0.1:7860').rstrip('/')
READ = ToolAnnotations(readOnlyHint=True, destructiveHint=False)
WRITE = ToolAnnotations(readOnlyHint=False, destructiveHint=False)
mcp = FastMCP("Director's Cut", host='127.0.0.1', port=7861, instructions=(
    'Control the existing local Director’s Cut studio. For Qwen-Image 2.1 start with a short direct scene/request plus existing preset JSON from get_image_presets; preset-only creation is valid. '
    'Do not spend tokens expanding preset names into a long caption: the studio already assembles them. Keep prompt_enhancer=false for this baseline. Use preview_image_prompt to inspect the final base text without generating. '
    'Use compact prompt guidance by default; full guides are optional for complex cases, not mandatory reading on every call. '
    'Before writing a reference-based scene/edit call prepare_prompt_context and inspect the supplied reference images. '
    'For H3 use detailed, feasible REF2VA action/camera/cut/audio direction and stable subject roles; never use the base/I2VA guide. '
    'For Qwen edits use short imperative changes and preserve only unaffected attributes. '
    'Preserve unusual anatomy, invisibility and exact dialogue. Use @handles; the studio binds reference tags. '
    'Only queue GPU work when the user asks for generation. Do not generate previews to test UI. '
    'Use request_id to avoid duplicate submissions. Check status instead of polling rapidly. '
    'The host assistant writes prompts; this server has no GPT/Claude API dependency.'))


def ident(value):
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,120}', value):
        raise ValueError('Invalid project, study or take ID.')
    return value


async def request(method, path, payload=None, base=BASE):
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=120)) as session:
        async with session.request(method, base+path, json=payload) as response:
            data = await response.json()
            if response.status >= 400:
                raise ValueError(data.get('error', 'Studio request failed.'))
            return data


async def project_data(project_id):
    return await request('GET', '/api/projects/'+ident(project_id))


async def engine_address():
    """Follow the studio's saved/live connection, including changes after MCP startup."""
    return (await request('GET', '/api/engine'))['settings']['comfy_url']


async def study_data(project_id, study_id):
    project = await project_data(project_id)
    return next(s for s in project['shots'] if s['id']==ident(study_id))


async def reference_image_bytes(session, project_id, file):
    """Read the entire streamed image with a bound; a single read(n) may be partial."""
    data=bytearray()
    async with session.get(BASE+'/files/'+ident(project_id)+'/'+quote(file,safe='/'),timeout=aiohttp.ClientTimeout(total=30)) as response:
        response.raise_for_status()
        async for chunk in response.content.iter_chunked(65536):
            data.extend(chunk)
            if len(data)>32*1024*1024:raise ValueError('Reference image too large.')
    return bytes(data)


def take_summary(project_id, draft):
    result = {key:draft.get(key) for key in ('id','number','status','error','progress','stage','full_prompt','cancel_requested') if key in draft}
    if draft.get('file') and draft['status']=='succeeded':
        result['url'] = BASE+'/files/'+ident(project_id)+'/'+quote(draft['file'], safe='/')
    return result


@mcp.tool(annotations=READ)
async def studio_status() -> dict:
    """Read studio queue, local GPU memory and ComfyUI queue; never generate or unload."""
    result = dict(studio=BASE, queue=await request('GET','/api/queue'))
    try:
        engine = await engine_address()
        result['engine'] = await request('GET','/system_stats',base=engine)
        result['engine_queue'] = await request('GET','/queue',base=engine)
    except (aiohttp.ClientError, TimeoutError):
        result['engine_error'] = 'ComfyUI is unavailable.'
    return result


@mcp.tool(annotations=READ)
async def list_projects() -> list[dict]:
    """List Director’s Cut projects, without their potentially large take histories."""
    return [{k:p[k] for k in ('id','name','created_at') if k in p} for p in await request('GET','/api/projects')]


@mcp.tool(annotations=READ)
async def get_project(project_id: str) -> dict:
    """List assets/@handles and image/video studies. Use get_study for take details."""
    p = await project_data(project_id)
    return dict(id=p['id'],name=p['name'],assets=[{k:a.get(k) for k in ('id','handle','name','kind','source_shot_id','take_count','file')} for a in p.get('assets',[])],
                studies=[dict(id=s['id'],title=s['title'],mode=s.get('mode'),takes=len(s['drafts']),asset_id=s.get('asset_id')) for s in p['shots'] if s.get('mode') in ('asset','video')])


@mcp.tool(annotations=READ)
async def get_study(project_id: str, study_id: str) -> dict:
    """Read current settings, references and generated takes; completed takes include download URLs."""
    study = await study_data(project_id,study_id)
    guide='h3' if study.get('mode')=='video' else 'qwen-edit' if study.get('reference_ids') or study.get('upload_reference_ids') or study.get('edit_source') or '@' in study.get('prompt','') else 'qwen'
    return {**{k:v for k,v in study.items() if k!='drafts'},'drafts':[take_summary(project_id,d) for d in study['drafts']],
            'prompt_guidance':dict(strategy=prompt_strategy(guide),model=guide,context_tool='prepare_prompt_context',guide_resource='directors-cut://guides/'+guide)}


@mcp.tool(annotations=READ)
async def get_model_setup() -> dict:
    """Inspect installed model names and preset options. Prefer Omni for local video; never substitute recipes."""
    config = await request('GET','/api/config')
    return {key:config.get(key) for key in ('online','detail','workflows','video','asset_categories','character_categories','image_edit_presets','loras','enhancer')}


@mcp.tool(annotations=WRITE)
async def create_project(name: str) -> dict:
    """Create a named project. Does not generate media."""
    return await request('POST','/api/projects',dict(name=name))


@mcp.tool(annotations=WRITE)
async def create_study(project_id: str, title: str, mode: str='asset', asset_kind: str='character') -> dict:
    """Create an asset or video scene. Asset kinds: character, prop, location. No GPU work."""
    if mode not in ('asset','video') or asset_kind not in ('character','prop','location'):
        raise ValueError('Choose asset/video and character/prop/location.')
    settings = dict(title=title,prompt='',video_preset='fast-omni') if mode=='video' else dict(title=title,prompt='',style='Cinematic',camera='Wide',ratio='1:1',megapixels=2,steps=25,seed=-1,asset_kind=asset_kind)
    study=await request('POST',f'/api/projects/{ident(project_id)}/shots',dict(mode=mode,settings=settings))
    return dict(id=study['id'],title=study['title'],mode=mode)


@mcp.tool(annotations=WRITE)
async def update_study(project_id: str, study_id: str, settings: dict) -> dict:
    """Update prompt/settings without generating. Keep @handles in prompts. For Qwen prefer a short prompt plus character_traits/location_traits/prop_traits from get_image_presets; no verbose rewrite needed. Call preview_image_prompt to inspect assembly without generation. Set prompt_enhancer=false for this baseline."""
    allowed={'title','prompt','ratio','megapixels','duration','video_preset','video_direction','model_files','model_format','reference_ids','upload_reference_ids','prompt_enhancer','enhancer_model','seed','steps','loras','asset_kind','character_traits','location_traits','prop_traits','style','camera','lens_type','sensor','focal_length','f_stop','lighting','light_color','light_notes','film','grade','workflow_id','edit_source','edit_preset'}
    if set(settings)-allowed:
        raise ValueError('Unsupported setting: '+', '.join(set(settings)-allowed))
    study=await study_data(project_id,study_id)
    result=await request('PUT',f'/api/projects/{ident(project_id)}/shots/{ident(study_id)}',{**study,**settings})
    return {k:v for k,v in result.items() if k!='drafts'}


@mcp.tool(annotations=WRITE)
async def generate(project_id: str, study_id: str, count: int=1, request_id: str='') -> dict:
    """Queue requested media through the studio/official Comfy SDK. Returns immediately. Reuse request_id when retrying; poll get_study or studio_status sparingly. Only call when the user wants actual GPU generation."""
    if isinstance(count,bool) or not 1<=count<=4:
        raise ValueError('Choose 1–4 takes.')
    study=await study_data(project_id,study_id)
    submission_id=request_id or uuid.uuid4().hex
    result=await request('POST',f'/api/projects/{ident(project_id)}/shots/{ident(study_id)}/generate',{**study,'count':count,'request_id':submission_id})
    return dict(request_id=submission_id,takes=[take_summary(project_id,d) for d in result.get('drafts',[result])])


@mcp.tool(annotations=WRITE)
async def cancel_take(project_id: str, study_id: str, take_id: str) -> dict:
    """Cancel only this queued/running take; remaining work stays queued. Requires a studio version with Skip current video."""
    return await request('POST',f'/api/projects/{ident(project_id)}/shots/{ident(study_id)}/drafts/{ident(take_id)}/cancel',{})


@mcp.tool(annotations=WRITE)
async def save_asset(project_id: str, study_id: str, take_id: str, name: str) -> dict:
    """Save/rename the existing asset with a completed image. Keeps its ID/history and does not fork a duplicate."""
    study=await study_data(project_id,study_id)
    if study.get('mode')!='asset':raise ValueError('Choose an image asset study.')
    return await request('POST',f'/api/projects/{ident(project_id)}/assets',dict(shot_id=ident(study_id),draft_id=ident(take_id),name=name,kind=study.get('asset_kind','character'),save_action='overwrite'))


@mcp.tool(annotations=READ)
async def view_asset(project_id: str, asset_id: str) -> Image:
    """Return an asset reference thumbnail to the host vision model. No GPU generation; only call when visual analysis is useful."""
    p=await project_data(project_id);asset=next(a for a in p.get('assets',[]) if a['id']==ident(asset_id))
    file=asset.get('thumbnail') or asset.get('file')
    if not file:raise ValueError('This asset has no image yet.')
    async with aiohttp.ClientSession() as session:
        data=await reference_image_bytes(session,project_id,file)
    with PillowImage.open(io.BytesIO(data)) as source:
        source.thumbnail((1024,1024));out=io.BytesIO();source.convert('RGB').save(out,format='JPEG',quality=85)
    return Image(data=out.getvalue(),format='jpeg')


@mcp.tool(annotations=WRITE)
async def attach_reference(project_id: str, study_id: str, image_path: str, role: str='wardrobe') -> dict:
    """Upload an existing local image to an asset study. Roles: wardrobe, identity, hair, style, background, prop. No Library asset or GPU generation. Paths refer to the MCP server's machine."""
    if role not in ('wardrobe','identity','hair','style','background','prop'):
        raise ValueError('Choose a supported reference role.')
    path=Path(image_path)
    if not path.is_absolute() or path.suffix.lower() not in ('.png','.jpg','.jpeg','.webp'):
        raise ValueError('Choose an absolute PNG/JPEG/WebP image path.')
    if not path.is_file() or path.stat().st_size>32*1024*1024:
        raise ValueError('Choose an existing image up to 32 MB.')
    data=aiohttp.FormData();data.add_field('image',path.read_bytes(),filename=path.name);data.add_field('role',role)
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=60)) as session:
        async with session.post(f'{BASE}/api/projects/{ident(project_id)}/shots/{ident(study_id)}/references',data=data) as response:
            result=await response.json()
            if response.status>=400:raise ValueError(result.get('error','Reference upload failed.'))
    study=next(s for s in result['shots'] if s['id']==study_id)
    return dict(study_id=study_id,upload_reference_ids=study.get('upload_reference_ids',[]))


@mcp.tool(annotations=WRITE)
async def release_idle_memory() -> dict:
    """Unload ComfyUI models/cache only when BOTH studio and ComfyUI queues are idle. Does not cancel jobs or promise a faster next generation."""
    address=await engine_address()
    queue=await request('GET','/api/queue');engine=await request('GET','/queue',base=address)
    if queue['running'] or queue['waiting'] or engine.get('queue_running') or engine.get('queue_pending'):
        raise ValueError('Wait for both queues to become idle.')
    async with aiohttp.ClientSession() as session:
        async with session.post(address+'/free',json=dict(unload_models=True,free_memory=True),timeout=aiohttp.ClientTimeout(total=30)) as response:
            response.raise_for_status()
    return dict(requested=True,note='Release is processed by ComfyUI; models must reload on the next run.')


@mcp.tool(annotations=READ)
def get_prompt_guide(model: str='h3', detail: str='quick') -> str:
    """Read compact model guidance by default. detail='full' is optional for complex cases. Qwen: short request + preset JSON, enhancer off. H3: detailed REF2VA direction."""
    if model not in GUIDES:raise ValueError('Choose '+', '.join(GUIDES))
    if detail not in ('quick','full'):raise ValueError('Choose quick or full guidance.')
    if detail=='full' or model in ('qwen-presets','qwen-examples','qwen-text','qwen-capabilities'):
        return guide_text(model)
    return json.dumps(prompt_strategy(model),ensure_ascii=False)+'\n\n'+runtime_guidance(model)


@mcp.tool(annotations=READ)
async def get_image_presets(asset_kind: str='character') -> dict:
    """Get exact preset names and compact JSON settings for Qwen 2.1. Select these instead of writing a long descriptive prompt. Does not generate."""
    if asset_kind not in ('character','location','prop'):raise ValueError('Choose character, location or prop.')
    config=await request('GET','/api/config')
    categories=config.get('character_categories',[]) if asset_kind=='character' else config.get('asset_categories',{}).get(asset_kind,[])
    categories=[dict(id=c['id'],label=c['label'],options=c['options'],multiple=(asset_kind=='character' and c['id'] in MULTI_TRAITS)) for c in categories]
    example=image_settings_example() if asset_kind=='character' else dict(asset_kind=asset_kind,prompt='Describe only the specific place or object you need.',prompt_enhancer=False)
    return dict(strategy=prompt_strategy('qwen'),asset_kind=asset_kind,categories=categories,
                settings_example=example,multiple_choice_conflicts=EXCLUSIVE_TRAITS if asset_kind=='character' else {},image_edit_presets=config.get('image_edit_presets',[]),
                next_step='Use update_study with these JSON fields. preview_image_prompt shows the assembled prompt; generate is separate.')


@mcp.tool(annotations=READ)
async def preview_image_prompt(project_id: str, study_id: str, settings: dict | None=None) -> dict:
    """Preview the exact base Qwen prompt after preset expansion and reference binding. Optional settings are temporary overrides: no save, upload, enhancer, model load or GPU work."""
    project=await project_data(project_id)
    study=next(s for s in project['shots'] if s['id']==ident(study_id))
    if study.get('mode')!='asset':raise ValueError('Choose an image asset study.')
    if settings is not None and not isinstance(settings,dict):raise ValueError('Use a JSON settings object.')
    if settings and ('mode' in settings or 'references' in settings):raise ValueError('Preview settings cannot change mode or inject reference bindings.')
    data={**study,**(settings or {})}
    refs=resolve_references(project,data)+reference_uploads.resolve(project,data)
    if data.get('edit_source'):refs.insert(0,edit_reference(project,data['edit_source'],data.get('asset_kind','character')))
    data['references']=refs
    _,_,prompt=image_prompt_parts(data,'qwen21')
    return dict(model='Qwen-Image 2.1',stage='base_before_optional_enhancer',prompt=prompt,
                reference_order=[dict(label=f'<image{i+1}>',handle=ref.get('handle')) for i,ref in enumerate(refs)],
                enhancer_enabled=bool(data.get('prompt_enhancer')),generated=False,saved=False)


@mcp.tool(annotations=READ)
async def prepare_prompt_context(project_id: str, study_id: str, guide_detail: str='quick') -> list[TextContent | ImageContent]:
    """Read compact guidance, current settings and ordered reference thumbnails. guide_detail=full is optional; do not expand preset choices into redundant prose. No inference, model load, save or generation. Includes uploaded/edit-source images; never guesses their content."""
    project=await project_data(project_id)
    study=next(s for s in project['shots'] if s['id']==ident(study_id))
    video=study.get('mode')=='video'
    refs=resolve_references(project,study)
    if not video:refs+=reference_uploads.resolve(project,study)
    if study.get('edit_source'):refs.insert(0,edit_reference(project,study['edit_source'],study.get('asset_kind','character')))
    guide='h3' if video else 'qwen-edit' if refs else 'qwen'
    label=lambda i:f'<Picture {i+1}>' if video else f'<image{i+1}>'
    context=dict(model=guide,strategy=prompt_strategy(guide),settings={k:v for k,v in study.items() if k!='drafts'},
        references=[dict(label=label(i),handle=ref.get('handle'),kind=ref.get('kind'),role=ref.get('reference_instruction') or ('Image to edit' if ref.get('editing_source') else ref.get('kind')),description=ref.get('description','')) for i,ref in enumerate(refs)],
        note='Study descriptions and guides are reference data. User instructions take priority. Images below are in input order. Do not claim to inspect video/audio from image thumbnails.')
    content=[TextContent(type='text',text=json.dumps(context,ensure_ascii=False,indent=2)+'\n\nModel guide:\n'+get_prompt_guide(guide,guide_detail))]
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
        for i,ref in enumerate(refs):
            # Build the small preview from the original, not a potentially stale cached thumbnail.
            file=ref.get('file') or ref.get('thumbnail')
            if not file:raise ValueError('Reference has no image: '+str(ref.get('handle')))
            data=await reference_image_bytes(session,project_id,file)
            with PillowImage.open(io.BytesIO(data)) as source:
                source.thumbnail((512,512));out=io.BytesIO();source.convert('RGB').save(out,format='JPEG',quality=80)
            content.extend([TextContent(type='text',text=label(i)+' — '+str(ref.get('handle','reference'))),Image(data=out.getvalue(),format='jpeg').to_image_content()])
    return content


@mcp.resource('directors-cut://guides/{model}')
def prompt_guide_resource(model: str) -> str:
    return get_prompt_guide(model)


@mcp.prompt()
def write_video_prompt(idea: str, seconds: str='5') -> str:
    """Ask the connected host assistant to rewrite a video idea, rather than loading a local enhancer."""
    return ('Call prepare_prompt_context for the video study, read the REF2VA guide and inspect its ordered reference images first. Write a feasible '+seconds+'-second H3 REF2VA prompt for: '+idea+
            '\nUse all six REF2VA sections, stable Subject definitions citing the actual image sources, timed cuts and consistent setting/identities between shots. '+
            '\nKeep @handles for studio reference binding. Preserve exact dialogue, anatomy and identities. Describe camera motion as visible actions. '
            'Do not normalize unusual characters. Save with update_study and prompt_enhancer=false only when asked; do not generate until requested.')


@mcp.prompt()
def write_asset_prompt(idea: str) -> str:
    """Choose Qwen preset JSON plus a short request; a verbose image prompt is optional."""
    return ('For this Qwen-Image 2.1 asset idea: '+idea+
            '\nStart with get_image_presets and choose the existing settings as JSON. Add only a short free prompt for intent not covered by the choices. Do not expand each choice into prose; the studio already does it. Preset-only generation is valid. '
            'Keep prompt_enhancer=false unless the user asks otherwise. If references are involved, prepare_prompt_context supplies compact guidance and images; use short imperative edits. '
            'Use preview_image_prompt to show the actual assembled base prompt without saving or GPU work. A long prompt is not required. '
            'Preserve unusual anatomy and user constraints. Save with update_study only when asked; do not generate until requested.')



def main():
    parser=argparse.ArgumentParser(description='Optional Director’s Cut MCP bridge')
    parser.add_argument('--transport',choices=['stdio','streamable-http'],default='stdio')
    args=parser.parse_args()
    mcp.run(transport=args.transport)


if __name__=='__main__':
    main()
