(() => {
  let state={},uploading=false,choose=null,globalAssets=[],replaceIndex=-1,pendingSource=null,objectURL=null,mentionIndex=0;
  const el=id=>document.getElementById('swap-'+id);
  const source=()=>project?.swap_sources?.find(r=>r.id===state.swap_source_id);
  const active=()=>window.DirectorApps?.id==='second-take'&&DirectorVideo.active;
  function models(saved={}){
    const result={};for(const row of config?.video?.presets?.['fast-omni']?.loaders||[]){
      const preferred=row.node==='127'?row.options.find(n=>/w4a8/i.test(n)):row.node==='128'?row.options.find(n=>/int4/i.test(n)):null;
      result[row.node]=row.options.includes(saved[row.node])?saved[row.node]:preferred||row.default;
    }return result;
  }
  const modes=()=>config?.second_take?.modes||[
    {id:'motion',code:'M',label:'Motion Transfer',lora:'minimax_h3_motion_transfer_tara_v1.0_ref2va.safetensors'},
    {id:'character-1',code:'C1',label:'Character Swap 1',lora:'h3_character_swap_v1.5.safetensors'},
    {id:'character-2',code:'C2',label:'Character Swap 2',lora:'minimax_h3_character_swap_v1.1_ref2va_fro.safetensors'}];
  const currentMode=()=>modes().find(m=>m.id===state.swap_mode)||modes()[0];
  function modeChoices(menu){for(const row of modes()){const option=button(row.label,'generation-choice',()=>{state.swap_mode=row.id;document.getElementById('video-mode-value').textContent=row.code;document.getElementById('video-choose-mode').title=row.label;change();DirectorVideo.closeChoices();});option.setAttribute('aria-pressed',String(currentMode().id===row.id));menu.append(option);}}
  function load(s){state={swap_cuts_reviewed:Boolean(s.swap_cuts_reviewed),swap_cut_candidates:structuredClone(s.swap_cut_candidates||[]),swap_cut_review_start:s.swap_cut_review_start??null,swap_cut_review_end:s.swap_cut_review_end??null,swap_mode:s.swap_mode||modes().find(m=>m.id!=='motion'&&s.loras?.some(l=>l.name===m.lora))?.id||'motion',swap_source_id:s.swap_source_id||'',swap_full_duration:s.swap_full_duration!==false,swap_start:s.swap_start||0,swap_end:s.swap_end||5,
    reference_ids:(s.reference_ids||[]).filter((_,i)=>s.swap_roles?.[i]!=='background'),swap_roles:(s.swap_roles||((s.reference_ids||[]).map((_,i)=>i?'accessory':'character'))).filter(r=>r!=='background'),
    swap_ignored_people:[...(s.swap_ignored_people||[])],swap_analysis_id:'',swap_people_map:{},swap_neutralize:false,swap_direction_enabled:Boolean(s.swap_direction_enabled),swap_direction:s.swap_roles?.includes('background')||s.swap_manual_targets?.length?'':s.swap_direction||''};if(s.swap_roles?.includes('background')||s.swap_manual_targets?.length){state.swap_direction_enabled=false;const objects=new Set((s.swap_manual_targets||[]).map(t=>t.reference_id));state.reference_ids=state.reference_ids.filter(id=>!objects.has(id)||Object.values(state.swap_people_map).includes(id));state.swap_roles=state.reference_ids.map(()=> 'character');}}
  load({});
  function capture(base){return {...base,...state,studio_app:'second-take',prompt:'Character swap',prompt_enhancer:Boolean(base.prompt_enhancer),video_direction:{},motion_reference_id:'',audio_reference_id:'',output_audio_id:'',loras:[{name:currentMode().lora,enabled:true,strength:1}]};}
  const change=()=>DirectorVideo.swapChanged();
  function range(){const src=source();return {start:state.swap_full_duration?0:state.swap_start,end:state.swap_full_duration?(src?.duration||0):state.swap_end};}
  function ready(){const src=source(),r=range(),many=state.swap_roles.filter(r=>r==='character').length>1;
    return Boolean((config?.video?.loras?.files||[]).includes(currentMode().lora)&&document.getElementById('video-preset').value!=='hyperflow'&&src&&state.swap_roles.includes('character')&&!uploading&&r.end-r.start>=4-1e-6&&r.end-r.start<=30+1e-6&&r.end<=src.duration+1/24);}
  function render(){
    if(!active())return;
    renderAdapter();document.getElementById('video-mode-value').textContent=currentMode().code;document.getElementById('video-choose-mode').title=currentMode().label;
    const src=source(),assets=project?.assets||[];
    const root=el('source');root.setAttribute('role','button');root.tabIndex=0;root.setAttribute('aria-label','Choose source video');root.onkeydown=e=>{if(e.target===root&&['Enter',' '].includes(e.key)){e.preventDefault();safe(openSource);}};const stamp=JSON.stringify([project?.id,src?.id,src?.file]);
    const player=el('source-preview');player.muted=true;player.loop=true;player.autoplay=false;player.controls=false;
    if(root.dataset.stamp!==stamp){root.dataset.stamp=stamp;player.pause();
      if(src){player.src=fileURL(src.file);player.dataset.source=src.id;player.hidden=false;
        const name=document.createElement('span');name.className='swap-source-name';name.textContent=src.name;
        const remove=button('','swap-media-remove subtle',()=>{state.swap_source_id='';state.swap_analysis_id='';state.swap_people_map={};player.pause();change();});remove.innerHTML=DirectorIcons.close;remove.setAttribute('aria-label','Remove source');
        root.replaceChildren(player,name,remove);root.onclick=e=>{if(!e.target.closest('.swap-media-remove'))safe(openSource);};root.onpointerenter=()=>player.play().catch(()=>{});root.onpointerleave=()=>player.pause();
      }else{player.removeAttribute('src');player.hidden=true;const pick=button('','swap-media-pick',()=>safe(openSource));pick.dataset.empty='true';const icon=document.createElement('span');icon.innerHTML=DirectorIcons.plus;const label=document.createElement('span');label.textContent='Choose video';pick.append(icon,label);root.replaceChildren(player,pick);}
    }
    el('upload-status').textContent=uploading?'Importing clip…':src&&!validRange(range().start,range().end,src.duration)?'Choose a 4–30 second range.':'';
    const grid=el('assets');grid.style.setProperty('--swap-columns',String(Math.min(3,state.reference_ids.length+1)));const key=JSON.stringify([state.reference_ids,state.swap_roles,assets.map(a=>[a.id,a.thumbnail,a.handle])]);
    if(grid.dataset.stamp!==key){grid.dataset.stamp=key;const add=el('add-asset');add.innerHTML=DirectorIcons.plus;grid.replaceChildren(add,...state.reference_ids.map((id,i)=>{
      const item=assets.find(a=>a.id===id),card=document.createElement('div');card.className='swap-asset-card';
      const image=button('','swap-media-pick',()=>{if(item)openImageViewer(fileURL(item.file||item.thumbnail));});if(item){const photo=document.createElement('img');photo.src=fileURL(item.thumbnail||item.file);photo.alt='';const name=document.createElement('span');name.textContent='@'+item.handle;image.append(photo,name);}
      const remove=button('','swap-media-remove subtle',()=>{const removed=state.reference_ids[i],handle=project.assets.find(a=>a.id===removed)?.handle,tail=config.second_take?.prompt_tail;state.reference_ids.splice(i,1);state.swap_roles.splice(i,1);state.swap_people_map=Object.fromEntries(Object.entries(state.swap_people_map).filter(([,ref])=>ref!==removed));if(tail&&state.swap_direction.endsWith(tail)&&handle){state.swap_direction=state.swap_direction.split('\n').filter(line=>!line.includes('with @'+handle+',')).join('\n');}change();});remove.innerHTML=DirectorIcons.close;remove.setAttribute('aria-label','Remove reference '+(i+1));
      card.append(image,remove);return card;}));
    }
    el('assets-count').textContent=state.reference_ids.length+' / 6';el('add-asset').disabled=uploading||state.reference_ids.length>=6;el('add-asset').hidden=state.reference_ids.length>=6;
    el('direction-enabled').checked=state.swap_direction_enabled;el('direction-body').hidden=false;el('direction').setAttribute('aria-label','Optional edit direction');
    if(document.activeElement!==el('direction'))el('direction').value=state.swap_direction;
    const many=state.swap_roles.filter(r=>r==='character').length>1;el('direction-hint').hidden=!many||Boolean(state.swap_direction.trim());
    el('example').disabled=!many;
    const r=range();document.getElementById('video-duration-value').textContent=src?(state.swap_full_duration&&src.duration<=30?'Full video':Math.max(0,r.end-r.start).toFixed(2)+'s'):'4–30s';
  }
  async function openPicker(index=-1){
    if(!active()||uploading||choose)return;replaceIndex=index;choose='loading';
    el('picker-title').textContent='Choose asset';el('picker-search').value='';el('picker-grid').textContent='Loading assets…';
    importPhoto.disabled=true;if(!el('picker').open)el('picker').showModal();
    try{globalAssets=await api('/second-take/assets');if(!active()||!el('picker').open)return;drawPicker();el('picker-search').focus();}
    catch(error){el('picker-grid').textContent=error.message;throw error;}
    finally{choose=null;importPhoto.disabled=false;}
  }
  function attachReference(id,role,index=-1){if(index>=0){state.reference_ids[index]=id;state.swap_roles[index]=role;return;}if(state.reference_ids.length>=6)throw new Error('Choose up to 6 references.');state.reference_ids.push(id);state.swap_roles.push(role);}
  function drawPicker(){
    const term=el('picker-search').value.trim().toLowerCase();el('picker-title').textContent='Choose asset';
    const rows=globalAssets.filter(a=>a.file&&(!term||(a.handle+' '+a.name+' '+a.project_name).toLowerCase().includes(term)));
    el('picker-grid').replaceChildren(...rows.map(item=>{const b=button('','video-picker-asset',()=>safe(async()=>{
      if(choose)return;choose='selecting';const index=replaceIndex;
      try{await DirectorVideo.save();const saved=await api('/second-take/assets','POST',{source_project:item.source_project,asset_id:item.id});if(!active())return;project=saved.project;
        const duplicate=state.reference_ids.indexOf(saved.asset.id);if(duplicate>=0&&duplicate!==index){if(window.DirectorSwapPeople?.picking){DirectorSwapPeople.bind(saved.asset.id);el('picker').close();return;}toast('This reference is already attached.');return;}
        attachReference(saved.asset.id,item.kind==='character'?'character':'product',index);
        el('picker').close();if(window.DirectorSwapPeople?.picking)DirectorSwapPeople.bind(saved.asset.id);change();
      }finally{choose=null;}
    }));b.title=item.project_name+' · @'+item.handle;const photo=document.createElement('img');photo.src=fileURL(item.thumbnail||item.file,item.source_project);photo.alt='';photo.loading='lazy';const label=document.createElement('span');label.className='video-picker-name';label.textContent='@'+item.handle;b.append(photo,label);return b;}));
    if(!rows.length)el('picker-grid').textContent='No matching assets. Import an image or create an asset first.';
  }
  function validRange(start,end,duration){return Number.isFinite(start)&&Number.isFinite(end)&&start>=0&&end<=duration+1/24&&end-start>=4-1e-6&&end-start<=30+1e-6;}
  function releaseURL(){if(objectURL){URL.revokeObjectURL(objectURL);objectURL=null;}}
  async function openSourcePicker(){if(!active()||uploading)return;el('import').classList.remove('show-generations');el('source-preview').pause();pendingSource=null;el('generated-list').hidden=true;el('import-trim').hidden=true;el('import-current').hidden=true;if(!el('import').open)el('import').showModal();}
  const sourceActions=document.createElement('dialog');sourceActions.className='swap-source-actions';sourceActions.setAttribute('aria-label','Source video');
  const uploadSource=button('Upload video','subtle',()=>{sourceActions.close();el('file').click();});
  const generationSource=button('Use Generation','subtle',()=>safe(async()=>{sourceActions.close();await openSourcePicker();await showGenerations();}));
  const trimSource=button('Adjust Trim','subtle',()=>safe(async()=>{sourceActions.close();const src=source(),r=range();if(src)await previewPending({kind:'current',source_id:src.id,url:fileURL(src.file),start:r.start,end:Math.min(r.end,r.start+30)});}));
  sourceActions.append(uploadSource,generationSource,trimSource);document.body.append(sourceActions);
  sourceActions.addEventListener('click',e=>{const r=sourceActions.getBoundingClientRect();if(e.target===sourceActions&&(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom))sourceActions.close();});
  async function openSource(){if(!active()||uploading)return;trimSource.disabled=!source();if(!sourceActions.open)sourceActions.showModal();}
  async function previewPending(item){
    pendingSource=item;el('import-trim').hidden=true;
    const detectCuts=async({start,end})=>{
      let response;
      if(item.kind==='file'&&!item.cutPreviewToken){const body=new FormData();body.append('video',item.file);body.append('start',String(start));body.append('end',String(end));response=await fetch('/api/second-take/cut-preview',{method:'POST',body});}
      else{const data={start,end,...(item.cutPreviewToken?{token:item.cutPreviewToken}:item.kind==='current'?{source_id:item.source_id}:{project_id:item.project_id,shot_id:item.shot_id,draft_id:item.draft_id})};response=await fetch('/api/second-take/cut-preview',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});}
      const result=await response.json();if(!response.ok){if(String(result.error).includes('expired'))item.cutPreviewToken=null;throw new Error(result.error||'Could not detect cuts.');}item.cutPreviewToken=result.token;return result;
    };
    const previous=item.kind==='current'&&item.source_id===state.swap_source_id?state.swap_cut_candidates:[];
    const selected=await DirectorClipTrim.open({url:item.url,min:4,max:30,start:item.start||0,end:item.end,detectCuts,cutCandidates:previous});
    if(!selected||!active()||pendingSource!==item)return;
    item.cutReview=selected;item.duration=selected.duration;el('import-in').value=String(selected.start);el('import-out').value=String(selected.end);await useClip();
  }

  function stageFile(file){if(!file)return;if(file.size>128*1024*1024)throw new Error('Choose a video up to 128 MB.');if(!/\.(mp4|mov|webm|mkv|m4v)$/i.test(file.name))throw new Error('Choose an MP4, MOV, MKV or WebM video.');releaseURL();objectURL=URL.createObjectURL(file);return previewPending({kind:'file',file,url:objectURL});}
  function syncTrim(){
    if(!pendingSource?.duration)return;const start=Number(el('import-in').value),end=Number(el('import-out').value);
    el('import-in-slider').value=String(start);el('import-out-slider').value=String(end);
    const valid=validRange(start,end,pendingSource.duration);el('import-use').disabled=!valid||uploading;
    el('import-status').textContent=valid?`${(end-start).toFixed(2)}s selected`:'Choose 4–30 seconds within the video.';
  }
  async function useClip(){
    const pending=pendingSource;if(!pending||uploading)return;const start=Number(el('import-in').value),end=Number(el('import-out').value);
    if(!validRange(start,end,pending.duration))return;await DirectorVideo.save();const pid=project.id,sid=DirectorVideo.currentShot?.id,previousSource=state.swap_source_id;if(!sid)return;
    uploading=true;el('import-use').disabled=true;render();
    try{let saved;if(pending.kind==='file'){
        const body=new FormData();body.append('video',pending.file);body.append('start',String(start));body.append('end',String(end));
        const response=await fetch(`/api/projects/${pid}/shots/${sid}/swap-source`,{method:'POST',body});saved=await response.json();if(!response.ok)throw new Error(saved.error||'Import failed.');
      }else saved=await api('/second-take/videos','POST',{shot_id:sid,start,end,...(pending.kind==='current'?{source_id:pending.source_id}:{project_id:pending.project_id,source_shot_id:pending.shot_id,draft_id:pending.draft_id})});
      if(project?.id!==pid||DirectorVideo.currentShot?.id!==sid)return;project=saved;load(project.shots.find(s=>s.id===sid));state.swap_cuts_reviewed=true;state.swap_cut_candidates=pending.cutReview.cut_candidates;state.swap_cut_review_start=pending.cutReview.cut_review_start;state.swap_cut_review_end=pending.cutReview.cut_review_end;state.swap_analysis_id='';state.swap_people_map={};state.swap_ignored_people=[];if(state.swap_source_id!==previousSource){state.swap_direction='';state.swap_direction_enabled=false;el('direction').value='';change();}change();el('import').close();toast('Source clip ready.');
    }finally{uploading=false;el('file').value='';syncTrim();window.render();}
  }
  async function showGenerations(){
    choose='loading';try{const rows=[...await api('/second-take/videos'),...(project.swap_sources||[]).map(r=>({...r,title:r.name,project_id:project.id,project_name:'Imported',source_id:r.id,kind:'current'}))];el('import-trim').hidden=true;el('generated-list').hidden=false;el('import').classList.add('show-generations');
      el('generated-list').replaceChildren(...rows.map(row=>{const b=button('','swap-generation-item',()=>safe(()=>previewPending({...row,kind:row.source_id?'current':'generated',url:fileURL(row.file,row.project_id)})));
        const thumb=document.createElement('video');thumb.src=fileURL(row.file,row.project_id)+'#t=0.1';thumb.preload='metadata';thumb.muted=true;thumb.playsInline=true;thumb.loop=true;b.onpointerenter=()=>thumb.play().catch(()=>{});b.onpointerleave=()=>thumb.pause();
        const title=document.createElement('strong');title.textContent=row.title;const sub=document.createElement('span');sub.textContent=row.project_name+(row.take?' · Take '+row.take:'')+(row.approved?' · Approved':'');b.append(thumb,title,sub);return b;}));
      if(!rows.length)el('generated-list').textContent='No completed videos yet.';
    }finally{choose=null;}
  }
  function durationChoices(menu){
    const src=source();if(!src){menu.textContent='Add a source video first.';return;}
    const edit=button('Adjust Trim & cuts','generation-choice',()=>safe(async()=>{DirectorVideo.closeChoices();const r=range();await previewPending({kind:'current',source_id:src.id,url:fileURL(src.file),start:r.start,end:Math.min(r.end,r.start+30)});}));menu.append(edit);
  }
  function selectedAssets(){return state.reference_ids.map(id=>project?.assets?.find(a=>a.id===id)).filter(Boolean);}
  function mentionOptions(){const field=el('direction'),match=field.value.slice(0,field.selectionStart).match(/@([a-zA-Z0-9_]*)$/);return match?[{handle:'video1'},...selectedAssets()].filter(a=>a.handle.toLowerCase().includes(match[1].toLowerCase())):[];}
  function acceptMention(item){const f=el('direction'),pos=f.selectionStart,before=f.value.slice(0,pos).replace(/@[a-zA-Z0-9_]*$/,'@'+item.handle+' ');f.value=before+f.value.slice(pos);f.focus();f.setSelectionRange(before.length,before.length);state.swap_direction=f.value;el('mentions').hidden=true;change();}
  function drawMentions(){const rows=mentionOptions();mentionIndex=0;el('mentions').replaceChildren(...rows.map((item,i)=>{const b=button('@'+item.handle,'subtle',()=>acceptMention(item));b.setAttribute('role','option');b.setAttribute('aria-selected',String(i===mentionIndex));return b;}));el('mentions').hidden=!rows.length;}
  el('add-asset').onclick=()=>safe(()=>openPicker());el('picker-search').oninput=drawPicker;el('picker-close').onclick=()=>el('picker').close();
  const importPhoto=button('Import image','subtle swap-picker-import',()=>photoInput.click());
  const photoInput=document.createElement('input');photoInput.type='file';photoInput.accept='image/png,image/jpeg,image/webp';photoInput.hidden=true;
  el('picker-search').before(importPhoto,photoInput);
  photoInput.onchange=()=>safe(async()=>{const file=photoInput.files[0];photoInput.value='';if(!file||!active()||choose)return;if(file.size>32*1024*1024)throw new Error('Choose an image up to 32 MB.');if(replaceIndex<0&&state.reference_ids.length>=6)throw new Error('Choose up to 6 references.');
    const pid=project.id,sid=DirectorVideo.currentShot?.id,index=replaceIndex;choose='importing';importPhoto.disabled=true;
    try{await DirectorVideo.save();const form=new FormData();form.append('name',importImageName(file));form.append('kind','character');form.append('image',file);const response=await fetch(`/api/projects/${pid}/assets`,{method:'POST',body:form});const asset=await response.json();if(!response.ok)throw new Error(asset.error||'Image import failed.');
      if(project?.id!==pid||DirectorVideo.currentShot?.id!==sid||!active())return;const updated=await api(`/projects/${pid}`);if(project?.id!==pid||DirectorVideo.currentShot?.id!==sid||!active())return;project=updated;attachReference(asset.id,'character',index);el('picker').close();if(window.DirectorSwapPeople?.picking)DirectorSwapPeople.bind(asset.id);change();
    }finally{choose=null;importPhoto.disabled=false;}
  });
  for(const id of ['picker','import'])el(id).addEventListener('click',e=>{if(e.target===el(id))el(id).close();});
  el('file').onchange=()=>safe(async()=>{await stageFile(el('file').files[0]);});
  el('import-file').onclick=()=>el('file').click();el('import-generated').onclick=()=>safe(showGenerations);el('import-close').onclick=()=>el('import').close();
  el('import-current').onclick=()=>safe(async()=>{const src=source();if(!src)return;const r=range();await previewPending({kind:'current',source_id:src.id,url:fileURL(src.file),start:r.start,end:Math.min(r.end,r.start+30)});});
  el('import').addEventListener('close',()=>{el('source-preview').pause();el('generated-list').querySelectorAll('video').forEach(v=>v.pause());el('import-preview').pause();el('import-preview').removeAttribute('src');releaseURL();el('file').value='';});
  el('import-use').onclick=()=>safe(useClip);
  for(const part of ['in','out']){el('import-'+part).oninput=syncTrim;el('import-'+part+'-slider').oninput=()=>{el('import-'+part).value=el('import-'+part+'-slider').value;syncTrim();const video=el('import-preview');if(Number.isFinite(video.duration))video.currentTime=Number(el('import-'+part).value);};}
  el('direction-enabled').onchange=()=>{state.swap_direction_enabled=el('direction-enabled').checked;change();if(state.swap_direction_enabled)el('direction').focus();};
  el('direction').oninput=()=>{state.swap_direction=el('direction').value;state.swap_direction_enabled=Boolean(state.swap_direction.trim());change();drawMentions();};
  el('direction').onkeydown=e=>{if(el('mentions').hidden)return;const rows=mentionOptions();if(e.key==='Escape'){el('mentions').hidden=true;e.stopPropagation();}if(e.key==='ArrowDown'||e.key==='ArrowUp'){e.preventDefault();mentionIndex=(mentionIndex+(e.key==='ArrowDown'?1:-1)+rows.length)%rows.length;[...el('mentions').children].forEach((b,i)=>b.setAttribute('aria-selected',String(i===mentionIndex)));el('mentions').children[mentionIndex]?.scrollIntoView({block:'nearest'});}if(e.key==='Enter'&&!e.ctrlKey){e.preventDefault();if(rows[mentionIndex])acceptMention(rows[mentionIndex]);}};
  el('example').onclick=()=>{const actors=state.reference_ids.map((id,i)=>state.swap_roles[i]==='character'?project.assets.find(a=>a.id===id):null).filter(Boolean);if(actors.length<2)return;state.swap_direction=`Replace the person on the left in @video1 with @${actors[0].handle}. Replace the person on the right with @${actors[1].handle}. Keep each reference identity distinct. Preserve the source scene, performance, timing and camera.`;change();};
  document.getElementById('video-workspace').addEventListener('dragover',e=>{if(active()&&e.dataTransfer.types.includes('Files')){e.preventDefault();el('panel').classList.add('swap-drop-active');}});
  document.getElementById('video-workspace').addEventListener('dragleave',e=>{if(!e.currentTarget.contains(e.relatedTarget))el('panel').classList.remove('swap-drop-active');});
  document.getElementById('video-workspace').addEventListener('drop',e=>{if(!active()||document.querySelector('dialog[open]'))return;const file=[...(e.dataTransfer?.files||[])].find(f=>f.type.startsWith('video/')||/\.(mp4|mov|webm|mkv|m4v)$/i.test(f.name));if(file){e.preventDefault();e.stopImmediatePropagation();el('panel').classList.remove('swap-drop-active');safe(async()=>{await stageFile(file);});}},true);
  new MutationObserver(()=>{const player=el('source-preview');player.pause();}).observe(document.body,{attributes:true,attributeFilter:['data-studio-app']});
  const adapter=document.createElement('section');adapter.className='swap-required-adapter';adapter.hidden=true;adapter.innerHTML='<strong>TARA motion-transfer LoRA required</strong><span></span><button type="button" class="primary"></button>';document.getElementById('video-workspace').querySelector('.video-editor').append(adapter);
  adapter.querySelector('button').onclick=()=>safe(async()=>{await DirectorModelDownloads.ensureSwap(true,currentMode().lora);renderAdapter();});
  function renderAdapter(){
    const row=currentMode(),status=window.DirectorModelDownloads?.swapStatus(row.lora),installed=(config?.video?.loras?.files||[]).some(f=>f.replaceAll('\\','/').split('/').at(-1)===row.lora);
    adapter.hidden=installed||status?.installed||!active();if(adapter.hidden)return;
    const job=status?.job,working=['queued','downloading','verifying'].includes(job?.status);adapter.querySelector('strong').textContent=working?'Downloading '+row.label:row.label+' LoRA required';
    adapter.querySelector('span').textContent=status?.error||(working&&job.total?Math.round((job.received||0)/job.total*100)+'%':row.lora);
    const action=adapter.querySelector('button');action.disabled=working;action.textContent=working?'Downloading…':status?.job?.status==='failed'?'Retry download':'Download LoRA';
  }
  document.addEventListener('swap-adapter-update',()=>{if(active())render();});
  window.DirectorSwap={modeChoices,get mode(){return currentMode().id;},get loraName(){return currentMode().lora;},setDirection(text){state.swap_direction=text;state.swap_direction_enabled=Boolean(text.trim());},get peopleState(){return state;},setPeople(ident,mapping,people=[],ignored=[]){state.swap_ignored_people=[...ignored];const changed=state.swap_analysis_id!==ident||JSON.stringify(state.swap_people_map)!==JSON.stringify(mapping);state.swap_analysis_id=ident;state.swap_people_map={...mapping};if(changed||!state.swap_direction.trim()){const lines=Object.entries(mapping).map(([id,ref])=>{const person=people.find(p=>p.id===id),asset=project.assets.find(a=>a.id===ref);const description=person?.matched?person.label.replace(/^<Subject\s*\d+>\s*[-:]?\s*/i,''):('person '+id.slice(1));return asset?`Replace the ${description} in @video1 with @${asset.handle}, including their face, hair, body and complete outfit.`:'';}).filter(Boolean);state.swap_direction=[...lines,config.second_take?.prompt_tail||"Preserve the original video's background, lighting, camera and performances throughout. Use the reference images only for the characters; ignore their studio backgrounds. Keep each replacement complete from the first frame to the last, without morphing or transitions."].join('\n');state.swap_direction_enabled=Boolean(state.swap_direction);el('direction').value=state.swap_direction;}change();},openSource,openPicker,load,capture,render,ready,models,durationChoices,useAsset(asset){if(!asset.file||state.reference_ids.length>=6)return;state.reference_ids.push(asset.id);state.swap_roles.push(asset.kind==='character'?'character':'product');change();},get busy(){return uploading||Boolean(choose);}};
})();
