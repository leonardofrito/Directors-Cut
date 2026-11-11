"""Download exact selected results; source paths are resolved from project metadata."""
import asyncio,re,uuid,zipfile
from aiohttp import web

async def create(request):
    store=request.app['studio'].store;p=store.load(request.match_info['project']);items=(await request.json()).get('items')
    if not isinstance(items,list) or not 1<=len(items)<=500:raise ValueError('Select between 1 and 500 results.')
    files=[];names=set();seen=set()
    for item in items:
        if not isinstance(item,dict):raise ValueError('Invalid selected result.')
        if item.get('asset_id'):
            asset=next((a for a in p.get('assets',[]) if a['id']==item['asset_id']),None)
            if not asset or not asset.get('file'):raise ValueError('The selected image is unavailable.')
            relative=asset['file'];title=asset.get('name') or asset.get('handle') or 'Asset'
        else:
            shot=store.shot(p,item.get('shot_id',''));take=next((d for d in shot.get('drafts',[]) if d['id']==item.get('draft_id') and d['status']=='succeeded'),None)
            if not take or not take.get('file'):raise ValueError('Select completed results only.')
            relative=take['file'];title=shot.get('title') or 'Shot'
        if relative in seen:continue
        seen.add(relative);path=store.file(p['id'],relative)
        if path.suffix.lower() not in ('.png','.jpg','.jpeg','.webp','.mp4') or not path.is_file():raise ValueError('The selected file is unavailable.')
        stem=re.sub(r'[<>:"/\\|?*\x00-\x1f]','_',title).strip().rstrip('. ')[:120] or 'Asset';name=stem+path.suffix.lower();i=1
        while name.casefold() in names:name=f'{stem} ({i}){path.suffix.lower()}';i+=1
        names.add(name.casefold());files.append((path,name))
    relative=f'exports/Selected results-{uuid.uuid4().hex[:12]}.zip';destination=store.file(p['id'],relative)
    def pack():
        destination.parent.mkdir(parents=True,exist_ok=True)
        try:
            with zipfile.ZipFile(destination,'w',compression=zipfile.ZIP_STORED,allowZip64=True) as archive:
                for path,name in files:archive.write(path,name)
        except BaseException:destination.unlink(missing_ok=True);raise
    await asyncio.to_thread(pack)
    return web.json_response(dict(download=relative,count=len(files)))

async def delete(request):
    from .assets import delete_asset
    from .storage import now
    store=request.app['studio'].store;p=store.load(request.match_info['project']);data=await request.json();items=data.get('items')
    if data.get('confirm') is not True:raise ValueError('Confirm deletion first.')
    if not isinstance(items,list) or not 1<=len(items)<=500:raise ValueError('Select between 1 and 500 items.')
    targets=[];seen=set();active={'queued','submitting','running','pending','downloading'}
    for item in items:
        if not isinstance(item,dict):raise ValueError('Invalid selection.')
        shot=store.shot(p,item.get('shot_id',''));ident=item.get('draft_id');key=(shot['id'],ident)
        if key in seen:continue
        seen.add(key)
        if any(c.get('shot_id')==shot['id'] for c in (p.get('editor_timeline') or {}).get('clips',[])):raise ValueError('Remove selected shots from the Timeline before deleting them.')
        takes=[next((d for d in shot.get('drafts',[]) if d['id']==ident),None)] if ident else shot.get('drafts',[])
        if ident and takes[0] is None:raise ValueError('The selected take no longer exists.')
        if any(d.get('status') in active for d in takes):raise ValueError('Wait for selected generations to finish before deleting them.')
        targets.append((shot,ident))
    # All validation precedes the first saved mutation; files stay recoverable.
    whole={shot['id'] for shot,ident in targets if ident is None}
    for shot,ident in targets:
        if ident is not None:
            if shot['id'] in whole:continue
            take=next(d for d in shot['drafts'] if d['id']==ident);shot['drafts'].remove(take);shot.setdefault('archived_drafts',[]).append({**take,'deleted_at':now()})
            if (shot.get('approved') or {}).get('draft_id')==ident:shot['approved']=None
            asset=next((a for a in p.get('assets',[]) if a.get('id')==shot.get('asset_id')),None)
            if asset and asset.get('source_draft_id')==ident:asset.pop('source_draft_id',None)
        elif shot in p['shots']:
            if shot.get('asset_id') and any(a['id']==shot['asset_id'] for a in p.get('assets',[])):delete_asset(store,p,shot['asset_id'],save=False)
            if shot in p['shots']:p['shots'].remove(shot);p.setdefault('archived_shots',[]).append(shot)
            p['storyboard']=[v for v in p.get('storyboard',[]) if v.get('shot_id')!=shot['id']]
    store.save(p)
    return web.json_response(p)
