"""Resolve friendly media mentions only when their actual REF2VA slot is attached."""
import re

MEDIA_MENTION = re.compile(r'(?<![\w@])@[ \t]*(video|vídeo|audio|áudio)(?:[ _]*1)?(?![\w]|[ _]*\d)', re.IGNORECASE)


def bind_media_mentions(prompt, settings):
    def replace(match):
        video = match[1].lower() in ('video', 'vídeo')
        attached = (settings.get('motion_reference') or settings.get('motion_reference_id')) if video else (settings.get('audio_reference') or settings.get('audio_reference_id'))
        return ('<Video 1>' if video else '<Audio 1>') if attached else match[0]
    return MEDIA_MENTION.sub(replace, prompt)
