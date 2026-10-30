"""Project-owned image references. Imported images become immutable local PNGs."""
import io
import re
import unicodedata
import uuid
import hashlib
import copy
import shutil

from PIL import Image, ImageOps, UnidentifiedImageError

from .storage import now, write_json
from .video_mentions import bind_media_mentions

KINDS = {'character', 'prop', 'location'}
MAX_UPLOAD = 32 * 1024 * 1024
MAX_REFERENCES = 10


def unique_names(project):
    used = set()
    for asset in project.get('assets', []):
        base = asset['name'].strip() or 'Asset'
        name, suffix = base, 2
        while name.casefold() in used:
            name = f'{base} ({suffix})'
            suffix += 1
        asset['name'] = name
        used.add(name.casefold())


def add_asset(store, project, content, name, kind='character', description='', existing=None):
    if kind not in KINDS:
        raise ValueError('Choose character, prop or location.')
    name = str(name).strip()[:120]
    if not name:
        raise ValueError('Give your asset a name.')
    if not content or len(content) > MAX_UPLOAD:
        raise ValueError('Choose an image up to 32 MB.')
    try:
        with Image.open(io.BytesIO(content)) as original:
            if original.format not in ('PNG', 'JPEG', 'WEBP'):
                raise ValueError('Choose a PNG, JPEG or WebP image.')
            if original.width * original.height > 40_000_000:
                raise ValueError('Image is too large (40 megapixels maximum).')
            image = ImageOps.exif_transpose(original)
            image.thumbnail((4096, 4096))
            image = image.convert('RGBA' if 'A' in image.getbands() else 'RGB')
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as exc:
        raise ValueError('Choose a valid PNG, JPEG or WebP image.') from exc
    slug = unicodedata.normalize('NFKD', name).encode('ascii', 'ignore').decode().lower()
    slug = re.sub(r'[^a-z0-9]+', '_', slug).strip('_')[:40] or kind
    handles = {a['handle'] for a in project.get('assets', []) + project.get('archived_assets', [])}
    handle, suffix = slug, 2
    while handle in handles:
        handle = f'{slug}_{suffix}'
        suffix += 1
    if existing:
        handle = existing['handle']
        name = existing['name']
    asset_id = existing['id'] if existing else uuid.uuid4().hex
    file = f'assets/{asset_id}.png'
    path = store.file(project['id'], file)
    path.parent.mkdir(parents=True, exist_ok=True)
    if existing and path.exists():
        history = [d for s in project.get('shots', []) + project.get('archived_shots', [])
                   for d in s.get('drafts', []) if d.get('file') == file]
        if history:
            preserved = f'assets/{asset_id}.history-{uuid.uuid4().hex}.png'
            shutil.copy2(path, store.file(project['id'], preserved))
            for draft in history:
                draft['file'] = preserved
    image.save(path, 'PNG')
    thumb = f'assets/{asset_id}.thumb.jpg'
    image.thumbnail((360, 360))
    image.convert('RGB').save(store.file(project['id'], thumb), 'JPEG', quality=85)
    asset = dict(id=asset_id, name=name, kind=kind, handle=handle, description=str(description)[:2000],
                 file=file, thumbnail=thumb, created_at=now())
    if existing:
        existing.update({**asset, 'created_at': existing.get('created_at', asset['created_at'])})
        asset = existing
    else:
        project.setdefault('assets', []).append(asset)
    unique_names(project)
    store.save(project)
    return asset


def sync_asset_studies(store, project):
    """Library entries and asset studies are two views of the same asset."""
    changed = False
    assets = project.setdefault('assets', [])
    first_run = project.get('asset_studies_linked') != 1
    if first_run:
        backup = store.file(project['id'], 'before-asset-linking.json')
        if not backup.exists():
            write_json(backup, project)
    if first_run or any(not any(s.get('asset_id') == a['id'] for s in project.get('shots', [])) for a in assets):
        for asset in list(assets):
            if not first_run and any(s.get('asset_id') == asset['id'] for s in project.get('shots', [])):
                continue
            studies = source_studies(store, project, asset) if asset.get('file') or asset.get('source_shot_id') else []
            study = studies[0] if studies else None
            if study is None and project.get('archived_shots'):
                archived = source_studies(store, {**project, 'shots': project['archived_shots']}, asset)
                if archived:
                    study = archived[0]
                    project['archived_shots'].remove(study)
                    project['shots'].append(study)
            if study is None:
                study = store.add_shot(project)
                draft_id = uuid.uuid4().hex
                study.update(mode='asset', title=asset['name'], prompt=asset.get('description', ''), asset_kind=asset['kind'], reference_ids=[])
                if asset.get('file'):
                    study['drafts'] = [dict(id=draft_id, number=1, status='succeeded', file=asset['file'],
                                           settings={k: study[k] for k in ('prompt', 'ratio', 'steps', 'seed')}, full_prompt=study['prompt'])]
            # Repeated saves from one study keep one library entry and all takes.
            primary = next((a for a in assets if a['id'] == study.get('asset_id')), None)
            if primary and primary['id'] != asset['id']:
                for shot in project['shots']:
                    shot['reference_ids'] = list(dict.fromkeys(primary['id'] if x == asset['id'] else x for x in shot.get('reference_ids', [])))
                    shot['prompt'] = re.sub(r'(?<![\w@])@' + re.escape(asset['handle']) + r'\b', lambda _: '@' + primary['handle'], shot.get('prompt', ''))
                assets.remove(asset)
                project.setdefault('archived_assets', []).append({**asset, 'linked_into': primary['id']})
                for group in assets:
                    if 'members' in group:
                        group['members'] = list(dict.fromkeys(primary['id'] if x == asset['id'] else x for x in group['members']))
                continue
            study['asset_id'] = asset['id']
            asset['source_shot_id'] = study['id']
            changed = True
        project['asset_studies_linked'] = 1
        changed = True
    for study in project.get('shots', []):
        if study.get('mode') != 'asset':
            continue
        asset = next((a for a in assets if a['id'] == study.get('asset_id')), None)
        if asset is None:
            # A metadata-only entry exists even before the first image is ready.
            slug = unicodedata.normalize('NFKD', study['title']).encode('ascii', 'ignore').decode().lower()
            slug = re.sub(r'[^a-z0-9]+', '_', slug).strip('_')[:40] or 'asset'
            handle, suffix = slug, 2
            used = {a['handle'] for a in assets + project.get('archived_assets', [])}
            while handle in used:
                handle = f'{slug}_{suffix}'
                suffix += 1
            asset = dict(id=uuid.uuid4().hex, name=study['title'], handle=handle,
                         kind=study.get('asset_kind', 'character'), description='', source_shot_id=study['id'], created_at=now(), file=None, thumbnail='')
            assets.append(asset)
            study['asset_id'] = asset['id']
            changed = True
        ready = [d for d in study['drafts'] if d['status'] == 'succeeded' and store.file(project['id'], d['file']).exists()]
        if not asset.get('file') and ready:
            draft = ready[-1]
            asset.update(file=draft['file'], thumbnail=draft['file'], source_draft_id=draft['id'])
            changed = True
        count = len(ready)
        if asset.get('take_count') != count or asset.get('kind') != study.get('asset_kind', 'character'):
            asset.update(take_count=count, kind=study.get('asset_kind', 'character'))
            changed = True
        if asset.get('source_shot_id') != study['id']:
            asset['source_shot_id'] = study['id']
            changed = True
    unique_names(project)
    for study in project.get('shots', []):
        asset = next((a for a in assets if a['id'] == study.get('asset_id')), None)
        if study.get('mode') == 'asset' and asset and study['title'] != asset['name']:
            study['title'] = asset['name']
            changed = True
    if changed:
        store.save(project)
    return project


def fork_asset_study(store, project, study, asset, selected):
    """Save As keeps completed history but never duplicates queued jobs."""
    fork = store.add_shot(project)
    new_id = fork['id']
    fork.update(copy.deepcopy(study))
    fork.update(id=new_id, title=asset['name'], asset_id=asset['id'], mode='asset', approved=None, asset_kind=asset['kind'])
    fork['drafts'] = []
    chosen_id = None
    for original in study['drafts']:
        if original['status'] != 'succeeded':
            continue
        draft = copy.deepcopy(original)
        draft.update(id=uuid.uuid4().hex, number=len(fork['drafts']) + 1)
        fork['drafts'].append(draft)
        if original['id'] == selected['id']:
            chosen_id = draft['id']
    fork.update(copy.deepcopy({key: value for key, value in selected.get('settings', {}).items()
                               if key not in ('id', 'title', 'asset_id', 'asset_kind', 'drafts', 'mode', 'references')}))
    asset.update(source_shot_id=new_id, source_draft_id=chosen_id)
    store.save(project)
    return fork


def edit_reference(project, source, kind):
    studies = project.get('shots', []) + project.get('archived_shots', [])
    study = next((s for s in studies if s['id'] == source['shot_id']), None)
    draft = next((d for d in study.get('drafts', []) if d['id'] == source['draft_id'] and d['status'] == 'succeeded'), None) if study else None
    if not draft:
        raise ValueError('Choose a completed image to edit.')
    return dict(id='edit_' + draft['id'], name='Selected image', handle='edit_source', kind=kind, editing_source=True,
                file=draft['file'], thumbnail=draft['file'], description='Image to edit. Preserve everything except the requested changes.')


def resolve_references(project, settings):
    assets = project.get('assets', [])
    selected = settings.get('reference_ids', [])
    if not isinstance(selected, list) or not all(isinstance(x, str) for x in selected):
        raise ValueError('Invalid asset references.')
    by_id = {a['id']: a for a in assets}
    if any(x not in by_id for x in selected):
        raise ValueError('A selected asset is no longer in this project.')
    mention_text = bind_media_mentions(settings['prompt'], settings) if settings.get('mode') == 'video' else settings['prompt']
    handles = re.findall(r'(?<![\w@])@([a-zA-Z0-9_]+)', mention_text)
    by_handle = {a['handle']: a for a in assets}
    missing = [h for h in handles if h not in by_handle]
    if missing and settings.get('mode') != 'video':
        raise ValueError('Asset mention not found: @' + missing[0])
    ids = list(dict.fromkeys(selected + [by_handle[h]['id'] for h in handles if h in by_handle]))
    expanded = []
    for asset_id in ids:
        asset = by_id[asset_id]
        if asset.get('members') == []:
            raise ValueError('This reference group is empty. Choose another asset.')
        for member in asset.get('members', [asset_id]):
            if member not in by_id:
                raise ValueError('A reference group contains a removed asset. Recreate the group.')
            if member not in [a['id'] for a in expanded]:
                if not by_id[member].get('file'):
                    raise ValueError('Generate or import an image for @' + by_id[member]['handle'] + ' before using it as a reference.')
                expanded.append(dict(by_id[member]))
    if len(expanded) > MAX_REFERENCES:
        raise ValueError('Use up to 10 reference images.')
    for asset in expanded:
        asset['group_handles'] = list(dict.fromkeys([asset['handle']] + [a['handle'] for a in assets if asset['id'] in a.get('members', []) and a['id'] in ids]))
    return expanded


def storyboard_reference_direction(settings):
    if settings.get('mode', 'storyboard') != 'storyboard' or settings.get('edit_source'):
        return ''
    characters, seen = [], set()
    references = settings.get('references', [])
    for index, ref in enumerate(references):
        identity = ref.get('id', ref.get('handle', index))
        if ref.get('kind') == 'character' and not ref.get('editing_source') and identity not in seen:
            characters.append(f'<image{index+1}>')
            seen.add(identity)
    if len(characters) < 2:
        return ''
    return (f'Include all {len(characters)} referenced characters from ' + ', '.join(characters) +
            ' together in the same scene as separate, distinct figures. Preserve each identity, clothing and unusual proportions; '
            'do not merge them or omit one. Compose the selected framing so every requested character remains identifiable. '
            'Keep bodies and solid objects spatially coherent, with natural occlusion rather than intersecting surfaces. '
            'Character reference studio backgrounds are not the scene background; use the requested setting.')


def reference_prompt(prompt, references, workflow_id):
    cues, bindings = [], {}
    roles = {'character': 'character identity and clothing', 'prop': 'object design', 'location': 'setting and architecture'}
    for i, ref in enumerate(references):
        label = f'<ref_image_{i}>' if workflow_id == 'flux3-klein' else f'<image{i+1}>' if workflow_id == 'qwen21' else f'Image {i+1}'
        for handle in ref.get('group_handles', [ref['handle']]):
            bindings.setdefault(handle, []).append(label)
        cues.append(f"For {label}: {ref['reference_instruction']}" if ref.get('reference_instruction') else f'Use {label} as the image to edit.' if ref.get('editing_source') else f"Use {label} for {roles[ref['kind']]}.")
    # Bind once after all photos are numbered, so one @asset can reference many photos.
    prompt = re.sub(r'(?<![\w@])@([a-zA-Z0-9_]+)',
                    lambda match: ' and '.join(bindings[match[1]]) if match[1] in bindings else match[0], prompt)
    preserve = 'Preserve reference identities, designs and rendering medium unless explicitly changed.'
    if any(ref.get('reference_instruction') for ref in references):
        preserve = 'Preserve character identity only from references assigned an identity role. For role-limited photos, copy only the requested feature; do not copy the clothing wearer or unrelated content. Preserve the requested rendering medium.'
    return ' '.join([prompt.strip(), *cues, preserve]) if cues else prompt


def merge_assets(store, project, ids):
    """Legacy group copy support; no longer exposed as a library action."""
    by_id = {a['id']: a for a in project.get('assets', [])}
    if not isinstance(ids, list) or not all(isinstance(x, str) for x in ids) or len(set(ids)) < 2 or any(x not in by_id for x in ids):
        raise ValueError('Choose at least two assets from this project.')
    members = list(dict.fromkeys(m for x in ids for m in by_id[x].get('members', [x])))
    if len(members) > MAX_REFERENCES:
        raise ValueError('A group supports up to 10 reference images.')
    first = by_id[members[0]]
    group = add_asset(store, project, store.file(project['id'], first['file']).read_bytes(),
                      ' + '.join(by_id[x]['name'] for x in ids)[:120], first['kind'], 'Reference group: images attached separately.')
    group['members'] = members
    store.save(project)
    return group


def rename_asset(store, project, asset_id, value):
    asset = next((a for a in project.get('assets', []) if a['id'] == asset_id), None)
    if not asset:
        raise ValueError('Asset not found.')
    if not isinstance(value, str) or len(value) > 120:
        raise ValueError('Choose an asset handle up to 40 characters.')
    handle = unicodedata.normalize('NFKD', value.strip().lstrip('@')).encode('ascii', 'ignore').decode().lower()
    handle = re.sub(r'[^a-z0-9_]+', '_', handle).strip('_')
    if not handle or len(handle) > 40:
        raise ValueError('Use 1–40 letters, numbers or underscores for the @handle.')
    if any(a['id'] != asset_id and a['handle'].casefold() == handle for a in project.get('assets', [])):
        raise ValueError('That @handle already exists. Choose another one.')
    studies = source_studies(store, project, asset)
    old = asset['handle']
    asset['handle'] = handle
    asset['name'] = handle
    for shot in project.get('shots', []):
        shot['prompt'] = re.sub(r'(?<![\w@])@' + re.escape(old) + r'\b', lambda _: '@' + handle, shot.get('prompt', ''))
    for study in studies:
        study['title'] = handle
    unique_names(project)
    store.save(project)
    return asset


def source_studies(store, project, asset):
    if asset.get('members') is not None:
        return []
    if asset.get('source_shot_id'):
        return [s for s in project.get('shots', []) if s['id'] == asset['source_shot_id'] and s.get('mode') == 'asset']
    # Older assets predate source metadata: compare decoded pixels, not names.
    def fingerprint(file):
        try:
            with Image.open(store.file(project['id'], file)) as image:
                image = ImageOps.exif_transpose(image)
                image.thumbnail((4096, 4096))
                image = image.convert('RGBA' if 'A' in image.getbands() else 'RGB')
                return image.size, image.mode, hashlib.sha256(image.tobytes()).digest()
        except (OSError, ValueError):
            return None
    target = fingerprint(asset['file'])
    if not target:
        return []
    return [s for s in project.get('shots', []) if s.get('mode') == 'asset' and any(
        d.get('status') == 'succeeded' and d.get('file') and fingerprint(d['file']) == target for d in s.get('drafts', []))]


def archive_asset_studies(store, project, asset):
    studies = source_studies(store, project, asset)
    active = {'queued', 'submitting', 'running', 'pending', 'downloading'}
    if any(d['status'] in active for s in studies for d in s.get('drafts', [])):
        raise ValueError('Wait for this asset study to finish generating before deleting it.')
    for study in studies:
        project['shots'].remove(study)
        project.setdefault('archived_shots', []).append(study)


def delete_asset(store, project, asset_id, *, save=True):
    asset = next((a for a in project.get('assets', []) if a['id'] == asset_id), None)
    if not asset:
        raise ValueError('Asset not found.')
    archive_asset_studies(store, project, asset)
    project['assets'].remove(asset)
    project.setdefault('archived_assets', []).append(asset)
    for group in project['assets']:
        if 'members' in group:
            group['members'] = [x for x in group['members'] if x != asset_id]
    for shot in project.get('shots', []):
        settings = shot
        settings['reference_ids'] = [x for x in settings.get('reference_ids', []) if x != asset_id]
        settings['prompt'] = re.sub(r'(?<![\w@])@' + re.escape(asset['handle']) + r'\b', asset['name'], settings.get('prompt', ''))
    if save:
        store.save(project)
