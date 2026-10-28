"""Build native bundles on their target OS; stage only distributable application files."""
import argparse,hashlib,importlib.metadata as metadata,json,os,platform,shutil,subprocess,sys,tempfile,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from openframe.version import VERSION
OUTPUT=ROOT/'release'/VERSION
STAGE=ROOT/'.runtime/package-stage'

PUBLIC_DOCS=['comfy-connection.md','model-downloads.md','model-setup.md','mcp.md','video-workspace.md','image-direction.md','asset-library.md','editing-prompts.md','competition-rules.md','release-readiness.md','windows-signing.md','publication-audit.md']

def sign_windows(executable,required=False,verify_only=False):
    thumbprint=os.environ.get('DIRECTORSCUT_SIGNING_THUMBPRINT','').strip()
    if not thumbprint and not verify_only:
        if required:raise RuntimeError('A trusted Windows signing identity is required; configure DIRECTORSCUT_SIGNING_THUMBPRINT first.')
        print('Windows EXE is unsigned: no signing identity configured.')
        return
    command=['powershell.exe','-NoProfile','-NonInteractive','-File',str(ROOT/'tools/sign_windows.ps1'),'-File',str(executable)]
    if verify_only:command+=['-VerifyOnly']
    else:command+=['-CertificateThumbprint',thumbprint]
    subprocess.run(command,cwd=ROOT,check=True)
def dependency_notices():
    from packaging.requirements import Requirement
    pending=['aiohttp','comfy-sdk','comfy-api-proxy','Pillow','psutil'];seen=set();sections=[]
    while pending:
        name=pending.pop();dist=metadata.distribution(name);key=dist.metadata['Name'].lower().replace('_','-')
        if key in seen:continue
        seen.add(key);parts=[dist.metadata['Name']+' '+dist.version,dist.metadata.get('License-Expression') or dist.metadata.get('License','See license text below.')]
        for item in dist.files or []:
            if '.dist-info/' in str(item).replace('\\','/') and any(x in item.name.lower() for x in ('license','copying','notice')):
                path=dist.locate_file(item)
                if path.is_file():parts.append(path.read_text(encoding='utf-8',errors='replace'))
        sections.append('\n\n'.join(parts))
        for text in dist.requires or []:
            req=Requirement(text)
            if not req.marker or req.marker.evaluate({'extra':''}):pending.append(req.name)
    sections.append('PyInstaller bootloader: GPL with a distribution exception for bundled applications.\nhttps://pyinstaller.org/en/stable/license.html')
    return '\n\n'.join(sections)

def stage():
    STAGE.mkdir(parents=True,exist_ok=True)
    # No recursive deletion: reuse only this explicit staging folder and overwrite its known files.
    for name in ['LICENSE','THIRD_PARTY_NOTICES.md']:
        shutil.copy2(ROOT/name,STAGE/name)
    (STAGE/'DEPENDENCY_NOTICES.txt').write_text(dependency_notices(),encoding='utf-8')
    index=json.loads((ROOT/'web/assets/previews/index.json').read_text(encoding='utf-8'))
    active={url.split('?',1)[0].removeprefix('/assets/previews/') for values in index.values() for url in values.values()}
    selected=[]
    for path in (ROOT/'web').rglob('*'):
        if not path.is_file():continue
        relative=path.relative_to(ROOT/'web');parts=relative.parts
        if 'commercial' in parts or path.suffix.lower() in ('.mp4','.wav','.mp3'):continue
        if parts[:2]==('assets','previews'):
            local=Path(*parts[2:]).as_posix()
            if local!='index.json' and local not in active:continue
        if path.name.endswith('-prompt.txt'):continue
        if relative.as_posix() in ('assets/branding/directors-cut-profile-glass.png','assets/branding/directors-cut-icon-only.png','assets/branding/Logo Pre - Realista.png'):continue
        target=STAGE/'web'/relative;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,target);selected.append(target)
    # API graphs only: no original UI workflow archives, private media or machine state.
    catalogs=json.loads((ROOT/'workflows/catalog.json').read_text(encoding='utf-8'))
    for item in catalogs:
        source=ROOT/'workflows'/item['graph'];target=STAGE/'workflows'/item['graph'];target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target)
    (STAGE/'workflows/catalog.json').write_text(json.dumps(catalogs,indent=2),encoding='utf-8')
    for path in (ROOT/'workflows/video').iterdir():
        if path.name.endswith('.api.json') or path.suffix=='.patch':
            target=STAGE/'workflows/video'/path.name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,target)
    for path in (ROOT/'docs/prompt-guides').iterdir():
        if not path.is_file():continue
        target=STAGE/'docs/prompt-guides'/path.name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,target)
    (STAGE/'openframe').mkdir(exist_ok=True);shutil.copy2(ROOT/'openframe/model_download_catalog.json',STAGE/'openframe/model_download_catalog.json')
    shutil.copy2(ROOT/'openframe/node_catalog.json',STAGE/'openframe/node_catalog.json')
    # Generate platform icons from the existing approved PNG; no new image generation.
    from PIL import Image
    with Image.open(ROOT/'web/assets/branding/directors-cut-icon-v1.png') as image:
        image.convert('RGBA').save(STAGE/'app.ico',sizes=[(16,16),(32,32),(48,48),(64,64),(128,128),(256,256)])
        image.convert('RGBA').save(STAGE/'app.icns')
    return active

def source_archive():
    target=OUTPUT/f'DirectorsCut-{VERSION}-source.zip';files=[]
    for folder in ['openframe','tools']:
        files.extend(p for p in (ROOT/folder).rglob('*.py') if '__pycache__' not in p.parts)
    with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED) as archive:
        archive.write(ROOT/'tools/sign_windows.ps1','tools/sign_windows.ps1')
        for path in files:
            if path.is_relative_to(ROOT/'tools') and path.name not in ['build_release.py','smoke_release.py','mcp_config.py','update_prompt_guides.py']:continue
            archive.write(path,path.relative_to(ROOT))
        for path in STAGE.rglob('*'):
            if path.is_file() and path.name not in ('app.ico','app.icns'):archive.write(path,path.relative_to(STAGE))
        for name in ['app_entry.py','run.py',"Start Director's Cut.bat","Start Director's Cut MCP.bat",'directors_cut_mcp.py','requirements.txt','requirements-mcp.txt','requirements-build.txt','setup.bat','setup.sh','start.sh','README.md','LICENSE','THIRD_PARTY_NOTICES.md']:
            if name not in ('LICENSE','THIRD_PARTY_NOTICES.md'):archive.write(ROOT/name,name)
        for name in PUBLIC_DOCS:
            archive.write(ROOT/'docs'/name,'docs/'+name)
        for name in ['directors-cut-banner.png','directors-cut-assets.png','directors-cut-video.png']:
            archive.write(ROOT/'docs/images'/name,'docs/images/'+name)
        for name in ['test_core.py','test_engine_connection.py','test_model_downloads.py','test_selflift_setup.py','test_release.py','test_windows_signing.py']:
            path=ROOT/'tests'/name
            if path.exists():archive.write(path,'tests/'+name)
        for path in (ROOT/'packaging').glob('*'):
            if path.is_file():archive.write(path,'packaging/'+path.name)
        for path in (ROOT/'.github/workflows').glob('*.yml'):archive.write(path,'.github/workflows/'+path.name)
    return target

def checksums():
    values=[]
    for path in sorted(OUTPUT.iterdir()):
        if path.is_file() and path.name!='SHA256SUMS.txt':values.append(hashlib.sha256(path.read_bytes()).hexdigest()+'  '+path.name)
    (OUTPUT/'SHA256SUMS.txt').write_text('\n'.join(values)+'\n',encoding='utf-8')

def windows_archive():
    executables=list(OUTPUT.glob('*-windows-*.exe'))
    if not executables:return
    if len(executables)!=1:raise RuntimeError('Choose one Windows artifact before finalizing the archive.')
    executable=executables[0];target=executable.with_suffix('.zip')
    with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED) as archive:
        archive.write(executable,executable.name)
        archive.write(ROOT/'packaging/QUICKSTART.md','START-HERE.md')
        archive.write(ROOT/'packaging/RELEASE-NOTES.md','RELEASE-NOTES.md')
        for name in ['LICENSE','THIRD_PARTY_NOTICES.md']:archive.write(ROOT/name,name)
        archive.write(STAGE/'DEPENDENCY_NOTICES.txt','DEPENDENCY_NOTICES.txt')

def main():
    global STAGE,OUTPUT
    parser=argparse.ArgumentParser();parser.add_argument('--source-only',action='store_true');parser.add_argument('--prepare-only',action='store_true');parser.add_argument('--require-windows-signing',action='store_true');parser.add_argument('--output-dir',type=Path);args=parser.parse_args()
    if args.output_dir:OUTPUT=args.output_dir.resolve()
    if args.require_windows_signing and platform.system()!='Windows':parser.error('--require-windows-signing is Windows-only.')
    OUTPUT.mkdir(parents=True,exist_ok=True);(ROOT/'.runtime').mkdir(exist_ok=True)
    STAGE=Path(tempfile.mkdtemp(prefix='package-stage-',dir=ROOT/'.runtime'));active=stage()
    if args.prepare_only:print('Staged',len(active),'active previews');return
    if not args.source_only:
        system=platform.system();arch=platform.machine().lower();arch='x64' if arch in ('amd64','x86_64') else arch
        name=f'DirectorsCut-{VERSION}-{system.lower()}-{arch}'
        command=[sys.executable,'-m','PyInstaller','--noconfirm','--name',name,'--distpath',str(OUTPUT),'--workpath',str(ROOT/'.runtime/pyinstaller-work'),'--specpath',str(ROOT/'.runtime')]
        command+=['--onedir','--windowed','--osx-bundle-identifier','org.directorscut.studio','--icon',str(STAGE/'app.icns')] if system=='Darwin' else ['--onefile']
        if system=='Windows':command+=['--windowed','--icon',str(STAGE/'app.ico')]
        for path in STAGE.iterdir():
            if path.name in ('app.ico','app.icns'):continue
            command+=['--add-data',str(path)+':'+(path.name if path.is_dir() else '.')]
        command+=['--collect-all','comfy_api_proxy','--collect-all','comfy_sdk','--copy-metadata','comfy-api-proxy','--copy-metadata','comfy-sdk','--hidden-import','uvicorn.logging','--hidden-import','uvicorn.loops.auto','--hidden-import','uvicorn.protocols.http.auto','--hidden-import','uvicorn.protocols.websockets.auto','--hidden-import','uvicorn.lifespan.on','--exclude-module','torch','--exclude-module','pytest','--exclude-module','IPython','--exclude-module','mcp',str(ROOT/'app_entry.py')]
        subprocess.run(command,cwd=ROOT,check=True)
        if system=='Windows':sign_windows(OUTPUT/(name+'.exe'),required=args.require_windows_signing)
        if system=='Darwin':
            app=OUTPUT/(name+'.app');subprocess.run(['ditto','-c','-k','--sequesterRsrc','--keepParent',str(app),str(OUTPUT/(name+'.zip'))],check=True)
    if args.source_only and args.require_windows_signing:
        sign_windows(OUTPUT/f'DirectorsCut-{VERSION}-windows-x64.exe',required=True,verify_only=True)
    source=source_archive();shutil.copy2(ROOT/'packaging/QUICKSTART.md',OUTPUT/'START-HERE.md');shutil.copy2(ROOT/'packaging/RELEASE-NOTES.md',OUTPUT/'RELEASE-NOTES.md');windows_archive();checksums()
    print('Release artifacts:',OUTPUT);print('Source:',source)
if __name__=='__main__':main()
