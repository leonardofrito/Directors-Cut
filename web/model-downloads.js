/* Shared, explicit model acquisition for the existing engine file selectors. */
(()=>{
 let catalog={models:[],unavailable:[]},jobs=[],loading=false;const active=new Set(['queued','downloading','verifying']);
 const basename=value=>String(value||'').replaceAll('\\','/').split('/').at(-1);
 const size=n=>n?`${(n/1e9).toFixed(n>=1e10?1:2)} GB`:'';
 const matching=(scope,role,format)=>catalog.models.filter(m=>(m.scope===scope||(scope==='video'&&['h3','omni'].includes(m.scope))||(scope==='shared'&&m.role==='enhancer'&&m.shared))&&m.role===role&&(!format||!['diffusion','encoder'].includes(role)||(m.filename.endsWith('.gguf')?'gguf':'standard')===format));
 const entry=(scope,role,file)=>matching(scope,role).find(m=>[m.filename,...(m.aliases||[])].includes(basename(file)));
 function options(scope,role,files,format){
  const result=files.filter(file=>!format||!['diffusion','encoder'].includes(role)||(file.endsWith('.gguf')?'gguf':'standard')===format).map(file=>({file,model:entry(scope,role,file),installed:true}));
  for(const m of matching(scope,role,format))if(!result.some(x=>x.model?.id===m.id))result.push({file:m.installed_file||m.filename,model:m,installed:m.installed});
  const rank=row=>row.model?.scope==='omni'||/fast[-_]?h3.*omni/i.test(row.file)?0:1;
  result.sort((a,b)=>rank(a)-rank(b)||Number(Boolean(a.model?.unofficial))-Number(Boolean(b.model?.unofficial))||a.file.localeCompare(b.file));
  return result.map(row=>{
   const m=row.model,unofficial=m?.unofficial||/fast[-_]?h3.*omni|w4a8/i.test(row.file);
   const sharedName=scope==='shared'&&/qwen3[._]5[_-]4b/i.test(row.file)?`Qwen3.5 4B · ${/int8/i.test(row.file)?'INT8':/w4a8/i.test(row.file)?'W4A8':/bf16/i.test(row.file)?'BF16':'Local weights'}`:null;
   const label=m?`${m.scope==='omni'?'Omni REF · ':''}${m.variant} · ${m.unofficial?'Unofficial':m.repo.startsWith('Comfy-Org/')?'Comfy':'Community'} · ${row.installed?'Installed':size(m.size)}`:sharedName?`${sharedName} · Installed`:`${row.file}${unofficial?' · Unofficial':''}`;
   const option=new Option(label,row.file);option.dataset.group=scope==='video'&&role==='diffusion'?(m?.scope==='omni'||/fast[-_]?h3.*omni/i.test(row.file)?'Omni REF · recommended · unofficial':'MiniMax H3 · Original'):m?.unofficial?'Community · unofficial':m?'Comfy':'Other installed files';option.title=m?`${m.filename}\n${m.repo}${m.note?'\n'+m.note:''}`:row.file;return option;
  });
 }
 function redraw(){if(typeof renderModels==='function'){renderModels();renderShared();window.DirectorDropdowns?.sync();}}
 const formats=new Map();
 function formatTabs(box,select,key){
  const all=[...select.options],current=select.value,initial=current?(current.endsWith('.gguf')?'gguf':'standard'):(formats.get(key)||'standard');
  const tabs=document.createElement('div');tabs.className='model-format-tabs';tabs.setAttribute('role','group');tabs.setAttribute('aria-label','Model format');
  function choose(format,notify){
   formats.set(key,format);const previous=select.value;
   const visible=all.filter(o=>!o.value.startsWith('unavailable:')&&(o.value.endsWith('.gguf')?'gguf':'standard')===format);
   select.replaceChildren(...visible);select.value=visible.some(o=>o.value===previous)?previous:visible.some(o=>o.value===current)?current:visible[0]?.value||'';select.disabled=!visible.length;
   tabs.querySelectorAll('button').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.format===format)));
   box.querySelector('.model-format-empty')?.remove();
   if(!visible.length){const p=document.createElement('p');p.className='control-help model-format-empty';p.textContent='No compatible '+(format==='gguf'?'GGUF':'Standard')+' files found. Refresh after installing a compatible loader/model.';box.append(p);}
   box._downloadUpdate?.();window.DirectorDropdowns?.sync();if(notify&&select.value)select.dispatchEvent(new Event('change'));
  }
  for(const [value,label] of [['standard','Standard'],['gguf','GGUF']]){const b=document.createElement('button');b.type='button';b.dataset.format=value;b.textContent=label;b.onclick=()=>choose(value,true);tabs.append(b);}
  select.before(tabs);choose(initial,false);
 }
 const sharedKey='directors-cut-shared-enhancer';
 function sharedValue(){try{return localStorage.getItem(sharedKey)??config?.video?.enhancer?.default??'';}catch{return '';}}
 function renderShared(){
  const select=document.getElementById('shared-enhancer-model');if(!select)return;
  const files=(config?.video?.enhancer?.files||[]),opts=options('shared','enhancer',files),previous=sharedValue();
  select.replaceChildren(new Option('Choose shared enhancer…',''),...opts);select.value=previous;
  const box=document.getElementById('shared-enhancer-download');box.replaceChildren();decorate(box,select,'shared','enhancer');
  document.getElementById('shared-enhancer-status').textContent='';
 }
 function setupShared(){
  const tabs=document.querySelector('#models-dialog .settings-tabs'),section=document.createElement('section');section.id='shared-enhancer-settings';section.hidden=true;section.setAttribute('role','tabpanel');section.setAttribute('aria-labelledby','settings-enhancer');section.innerHTML='<h3>Prompt enhancer</h3><label for="shared-enhancer-model">Model</label><select id="shared-enhancer-model"></select><div id="shared-enhancer-download" class="model-file"></div><p id="shared-enhancer-status" class="control-help"></p><button type="button" id="shared-enhancer-refresh">Refresh installed models</button><details class="model-source-links"><summary>Sources</summary><div id="shared-enhancer-links"></div></details>';
  document.getElementById('connection-settings').before(section);const tab=document.createElement('button');tab.type='button';tab.id='settings-enhancer';tab.setAttribute('role','tab');tab.setAttribute('aria-controls',section.id);tab.textContent='Prompt enhancer';tab.onclick=()=>{selectSettingsSection('enhancer');renderShared();};tabs.insertBefore(tab,document.getElementById('settings-connection'));
  document.querySelector('.enhancer-model-control').hidden=true;document.querySelector('.enhancer-model-control').previousElementSibling.hidden=true;
  document.getElementById('shared-enhancer-model').onchange=event=>{const file=event.target.value;try{localStorage.setItem(sharedKey,file);}catch{}document.dispatchEvent(new CustomEvent('shared-enhancer-change',{detail:file}));};
  document.getElementById('shared-enhancer-refresh').onclick=()=>safe(async()=>{config=await api('/config');await refresh();renderShared();});renderShared();
 }
 async function refresh(){
  if(loading)return;loading=true;
  try{catalog=await api('/models/catalog');jobs=catalog.jobs||[];redraw();}
  catch(error){document.querySelectorAll('.model-download-state').forEach(el=>el.textContent=error.message);}
  finally{loading=false;}
 }
 function unavailable(scope,role){return catalog.unavailable.filter(m=>m.scope===scope&&m.role===role).map(m=>{const o=new Option(`${m.variant} · ${m.unofficial?'Unofficial · ':''}Unavailable`,'unavailable:'+scope+':'+m.variant);o.disabled=true;o.title=m.note;return o;});}
 function decorate(box,select,scope,role){
  const actions=document.createElement('div');actions.className='model-download-actions';
  const primary=document.createElement('button');primary.type='button';primary.className='model-download-button';
  const cancel=document.createElement('button');cancel.type='button';cancel.className='subtle model-download-cancel';cancel.textContent='Pause';
  const state=document.createElement('span');state.className='model-download-state';state.setAttribute('role','status');
  const progress=document.createElement('progress');progress.max=1;
  const source=document.createElement('a');source.className='model-download-source';source.target='_blank';source.rel='noopener noreferrer';
  function update(){
   const m=entry(scope,role,select.value),job=m&&jobs.find(j=>j.id===m.id),installed=m&&(m.installed||job?.status==='installed');
   primary.hidden=!m||installed;primary.disabled=Boolean(m?.download_error||(job&&active.has(job.status)));primary.classList.toggle('primary',!installed);box.classList.toggle('model-download-missing',Boolean(m&&!installed));
   primary.innerHTML=(window.DirectorIcons?.download||'')+`<span>${job?.status==='paused'?'Resume download':job?.status==='failed'?'Retry download':'Download'}${m?' · '+size(m.size):''}</span>`;
   cancel.hidden=!job||!['queued','downloading'].includes(job.status);
   progress.hidden=!job||!active.has(job.status);progress.value=(job?.received||0)/(job?.total||1);
   state.textContent=installed?'Installed':job?.status==='verifying'?'Checking SHA-256…':job?.status==='queued'?'Waiting to download…':job?.status==='downloading'?`${Math.floor((job.received||0)/job.total*100)}% · ${size(job.received)} / ${size(job.total)}`:job?.error||m?.download_error||m?.note||'';
   source.hidden=!m;if(m){source.href=m.source;source.textContent=`${m.unofficial?'Unofficial · ':''}${m.repo} ↗`;}
  }
  primary.onclick=()=>safe(async()=>{const m=entry(scope,role,select.value);if(!m)return;const result=await api('/models/downloads','POST',{id:m.id});jobs=jobs.filter(x=>x.id!==m.id);jobs.push(result);update();});
  cancel.onclick=()=>safe(async()=>{const m=entry(scope,role,select.value);await api('/models/downloads/'+encodeURIComponent(m.id)+'/cancel','POST',{});await poll();});
  select.addEventListener('change',update);actions.append(primary,cancel,state);box.append(actions,progress);
  const linkBox=document.getElementById(scope==='qwen21'?'model-links':scope==='video'?'video-model-links':'shared-enhancer-links');
  if(linkBox){const key=scope+'-'+role;linkBox.querySelector(`[data-source-role="${key}"]`)?.remove();source.dataset.sourceRole=key;linkBox.append(source);}box._downloadUpdate=update;update();
 }
 async function poll(){
  if(!document.getElementById('models-dialog')?.open&&!jobs.some(j=>active.has(j.status)))return;
  try{
   const next=(await api('/models/downloads')).jobs;
   const installed=next.some(j=>j.status==='installed'&&jobs.find(old=>old.id===j.id)?.status!=='installed');jobs=next;
   document.querySelectorAll('.model-file').forEach(box=>box._downloadUpdate?.());
   if(installed){config=await api('/config');populateWorkflows();await refresh();toast('Model installed. Ready to select.');}
  }catch{}
 }
 window.DirectorModelDownloads={options,decorate,unavailable,formatTabs,sharedValue,renderShared,preset:file=>catalog.models.find(m=>m.role==='diffusion'&&m.filename===basename(file))?.scope==='omni'?'fast-omni':null,refresh};
 document.addEventListener('DOMContentLoaded',()=>{setupShared();refresh();for(const id of ['refresh-models','video-refresh-models'])document.getElementById(id)?.addEventListener('click',refresh);setInterval(poll,2000);});
})();
