/* Shared, explicit model acquisition for the existing engine file selectors. */
(()=>{
 let catalog={models:[],unavailable:[]},jobs=[],loading=false;const active=new Set(['queued','downloading','verifying']);
 const basename=value=>String(value||'').replaceAll('\\','/').split('/').at(-1);
 const size=n=>n?`${(n/1e9).toFixed(n>=1e10?1:2)} GB`:'';
 const matching=(scope,role,format)=>catalog.models.filter(m=>(m.scope===scope||(scope==='video'&&['h3','omni'].includes(m.scope)))&&m.role===role&&(!format||role!=='diffusion'||(m.filename.endsWith('.gguf')?'gguf':'standard')===format));
 const entry=(scope,role,file)=>matching(scope,role).find(m=>[m.filename,...(m.aliases||[])].includes(basename(file)));
 function options(scope,role,files,format){
  const result=files.map(file=>({file,model:entry(scope,role,file),installed:true}));
  for(const m of matching(scope,role,format))if(!result.some(x=>x.model?.id===m.id))result.push({file:m.installed_file||m.filename,model:m,installed:m.installed});
  return result.map(row=>{
   const m=row.model,unofficial=m?.unofficial||/fast[-_]?h3.*omni|w4a8/i.test(row.file);
   const label=m?`${m.scope==='omni'?'Omni REF · ':''}${m.variant} · ${m.unofficial?'Unofficial':m.repo.startsWith('Comfy-Org/')?'Comfy':'Community'} · ${row.installed?'Installed':size(m.size)}`:`${row.file}${unofficial?' · Unofficial':''}`;
   const option=new Option(label,row.file);option.title=m?`${m.filename}\n${m.repo}${m.note?'\n'+m.note:''}`:row.file;return option;
  });
 }
 function redraw(){if(typeof renderModels==='function'){renderModels();window.DirectorDropdowns?.sync();}}
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
  select.addEventListener('change',update);actions.append(primary,cancel,state);box.append(actions,progress,source);box._downloadUpdate=update;update();
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
 window.DirectorModelDownloads={options,decorate,unavailable,preset:file=>catalog.models.find(m=>m.role==='diffusion'&&m.filename===basename(file))?.scope==='omni'?'fast-omni':null,refresh};
 document.addEventListener('DOMContentLoaded',()=>{refresh();for(const id of ['refresh-models','video-refresh-models'])document.getElementById(id)?.addEventListener('click',refresh);setInterval(poll,2000);});
})();
