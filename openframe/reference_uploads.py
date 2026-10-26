"""Images attached to an asset study without creating library assets."""
import io
import uuid
import asyncio
import ipaddress
import socket
from urllib.parse import unquote

import aiohttp
from yarl import URL

from PIL import Image, ImageOps, UnidentifiedImageError

from .assets import MAX_UPLOAD

ROLES = {'reference':'Use this image as a visual reference, following the written request for what to preserve or change.',
         'wardrobe':'Use only the clothing design, fabric, colors and accessories; do not copy the wearer or background.',
         'identity':'Use the character identity and facial appearance; follow the requested clothing and background.',
         'hair':'Use only the hairstyle and hair color, not the face, clothes or background.',
         'style':'Use the visual rendering style and surface treatment, not the depicted identity or composition.',
         'background':'Use the environment design only, not any people in this image.',
         'prop':'Use only the referenced object design.'}


def public_address(address):
    ip = ipaddress.ip_address(address)
    if not ip.is_global or ip.is_multicast or (isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped is not None):
        raise ValueError('Use a public internet image address.')


class PublicImageResolver(aiohttp.abc.AbstractResolver):
    """Check the actual DNS answers used by the connector, including redirects."""
    def __init__(self):
        self.delegate = aiohttp.resolver.DefaultResolver()

    async def resolve(self, host, port=0, family=socket.AF_INET):
        records = await self.delegate.resolve(host, port, family)
        for record in records:
            public_address(record['host'])
        return records

    async def close(self):
        await self.delegate.close()


def image_url(value):
    if not isinstance(value, str) or len(value)>8192:
        raise ValueError('Choose a valid internet image address.')
    url = URL(value)
    if url.scheme not in ('http', 'https') or not url.host or url.user is not None or url.port not in (80,443):
        raise ValueError('Use an HTTP or HTTPS image address.')
    try:
        ipaddress.ip_address(url.host)
    except ValueError:
        pass  # DNS names are checked by PublicImageResolver at connection time.
    else:
        public_address(url.host)
    return url.with_fragment(None)


async def download_image(value):
    url=image_url(value)
    resolver=PublicImageResolver()
    try:
        async with asyncio.timeout(30):
            connector=aiohttp.TCPConnector(resolver=resolver)
            async with aiohttp.ClientSession(connector=connector,timeout=aiohttp.ClientTimeout(total=30),cookie_jar=aiohttp.DummyCookieJar(),trust_env=False) as session:
                for _ in range(5):
                    async with session.get(url,allow_redirects=False,headers={'Accept':'image/*','User-Agent':'DirectorsCut/1.0'}) as response:
                        if response.status in (301,302,303,307,308):
                            location=response.headers.get('Location')
                            if not location:raise ValueError('The image link redirected without a destination.')
                            url=image_url(str(url.join(URL(location))))
                            continue
                        if response.status!=200:
                            raise ValueError('This site blocked the image download. Copy the image or save it first.')
                        if response.content_length and response.content_length>MAX_UPLOAD:
                            raise ValueError('Choose an image up to 32 MB.')
                        content=bytearray()
                        async for chunk in response.content.iter_chunked(65536):
                            content.extend(chunk)
                            if len(content)>MAX_UPLOAD:raise ValueError('Choose an image up to 32 MB.')
                        return bytes(content),unquote(url.path.rsplit('/',1)[-1])[:120] or 'Web reference'
                raise ValueError('The image link redirected too many times.')
    except (aiohttp.ClientError,TimeoutError,OSError) as exc:
        raise ValueError('Could not download this image. Copy the image or save it first.') from exc
    finally:
        await resolver.close()


async def attach_image(request, store):
    project=store.load(request.match_info['project']);shot=store.shot(project,request.match_info['shot'])
    if shot.get('mode')!='asset':
        raise ValueError('Direct image uploads belong to asset creation.')
    content=bytearray();role='reference';name='Reference'
    if request.content_type=='application/json':
        data=await request.json()
        if not isinstance(data,dict):raise ValueError('Choose an image address.')
        role=data.get('role','reference')
        if not isinstance(role,str) or role not in ROLES:raise ValueError('Choose a reference role.')
        if len(shot.get('upload_reference_ids',[]))+len(shot.get('reference_ids',[]))>=10:raise ValueError('Use up to 10 reference images.')
        content,name=await download_image(data.get('url'))
    else:
        reader=await request.multipart()
        async for part in reader:
            if part.name=='image':
                name=(part.filename or name)[:120]
                while chunk:=await part.read_chunk():
                    content.extend(chunk)
                    if len(content)>MAX_UPLOAD:raise ValueError('Choose an image up to 32 MB.')
            elif part.name=='role':
                value=await part.read();role=value.decode() if len(value)<80 else ''
    if not isinstance(role,str) or role not in ROLES:raise ValueError('Choose a reference role.')
    if not content:raise ValueError('Choose an image.')
    try:
        with Image.open(io.BytesIO(content)) as original:
            if original.format not in ('PNG','JPEG','WEBP') or original.width*original.height>40_000_000:
                raise ValueError('Choose a PNG, JPEG or WebP up to 40 megapixels.')
            image=ImageOps.exif_transpose(original);image.thumbnail((4096,4096));image=image.convert('RGB')
    except (UnidentifiedImageError,OSError,Image.DecompressionBombError) as exc:
        raise ValueError('Choose a valid reference image.') from exc
    # Re-read after upload, so a concurrent save does not lose other project changes.
    project=store.load(project['id']);shot=store.shot(project,shot['id'])
    ids=shot.get('upload_reference_ids',[])
    if len(ids)+len(shot.get('reference_ids',[]))>=10:raise ValueError('Use up to 10 reference images.')
    ident=uuid.uuid4().hex;file=f'references/{ident}.png';path=store.file(project['id'],file);path.parent.mkdir(parents=True,exist_ok=True);image.save(path,'PNG')
    ref=dict(id=ident,file=file,thumbnail=file,name=name,handle='upload_'+ident,kind='prop',reference_role=role,reference_instruction=ROLES[role])
    project.setdefault('reference_images',[]).append(ref);shot['upload_reference_ids']=[*ids,ident];store.save(project)
    return project


def resolve(project,settings):
    ids=settings.get('upload_reference_ids',[]);by_id={ref['id']:ref for ref in project.get('reference_images',[])}
    if any(ident not in by_id for ident in ids):raise ValueError('An uploaded reference is no longer available.')
    return [dict(by_id[ident]) for ident in ids]
