"""Uploaded project covers are presentation metadata, never generation inputs."""
import asyncio
import io
import uuid

from PIL import Image, ImageOps, UnidentifiedImageError

from .assets import MAX_UPLOAD


def cover_bytes(content):
    try:
        with Image.open(io.BytesIO(content)) as original:
            if original.format not in ('PNG', 'JPEG', 'WEBP') or original.width*original.height>40_000_000:
                raise ValueError('Choose a PNG, JPEG or WebP up to 40 megapixels.')
            image=ImageOps.exif_transpose(original).convert('RGBA')
            image=ImageOps.fit(image,(960,640),method=Image.Resampling.LANCZOS)
            background=Image.new('RGB',image.size,(13,13,13))
            background.paste(image,mask=image.getchannel('A'))
            output=io.BytesIO();background.save(output,format='JPEG',quality=88,optimize=True)
            return output.getvalue()
    except (UnidentifiedImageError,OSError,Image.DecompressionBombError) as exc:
        raise ValueError('Choose a valid PNG, JPEG or WebP cover.') from exc


async def attach(request,store):
    pid=request.match_info['project'];store.load(pid)
    reader=await request.multipart();content=bytearray()
    async for part in reader:
        if part.name!='image':continue
        while chunk:=await part.read_chunk():
            content.extend(chunk)
            if len(content)>MAX_UPLOAD:raise ValueError('Choose an image up to 32 MB.')
    if not content:raise ValueError('Choose a cover image.')
    encoded=await asyncio.to_thread(cover_bytes,content)
    # Re-read after image processing, preserving concurrent project/asset updates.
    project=store.load(pid)
    path=store.file(pid,'cover.jpg');temporary=path.with_suffix('.jpg.tmp')
    temporary.write_bytes(encoded);temporary.replace(path)
    project.update(cover_image='cover.jpg',cover_revision=uuid.uuid4().hex)
    store.save(project)
    return project
