(() => {
  let active=false,pid=null,sceneId=null,selected=null,refs=[],loading=false,submitting=false;
  let dirty=false,saveTimer=null,saveQueue=Promise.resolve(),pending=null,lastReady=null,upscalingTake=null;
  let pendingDroppedAudio=null,creatingShot=false;
  let previewReturn=null,soundtrackQueue=Promise.resolve();
  let choice=null,mentionIndex=0,motionReferenceId='',motionUploading=false,audioReferenceId='',outputAudioId='',outputAudioSelectionId='',audioUploading=null,applyingAudio=false;
  let selectedVideoModels={},selectedVideoLoras=[],videoPreferences=null,mentionedIds=new Set();
  let videoDirection={},videoEnhancerModel='';
  try{videoPreferences=JSON.parse(localStorage.getItem('directors-cut-video-engine')||'null');}catch{}
  if(videoPreferences?.loras)videoPreferences.loras=videoPreferences.loras.filter(row=>!/(?:h3_character_swap|minimax_h3_motion_transfer_tara|minimax_h3_character_swap)/i.test(row.name));
  selectedVideoLoras=structuredClone(videoPreferences?.loras||[]);
  videoEnhancerModel=videoPreferences?.enhancer_model||'';
  const $v=id=>document.getElementById('video-'+id);
  const swapMode=()=>window.DirectorApps?.id==='second-take';
  const scenes=()=>project?.shots.filter(s=>s.mode==='video'&&(s.studio_app==='second-take')===swapMode())||[];
  const scene=()=>scenes().find(s=>s.id===sceneId);
  function normalizeModelRecipe(){
    const filename=selectedVideoModels['127'];if(!filename)return;
    const family=/hyperflow/i.test(filename)?'hyperflow':/fast[-_]?h3.*omni/i.test(filename)?'fast-omni':'original';
    $v('preset').value=family;
    if(family!=='original'){delete selectedVideoModels['145'];delete selectedVideoModels['156'];}
  }
  function mediaMentions(){
    if(swapMode()){const state=cutEdit?scene()?.drafts.find(d=>d.id===cutEdit.baseId)?.settings:window.DirectorSwap?.peopleState,src=project?.swap_sources?.find(r=>r.id===state?.swap_source_id);return src?[{id:'media-video-1',handle:'video1',name:src.name,thumbnail:src.thumbnail,file:src.file,media:'video'},...(src.audio?[{id:'media-audio-1',handle:'audio1',name:'Source audio',media:'audio'}]:[])]:[];}
    const items=[],motion=project?.motion_references?.find(r=>r.id===motionReferenceId),audio=project?.audio_references?.find(r=>r.id===audioReferenceId);
    if(motion)items.push({id:'media-video-1',handle:'video1',name:motion.name,thumbnail:motion.thumbnail,media:'video'});
    if(audio)items.push({id:'media-audio-1',handle:'audio1',name:audio.name,media:'audio'});
    return items;
  }
  function mediaMentionMatches(text){
    const media=mediaMentions();
    return [...text.matchAll(/(?<![\w@])@[ \t]*(video|vídeo|audio|áudio)(?:[ _]*1)?(?![\p{L}\p{N}_]|[ _]*\d)/giu)].map(match=>{
      const kind=/^v/i.test(match[1])?'video':'audio',item=media.find(m=>m.media===kind);
      return item?{index:match.index,text:match[0],item}:null;
    }).filter(Boolean);
  }
  function imageMentionText(){
    const text=$v('prompt').value,matches=mediaMentionMatches(text);let masked=text;
    for(const match of matches.slice().reverse())masked=masked.slice(0,match.index)+' '.repeat(match.text.length)+masked.slice(match.index+match.text.length);
    return masked;
  }
  function referenceIds(){
    if(swapMode())return [...(cutEdit?.references||window.DirectorSwap?.peopleState?.reference_ids||[])];
    const handles=[...imageMentionText().matchAll(/(?<![\w@])@([a-zA-Z0-9_]+)/g)].map(m=>m[1]);
    return [...new Set([...refs,...(project?.assets || []).filter(a=>handles.includes(a.handle)).map(a=>a.id)])];
  }
  function syncMentionReferences(){
    if(swapMode())return;
    const handles=[...imageMentionText().matchAll(/(?<![\w@])@([a-zA-Z0-9_]+)/g)].map(m=>m[1]);
    const current=new Set((project?.assets||[]).filter(a=>handles.includes(a.handle)).map(a=>a.id));
    refs=refs.filter(id=>!mentionedIds.has(id)||current.has(id));
    refs=[...new Set([...refs,...current])];mentionedIds=current;
  }
  function renderPromptHighlights(){
    const field=$v('prompt'),mirror=$v('prompt-highlights');if(!mirror)return;
    if(field.clientWidth)mirror.style.width=field.clientWidth+'px';
    const text=field.value,parts=[],matches=mediaMentionMatches(text);let start=0;
    for(const match of text.matchAll(/(?<![\w@])@([a-zA-Z0-9_]+)/g)){
      if(matches.some(m=>match.index>=m.index&&match.index<m.index+m.text.length))continue;
      const asset=(project?.assets||[]).find(a=>a.handle===match[1]);if(asset)matches.push({index:match.index,text:match[0],item:asset});
    }
    matches.sort((a,b)=>a.index-b.index);
    for(const match of matches){
      parts.push(document.createTextNode(text.slice(start,match.index)));
      const mark=document.createElement('mark');mark.textContent=match.text;mark.dataset.asset=match.item.id;parts.push(mark);start=match.index+match.text.length;
    }
    parts.push(document.createTextNode(text.slice(start)+'\n'));mirror.replaceChildren(...parts);mirror.scrollTop=field.scrollTop;
  }
  function capture(){const data={mode:'video',title:$v('title').value.trim()||'Video shot',prompt:$v('prompt').value,
    ratio:$v('ratio').value,megapixels:Number($v('mp').value),duration:Number($v('duration').value),
    audio_reference_id:audioReferenceId,output_audio_id:outputAudioId,output_audio_selection_id:outputAudioSelectionId,motion_reference_id:motionReferenceId,video_preset:$v('preset').value,model_files:{...selectedVideoModels},loras:structuredClone(selectedVideoLoras),reference_ids:referenceIds(),seed:window.DirectorSeeds?.get(swapMode()?'second-take':'directors-cut')??-1,seed_mode:window.DirectorSeeds?.mode(swapMode()?'second-take':'directors-cut')||'random',
    video_direction:{...videoDirection},selflift:$v('selflift').checked,prompt_enhancer:$v('enhancer-toggle').checked,enhancer_model:videoEnhancerModel};return swapMode()?DirectorSwap.capture(data):data;}
  function load(s,exact=false){
    $v('selflift').checked=Boolean(!exact&&videoPreferences?videoPreferences.selflift:s.selflift);
    rememberWorkspaceItem(swapMode()?'video-second-take':'video',s.id);
    if(swapMode())DirectorSwap.load(s);
    clearDroppedAudio();
    closeChoices();$v('mentions').hidden=true;
    stopAdvancedMedia();sceneId=s.id;audioReferenceId=s.audio_reference_id||'';outputAudioId=s.output_audio_id||'';outputAudioSelectionId=s.output_audio_selection_id||outputAudioId;motionReferenceId=s.motion_reference_id||'';selected=s.drafts.find(d=>d.id===s.approved?.draft_id&&d.status==='succeeded')?.id||s.drafts.filter(d=>d.status==='succeeded').at(-1)?.id||s.drafts.at(-1)?.id;
    lastReady=s.drafts.filter(d=>d.status==='succeeded').at(-1)?.id;
    $v('title').value=s.title;$v('prompt').value=swapMode()?(s.swap_direction||''):(s.prompt||'');$v('ratio').value=s.ratio||'16:9';
    $v('mp').value=String(s.megapixels||.5);$v('duration').value=String(s.duration||5);
    selectedVideoModels={...(!exact&&videoPreferences?videoPreferences.model_files:s.model_files)};
    selectedVideoLoras=swapMode()?[{name:'minimax_h3_motion_transfer_tara_v1.0_ref2va.safetensors',strength:1,enabled:true}]:structuredClone((!exact&&videoPreferences?videoPreferences.loras:s.loras)||[]);
    videoDirection={...(s.video_direction||{})};if(videoDirection.lens==='Halation vintage')delete videoDirection.lens;delete videoDirection.camera;delete videoDirection.sensor;delete videoDirection.palette;delete videoDirection.lighting;delete videoDirection.era;delete videoDirection.genre;videoEnhancerModel=(!exact?(window.DirectorModelDownloads?.sharedValue()||videoPreferences?.enhancer_model):s.enhancer_model)||config?.video?.enhancer?.default||'';$v('enhancer-toggle').checked=Boolean(s.prompt_enhancer);
    $v('preset').value=(!exact&&videoPreferences?videoPreferences.video_preset:s.video_preset)||'fast-omni';normalizeModelRecipe();refs=[...(s.reference_ids||[])];mentionedIds=new Set();syncMentionReferences();dirty=false;pending=null;
  }
  function save(){
    clearTimeout(saveTimer);if(cutEdit||!dirty||!pid||!sceneId)return saveQueue;
    const data=capture(),projectId=pid,id=sceneId;dirty=false;
    saveQueue=saveQueue.catch(()=>{}).then(async()=>{
      try{const saved=await api(`/projects/${projectId}/shots/${id}`,'PUT',data);
        if(project?.id===projectId){const current=project.shots.find(s=>s.id===id);if(current)Object.assign(current,{...saved,drafts:current.drafts});}
      }catch(error){if(pid===projectId&&sceneId===id)dirty=true;throw error;}
    });return saveQueue;
  }
  function changed(){if(cutEdit&&swapMode()){cutEdit.prompts[cutEdit.index]=$v('prompt').value;renderPromptHighlights();return;}dirty=true;pending=null;clearTimeout(saveTimer);saveTimer=setTimeout(()=>safe(save),650);render(project);}
  async function newScene(){
    if(!project||loading||submitting)return;await save();loading=true;render(project);
    try{const id=project.id,s=await api(`/projects/${id}/shots`,'POST',{mode:'video',settings:swapMode()?{studio_app:'second-take',title:'New swap',megapixels:.4}:undefined});
      if(project?.id===id){project.shots.push(s);load(s);}}
    finally{loading=false;render(project);}
  }
  $v('new').onclick=()=>safe(async()=>{
    if(!active||!project||loading||submitting||creatingShot||motionUploading||audioUploading)return;
    creatingShot=true;$v('new').disabled=true;
    try{await newScene();if(active)$v('prompt').focus();}
    finally{creatingShot=false;render(project);}
  });
  async function enter(){
    if(!project||active)return;if(!swapMode())await saveNotes(false);active=true;pid=null;render(project);
  }
  async function leave(){if(cutEdit)closeCuts();if(previewReturn)window.DirectorVideo.endPreview();clearDroppedAudio();await save();stopAdvancedMedia();$v('preview').querySelector('video')?.pause();active=false;$v('workspace').hidden=true;document.body.classList.remove('video-workspace-active');window.render();}
  function useAsset(asset){
    if(swapMode()){DirectorSwap.useAsset(asset);return;}
    if(!asset.file){toast('Generate or import an image for this asset first.');return;}
    if(!referenceIds().includes(asset.id)&&referenceIds().length>=9){toast('H3 supports up to 9 image references.');return;}
    const field=$v('prompt');field.value+=(field.value&&!/\s$/.test(field.value)?' ':'')+'@'+asset.handle+' ';
    syncMentionReferences();changed();renderPicker();
  }
  async function run(){
    const ready=selectedReadiness();if(submitting||loading||motionUploading||audioUploading||!scene()||!ready?.ready||(swapMode()?!DirectorSwap.ready():!$v('prompt').value.trim()))return;
    submitting=true;render(project);
    try{
      if(swapMode()&&!DirectorSwap.ready())return;
      await save();const data=capture(),signature=JSON.stringify(data);
      if(!pending||pending.signature!==signature)pending={signature,id:submissionId()};
      const projectId=pid,id=sceneId;
      const result=await api(`/projects/${projectId}/shots/${id}/generate`,'POST',{...data,count:1,request_id:pending.id});pending=null;window.DirectorSeeds?.advance(swapMode()?'second-take':'directors-cut',1,data);
      if(project?.id===projectId){project=await api(`/projects/${projectId}`);if(sceneId===id)selected=result.id;}
      toast('Video added to queue.');await refreshQueue();
    }finally{submitting=false;render(project);}
  }
  function render(p){
    if(!active)return;
    document.body.classList.add('video-workspace-active');document.body.dataset.workspace='video';$v('workspace').hidden=false;
    for(const mode of ['assets','video'])document.getElementById('tab-'+mode).setAttribute('aria-selected',String(mode==='video'));
    if(!p)return;
    if(pid!==p.id){
      pid=p.id;sceneId=null;refs=[];dirty=false;pending=null;const first=lastWorkspaceItem(swapMode()?'video-second-take':'video',scenes(),p.id);
      if(first)load(first);else if(!loading)safe(newScene);
    }
    const current=scene();
    $v('editor-heading').textContent=current?.title||'New shot';
    for(const action of ['rename','delete','browse'])$v(action).disabled=loading||submitting||action!=='browse'&&!current;
    $v('new').disabled=!project||loading||submitting||creatingShot||motionUploading||Boolean(audioUploading);
    renderSettings();
    const ready=selectedReadiness();
    $v('setup-status').hidden=Boolean(ready?.ready);$v('setup-status').textContent=ready?.ready?'':(ready?.missing?.join(' ')||'Checking video engine…');
    updateChoices();
    $v('generate').disabled=loading||submitting||motionUploading||Boolean(audioUploading)||!current||!ready?.ready||!config?.online||(swapMode()?!DirectorSwap.ready():!$v('prompt').value.trim());
    $v('generate').innerHTML=DirectorIcons.plus+'<span>'+(submitting?'Adding to queue…':'Generate Video')+'</span>';
    if(swapMode()){DirectorSwap.render();if(!cutEdit&&document.activeElement!==$v('prompt'))$v('prompt').value=DirectorSwap.peopleState.swap_direction||'';renderReferences(p);}else {renderReferences(p);renderAdvanced(p);}
    if(!current){$v('preview').textContent='Preparing shot…';return;}
    const drafts=current.drafts,latest=drafts.filter(d=>d.status==='succeeded').at(-1)?.id;
    const newlyCompleted=Boolean(latest&&latest!==lastReady);
    if(newlyCompleted){selected=latest;lastReady=latest;}
    if(!drafts.some(d=>d.id===selected))selected=latest||drafts.at(-1)?.id;
    const take=drafts.find(d=>d.id===selected),preview=$v('preview');
    if(newlyCompleted&&!swapMode())safe(syncSoundtrack);
    const position=drafts.findIndex(d=>d.id===selected);
    $v('position').textContent=drafts.length?`${position+1} / ${drafts.length}`:'No videos yet';
    $v('previous').disabled=position<=0;$v('next').disabled=position<0||position>=drafts.length-1;
    $v('scene-heading').textContent=current.title;
    if(take?.status==='succeeded'){
      const revision=take.id+(take.audio_applied_at||'');if(preview.dataset.draft!==revision){const previous=preview.querySelector('video'),resume=Boolean(previous&&!previous.paused);previous?.pause();const player=DirectorPlayer.create(fileURL(take.file)+(take.audio_applied_at?'?v='+encodeURIComponent(take.audio_applied_at):''),{autoplay:(newlyCompleted||resume)&&(!window.DirectorBoard||DirectorBoard.videoPreviewOpen),loop:true});preview.replaceChildren(player);preview.dataset.draft=revision;}
      $v('download').href=fileURL(take.file)+'?v='+encodeURIComponent(take.audio_applied_at||take.id);$v('download').download=(swapMode()?'Swap '+(take.number||position+1):current.title).replace(/[<>:"/\\|?*\x00-\x1f]/g,'_')+'.mp4';$v('download').hidden=false;
      $v('output-info').textContent=`${take.settings.ratio} · ${take.settings.megapixels*(take.postprocess?.scale||1)**2} MP · ${take.settings.duration}s · ${take.postprocess?.type==='rtx-upscale'?'RTX 2× · ':''}${take.applied_output_audio_id?'custom audio':'H3 audio'}`;
      $v('used-details').hidden=false;$v('prompt-used').textContent=take.full_prompt||take.settings.prompt;
    }else{
      const stamp=take?.id+':'+take?.status;
      if(preview.dataset.draft!==stamp){preview.querySelector('video')?.pause();const panel=document.createElement('div');panel.className='generation-preview';
        if(take&&activeDraft(take)){const pulse=document.createElement('span');pulse.className='generation-orbit';panel.append(pulse);}
        const text=document.createElement('p');text.textContent=!take?'Your first video appears here.':take.status==='queued'?'Waiting in queue…':activeDraft(take)?'Generating video and audio…':take.status==='failed'?'Video generation failed':'Cancelled';panel.append(text);preview.replaceChildren(panel);preview.dataset.draft=stamp;}
      window.DirectorMotion?.generation(preview.querySelector('.generation-preview'),take);
      const surface=preview.querySelector('.generation-preview');let details=surface?.querySelector('.video-processing-details');
      if(take&&activeDraft(take)){if(!details){details=document.createElement('div');details.className='video-processing-details';details.setAttribute('role','status');surface.append(details);}const rows=[];if(take.segment_count)rows.push(['Part',take.segment_number+' / '+take.segment_count]);if(take.node_label||take.node_type)rows.push(['Node',take.node_label||take.node_type]);if(take.settings?.selflift)rows.push(['Workflow','SelfLift']);rows.push(['Output',(take.settings?.duration||'')+' s · '+(take.settings?.megapixels||'')+' MP']);if(take.progress_updated_at)rows.push(['Last signal',new Date(take.progress_updated_at).toLocaleTimeString()]);const stamp=JSON.stringify([rows,Boolean(take.sampling_steps)]);if(details.dataset.stamp!==stamp){details.dataset.stamp=stamp;details.replaceChildren();for(const [label,value]of rows){const line=document.createElement('div'),name=document.createElement('span'),text=document.createElement('strong');name.textContent=label;text.textContent=value;line.append(name,text);details.append(line);}if(!take.sampling_steps){const note=document.createElement('p');note.textContent='Sampling steps not reported by the engine yet.';details.append(note);}}}else details?.remove();
      $v('download').hidden=true;$v('used-details').hidden=true;$v('output-info').textContent='MiniMax H3 Ref2VA';
    }
    const approved=Boolean(take&&take.id===current.approved?.draft_id);
    $v('approve').disabled=swapMode()?!take?.swap_segments?.length:take?.status!=='succeeded'||approved;
    $v('approve').innerHTML=(swapMode()?DirectorIcons.select:DirectorIcons.save)+'<span>'+(swapMode()?'View cuts':approved?'Approved':'Approve take')+'</span>';
    if(swapMode())$v('approve').removeAttribute('aria-pressed');else $v('approve').setAttribute('aria-pressed',String(approved));
    const hasUpscale=drafts.some(d=>d.postprocess?.source_draft_id===take?.id&&activeDraft(d));
    $v('rtx-upscale').hidden=!config?.rtx_upscale?.ready||take?.status!=='succeeded'||take?.postprocess?.type==='rtx-upscale';
    $v('rtx-upscale').disabled=Boolean(upscalingTake===take?.id||hasUpscale);
    $v('rtx-upscale').innerHTML=DirectorIcons.upscale+'<span>'+(hasUpscale?'Upscale queued':'RTX Upscale')+'</span>';
    const running=drafts.find(activeDraft),failed=drafts.at(-1)?.status==='failed'?drafts.at(-1):null;
    const cancellable=drafts.find(d=>activeDraft(d)&&d.status!=='queued')||(take&&activeDraft(take)?take:running);
    $v('stop').hidden=!cancellable;$v('stop').disabled=Boolean(cancellable?.cancel_requested);
    $v('stop').dataset.draft=cancellable?.id||'';
    const queued=cancellable?.status==='queued';
    $v('stop').innerHTML=(queued?DirectorIcons.close:DirectorIcons.skip)+'<span>'+(cancellable?.cancel_requested?'Stopping…':queued?'Remove':'Skip')+'</span>';
    $v('stop').title=queued?'Remove queued video':'Skip current video';$v('stop').setAttribute('aria-label',$v('stop').title);
    const centralProgress=take&&activeDraft(take)&&window.DirectorMotion?.progress;
    if(centralProgress)$v('status').replaceChildren();
    else if(!running||!window.DirectorMotion?.progress)$v('status').textContent=running?(running.status==='queued'?'Waiting in queue…':`${running.stage||'Generating video and audio'}${running.progress?' · '+Math.round(running.progress*100)+'%':''}`):failed?'Failed: '+failed.error:'';
    $v('status').className=failed&&!running?'error':'';if(running&&!centralProgress&&window.DirectorMotion?.progress)window.DirectorMotion.progress($v('status'),running,true);
    renderTakes(current);syncCutEditor();window.DirectorBoard?.renderVideo(p);
    $v('queue-status').textContent=`${queueState.running} active · ${queueState.waiting} queued`;
    renderLibrary();
    window.DirectorDropdowns.sync();
  }
  $v('rtx-upscale').onclick=()=>safe(async()=>{
    const current=scene(),take=current?.drafts.find(d=>d.id===selected);
    if(!current||take?.status!=='succeeded'||upscalingTake||!config?.rtx_upscale?.ready)return;
    const projectId=pid,shotId=current.id;upscalingTake=take.id;render(project);
    try{
      const draft=await api(`/projects/${projectId}/shots/${shotId}/drafts/${take.id}/rtx-upscale`,'POST',{});
      if(project?.id===projectId){const target=project.shots.find(s=>s.id===shotId);if(target&&!target.drafts.some(d=>d.id===draft.id))target.drafts.push(draft);}
      await refreshQueue();toast('RTX 2× upscale added to queue.');
    }finally{upscalingTake=null;render(project);}
  });
  $v('approve').onclick=()=>safe(async()=>{
    const current=scene(),take=current?.drafts.find(d=>d.id===selected&&(swapMode()||d.status==='succeeded'));if(!take)return;
    if(swapMode()){openSwapCuts(take);return;}
    const projectId=pid,shotId=current.id;$v('approve').disabled=true;
    try{const saved=await api(`/projects/${projectId}/shots/${shotId}/approve`,'POST',{draft_id:take.id});
      if(project?.id===projectId){const shot=project.shots.find(s=>s.id===shotId);if(shot)shot.approved=saved.approved;render(project);renderLibrary(true);}
      toast('Video take approved.');
    }finally{render(project);}
  });
  let cutEdit=null,cutBusy=false;
  const finishCuts=button('Join cuts','primary join-cuts-action',()=>safe(()=>submitCut(true)));finishCuts.innerHTML='<strong>Join Cuts</strong><span>Finish</span>';finishCuts.setAttribute('aria-label','Join Cuts, Finish');finishCuts.hidden=true;
  function cutParts(){return cutEdit?.parts||[];}
  function cutRevisionStamp(context){return JSON.stringify((project?.shots.find(s=>s.id===context.sid)?.drafts||[]).map(d=>[d.id,d.status,d.deleted_at,(d.swap_segments||[]).map(p=>p.status)]));}
  function refreshCutVersions(context){
    const stamp=cutRevisionStamp(context);if(context.refreshing||context.versionStamp===stamp)return;context.refreshing=true;context.versionStamp=stamp;
    api(`/projects/${context.pid}/shots/${context.sid}/drafts/${context.baseId}/cuts`).then(details=>{if(cutEdit!==context)return;context.parts=details.parts;
      for(const [index,id] of Object.entries(context.autoChoices||{})){const ready=details.parts.find(p=>p.index===Number(index))?.versions.find(v=>v.draft_id===id&&v.status==='succeeded');if(ready){context.choices[index]=id;delete context.autoChoices[index];}}
      window.DirectorBoard?.refreshCuts();
    }).catch(error=>{context.error=error.message;}).finally(()=>{context.refreshing=false;});
  }
  function showCutPrompt(index,version){
    if(!cutEdit)return;cutEdit.index=index;const part=cutParts().find(p=>p.index===index),chosen=version||part?.versions.find(v=>v.draft_id===cutEdit.choices[index])||part;
    if(version){cutEdit.choices[index]=version.draft_id;cutEdit.prompts[index]=version.prompt;}
    $v('prompt').value=cutEdit.prompts[index]??chosen?.prompt??'';renderPromptHighlights();syncCutEditor();window.DirectorBoard?.refreshCuts();
  }
  function selectCut(index){showCutPrompt(index);}
  function chooseCutVersion(index,id){const version=cutParts().find(p=>p.index===index)?.versions.find(v=>v.revision_id===id);if(version?.status==='succeeded'){delete cutEdit.autoChoices?.[index];showCutPrompt(index,version);}}
  function closeCuts(){$v('generate').hidden=false;cutEdit=null;$v('prompt').disabled=false;$v('prompt').value=window.DirectorSwap?.peopleState?.swap_direction||'';renderPromptHighlights();finishCuts.hidden=true;document.body.classList.remove('editing-swap-cuts');render(project);}
  async function openCutsFor(shotId,takeId){await save();sceneId=shotId;const take=scene()?.drafts.find(d=>d.id===takeId);if(take?.swap_segments?.length)await openSwapCuts(take);}
  async function openSwapCuts(take){
    const projectId=pid,shotId=sceneId;await save();
    const details=await api(`/projects/${projectId}/shots/${shotId}/drafts/${take.id}/cuts`);
    const byId=new Map(scene().drafts.map(d=>[d.id,d]));let root=take;while(root.regenerated_from&&byId.has(root.regenerated_from))root=byId.get(root.regenerated_from);const completed=root.status==='succeeded'?root:take;
    cutEdit={pid:projectId,sid:shotId,id:take.id,baseId:completed.id,loadedId:take.id,index:1,parts:details.parts,references:details.reference_ids,autoChoices:{},
      prompts:Object.fromEntries(details.parts.map(p=>[p.index,p.prompt])),choices:Object.fromEntries(details.parts.map(p=>[p.index,p.versions.find(v=>v.revision_id===p.revision_id)?.draft_id||take.id]))};
    cutEdit.versionStamp=cutRevisionStamp(cutEdit);
    window.DirectorVideo.endPreview();sceneId=shotId;selected=take.id;window.DirectorBoard.openCuts(shotId);selectCut(1);
  }
  function syncCutEditor(){
    const enabled=Boolean(cutEdit&&swapMode()&&cutEdit.pid===pid);finishCuts.hidden=!enabled||Boolean(project?.shots.find(s=>s.id===cutEdit?.sid)?.drafts.find(d=>d.id===cutEdit?.id)?.postprocess?.type==='rtx-upscale');document.body.classList.toggle('editing-swap-cuts',enabled);
    if(!enabled)return;
    const take=project.shots.find(s=>s.id===cutEdit.sid)?.drafts.find(d=>d.id===cutEdit.id),base=project.shots.find(s=>s.id===cutEdit.sid)?.drafts.find(d=>d.id===cutEdit.baseId),busy=cutBusy||base?.status!=='succeeded';
    const rtx=take?.postprocess?.type==='rtx-upscale';$v('generate').hidden=rtx;
    $v('editor-heading').textContent='Cut '+cutEdit.index;$v('generate').innerHTML=DirectorIcons.plus+'<span>Generate Video</span>';$v('generate').disabled=busy;
    finishCuts.disabled=busy||cutParts().some(p=>p.versions.some(v=>activeDraft(v)));$v('prompt').disabled=busy;
    const part=cutParts().find(p=>p.index===cutEdit.index);$v('size-value').textContent=(take?.settings?.megapixels||'')+' MP';$v('duration-value').textContent=part?(part.frames/24).toFixed(2)+'s':'';for(const key of ['size','duration','frame'])$v('choose-'+key).disabled=true;
    if(cutEdit.error){$v('status').textContent=cutEdit.error;$v('status').className='error';}
    refreshCutVersions(cutEdit);
    renderReferences(project);
  }
  async function submitCut(finish=false){
    if(!cutEdit||cutBusy)return;const context=cutEdit,index=context.index;context.error='';cutBusy=true;syncCutEditor();
    try{
      const seed=window.DirectorSeeds?.get('second-take')??-1,seed_mode=window.DirectorSeeds?.mode('second-take')||'random';
      if(project.shots.find(s=>s.id===context.sid)?.drafts.find(d=>d.id===context.id)?.postprocess?.type==='rtx-upscale')throw new Error('RTX cuts are processed automatically. Regenerate the original swap instead.');
      const data={index,finish,prompt:finish?undefined:$v('prompt').value,choices:{...context.choices},seed,...(!finish?{engine:{video_preset:$v('preset').value,model_files:{...selectedVideoModels},selflift:$v('selflift').checked,swap_mode:DirectorSwap.mode}}:{})},signature=JSON.stringify([context.baseId,data]);if(context.pending?.signature!==signature)context.pending={signature,id:submissionId()};
      const result=await api(`/projects/${context.pid}/shots/${context.sid}/drafts/${context.baseId}/cuts/regenerate`,'POST',{...data,request_id:context.pending.id});context.pending=null;
      if(!finish)window.DirectorSeeds?.advance('second-take',1,{seed,seed_mode});
      if(!finish)(context.autoChoices||={})[index]=result.id;
      context.id=result.id;project=await api(`/projects/${context.pid}`);selected=result.id;
      if(finish){closeCuts();window.DirectorBoard.closeCuts();toast('Joining selected cuts with the original audio.');}
      else {render(project);toast('Cut '+index+' added to the queue.');}
      await refreshQueue();
    }catch(error){context.error=error.message;throw error;}finally{cutBusy=false;syncCutEditor();}
  }
  const activeDraft=d=>['queued','submitting','pending','running','downloading'].includes(d.status);
  $v('stop').onclick=()=>safe(async()=>{
    const draft=$v('stop').dataset.draft;if(!draft||!scene())return;
    const projectId=pid,currentScene=sceneId;$v('stop').disabled=true;
    try{
      await api(`/projects/${projectId}/shots/${currentScene}/drafts/${draft}/cancel`,'POST',{});
      if(project?.id===projectId)project=await api(`/projects/${projectId}`);
      await refreshQueue();render(project);
    }finally{if(!$v('stop').hidden&&!scene()?.drafts.find(d=>d.id===draft)?.cancel_requested)$v('stop').disabled=false;}
  });
  function renderReferences(p){
    renderPromptHighlights();
    const ids=referenceIds();$v('reference-panel').hidden=!ids.length;$v('reference-count').textContent=String(ids.length);
    const root=$v('references'),stamp=JSON.stringify([p.id,ids,p.assets.map(a=>[a.id,a.handle,a.thumbnail,a.file])]);
    if(root.dataset.stamp===stamp)return;root.dataset.stamp=stamp;
    root.replaceChildren(...ids.map((id,index)=>{
      const asset=p.assets.find(a=>a.id===id);if(!asset)return document.createTextNode('');
      return referenceTile({thumbnail:fileURL(asset.thumbnail||asset.file),source:fileURL(asset.file||asset.thumbnail),label:`${index+1} · @${asset.handle}`,
        onRemove:()=>{refs=refs.filter(x=>x!==id);$v('prompt').value=$v('prompt').value.replace(new RegExp('(?<![\\w@])@'+asset.handle+'\\b','g'),asset.name);changed();}
      });
    }));
  }
  function renderMotionReference(p){
    const ref=p.motion_references?.find(r=>r.id===motionReferenceId),root=$v('motion-reference');root.hidden=!ref;
    $v('attach-motion').disabled=motionUploading||Boolean(audioUploading);$v('attach-motion').hidden=Boolean(ref)&&!motionUploading;$v('attach-motion').textContent=motionUploading?'Preparing clip…':ref?'Replace motion video':'Choose motion video';
    const stamp=ref?.id||'';if(root.dataset.stamp===stamp)return;root.dataset.stamp=stamp;root.querySelector('video')?.pause();root.replaceChildren();if(!ref)return;
    const player=document.createElement('video');player.muted=true;player.loop=true;player.playsInline=true;player.preload='metadata';player.poster=fileURL(ref.thumbnail);player.src=fileURL(ref.file);
    const preview=button('','motion-preview-button',()=>{$v('attach-motion').click();});preview.setAttribute('aria-label','Replace motion video');preview.append(player);
    root.onpointerenter=()=>player.play().catch(()=>{});root.onpointerleave=()=>player.pause();
    const label=document.createElement('span');label.className='motion-card-label';label.textContent=ref.name+' · '+ref.duration+'s';
    const remove=button('','icon-button',()=>{motionReferenceId='';changed();});remove.innerHTML=DirectorIcons.close;remove.setAttribute('aria-label','Remove motion reference');root.append(preview,label,remove);
  }
  $v('attach-motion').onclick=()=>{if(!scene()||motionUploading||audioUploading)return;$v('motion-file').value='';$v('motion-file').click();};
  $v('attach-motion').title='Use a video as a movement reference. Choose a 2–15 second range, without source audio.';
  async function uploadMotionFile(file){
    if(!file||!active||!scene()||motionUploading||audioUploading)return;
    const projectId=project.id,shot=sceneId;if(file.size>128*1024*1024)throw new Error('Choose a motion video up to 128 MB.');
    const url=URL.createObjectURL(file);let range;try{range=await DirectorClipTrim.open({url,min:2,max:15});}finally{URL.revokeObjectURL(url);}
    if(!range||!active||project?.id!==projectId||sceneId!==shot)return;motionUploading=true;render(project);
    try{await save();const data=new FormData();data.append('video',file);data.append('start',String(range.start));data.append('end',String(range.end));const response=await fetch(`/api/projects/${projectId}/shots/${shot}/motion-reference`,{method:'POST',body:data}),result=await response.json();
      if(!response.ok)throw new Error(result.error||'Motion upload failed.');
      if(project?.id===projectId){project=result;if(sceneId===shot)motionReferenceId=project.shots.find(s=>s.id===shot).motion_reference_id;}toast('Motion reference added.');
    }finally{motionUploading=false;$v('motion-file').value='';render(project);}
  }
  $v('motion-file').onchange=()=>{const input=$v('motion-file'),file=input.files[0];input.value='';safe(()=>uploadMotionFile(file));};

  function stopAdvancedMedia(){
    for(const media of $v('advanced').querySelectorAll('audio,video'))media.pause();
  }
  function renderAudioCard(kind,ref){
    const root=$v(kind+'-audio-card');root.hidden=!ref;
    const stamp=(ref?.id||'')+':'+outputAudioId;if(root.dataset.stamp===stamp)return;root.dataset.stamp=stamp;
    root.querySelector('audio')?.pause();root.replaceChildren();if(!ref)return;
    const title=document.createElement('div');title.className='audio-file-heading';
    const name=button(ref.name,'audio-card-name',()=>{$v('attach-'+kind+'-audio').click();});name.title='Replace '+ref.name;
    const remove=button('','icon-button',()=>{if(kind==='reference')audioReferenceId='';else{outputAudioSelectionId='';if(outputAudioId===ref.id)outputAudioId='';}changed();if(kind==='output')safe(syncSoundtrack);});remove.innerHTML=DirectorIcons.close;remove.setAttribute('aria-label','Remove '+ref.name);const finalLabel=document.createElement('label');finalLabel.className='enhancer-toggle audio-final-toggle';const finalToggle=document.createElement('input');finalToggle.type='checkbox';finalToggle.setAttribute('role','switch');finalToggle.setAttribute('aria-label','Use '+ref.name+' as final audio');finalToggle.checked=outputAudioId===ref.id;finalToggle.onchange=()=>{outputAudioId=finalToggle.checked?ref.id:'';if(finalToggle.checked)outputAudioSelectionId=ref.id;changed();safe(syncSoundtrack);};const finalText=document.createElement('span');finalText.textContent='Final';finalLabel.append(finalToggle,finalText);title.append(name,finalLabel,remove);
    const audio=document.createElement('audio');audio.preload='metadata';audio.muted=false;audio.volume=1;audio.src=fileURL(ref.file);audio.onerror=()=>toast('Could not play this audio. Try importing the clip again.');
    const controls=document.createElement('div');controls.className='audio-preview-controls';
    const play=button('','audio-preview-play',()=>{if(audio.paused)audio.play().catch(error=>toast(error.message));else audio.pause();});play.innerHTML=DirectorIcons.play;play.setAttribute('aria-label','Play '+ref.name);
    const bars=document.createElement('div');bars.className='audio-waveform';bars.tabIndex=0;bars.setAttribute('role','slider');bars.setAttribute('aria-label','Audio preview position');bars.setAttribute('aria-valuemin','0');bars.setAttribute('aria-valuemax',String(ref.duration));bars.setAttribute('aria-valuenow','0');
    for(const peak of ref.waveform||[]){const bar=document.createElement('i');bar.style.height=Math.max(6,peak*100)+'%';bars.append(bar);}
    const time=document.createElement('span');time.className='audio-preview-time';
    const clock=seconds=>Math.floor(seconds/60)+':'+String(Math.floor(seconds%60)).padStart(2,'0');time.textContent=clock(ref.duration);
    const seek=seconds=>{if(audio.readyState){audio.currentTime=Math.max(0,Math.min(ref.duration,seconds));}else{audio.addEventListener('loadedmetadata',()=>{audio.currentTime=seconds;},{once:true});audio.play().catch(()=>{});}};
    bars.onclick=event=>{const bounds=bars.getBoundingClientRect();seek(Math.max(0,Math.min(1,(event.clientX-bounds.left)/bounds.width))*ref.duration);};
    bars.onkeydown=event=>{const delta=event.key==='ArrowRight'?1:event.key==='ArrowLeft'?-1:0;if(delta){event.preventDefault();seek(audio.currentTime+delta);}};
    audio.onplay=()=>{for(const other of $v('advanced').querySelectorAll('audio,video'))if(other!==audio)other.pause();$v('preview').querySelector('video')?.pause();root.classList.add('is-playing');play.innerHTML=DirectorIcons.pause;play.setAttribute('aria-label','Pause '+ref.name);};
    audio.onpause=audio.onended=()=>{root.classList.remove('is-playing');play.innerHTML=DirectorIcons.play;play.setAttribute('aria-label','Play '+ref.name);};
    audio.ontimeupdate=()=>{bars.style.setProperty('--played',Math.min(100,audio.currentTime/ref.duration*100)+'%');bars.setAttribute('aria-valuenow',String(Math.round(audio.currentTime*10)/10));time.textContent=clock(audio.currentTime)+' / '+clock(ref.duration);};
    controls.append(play,bars,time);root.append(title,controls,audio);root.onclick=e=>{if(!e.target.closest('button,input,label,.audio-waveform'))$v('attach-'+kind+'-audio').click();};
  }
  function renderAdvanced(p){
    renderMotionReference(p);
    const reference=p.audio_references?.find(ref=>ref.id===audioReferenceId),output=p.audio_references?.find(ref=>ref.id===(outputAudioSelectionId||outputAudioId));
    renderAudioCard('reference',reference);renderAudioCard('output',output);
    const count=[motionReferenceId,audioReferenceId,outputAudioId].filter(Boolean).length;
    $v('advanced-count').textContent=count?count+' active':'';$v('advanced').classList.toggle('has-selection',Boolean(count));
    for(const [kind,ref] of [['reference',reference],['output',output]]){
      const control=$v('attach-'+kind+'-audio');control.disabled=Boolean(audioUploading)||motionUploading;control.hidden=Boolean(ref)&&!audioUploading;control.textContent=audioUploading===kind?'Preparing audio…':ref?'Replace '+(kind==='output'?'final audio':'speech audio'):'Choose '+(kind==='output'?'final audio':'speech audio');
      $v('advanced-tab-'+kind).classList.toggle('has-media',Boolean(ref));
    }
    $v('advanced-tab-motion').classList.toggle('has-media',Boolean(motionReferenceId));
    $v('audio-exact-row').hidden=true;$v('audio-exact').checked=Boolean(reference&&outputAudioId===audioReferenceId);
    const take=scene()?.drafts.find(d=>d.id===selected&&d.status==='succeeded');
    $v('apply-audio').hidden=true;$v('restore-audio').hidden=!take?.applied_output_audio_id;
    $v('apply-audio').disabled=applyingAudio||take?.applied_output_audio_id===outputAudioId;
    $v('apply-audio').textContent=applyingAudio?'Applying…':take?.applied_output_audio_id===outputAudioId?'Applied to this take':'Apply to this take';
    $v('restore-audio').disabled=applyingAudio;
  }
  for(const kind of ['motion','output','reference'])$v('advanced-tab-'+kind).onclick=()=>{
    stopAdvancedMedia();for(const name of ['motion','output','reference']){$v('advanced-tab-'+name).setAttribute('aria-selected',String(name===kind));$v('advanced-tab-'+name).tabIndex=name===kind?0:-1;$v('advanced-'+name).hidden=name!==kind;}
  };
  for(const [index,kind] of ['motion','output','reference'].entries()){
    const tab=$v('advanced-tab-'+kind);tab.tabIndex=index===0?0:-1;
    tab.onkeydown=event=>{const keys=['motion','output','reference'];let next=event.key==='ArrowRight'?(index+1)%3:event.key==='ArrowLeft'?(index+2)%3:event.key==='Home'?0:event.key==='End'?2:null;if(next!==null){event.preventDefault();const target=$v('advanced-tab-'+keys[next]);target.click();target.focus();}};
  }
  const advancedIcon=$v('advanced').querySelector('summary>.ui-icon');advancedIcon.removeAttribute('style');advancedIcon.className='advanced-symbol';advancedIcon.innerHTML=DirectorIcons.advanced;
  $v('attach-reference-audio').title='Use up to the first 15 seconds to guide speech and voice. Lip-sync fidelity depends on the model.';
  $v('attach-output-audio').title='Use up to the first 30 seconds. The soundtrack is trimmed or padded to the final video length.';
  $v('advanced').addEventListener('toggle',()=>{
    if(!$v('advanced').open)stopAdvancedMedia();
    else requestAnimationFrame(()=>{if($v('advanced').open)$v('advanced').scrollIntoView({block:'nearest',behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'instant':'smooth'});});
  });
  for(const kind of ['output','reference']){
    $v('attach-'+kind+'-audio').onclick=()=>{if(!scene()||audioUploading||motionUploading)return;$v(kind+'-audio-input').value='';$v(kind+'-audio-input').click();};
    $v(kind+'-audio-input').onchange=()=>{const input=$v(kind+'-audio-input'),file=input.files[0];input.value='';safe(()=>uploadAudioFile(kind,file));};
  }
  async function uploadAudioFile(kind,file){
    if(!file||!active||!scene()||audioUploading||motionUploading)return;
    const projectId=project.id,shot=sceneId,wasFinal=kind==='reference'&&audioReferenceId&&audioReferenceId===outputAudioId;audioUploading=kind;render(project);
    try{await save();const form=new FormData();form.append('audio',file);const response=await fetch(`/api/projects/${projectId}/shots/${shot}/audio/${kind}`,{method:'POST',body:form}),result=await response.json();
      if(!response.ok)throw new Error(result.error||'Audio upload failed.');
      if(project?.id===projectId){project=result;if(sceneId===shot){const saved=project.shots.find(s=>s.id===shot);audioReferenceId=saved.audio_reference_id||'';outputAudioId=saved.output_audio_id||'';outputAudioSelectionId=saved.output_audio_selection_id||outputAudioId;if(wasFinal){outputAudioId=audioReferenceId;outputAudioSelectionId=audioReferenceId;changed();}}}await syncSoundtrack();toast('Audio added.');
    }finally{audioUploading=null;render(project);if(project?.id===projectId&&sceneId===shot)$v(kind+'-audio-card').querySelector('audio')?.play().catch(()=>{});}
  }

  function clearDroppedAudio(){pendingDroppedAudio=null;$v('drop-audio-choice')?.remove();}
  function revealMediaSlot(kind){$v('advanced').open=true;$v('advanced-tab-'+kind).click();}
  function chooseDroppedAudio(file,clipAudio=false){
    clearDroppedAudio();pendingDroppedAudio={file,projectId:project.id,shotId:sceneId};
    const chooser=document.createElement('div');chooser.id='video-drop-audio-choice';chooser.className='video-drop-audio-choice';chooser.setAttribute('role','group');chooser.setAttribute('aria-label','Use dropped audio as');
    const name=document.createElement('strong');name.textContent=(clipAudio?'Use clip audio (optional): ':'')+file.name;name.title=file.name;
    const actions=document.createElement('div');actions.className='video-drop-actions';
    for(const [kind,label] of [['reference','Audio reference'],['output','Final audio']])actions.append(button(label,'subtle',()=>safe(async()=>{
      const pending=pendingDroppedAudio;clearDroppedAudio();if(!pending)return;
      if(project?.id!==pending.projectId||sceneId!==pending.shotId||!active){toast('The shot changed. Drop the audio again.');return;}
      revealMediaSlot(kind);await uploadAudioFile(kind,pending.file);
    })));
    const cancel=button('','icon-button',clearDroppedAudio);cancel.innerHTML=DirectorIcons.close;cancel.setAttribute('aria-label','Cancel audio import');actions.append(cancel);chooser.append(name,actions);$v('prompt').closest('.video-prompt-composer').append(chooser);actions.firstElementChild.focus({preventScroll:true});
  }
  function droppedVideoMediaKind(file){
    if(/^audio\//i.test(file.type))return 'audio';
    if(/^video\//i.test(file.type))return 'video';
    if(/\.(wav|mp3|flac|ogg|m4a|aac|aiff?|opus)$/i.test(file.name))return 'audio';
    if(/\.(mp4|mov|webm|mkv|m4v)$/i.test(file.name))return 'video';
    return null;
  }
  (()=>{
    const overlay=document.createElement('div');overlay.className='video-workspace-drop-zone';overlay.hidden=true;overlay.setAttribute('aria-hidden','true');
    const message=document.createElement('strong');overlay.append(message);document.body.append(overlay);let depth=0;
    const fileDrag=event=>Array.from(event.dataTransfer?.types||[]).includes('Files');
    const available=()=>active&&Boolean(scene())&&!loading&&!submitting&&!motionUploading&&!audioUploading&&!document.querySelector('dialog[open]');
    const relevant=event=>active&&!swapMode()&&fileDrag(event)&&!document.querySelector('dialog[open]');
    function targetSlot(event){
      if(event.target.closest?.('#video-advanced-output,#video-advanced-tab-output'))return 'output';
      if(event.target.closest?.('#video-advanced-reference,#video-advanced-tab-reference'))return 'reference';
      return null;
    }
    function clear(){depth=0;overlay.hidden=true;}
    function show(event){
      const slot=targetSlot(event);overlay.hidden=false;
      message.textContent=slot==='output'?'Drop audio or extract a video’s soundtrack':slot==='reference'?'Drop voice audio or extract it from a video':'Drop video or audio into this shot';
    }
    document.addEventListener('dragenter',event=>{if(!relevant(event))return;event.preventDefault();if(available()){depth++;show(event);}});
    document.addEventListener('dragover',event=>{if(!relevant(event))return;event.preventDefault();event.dataTransfer.dropEffect=available()?'copy':'none';if(available())show(event);else clear();});
    document.addEventListener('dragleave',event=>{if(overlay.hidden)return;depth=Math.max(0,depth-1);if(!depth||!event.relatedTarget)clear();});
    document.addEventListener('drop',event=>{
      if(!relevant(event)){clear();return;}event.preventDefault();event.stopPropagation();const allowed=available(),slot=targetSlot(event);clear();if(!allowed)return;
      const files=Array.from(event.dataTransfer.files||[]),videos=files.filter(file=>droppedVideoMediaKind(file)==='video'),audios=files.filter(file=>droppedVideoMediaKind(file)==='audio');
      if(!files.length||videos.length+audios.length!==files.length){toast('Drop a video or audio file. Images belong in the Project Library.');return;}
      if(videos.length>1||audios.length>1||slot&&files.length>1){toast(slot?'Drop one file into an audio slot.':'Drop one video and one audio at a time.');return;}
      if(videos.some(file=>file.size>128*1024*1024)||audios.some(file=>file.size>64*1024*1024)){toast('Use videos up to 128 MB and audio up to 64 MB.');return;}
      clearDroppedAudio();const projectId=project.id,shot=sceneId;
      safe(async()=>{
        if(slot){revealMediaSlot(slot);await uploadAudioFile(slot,files[0]);return;}
        if(videos.length){revealMediaSlot('motion');await uploadMotionFile(videos[0]);}
        if(!active||project?.id!==projectId||sceneId!==shot)return;
        if(audios.length)chooseDroppedAudio(audios[0]);
        else if(videos.length)chooseDroppedAudio(videos[0],true);
      });
    });
    document.addEventListener('keydown',event=>{if(active&&event.key==='Escape'){clear();clearDroppedAudio();}});
    document.addEventListener('click',event=>{const chooser=$v('drop-audio-choice');if(chooser&&!chooser.contains(event.target))clearDroppedAudio();});
    const visibility=new MutationObserver(()=>{if(!active||swapMode()||document.querySelector('dialog[open]'))clear();});visibility.observe($v('workspace'),{attributes:true,attributeFilter:['hidden']});
    window.addEventListener('dragend',clear);window.addEventListener('blur',clear);
  })();
  $v('audio-exact').onchange=()=>{if($v('audio-exact').checked)outputAudioId=audioReferenceId;else if(outputAudioId===audioReferenceId)outputAudioId='';changed();};
  function syncSoundtrack(){const context={project:project?.id,shot:sceneId,take:selected};soundtrackQueue=soundtrackQueue.catch(()=>{}).then(async()=>{if(project?.id!==context.project||sceneId!==context.shot||selected!==context.take)return;await save();const take=scene()?.drafts.find(d=>d.id===selected&&d.status==='succeeded');if(!take)return;if(outputAudioId&&take.applied_output_audio_id!==outputAudioId)await applyAudio();else if(!outputAudioId&&take.applied_output_audio_id)await applyAudio(true);});return soundtrackQueue;}
  async function applyAudio(restore=false){
    const take=scene()?.drafts.find(d=>d.id===selected&&d.status==='succeeded');if(!take||applyingAudio||!restore&&!outputAudioId)return;
    const projectId=project.id,shot=sceneId,id=take.id;applyingAudio=true;const preview=$v('preview').querySelector('video');if(preview){preview.pause();preview.removeAttribute('src');preview.load();}renderAdvanced(project);
    try{await save();const result=await api(`/projects/${projectId}/shots/${shot}/drafts/${id}/soundtrack`,'POST',{audio_id:outputAudioId,restore});if(project?.id===projectId){project=result;$v('preview').dataset.draft='';}toast(restore?'Original H3 audio restored.':'Final audio applied.');}
    finally{applyingAudio=false;$v('preview').dataset.draft='';render(project);}
  }
  $v('apply-audio').onclick=()=>safe(()=>applyAudio());$v('restore-audio').onclick=()=>safe(()=>applyAudio(true));

  function reuseVideoTakeSettings(id,notify=true){
    const current=scene(),take=current?.drafts.find(d=>d.id===id);if(!take?.settings)return;
    load({...current,...structuredClone(take.settings),id:current.id,title:current.title,drafts:current.drafts},true);
    selected=take.id;saveVideoPreferences();changed();if(notify)$v('prompt').focus({preventScroll:true});
    if(notify)toast('Prompt and settings restored from this take.');
  }
  function renderTakes(current){
    const root=$v('takes'),stamp=JSON.stringify([current.id,selected,current.approved?.draft_id,current.drafts.map(d=>[d.id,d.status,d.file,Boolean(d.settings)])]);
    window.DirectorMotion?.pruneVideos();
    $v('take-count').textContent=String(current.drafts.filter(d=>d.status==='succeeded').length);
    if(root.dataset.stamp===stamp){for(const card of root.children)window.DirectorMotion?.take(card,current.drafts.find(d=>d.id===card.dataset.draft));return;}root.dataset.stamp=stamp;
    root.replaceChildren(...current.drafts.map((d,index)=>{
      const card=document.createElement('article');card.className='take'+(d.id===selected?' selected':'')+(d.id===current.approved?.draft_id?' approved-take':'');card.dataset.active=String(activeDraft(d));card.dataset.draft=d.id;
      const choose=button('','take-select',()=>{selected=d.id;render(project);});choose.setAttribute('aria-label',`Video take ${index+1}`);
      if(d.status==='succeeded'){const thumb=document.createElement('video');thumb.dataset.lazyVideo=fileURL(d.file)+'#t=0.1';thumb.preload='none';window.DirectorMotion?.observeVideo(thumb);thumb.muted=true;thumb.playsInline=true;choose.append(thumb);}
      else{const state=document.createElement('div');state.className='take-placeholder';state.textContent=d.status;choose.append(state);}
      const number=document.createElement('span');number.className='take-overlay';number.textContent=String(index+1).padStart(2,'0');choose.append(number);if(d.id===current.approved?.draft_id){const mark=document.createElement('span');mark.className='take-approved';mark.innerHTML=DirectorIcons.save;mark.title='Approved take';choose.append(mark);}card.append(choose);
      if(d.settings){const reuse=button('Reuse Settings','take-reuse',()=>reuseVideoTakeSettings(d.id));reuse.setAttribute('aria-label',`Reuse prompt and settings from video take ${index+1}`);card.append(reuse);}
      window.DirectorMotion?.take(card,d);return card;
    }));
  }
  function closeChoices(){
    const menu=$v('choice-menu'),trigger=choice&&$v('choose-'+choice);
    if(menu.contains(document.activeElement))trigger?.focus({preventScroll:true});
    choice=null;window.DirectorControls.closeChoices(menu);
    for(const id of ['frame','size','duration','mode'])$v('choose-'+id).setAttribute('aria-expanded','false');
  }
  function updateChoices(){
    $v('choose-mode').hidden=!swapMode();
    $v('choose-seed').disabled=loading||submitting;
    $v('frame-value').textContent=$v('ratio').value;$v('size-value').textContent=Number($v('mp').value)+' MP';$v('duration-value').textContent=$v('duration').value+'s';
    for(const id of ['frame','size','duration','mode'])$v('choose-'+id).disabled=loading||submitting;
  }
  function showChoices(kind){
    if(kind==='mode'&&!swapMode()){closeChoices();return;}
    if(choice===kind){closeChoices();return;}choice=kind;const menu=$v('choice-menu');menu.replaceChildren();
    for(const id of ['frame','size','duration','mode'])$v('choose-'+id).setAttribute('aria-expanded',String(id===kind));
    if(swapMode()&&kind==='mode')DirectorSwap.modeChoices(menu);
    else if(swapMode()&&kind==='duration')DirectorSwap.durationChoices(menu);
    else if(kind==='frame')window.DirectorControls.ratioChoices(menu,$v('ratio').value,value=>{$v('ratio').value=value;changed();});
    else window.DirectorControls.sliderChoices(menu,{kind,value:$v(kind==='size'?'mp':'duration').value,
      min:kind==='size'?.2:2,max:kind==='size'?2:30,step:kind==='size'?.1:1,
      ticks:kind==='size'?['0.2','0.5','1','1.5','2']:['2','5','10','20','30'],id:'video-choice-slider',
      onChange:value=>{$v(kind==='size'?'mp':'duration').value=String(value);changed();}});
    window.DirectorControls.openChoices(menu);
  }

  function showScenes(){if(swapMode())DirectorNavigator.open({title:'Swaps',current:sceneId,newLabel:'+ New swap',items:scenes().map(s=>({id:s.id,title:s.title,video:true,file:s.approved?.file||s.drafts.filter(d=>d.status==='succeeded').at(-1)?.file,count:s.drafts.length})),onSelect:selectVideoShot,onNew:newScene});else if(project)openLibrary('all','shots');}
  async function selectVideoShot(id,takeId){await save();if(!active)await enter();const item=project.shots.find(s=>s.id===id&&s.mode==='video');if(item&&DirectorApps.id!==(item.studio_app==='second-take'?'second-take':'directors-cut'))await DirectorApps.select(item.studio_app==='second-take'?'second-take':'directors-cut');if(!active)await enter();const target=project.shots.find(s=>s.id===id&&s.mode==='video');if(target){load(target);if(target.drafts.some(d=>d.id===takeId))selected=takeId;render(project);}}
  async function deleteVideoShot(id){await save();project=await api(`/projects/${project.id}/shots/${id}`,'DELETE');if(id===sceneId){sceneId=null;selected=null;const next=scenes()[0];if(next)load(next);else if(active)await newScene();}render(project);}
  async function deleteVideoShots(ids){
    await save();project=await api(`/projects/${project.id}/shots/batch`,'POST',{action:'delete',ids});
    if(ids.includes(sceneId)){sceneId=null;selected=null;const next=scenes()[0];if(next)load(next);else if(active)await newScene();}render(project);
  }
  function openPicker(){if(!project)return;$v('picker-search').value='';$v('asset-picker').showModal();renderPicker();$v('picker-search').focus();}
  function renderPicker(){
    if(!$v('asset-picker').open)return;
    const selectedIds=referenceIds(),term=$v('picker-search').value.trim().toLowerCase();
    const assets=(project?.assets||[]).filter(a=>a.file&&(!term||(a.name+' '+a.handle).toLowerCase().includes(term)));
    $v('picker-grid').replaceChildren(...assets.map(asset=>{
      const chosen=selectedIds.includes(asset.id),card=button('','video-picker-asset',()=>useAsset(asset));card.disabled=chosen;card.setAttribute('aria-label',(chosen?'Selected ':'Add reference @')+asset.handle);
      const image=document.createElement('img');image.src=fileURL(asset.thumbnail||asset.file);image.alt='';image.loading='lazy';
      const plus=document.createElement('span');plus.className='video-picker-plus';plus.textContent=chosen?'✓':'＋';
      const name=document.createElement('span');name.className='video-picker-name';name.textContent='@'+asset.handle;card.append(image,plus,name);return card;
    }));
    if(!assets.length){const empty=document.createElement('p');empty.textContent='No assets found.';$v('picker-grid').append(empty);}
    $v('picker-count').textContent=selectedIds.length+' / 9 references';
  }
  const mentionTail=/@[ \t]*((?:(?:v[ií]deo|[aá]udio)[ _]*\d*|[\p{L}\p{N}_]*))$/iu;
  const mentionKey=text=>text.normalize('NFD').replace(/[\u0300-\u036f]/g,'').replace(/[ _]/g,'').toLowerCase();
  function mentionOptions(){
    const field=$v('prompt'),match=field.value.slice(0,field.selectionStart).match(mentionTail);
    if(!match)return [];
    const query=mentionKey(match[1]);
    return [...mediaMentions(),...(project?.assets||[]).filter(a=>a.file&&(!swapMode()||referenceIds().includes(a.id)))].filter(a=>mentionKey('@'+a.handle+' '+a.name).includes(query));
  }
  function useMention(asset){
    if(!asset.media&&!referenceIds().includes(asset.id)&&referenceIds().length>=9){toast('H3 supports up to 9 image references.');return;}
    const field=$v('prompt'),position=field.selectionStart;
    const before=field.value.slice(0,position).replace(mentionTail,'@'+asset.handle+' ');
    field.value=before+field.value.slice(position);syncMentionReferences();
    $v('mentions').hidden=true;field.focus();field.setSelectionRange(before.length,before.length);if(swapMode()&&!cutEdit)DirectorSwap.setDirection(field.value);changed();
  }
  function renderMentions(){
    const options=mentionOptions(),menu=$v('mentions');mentionIndex=0;menu.hidden=!options.length;menu.scrollTop=0;
    menu.replaceChildren(...options.map((asset,index)=>{const item=button('','video-mention-option',()=>useMention(asset));item.setAttribute('role','option');item.setAttribute('aria-selected',String(index===0));
      if(asset.media==='audio'){const icon=document.createElement('span');icon.className='video-mention-media-icon';icon.innerHTML=DirectorIcons.waveform;item.append(icon);}
      else{const image=document.createElement('img');image.src=fileURL(asset.thumbnail||asset.file);image.alt='';item.append(image);}
      const text=document.createElement('span');text.textContent='@'+asset.handle;item.title=asset.name;item.append(text);item.onmousedown=event=>event.preventDefault();return item;}));
  }
  $v('title').addEventListener('input',changed);
  $v('prompt').addEventListener('input',()=>{if(swapMode()&&!cutEdit)DirectorSwap.setDirection($v('prompt').value);syncMentionReferences();changed();renderMentions();});
  $v('prompt').addEventListener('scroll',()=>{$v('prompt-highlights').scrollTop=$v('prompt').scrollTop;$v('reference-hover').hidden=true;});
  $v('prompt').addEventListener('mousemove',event=>{
    const mark=[...$v('prompt-highlights').querySelectorAll('mark')].find(el=>[...el.getClientRects()].some(r=>event.clientX>=r.left&&event.clientX<=r.right&&event.clientY>=r.top&&event.clientY<=r.bottom));
    const tooltip=$v('reference-hover'),asset=[...mediaMentions(),...(project?.assets||[])].find(a=>a.id===mark?.dataset.asset);tooltip.hidden=!asset;
    if(asset){const image=$v('reference-hover-image');image.hidden=asset.media==='audio';if(!image.hidden)image.src=fileURL(asset.thumbnail||asset.file);$v('reference-hover-name').textContent='@'+asset.handle+(asset.media?' · '+asset.name:'');tooltip.style.left=Math.min(event.clientX+14,window.innerWidth-190)+'px';tooltip.style.top=Math.max(8,Math.min(event.clientY+18,window.innerHeight-220))+'px';}
  });
  $v('prompt').addEventListener('mouseleave',()=>{$v('reference-hover').hidden=true;});
  if(typeof ResizeObserver!=='undefined')new ResizeObserver(renderPromptHighlights).observe($v('prompt'));
  $v('prompt').addEventListener('keydown',event=>{
    if($v('mentions').hidden||event.ctrlKey||event.metaKey)return;
    if(event.key==='Escape'){event.preventDefault();event.stopPropagation();$v('mentions').hidden=true;return;}
    const options=mentionOptions();if(!options.length)return;
    if(event.key==='ArrowDown'||event.key==='ArrowUp'){event.preventDefault();mentionIndex=(mentionIndex+(event.key==='ArrowDown'?1:-1)+options.length)%options.length;[...$v('mentions').children].forEach((item,index)=>item.setAttribute('aria-selected',String(index===mentionIndex)));revealMentionOption($v('mentions'),mentionIndex);}
    if(event.key==='Enter'&&options[mentionIndex]){event.preventDefault();useMention(options[mentionIndex]);}
  });
  $v('prompt').addEventListener('blur',()=>setTimeout(()=>{const menu=$v('mentions');if(!menu.matches(':hover')&&!menu.contains(document.activeElement))menu.hidden=true;},150));
  $v('mentions').addEventListener('mouseleave',()=>{if(document.activeElement!==$v('prompt'))$v('mentions').hidden=true;});

  function saveVideoPreferences(){
    videoPreferences={video_preset:$v('preset').value,model_files:{...selectedVideoModels},loras:structuredClone(selectedVideoLoras.filter(row=>! /(?:h3_character_swap|minimax_h3_motion_transfer_tara|minimax_h3_character_swap)/i.test(row.name))),selflift:$v('selflift').checked,enhancer_model:videoEnhancerModel};
    localStorage.setItem('directors-cut-video-engine',JSON.stringify(videoPreferences));
  }
  function selectedReadiness(){
    const profile=config?.video?.presets?.[$v('preset').value];if(!profile?.loaders)return profile;
    const files=active?selectedVideoModels:(videoPreferences?.model_files||selectedVideoModels);
    const readinessLoras=swapMode()?[{name:DirectorSwap.loraName,enabled:true,strength:1}]:selectedVideoLoras;
    const missing=[...(profile.fixed_missing||[]),...profile.loaders.filter(loader=>!loader.options.includes(files[loader.node]||loader.default)).map(loader=>'File: '+(files[loader.node]||loader.default)),...readinessLoras.filter(row=>row.enabled&&row.strength!==0&&!config?.video?.loras?.files?.includes(row.name)).map(row=>'LoRA: '+row.name)];
    if(swapMode()&&$v('preset').value==='hyperflow')missing.push('HyperFlow does not support Character Swap. Choose Base or OmniRef.');
    if($v('selflift').checked&&!config?.video?.selflift?.ready)missing.push('Install SelfLift in Connection → Workflow nodes and restart ComfyUI.');
    return {...profile,ready:!missing.length,missing};
  }
  function renderSettings(){
    if(!active&&videoPreferences)$v('selflift').checked=Boolean(videoPreferences.selflift);
    $v('selflift-status').textContent=config?.video?.selflift?.ready?'':'Install the optional SelfLift node under Connection → Workflow nodes.';
    if(!active&&videoPreferences){$v('preset').value=videoPreferences.video_preset||'original';selectedVideoModels={...videoPreferences.model_files};}
    normalizeModelRecipe();
    const hyper=$v('preset').querySelector('option[value=hyperflow]');if(hyper)hyper.disabled=swapMode();
    for(const b of document.querySelectorAll('[data-video-family]')){b.setAttribute('aria-pressed',String(b.dataset.videoFamily===$v('preset').value));b.disabled=swapMode()&&b.dataset.videoFamily==='hyperflow';}
    $v('family-note').textContent=$v('preset').value==='hyperflow'?'HyperFlow does not support Character Swap.':'';
    const profile=selectedReadiness(),root=$v('model-files');
    const stamp=JSON.stringify([$v('preset').value,profile?.loaders,selectedVideoModels,config?.video?.models,window.DirectorModelDownloads?.options('video','diffusion',[]).map(o=>o.textContent)]);
    if(root.dataset.stamp!==stamp){root.dataset.stamp=stamp;root.replaceChildren(...(profile?.loaders||[]).filter(loader=>!['145','156'].includes(loader.node)).map((loader,index)=>{
      const box=document.createElement('div');box.className='model-file';const label=document.createElement('label');label.textContent=loader.role;label.htmlFor='video-model-file-'+index;
      const select=document.createElement('select');select.id=label.htmlFor;const chosen=selectedVideoModels[loader.node]||loader.default;
      const options=loader.options;
      const role=({'127':'diffusion','128':'encoder','119':'video_vae','120':'audio_vae','145':'acceleration'})[loader.node];
      const downloads=window.DirectorModelDownloads;
      select.replaceChildren(...(downloads&&role&&loader.node!=='127'?[...downloads.options('video',role,options),...downloads.unavailable('h3',role)]:options.map(file=>new Option(file,file))));
      if(![...select.options].some(o=>o.value===chosen))select.append(new Option('Not installed · '+chosen,chosen));select.value=chosen;select.disabled=!select.options.length;
      select.onchange=()=>{
        selectedVideoModels[loader.node]=select.value;
        if(loader.node==='127'){
          const target=config.video.models?.find(m=>m.file===select.value)?.preset||(/hyperflow/i.test(select.value)?'hyperflow':/omni/i.test(select.value)?'fast-omni':'original');$v('preset').value=target;
          const loaders=config.video.presets[target].loaders;
          selectedVideoModels=Object.fromEntries(loaders.map(row=>[row.node,row.node==='127'?select.value:row.options.includes(selectedVideoModels[row.node])?selectedVideoModels[row.node]:row.default]));
        }
        saveVideoPreferences();if(active)changed();else renderSettings();window.DirectorDropdowns.sync();
      };
      box.append(label,select);if(downloads&&role){downloads.decorate(box,select,'video',role);if(['diffusion','encoder'].includes(role))downloads.formatTabs(box,select,'video-'+role);}return box;
    }));}
    $v('model-status').textContent=profile?.ready?'':profile?.missing?.join(' ')||'Connect the engine to list installed models.';
    $v('model-status').className=profile?.ready?'control-help ready':'control-help';
    renderVideoLoras();
    renderDirection();renderVideoEnhancer();
  }
  const videoPresetIcons={genre:'render_style',era:'era',tempo:'atmosphere',camera:'pose',sensor:'sensor',lens:'lens_type',aperture:'lens_type',framing:'framing',palette:'grade',lighting:'lighting',movement:'proportions'};
  const cameraKeys=['lens','aperture','focal_length'];
  const focalStops=[5,8,10,12,14,16,18,20,24,28,30,35,40,50,55,65,75,85,95,100,105,135,150,180,200,250,300,400,500];
  const focalPosition=mm=>Math.log(Math.max(5,Math.min(500,mm))/5)/Math.log(100)*1000;
  const focalAt=position=>focalStops.reduce((best,mm)=>Math.abs(focalPosition(mm)-position)<Math.abs(focalPosition(best)-position)?mm:best);
  const directionKeys=['framing','movement','tempo'];
  function cameraGroup(categories,keys=cameraKeys,title='Camera',icon='pose'){
    const box=document.createElement('details');box.className='character-option preset-section video-camera-group';box.dataset.category=keys===cameraKeys?'camera_group':'direction_group';
    const summary=document.createElement('summary');summary.className='preset-heading';
    const label=document.createElement('span');label.className='preset-label';label.textContent=title;
    const current=document.createElement('span');current.className='preset-current';
    const arrow=document.createElement('span');arrow.className='preset-chevron';arrow.innerHTML=window.DirectorIcons.chevron;
    summary.append(presetIcon({id:icon}),label,current,arrow);
    const body=document.createElement('div');body.className='video-camera-body';
    const tabs=document.createElement('div');tabs.className='video-camera-tabs';tabs.setAttribute('role','group');tabs.setAttribute('aria-label',title+' controls');
    const panel=document.createElement('div');panel.id='video-'+box.dataset.category+'-panel';panel.className='video-camera-panel';
    let activeKey=keys[0];
    const labels={...Object.fromEntries(categories.map(c=>[c.key,c.label])),camera:'Type',sensor:'Sensor',lens:'Lens',aperture:'Aperture',focal_length:'Focal length',movement:'Movement',tempo:'Pacing'};
    function drawPanel(){
      const category=categories.find(item=>item.key===activeKey);if(!category)return;
      const value=videoDirection[activeKey]||'',stamp=JSON.stringify([activeKey,value]);
      if(panel.dataset.stamp===stamp)return;
      if(panel.contains(document.activeElement))return;
      panel.dataset.stamp=stamp;panel.dataset.previewCategory=activeKey;panel.replaceChildren();
      const choices=document.createElement('div');choices.className='video-camera-choices';if(['movement','framing','tempo','camera','sensor','lens','aperture','focal_length'].includes(activeKey))choices.classList.add('video-movement-previews');
      const choose=selected=>{if(selected)videoDirection[activeKey]=selected;else delete videoDirection[activeKey];changed();};
      const auto=button('Auto','generation-choice',()=>{auto.blur();choose('');});auto.setAttribute('aria-pressed',String(!value));choices.append(auto);
      const numeric=activeKey==='aperture'||activeKey==='focal_length';
      if(numeric){
        const sliderBox=document.createElement('div'),aperture=activeKey==='aperture';
        const index=Math.max(0,category.options.indexOf(value|| (aperture?'f/4':'50mm')));
        const currentFocal=parseInt(value)||50;
        // Retain older saved focal values while snapping new choices to familiar lenses.
        const stops=[...new Set([...focalStops,currentFocal])].sort((a,b)=>a-b);
        window.DirectorControls.sliderChoices(sliderBox,{kind:'camera',value:aperture?index:focalPosition(currentFocal),
          min:0,max:aperture?category.options.length-1:1000,step:aperture?1:'any',
          snapPoints:aperture?[]:stops.map(focalPosition),
          ticks:aperture?['f/0.7','f/1.4','f/2.8','f/5.6','f/11','f/32'].map(label=>({value:category.options.indexOf(label),label})):[5,16,50,150,500].map(mm=>({value:focalPosition(mm),label:mm+' mm'})),id:'video-camera-slider',caption:category.label,
          format:n=>aperture?category.options[n]:(Math.abs(n-focalPosition(currentFocal))<.001?currentFocal:focalAt(n))+' mm',
          onChange:n=>choose(aperture?category.options[n]:(Math.abs(n-focalPosition(currentFocal))<.001?currentFocal:focalAt(n))+'mm')});
        sliderBox.classList.add('camera-inline-slider');panel.append(sliderBox);
        window.DirectorVideoPreviews?.sliderPreview(sliderBox.querySelector('input[type="range"]'),activeKey);
      }else for(const option of category.options.filter(option=>!(activeKey==='lens'&&option==='Halation vintage'))){
        const item=button(option,'generation-choice',()=>{item.blur();choose(option);});item.setAttribute('aria-pressed',String(value===option));window.DirectorVideoPreviews?.decorate(item,activeKey,option);choices.append(item);
      }
      const custom=button('+ Custom','generation-choice',()=>{custom.blur();choose('custom:');panel.querySelector('textarea')?.focus();});custom.setAttribute('aria-pressed',String(value.startsWith('custom:')));choices.append(custom);
      panel.append(choices);
      if(value.startsWith('custom:')){
        const field=document.createElement('textarea');field.className='custom-preset-text';field.maxLength=1000;field.value=value.slice(7);field.placeholder='Your own '+category.label.toLowerCase()+'…';field.setAttribute('aria-label','Custom '+category.label);
        field.oninput=()=>{choose(field.value.trim()?'custom:'+field.value:'');resizeCustomPreset(field);};
        field.onblur=()=>{panel.dataset.stamp='';drawPanel();};panel.prepend(field);
      }
      panel.classList.remove('camera-panel-enter');void panel.offsetWidth;panel.classList.add('camera-panel-enter');
    }
    for(const key of keys){
      const tab=button('','video-camera-tab',()=>{activeKey=key;tab.blur();panel.dataset.stamp='';box.syncCamera();});tab.dataset.key=key;tab.setAttribute('aria-controls',panel.id);
      const name=document.createElement('span');name.textContent=labels[key];const value=document.createElement('strong');tab.append(name,value);tabs.append(tab);
    }
    box.syncCamera=()=>{
      const selected=keys.filter(key=>videoDirection[key]);current.textContent=selected.length?selected.length+' selected':'';box.classList.toggle('has-selection',selected.length>0);
      for(const tab of tabs.children){const value=videoDirection[tab.dataset.key]||'';tab.querySelector('strong').textContent=value.startsWith('custom:')?'Custom':value||'Auto';tab.title=labels[tab.dataset.key]+': '+(value.startsWith('custom:')?value.slice(7):value||'Auto');tab.setAttribute('aria-pressed',String(activeKey===tab.dataset.key));}
      drawPanel();
    };
    summary.onclick=event=>{
      event.preventDefault();const opening=!box.open,scroller=window.DirectorBoard?.videoScroller()||$v('editor-scroll'),top=summary.getBoundingClientRect().top;
      if(opening)for(const other of $v('preset-options').querySelectorAll('.preset-section[open]'))if(other!==box)other.open=false;
      box.open=opening;scroller.scrollTop+=summary.getBoundingClientRect().top-top;
      if(opening)requestAnimationFrame(()=>body.scrollIntoView({block:'nearest',behavior:'smooth'}));
    };
    body.append(tabs,panel);box.append(summary,body);return box;
  }
  function renderDirection(){
    if(videoDirection.lens==='Halation vintage')delete videoDirection.lens;delete videoDirection.camera;delete videoDirection.sensor;delete videoDirection.palette;delete videoDirection.lighting;
    delete videoDirection.era;delete videoDirection.genre;
    const root=$v('preset-options'),categories=config?.video?.prompt_presets||[],stamp=JSON.stringify(categories);
    $v('preset-count').textContent=Object.keys(videoDirection).length?Object.keys(videoDirection).length+' selected':'Optional details';
    if(root.dataset.stamp!==stamp){root.dataset.stamp=stamp;
      const visible=categories.filter(category=>!['palette','era','genre','lighting','sensor','camera'].includes(category.key)&&(!cameraKeys.includes(category.key)||category.key==='lens')&&(!directionKeys.includes(category.key)||category.key==='framing'));
      root.replaceChildren(...visible.map(category=>{
        if(category.key==='lens')return cameraGroup(categories);
        if(category.key==='framing')return cameraGroup(categories,directionKeys,'Direction','framing');
        const iconCategory={id:videoPresetIcons[category.key]||category.key};
        const box=document.createElement('details');box.className='character-option preset-section';box.dataset.category=category.key;
        const summary=document.createElement('summary');summary.className='preset-heading';
        const label=document.createElement('span');label.className='preset-label';label.textContent=category.label;
        const count=document.createElement('span');count.className='preset-option-count';count.textContent=String(category.options.length);
        const selected=document.createElement('span');selected.className='preset-current';
        const arrow=document.createElement('span');arrow.className='preset-chevron';arrow.innerHTML=window.DirectorIcons.chevron;arrow.setAttribute('aria-hidden','true');
        summary.append(presetIcon(iconCategory),label,count,selected,arrow);
        const custom=document.createElement('textarea');custom.className='custom-preset-text';custom.rows=6;custom.maxLength=1000;custom.hidden=true;custom.placeholder='Your own '+category.label.toLowerCase()+'…';custom.setAttribute('aria-label','Custom '+category.label.toLowerCase());
        const grid=document.createElement('div');grid.className='preset-card-grid';grid.setAttribute('role','group');grid.setAttribute('aria-label',category.label+' options');
        const options=[{label:'Custom',value:'custom:'},{label:'No preference',value:''},...category.options.map(value=>({label:value,value}))];
        grid.append(...options.map(option=>{
          const card=button('','preset-card',()=>{
            if(option.value)videoDirection[category.key]=option.value;else delete videoDirection[category.key];changed();
            if(option.value==='custom:'){resizeCustomPreset(custom);custom.focus({preventScroll:true});custom.scrollIntoView({block:'nearest',behavior:'smooth'});}
          });card.dataset.value=option.value;
          const visual=document.createElement('span');visual.className='preset-card-image';
          const preview=config?.preview_images?.['asset-location-'+iconCategory.id]?.[option.value];
          if(!option.value||option.value==='custom:'){visual.classList.add('preset-card-symbol');visual.textContent=option.value?'+':'○';}
          else if(category.palettes?.[option.value]){visual.classList.add('video-palette-preview');for(const color of category.palettes[option.value]){const swatch=document.createElement('i');swatch.style.backgroundColor=color;visual.append(swatch);}}
          else if(preview){const image=document.createElement('img');image.src=preview;image.alt='';image.loading='lazy';visual.append(image);image.onerror=()=>{image.remove();visual.append(presetIcon(iconCategory));};}
          else visual.append(presetIcon(iconCategory));
          const text=document.createElement('span');text.className='preset-card-label';text.textContent=window.DirectorControls.presetLabel(option.label);card.append(visual,text);return card;
        }));
        custom.oninput=()=>{const text=custom.value;if(text.trim())videoDirection[category.key]='custom:'+text;else delete videoDirection[category.key];changed();resizeCustomPreset(custom);};
        custom.onblur=()=>{if(!custom.value.trim()&&videoDirection[category.key]?.startsWith('custom:')){delete videoDirection[category.key];changed();}};
        summary.addEventListener('click',event=>{
          event.preventDefault();const opening=!box.open,scroller=window.DirectorBoard?.videoScroller()||$v('editor-scroll'),top=summary.getBoundingClientRect().top;
          if(opening)for(const other of root.querySelectorAll('.preset-section[open]'))if(other!==box)other.open=false;
          box.open=opening;scroller.scrollTop+=summary.getBoundingClientRect().top-top;
          if(opening)requestAnimationFrame(()=>{resizeCustomPreset(custom);revealPresetOptions(box,scroller);});
        });
        box.append(summary,custom,grid);return box;
      }));
    }
    for(const box of root.children){
      if(box.syncCamera){box.syncCamera();continue;}
      const value=videoDirection[box.dataset.category]||'',isCustom=value.startsWith('custom:');
      box.querySelector('.preset-current').textContent=isCustom?'Custom':window.DirectorControls.presetLabel(value);
      box.classList.toggle('has-selection',Boolean(value));
      for(const card of box.querySelectorAll('.preset-card'))card.setAttribute('aria-pressed',String(card.dataset.value===(isCustom?'custom:':value)));
      const custom=box.querySelector('textarea');custom.hidden=!isCustom;if(document.activeElement!==custom)custom.value=isCustom?value.slice(7):'';
    }
  }
  function renderVideoEnhancer(){
    const status=config?.video?.enhancer,files=status?.files||[],select=$v('enhancer-model');
    const options=window.DirectorModelDownloads?.options('video','enhancer',files)||files.map(file=>new Option(file,file)),stamp=JSON.stringify(options.map(o=>[o.value,o.textContent]));
    if(!videoEnhancerModel)videoEnhancerModel=status?.default||'';
    if(select.dataset.stamp!==stamp){select.dataset.stamp=stamp;select.replaceChildren(new Option('Choose video enhancer…',''),...options);const box=$v('enhancer-download');box.replaceChildren();window.DirectorModelDownloads?.decorate(box,select,'video','enhancer');}select.value=videoEnhancerModel;
    const ready=Boolean(status?.ready&&files.includes(videoEnhancerModel));$v('enhancer-toggle').disabled=!ready;
    if(!ready)$v('enhancer-toggle').checked=false;
    $v('enhancer-status').textContent=ready?(status.vision?'Local Qwen3.5 4B · reads attached references and expands video direction.':'Local Qwen3.5 4B · text-only video rewriter; reference tags are preserved.'):status?.missing?.join(' ')||'Install Qwen3.5 4B in ComfyUI/models/text_encoders and refresh.';
  }
  $v('reset-presets').onclick=()=>{videoDirection={};changed();};
  $v('selflift').onchange=()=>{saveVideoPreferences();if(active)changed();else renderSettings();};
  $v('enhancer-toggle').onchange=changed;
  $v('enhancer-model').onchange=()=>{videoEnhancerModel=$v('enhancer-model').value;saveVideoPreferences();if(active)changed();else renderSettings();};
  document.addEventListener('shared-enhancer-change',event=>{videoEnhancerModel=event.detail;saveVideoPreferences();if(active)changed();else renderSettings();});
  function renderVideoLoras(){
    const root=$v('lora-stack'),files=(config?.video?.loras?.files||[]).filter(file=>! /(?:h3_character_swap|minimax_h3_motion_transfer_tara|minimax_h3_character_swap)/i.test(file)),stamp=JSON.stringify([files,selectedVideoLoras]);if(root.dataset.stamp===stamp)return;root.dataset.stamp=stamp;
    root.replaceChildren(...selectedVideoLoras.map((row,index)=>({row,index})).filter(({row})=>! /(?:h3_character_swap|minimax_h3_motion_transfer_tara|minimax_h3_character_swap)/i.test(row.name)).map(({row,index})=>{
      const card=document.createElement('div');card.className='lora-row';
      const enabled=document.createElement('input');enabled.type='checkbox';enabled.checked=row.enabled;enabled.setAttribute('aria-label','Enable video LoRA '+(index+1));
      const select=document.createElement('select');select.setAttribute('aria-label','Video LoRA file');select.append(new Option('Choose H3-compatible LoRA…',''),...files.map(file=>new Option(file,file)));if(row.name&&!files.includes(row.name))select.append(new Option('Missing · '+row.name,row.name));select.value=row.name;
      const strength=document.createElement('input');strength.type='number';strength.min='-10';strength.max='10';strength.step='.05';strength.value=String(row.strength);strength.setAttribute('aria-label','Video LoRA strength');
      const save=()=>{saveVideoPreferences();if(active)changed();else renderSettings();};
      enabled.onchange=()=>{row.enabled=enabled.checked;save();};select.onchange=()=>{row.name=select.value;row.enabled=Boolean(row.name);save();};strength.onchange=()=>{const value=Number(strength.value);if(!strength.value||!Number.isFinite(value)||Math.abs(value)>10){strength.value=String(row.strength);return;}row.strength=value;save();};
      const weight=document.createElement('label');weight.className='lora-strength';weight.append('Strength',strength);const remove=button('×','subtle',()=>{selectedVideoLoras.splice(index,1);save();});remove.setAttribute('aria-label','Remove video LoRA');card.append(enabled,select,weight,remove);return card;
    }));$v('add-lora').disabled=selectedVideoLoras.length>=16;
  }
  $v('add-lora').onclick=()=>{selectedVideoLoras.push({name:'',strength:1,enabled:false});saveVideoPreferences();renderSettings();window.DirectorDropdowns.sync();};
  $v('import-lora').onclick=()=>$v('lora-file').click();$v('import-gguf').onclick=()=>$v('gguf-file').click();
  for(const kind of ['lora','gguf'])$v(kind+'-file').onchange=()=>safe(async()=>{
    const input=$v(kind+'-file'),file=input.files[0];if(!file)return;
    const body=new FormData();body.append('file',file);$v('import-status').textContent='Importing '+file.name+'…';
    try{const response=await fetch('/api/video/import/'+kind,{method:'POST',body}),result=await response.json();if(!response.ok)throw new Error(result.error||'Import failed');config=await api('/config');$v('import-status').textContent='Installed '+result.file;renderSettings();window.DirectorDropdowns.sync();}
    catch(error){$v('import-status').textContent=error.message;throw error;}finally{input.value='';}
  });
  for(const id of ['ratio','mp','duration'])$v(id).addEventListener('change',changed);
  for(const b of document.querySelectorAll('[data-video-family]'))b.onclick=()=>{if(b.disabled)return;$v('preset').value=b.dataset.videoFamily;$v('preset').onchange();};
  $v('preset').onchange=()=>{
    const loaders=config?.video?.presets?.[$v('preset').value]?.loaders;
    if(loaders)selectedVideoModels=Object.fromEntries(loaders.map(loader=>[loader.node,
      loader.options.includes(selectedVideoModels[loader.node])?selectedVideoModels[loader.node]:loader.default]));
    saveVideoPreferences();if(active)changed();else renderSettings();window.DirectorDropdowns.sync();
  };
  $v('refresh-models').onclick=()=>safe(async()=>{config=await api('/config');renderSettings();if(active)render(project);window.DirectorDropdowns.sync();toast('Installed video models refreshed.');});
  $v('generate').onclick=()=>safe(()=>cutEdit&&swapMode()?submitCut(false):run());
  $v('browse').onclick=showScenes;
  $v('rename').onclick=()=>safe(async()=>{
    if(!scene())return;const value=await window.DirectorNavigator.rename(scene().title);if(!value)return;
    $v('title').value=value;changed();await save();render(project);
  });
  $v('editor-heading').ondblclick=()=>$v('rename').onclick();
  $v('delete').onclick=()=>safe(async()=>{
    const current=scene();if(!current||!await confirmAssetDeletion({name:current.title}))return;
    await save();project=await api(`/projects/${pid}/shots/${current.id}`,'DELETE');
    const next=scenes()[0];sceneId=null;selected=null;
    if(next)load(next);else await newScene();render(project);toast('Shot deleted.');
  });
  for(const [id,delta] of [['previous',-1],['next',1]])$v(id).onclick=()=>{const drafts=scene()?.drafts||[],index=drafts.findIndex(d=>d.id===selected),take=drafts[index+delta];if(take){selected=take.id;render(project);}};
  $v('copy-prompt').onclick=()=>safe(async()=>{await navigator.clipboard.writeText($v('prompt-used').textContent);toast('Prompt copied.');});

  $v('picker-done').onclick=()=>$v('asset-picker').close();$v('picker-search').oninput=renderPicker;
  for(const kind of ['frame','size','duration','mode'])$v('choose-'+kind).onclick=()=>showChoices(kind);
  document.addEventListener('click',event=>{if(!event.target.closest('.video-quick-generation'))closeChoices();});
  document.addEventListener('keydown',event=>{if(event.key==='Escape'){closeChoices();}});
  document.getElementById('tab-video').onclick=()=>safe(enter);
  document.addEventListener('keydown',event=>{if(!active||event.key!=='Enter'||!event.ctrlKey||event.isComposing||document.querySelector('dialog[open]'))return;event.preventDefault();event.stopImmediatePropagation();if(!event.repeat)safe(()=>cutEdit&&swapMode()?submitCut(false):run());});
  function syncReferences(){const current=scene();if(!current)return;$v('prompt').value=current.prompt;refs=[...(current.reference_ids||[])];mentionedIds=new Set();syncMentionReferences();render(project);}
  window.DirectorVideo={openCutsFor,get cutEdit(){return cutEdit;},get finishCuts(){return finishCuts;},cutParts,chooseCutVersion,selectCut,closeCuts,async selectPreview(id,takeId){await save();if(!previewReturn)previewReturn={id:sceneId,selected,lastReady};sceneId=id;selected=takeId;lastReady=scene()?.drafts.filter(d=>d.status==='succeeded').at(-1)?.id;render(project);},endPreview(){if(previewReturn){const before=previewReturn;previewReturn=null;sceneId=before.id;selected=before.selected;lastReady=before.lastReady;render(project);}},workingSettings:capture,restoreWorking(snapshot){const current=scene();if(current){load({...current,...structuredClone(snapshot),id:current.id,title:current.title,drafts:current.drafts},true);changed();}},closeChoices,reuseSettings:reuseVideoTakeSettings,swapChanged:changed,get currentShot(){return scene();},get active(){return active;},enter,leave,render,useAsset,referenceIds,save,openPicker,renderSettings,syncReferences,selectShot:selectVideoShot,deleteShot:deleteVideoShot,deleteShots:deleteVideoShots,newShot:newScene};
})();

