"""Download public prompt reference documents as inert data, never execute them."""
import hashlib
import json
from pathlib import Path
from urllib.request import Request, urlopen

ROOT=Path(__file__).resolve().parent.parent/'docs/prompt-guides'
SOURCES={
    'h3-ref2va.md':'https://huggingface.co/MiniMaxAI/MiniMax-H3/raw/main/docs/VIDEO_PROMPT_WRITING_GUIDE_ref_en.md',
    'qwen-overview.md':'https://raw.githubusercontent.com/kjranyone/qwen-image-2.1-prompt-guide/main/skills/qwen-image-prompt-en/SKILL.md',
    'qwen-image.md':'https://raw.githubusercontent.com/kjranyone/qwen-image-2.1-prompt-guide/main/skills/qwen-image-prompt-en/references/text-to-image.md',
    'qwen-image-editing.md':'https://raw.githubusercontent.com/kjranyone/qwen-image-2.1-prompt-guide/main/skills/qwen-image-prompt-en/references/image-editing.md',
    'qwen-examples.md':'https://raw.githubusercontent.com/kjranyone/qwen-image-2.1-prompt-guide/main/skills/qwen-image-prompt-en/references/examples.md',
    'qwen-text-rendering.md':'https://raw.githubusercontent.com/kjranyone/qwen-image-2.1-prompt-guide/main/skills/qwen-image-prompt-en/references/text-rendering.md',
    'qwen-capabilities.md':'https://raw.githubusercontent.com/kjranyone/qwen-image-2.1-prompt-guide/main/skills/qwen-image-prompt-en/references/capabilities.md',
    'QWEN-GUIDE-LICENSE.txt':'https://raw.githubusercontent.com/kjranyone/qwen-image-2.1-prompt-guide/main/LICENSE',
}


def main():
    ROOT.mkdir(parents=True,exist_ok=True)
    manifest={}
    for name,url in SOURCES.items():
        with urlopen(Request(url,headers={'User-Agent':'Directors-Cut-guide-downloader'}),timeout=30) as response:
            content=response.read(2_000_001)
        if len(content)>2_000_000 or not content.strip():raise ValueError('Unexpected guide size: '+name)
        content.decode('utf-8')
        temporary=ROOT/(name+'.tmp');temporary.write_bytes(content);temporary.replace(ROOT/name)
        manifest[name]=dict(source=url,sha256=hashlib.sha256(content).hexdigest())
        print('Saved '+name)
    (ROOT/'sources.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')


if __name__=='__main__':main()
