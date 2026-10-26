const $ = id => document.getElementById(id);
function submissionId() {
  if(typeof globalThis.crypto.randomUUID==='function')return globalThis.crypto.randomUUID();
  // getRandomValues also works over HTTP on LAN/Tailscale addresses.
  const bytes=globalThis.crypto.getRandomValues(new Uint8Array(16));
  bytes[6]=(bytes[6]&15)|64;
  bytes[8]=(bytes[8]&63)|128;
  const hex=Array.from(bytes,b=>b.toString(16).padStart(2,'0')).join('');
  return `${hex.slice(0,8)}-${hex.slice(8,12)}-${hex.slice(12,16)}-${hex.slice(16,20)}-${hex.slice(20)}`;
}
let config, project, shotId, selectedDraft, timer, busy = false;
let imageEdit=null;
let selectedModels = {}, selectedLoras = [], legacyEnhancer = false;
let enginePreferences;
try {enginePreferences=JSON.parse(localStorage.getItem('directors-cut-engine') || 'null');}catch {enginePreferences=null;}
function saveEnginePreferences() {
  enginePreferences={model_format:$('model-format').value,model_files:{...selectedModels},enhancer_model:$('enhancer_model').value,loras:structuredClone(selectedLoras)};
  localStorage.setItem('directors-cut-engine',JSON.stringify(enginePreferences));
}
let assetTraitDrafts={character:{},location:{},prop:{}},traitEditorKind='character';
let creationMode='asset', referenceIds=[], libraryStamp='', libraryAssets=[], librarySource='', assetSaveSource=null, libraryLoadVersion=0, mentionIndex=0;
const modeOf=shot=>shot?.mode==='video'?'video':shot?.mode==='asset'?'asset':'legacy';
const visibleStudies=()=>project?.shots.filter(s=>modeOf(s)===creationMode) || [];
let pendingSubmission=null, queueState={items:[],waiting:0,running:0}, queueStamp='', takesStamp='';
let assetNameChange=null;
let uploadedReferenceIds=[];
const latestReadyByShot=new Map();
let takePage=0, takePageSize=0, takeGalleryKey='', revealSelectedTake=false;
const editorFields = ['title','prompt','style','camera','ratio','megapixels','steps','seed','lens_type','sensor','focal_length','f_stop','enhancer_model','lighting','light_color','light_notes','film','grade'];
const active = d => ['queued','submitting','running','pending','downloading'].includes(d.status);
const fileURL = (path,pid=project.id) => `/files/${encodeURIComponent(pid)}/${path.split('/').map(encodeURIComponent).join('/')}`;
async function api(path, method='GET', data) {
  const response = await fetch('/api'+path, {method, headers: data ? {'Content-Type':'application/json'} : {}, body: data ? JSON.stringify(data) : undefined});
  const result = await response.json();
  if (!response.ok) throw new Error(result.error || `Request failed (${response.status})`);
  return result;
}
function toast(message) { $('toast').textContent=message; $('toast').hidden=false; clearTimeout(timer); timer=setTimeout(()=>$('toast').hidden=true,6000); }
function button(text, cls, callback) { const el=document.createElement('button'); el.type='button'; el.textContent=text; el.className=cls; el.onclick=callback; return el; }
const workspaceItems=new Map();
function rememberWorkspaceItem(mode,id,projectId=project?.id){
  if(!projectId||!id)return;
  const key='directors-cut-last-item:'+projectId+':'+mode;workspaceItems.set(key,id);
  try{localStorage.setItem(key,id);}catch{}
}
function lastWorkspaceItem(mode,items,projectId=project?.id){
  const key='directors-cut-last-item:'+projectId+':'+mode;let id=workspaceItems.get(key);
  if(!id)try{id=localStorage.getItem(key);}catch{}
  return items.find(item=>item.id===id)||items[0];
}
function currentShot() { return project?.shots.find(s=>s.id===shotId); }
function settings() { return {...Object.fromEntries(editorFields.map(id=>[id,$(id).value])), title:currentShot()?.title || $('title').value,steps:25,seed:-1,prompt_enhancer:$('prompt_enhancer').checked, workflow_id:$('workflow-model').value, model_format:$('model-format').value, model_files:{...selectedModels}, loras:structuredClone(selectedLoras), mode:creationMode,edit_source:imageEdit?.source || null, edit_preset:imageEdit?$('edit-preset').value:'', reference_ids:[...referenceIds],upload_reference_ids:[...uploadedReferenceIds], asset_kind:$('asset_kind').value, ...captureAssetTraits()}; }
function setEditor(shot,exact=false) {
  rememberWorkspaceItem(modeOf(shot),shot.id);
  imageEdit=null;$('edit-preset').value=shot.edit_source?(shot.edit_preset||''):'';
  if(shot.edit_source){
    const sourceStudy=[...(project?.shots || []),...(project?.archived_shots || [])].find(s=>s.id===shot.edit_source.shot_id);
    const take=sourceStudy?.drafts.find(d=>d.id===shot.edit_source.draft_id);
    if(take)imageEdit={source:structuredClone(shot.edit_source),file:take.file,original:{...structuredClone(shot),...structuredClone(take.settings || {}),edit_source:null,title:shot.title}};
  }

  if(shot.workflow_id&&!['qwen21','qwen21-edit'].includes(shot.workflow_id))shot={...shot,workflow_id:'qwen21',model_files:{},enhancer_model:'',prompt_enhancer:false};
  if(enginePreferences&&!exact)shot={...shot,...enginePreferences,model_files:{...enginePreferences.model_files},workflow_id:'qwen21'};
  referenceIds=[...(shot.reference_ids || [])];
  uploadedReferenceIds=[...(shot.upload_reference_ids||[])];
  $('asset_kind').value=shot.asset_kind || 'character';setAssetEditor(shot);
  if(shot.workflow_id==='qwen21-edit')shot={...shot,workflow_id:'qwen21',model_files:Object.fromEntries(Object.entries(shot.model_files || {}).map(([key,value])=>[key.replace(/^459_/,''),value]))};
  $('workflow-model').value=shot.workflow_id || 'qwen21';
  $('model-format').value=shot.model_format || 'standard';
  renderEnhancers(shot.enhancer_model || '');
  const legacy=config.legacy_camera_defaults?.[shot.lens || 'Natural perspective'] || {};
  const defaults={...legacy,megapixels:2,lighting:'Natural light',light_color:'As scene / preset',light_notes:'',film:'Digital clean',grade:'Natural',f_stop:'',enhancer_model:''};
  for(const key of editorFields) $(key).value=shot[key] ?? defaults[key];
  legacyEnhancer=Boolean(shot.prompt_enhancer&&!shot.enhancer_model);
  $('prompt_enhancer').checked=Boolean(shot.prompt_enhancer&&shot.enhancer_model&&selectedEnhancer()?.ready);
  $('workflow-model').value=shot.workflow_id || 'qwen21';
  $('model-format').value=shot.model_format || 'standard';
  selectedModels={...(shot.model_files || {})};
  selectedLoras=structuredClone(shot.loras || []);
  renderLoras();renderModels();
  $('shot-heading').textContent=shot.title;
  updateResolutionSize();
}
function startImageEdit(){
  const shot=currentShot(),take=shot?.drafts.find(d=>d.id===selectedDraft&&d.status==='succeeded');if(!take)return;
  const original=imageEdit?.original || structuredClone(settings());
  imageEdit={source:{shot_id:shot.id,draft_id:take.id},file:take.file,original};referenceIds=[];uploadedReferenceIds=[];$('prompt').value='';$('edit-preset').value='';pendingSubmission=null;
  renderEnhancers();render();$('prompt').focus();
}
async function stopImageEdit(){
  if(!imageEdit)return;const original=imageEdit.original;imageEdit=null;
  setEditor({...currentShot(),...original,title:currentShot().title,edit_source:null});render();await saveNotes(false);
}
function currentWorkflow() { return config?.workflows?.find(w=>w.id===$('workflow-model').value); }
function renderModels() {
  renderEnhancers();renderLoras();
  window.DirectorVideo?.renderSettings();
  const workflow=currentWorkflow(), format=workflow?.formats[$('model-format').value];
  if(!format)return;
  const status=$('model-status');
  status.className='model-status '+(format.ready?'ready':'');
  status.textContent=format.ready ? '' : 'Setup needed · '+format.missing[0];
  $('models-heading').textContent='Engine settings';
  $('model-files').replaceChildren(...format.loaders.map((loader,index)=>{
    const box=document.createElement('div');box.className='model-file';
    const label=document.createElement('label');label.textContent=loader.role;label.htmlFor='file-'+index;
    const select=document.createElement('select');select.id='file-'+index;
    const role={UNETLoader:'diffusion',CLIPLoader:'encoder',VAELoader:'vae'}[loader.kind];
    const downloadOptions=window.DirectorModelDownloads;
    select.replaceChildren(...(downloadOptions?[...downloadOptions.options('qwen21',role,loader.options,$('model-format').value),...downloadOptions.unavailable('qwen21',role)]:loader.options.map(x=>new Option(x,x))));
    select.disabled=!select.options.length;
    select.value=[...select.options].some(o=>o.value===selectedModels[loader.node])?selectedModels[loader.node]:loader.default;
    if(!select.value&&select.options.length)select.selectedIndex=0;
    if(select.value)selectedModels[loader.node]=select.value;
    select.onchange=()=>{selectedModels[loader.node]=select.value;saveEnginePreferences();lock();};
    const info=document.createElement('code');
    const folder={UNETLoader:'diffusion_models',CLIPLoader:'text_encoders',VAELoader:'vae'}[loader.kind];
    info.textContent=`ComfyUI/models/${folder}/ · ${loader.target_kind}${loader.options.length?'':' · Expected family: '+loader.expected}`;
    box.append(label,select,info);if(downloadOptions)downloadOptions.decorate(box,select,'qwen21',role);return box;
  }));
  $('model-missing').replaceChildren(...format.missing.map(message=>{const p=document.createElement('p');p.textContent=message;return p;}));
  $('model-links').replaceChildren(...workflow.links.map(url=>{const a=document.createElement('a');a.href=url;a.target='_blank';a.rel='noreferrer';a.textContent=decodeURIComponent(url.replace('https://huggingface.co/',''));return a;}));
  const guide=document.createElement('a');guide.href='https://github.com/leejet/ComfyUI-GGUF';guide.target='_blank';guide.rel='noreferrer';guide.textContent='GGUF loader installation & compatibility ↗';$('model-links').append(guide);
  lock();
}
function renderLoras(){
  const files=config?.loras?.files || [],ready=Boolean(config?.loras?.ready);
  // Keep the active input intact while background connection checks refresh.
  const root=$('lora-stack'),stamp=JSON.stringify([files,ready,selectedLoras]);if(root.dataset.stamp===stamp)return;root.dataset.stamp=stamp;
  root.replaceChildren(...selectedLoras.map((row,index)=>{
    const card=document.createElement('div');card.className='lora-row';
    const enabled=document.createElement('input');enabled.type='checkbox';enabled.checked=row.enabled!==false;enabled.setAttribute('aria-label',`Enable LoRA ${index+1}`);
    const select=document.createElement('select');select.id='lora-file-'+index;select.setAttribute('aria-label',`LoRA ${index+1} file`);
    select.append(new Option('Choose LoRA…',''),...files.map(name=>new Option(name,name)));
    if(row.name&&!files.includes(row.name))select.append(new Option('Missing · '+row.name,row.name));select.value=row.name;select.disabled=!ready;
    const strength=document.createElement('input');strength.type='number';strength.min='-10';strength.max='10';strength.step='0.05';strength.value=String(row.strength);strength.title='Model strength';strength.setAttribute('aria-label',`LoRA ${index+1} strength`);
    const change=()=>{row.name=select.value;row.enabled=enabled.checked;saveEnginePreferences();root.dataset.stamp=JSON.stringify([files,ready,selectedLoras]);};
    enabled.onchange=change;select.onchange=()=>{enabled.checked=Boolean(select.value);change();};
    strength.onchange=()=>{const value=Number(strength.value);if(strength.value===''||!Number.isFinite(value)||value< -10||value>10){strength.value=String(row.strength);return;}row.strength=value;change();};
    const remove=button('×','subtle',()=>{selectedLoras.splice(index,1);saveEnginePreferences();renderLoras();});remove.setAttribute('aria-label',`Remove LoRA ${index+1}`);
    const weight=document.createElement('label');weight.className='lora-strength';weight.append('Strength',strength);card.append(enabled,select,weight,remove);return card;
  }));
  $('add-lora').disabled=!ready||!files.length||selectedLoras.length>=16;
  $('lora-status').textContent=!ready?'Connect ComfyUI with LoraLoaderModelOnly to load LoRAs.':!files.length?'No LoRAs found. Add compatible files to the folder above and refresh.':!selectedLoras.length?'No LoRAs selected.':`${selectedLoras.length} LoRA(s) · applied in list order. Disabled or zero-strength rows are skipped.`;
  window.DirectorDropdowns.sync();
}
$('add-lora').onclick=()=>{selectedLoras.push({name:'',strength:1,enabled:false});saveEnginePreferences();renderLoras();};
$('refresh-loras').onclick=()=>safe(async()=>{config=await api('/config');renderLoras();toast('Installed LoRAs refreshed.');});
function populateWorkflows() {
  $('workflow-model').replaceChildren(new Option('Qwen 2.1','qwen21'));$('workflow-model').value='qwen21';
}
function lock() {
  const shot=currentShot();
  for(const id of [...editorFields.filter(id=>id!=='enhancer_model'),'save-shot','batch-count','choose-frame','choose-size','choose-count']) $(id).disabled=!shot || busy;
  $('enhancer_model').disabled=busy;$('model-format').disabled=busy;$('workflow-model').disabled=false;
  $('asset_kind').disabled=!shot || busy;
  for(const field of $('character-options').querySelectorAll('input,select,textarea,button'))field.disabled=!shot || busy;
  $('clear-character').disabled=!shot || busy;
  const enhancer=selectedEnhancer();
  // A checked but missing model must still allow the user to switch enhancement off.
  $('prompt_enhancer').disabled=!shot || busy || (!enhancer?.ready&&!$('prompt_enhancer').checked);
  $('enhancer-file').textContent=enhancer?.installed ? enhancer.file : '';
  $('enhancer-status').textContent=enhancer ? (enhancer.ready ? enhancer.hint+( $('prompt_enhancer').checked?' Enabled.':' Switch on to use it.') : enhancer.missing.join('; ')) : legacyEnhancer?'Previous automatic encoder reuse is off. Choose dedicated enhancer weights below.':'Choose an installed dedicated enhancer, or open the download links below.';
  const hasReferences=Boolean(imageEdit)||resolvedReferenceIds().length>0||uploadedReferenceIds.length>0;
  const selectedFormat=currentWorkflow()?.formats[$('model-format').value];
  const ready=selectedFormat?.[hasReferences?'edit_ready':'ready']&&selectedFormat.loaders.every(loader=>loader.options.includes(selectedModels[loader.node]||loader.default));
  $('edit-image').disabled=!currentShot()?.drafts.some(d=>d.id===selectedDraft&&d.status==='succeeded')||busy;$('cancel-image-edit').disabled=busy;
  $('save-as-asset').disabled=!currentShot()?.drafts.some(d=>d.id===selectedDraft&&d.status==='succeeded') || busy || Boolean(project?.assets?.find(a=>a.id===currentShot()?.asset_id&&a.source_draft_id===selectedDraft));
  $('open-library').disabled=!project;$('studies').disabled=!project||busy;
  $('import-asset').disabled=!project;
  $('attach-reference').disabled=!shot||referenceUploadBusy;
  $('reference-status').hidden=true;
  $('reference-status').textContent='';
  if(hasReferences&&enhancer?.ready){$('enhancer-status').textContent=enhancer.reference_only?'Enhances editing instructions using the attached images.':'Enhances editing instructions and preserves image tags. This enhancer reads text only.';}
  $('generate').disabled=!shot || busy || referenceUploadBusy || !config?.online || !ready || ($('prompt_enhancer').checked&&!enhancer?.ready);
  $('add-shot').disabled=!project || busy;
  for(const field of document.querySelectorAll('.direction-controls button,.direction-controls input,.direction-controls textarea'))field.disabled=!shot||busy;
  $('generate').firstChild.textContent=busy?'◌ Adding… ':'＋ Add to queue ';
  window.DirectorDropdowns.sync();
}
async function projectList() {
  const projects=await api('/projects?summary=1');window.DirectorLibrary?.setProjects(projects);
  const source=$('library-source'),previous=source.value;source.replaceChildren(new Option('This project',''),...projects.filter(p=>p.id!==project?.id).map(p=>new Option(p.name,p.id)));source.value=previous;
  $('projects').replaceChildren(new Option('Select a project',''), ...projects.map(p=>new Option(p.name,p.id)),new Option('＋ New project','__new__'));
  if(project) $('projects').value=project.id;
  $('project-picker-name').textContent=project?.name||'Projects';
  return projects;
}
async function openProject(id) {
  if(window.DirectorVideo?.active)await window.DirectorVideo.save();
  if(project && currentShot()) await saveNotes(false);
  project=await api(`/projects/${id}`);
  shotId=lastWorkspaceItem(creationMode,visibleStudies())?.id; selectedDraft=null;
  if(!shotId) { const shot=await api(`/projects/${id}/shots`,'POST',{mode:creationMode}); project.shots.push(shot); shotId=shot.id; }
  localStorage.setItem('openframe-project',id);
  $('projects').value=id;
  $('project-name').textContent=project.name;
 populateWorkflows();setEditor(currentShot()); librarySource='';$('library-source').value='';libraryStamp='';render();await projectList();
}
const GENERATION_CHOICES={frame:{field:'ratio',values:['16:9','5:4','4:3','3:2','1:1','2:3','3:4','4:5','9:16']},size:{field:'megapixels',values:['0.5','0.75','1','1.5','2','4']},count:{field:'batch-count',values:['1','2','3','4']}};
let activeGenerationChoice=null;
function closeGenerationChoices(){
  const menu=$('generation-choice-menu'),trigger=activeGenerationChoice&&$('choose-'+activeGenerationChoice);
  if(menu.contains(document.activeElement))trigger?.focus({preventScroll:true});
  activeGenerationChoice=null;window.DirectorControls.closeChoices(menu);
  for(const kind of Object.keys(GENERATION_CHOICES))$('choose-'+kind).setAttribute('aria-expanded','false');
}
function updateResolutionSize(){
  $('frame-choice-value').textContent=$('ratio').value;$('size-choice-value').textContent=$('megapixels').value+' MP';$('count-choice-value').textContent='×'+$('batch-count').value;
  for(const [kind,label] of [['frame','Frame'],['size','Size'],['count','Takes to queue']])$('choose-'+kind).setAttribute('aria-label',label+': '+$(GENERATION_CHOICES[kind].field).value);
}
function showGenerationChoices(kind){
  activeGenerationChoice=kind;const config=GENERATION_CHOICES[kind],menu=$('generation-choice-menu');menu.setAttribute('aria-label',kind+' choices');
  const select=value=>{$(config.field).value=value;menu.querySelectorAll('.generation-choice[data-value]').forEach(item=>item.setAttribute('aria-pressed',String(item.dataset.value===value)));updateResolutionSize();$(config.field).dispatchEvent(new Event('change',{bubbles:true}));};
  if(kind==='frame')window.DirectorControls.ratioChoices(menu,$('ratio').value,select);
  else if(kind==='size')window.DirectorControls.sliderChoices(menu,{kind:'size',value:$('megapixels').value,min:.5,max:4,step:.1,
    ticks:['0.5','1','2','3','4'],id:'asset-size-slider',onChange:value=>{$('megapixels').value=String(value);updateResolutionSize();$('megapixels').dispatchEvent(new Event('change',{bubbles:true}));}});
  else{menu.className='generation-choice-menu';menu.replaceChildren(...config.values.map(value=>{const item=button('×'+value,'generation-choice',()=>select(value));item.dataset.value=value;item.setAttribute('aria-pressed',String($(config.field).value===value));return item;}));}
  window.DirectorControls.openChoices(menu);
  for(const name of Object.keys(GENERATION_CHOICES))$('choose-'+name).setAttribute('aria-expanded',String(name===kind));
}
for(const kind of Object.keys(GENERATION_CHOICES))$('choose-'+kind).onclick=()=>activeGenerationChoice===kind?closeGenerationChoices():showGenerationChoices(kind);
document.addEventListener('click',event=>{if(!event.target.closest('.quick-generation'))closeGenerationChoices();});
document.addEventListener('keydown',event=>{if(event.key==='Escape')closeGenerationChoices();});
async function saveNotes(notify=true) {
  if(!project || !currentShot()) return;
  const saved=await api(`/projects/${project.id}/shots/${shotId}`,'PUT',settings());
  Object.assign(currentShot(),saved);
  if(notify) {render();toast(creationMode==='asset'?'Asset notes saved.':'Shot notes saved.');}
}
async function selectShot(id) { if(window.DirectorVideo?.active)await window.DirectorVideo.leave(); await saveNotes(false); creationMode=modeOf(project.shots.find(s=>s.id===id));populateWorkflows();shotId=id; selectedDraft=null; setEditor(currentShot()); render(); }
function render() {
  if(window.DirectorVideo?.active){window.DirectorVideo.render(project);return;}
  const shot=currentShot();
  renderCreationMode();renderReferenceChips();renderLibrary();
  syncStudySelector();
  if(!shot) {lock();return;}
  $('shot-heading').textContent=shot.title;
  const drafts=shot.drafts.filter(d=>d.status==='succeeded');
  const key=project.id+'/'+shot.id, latest=drafts.at(-1)?.id;
  const newImage=latestReadyByShot.has(key)&&latest&&latestReadyByShot.get(key)!==latest;
  latestReadyByShot.set(key,latest);
  if(newImage || !shot.drafts.some(d=>d.id===selectedDraft)) {selectedDraft=latest || shot.drafts.at(-1)?.id;revealSelectedTake=true;}
  const selectedTake=shot.drafts.find(d=>d.id===selectedDraft);
  const draft=drafts.find(d=>d.id===selectedDraft), imageIndex=drafts.findIndex(d=>d.id===selectedDraft);
  $('previous-image').disabled=imageIndex<=0;
  $('next-image').disabled=imageIndex<0 || imageIndex>=drafts.length-1;
  $('image-position').textContent=draft?`Image ${imageIndex+1} / ${drafts.length}`:selectedTake?'Take '+(selectedTake.number || shot.drafts.indexOf(selectedTake)+1):'No images yet';
  renderTakes(shot);
  const coverAsset=project.assets?.find(a=>a.id===shot.asset_id);
  $('save-as-asset').querySelector('span').textContent=coverAsset?.source_draft_id===selectedDraft?'Cover set':'Set cover';
  $('save-as-asset').title='Choose the image used in the Library and @references. All takes stay saved.';
  $('prompt-inspector').hidden=!draft;
  // Diagnostics belong to the status panel, never to the displayed generation text.
  $('prompt-used').textContent=draft ? (draft.full_prompt || draft.settings.prompt) : '';
  if(draft) {
    let img=$('preview').querySelector('img');
    if(!img) {img=document.createElement('img');$('preview').replaceChildren(img);}
    const url=fileURL(draft.file);if(img.getAttribute('src')!==url) img.src=url;
    img.alt=draft.settings.prompt;
    $('download').href=url;$('download').download=(coverAsset?.name||shot.title).replace(/[<>:"/\\|?*\x00-\x1f]/g,'_')+'.png';$('download').hidden=false;
    $('image-info').textContent=`${draft.settings.ratio} / ${draft.settings.megapixels || 2} MP`;
  } else if(selectedTake) {
    const pending=active(selectedTake),stamp=selectedTake.id+':'+pending;
    if($('preview').dataset.pending!==stamp||!$('preview').querySelector('.generation-preview')){
      const panel=document.createElement('div');panel.className='generation-preview';panel.setAttribute('role','status');
      if(pending){const pulse=document.createElement('span');pulse.className='generation-orbit';pulse.setAttribute('aria-hidden','true');panel.append(pulse);}
      const text=document.createElement('p');text.textContent=pending?'Generating image…':selectedTake.status==='failed'?'Generation failed':'Generation cancelled';panel.append(text);
      $('preview').replaceChildren(panel);$('preview').dataset.pending=stamp;
    }
    $('preview').querySelector('.generation-preview p').textContent=selectedTake.status==='queued'?'Waiting in queue…':active(selectedTake)?'Generating image…':selectedTake.status==='failed'?'Generation failed':'Generation cancelled';
    window.DirectorMotion?.generation($('preview').querySelector('.generation-preview'),selectedTake);
    $('download').hidden=true;$('image-info').textContent='Take '+(selectedTake.number || shot.drafts.indexOf(selectedTake)+1);
  } else {
    if(!$('preview').querySelector('.empty')) $('preview').innerHTML='<div class="empty"><span class="aspect-hint">16:9</span><h2>Your first shot appears here</h2><p>Write a scene, set the direction, then Generate.</p></div>';
    $('preview').querySelector('.aspect-hint').textContent=$('ratio').value || '16:9';
    $('preview').querySelector('h2').textContent=creationMode==='asset'?'Your first asset appears here':'Your first shot appears here';
    $('preview').querySelector('p').textContent=creationMode==='asset'?'':'';
    $('download').hidden=true;$('image-info').textContent=(currentWorkflow()?.label || 'Local model')+' / Local generation';
  }
  const running=shot.drafts.find(d=>active(d)&&d.status!=='queued') || shot.drafts.find(active), failed=shot.drafts.at(-1)?.status==='failed' ? shot.drafts.at(-1) : null;
  const centralProgress=selectedTake&&active(selectedTake)&&window.DirectorMotion?.progress;
  const status=$('generation-status');if(centralProgress||!running||!window.DirectorMotion?.progress)status.replaceChildren();status.className=failed&&!running?'error':'';status.title=failed?.error || draft?.prompt_note || '';
  if(running&&!centralProgress) {
    const text=document.createElement('span');text.textContent=running.status==='queued'?'Queued — your frame will start shortly.':running.status==='downloading'?'Saving your frame…':running.stage ? `${running.stage} · ${Math.round((running.progress || 0)*100)}%` : 'Generating — loading local models may take a moment.';
    const bar=document.createElement('progress');bar.max=1;if(running.progress>0&&running.progress<1)bar.value=running.progress;
    if(window.DirectorMotion?.progress)window.DirectorMotion.progress(status,running,true);else status.append(text,bar);
  } else if(centralProgress) status.replaceChildren();
  else if(failed) status.textContent=failed.error || 'Generation failed. Check ComfyUI and try again.';
  else if(draft?.prompt_note) status.textContent=draft.prompt_note;
  lock();
  if(newImage&&!document.activeElement?.matches('input,textarea,select,[role=combobox]'))requestAnimationFrame(()=>$('preview').scrollIntoView({behavior:'smooth',block:'nearest'}));
}
function syncStudySelector() {
  const root=$('studies'),items=visibleStudies(),stamp=JSON.stringify([creationMode,items.map(s=>[s.id,s.title,project.assets?.find(a=>a.id===s.asset_id)?.handle])]);
  if(root.dataset.stamp!==stamp){
    root.dataset.stamp=stamp;
    root.replaceChildren(...items.map(s=>new Option(s.asset_id?'@'+(project.assets.find(a=>a.id===s.asset_id)?.handle || s.title):s.title,s.id)),new Option(creationMode==='asset'?'＋ New asset':'＋ New shot','__new__'));
  }
  root.value=shotId || '';root.disabled=!project||busy;
}
async function reuseTakeSettings(id) {
  const shot=currentShot(),take=shot?.drafts.find(d=>d.id===id);if(!take?.settings)return;
  const snapshot={...shot,...structuredClone(take.settings),id:shot.id,title:shot.title,asset_id:shot.asset_id,drafts:shot.drafts};
  creationMode=modeOf(shot);setEditor(snapshot,true);selectedLoras=structuredClone(take.settings.loras || []);saveEnginePreferences();renderLoras();selectedDraft=take.id;revealSelectedTake=true;pendingSubmission=null;
  latestReadyByShot.set(project.id+'/'+shot.id,shot.drafts.filter(d=>d.status==='succeeded').at(-1)?.id);
  render();$('prompt').focus({preventScroll:true});
  const projectId=project.id,studyId=shot.id,data=settings();
  const saved=await api(`/projects/${projectId}/shots/${studyId}`,'PUT',data);
  if(project?.id===projectId){const target=project.shots.find(s=>s.id===studyId);if(target)Object.assign(target,{...saved,drafts:target.drafts});}
  toast('Prompt and settings restored from this take.');
}
function renderTakes(shot) {
  const root=$('takes'),complete=shot.drafts.filter(d=>d.status==='succeeded').length,waiting=shot.drafts.filter(active).length;
  $('take-count').textContent=String(complete);$('take-count').title=`${complete} ready · ${waiting} queued / generating`;
  const key=project.id+'/'+shot.id;
  if(takeGalleryKey!==key){takeGalleryKey=key;root.replaceChildren();root.scrollTop=0;revealSelectedTake=true;}
  const existing=new Map([...root.children].map(el=>[el.dataset.draft,el]));
  for(const [index,d] of shot.drafts.entries()) {
    let card=existing.get(d.id);existing.delete(d.id);
    if(!card){card=document.createElement('article');card.dataset.draft=d.id;root.append(card);}
    const ready=d.status==='succeeded',number=d.number || index+1;
    card.className=`take ${d.id===selectedDraft?'selected':''} take-${d.status}`;card.dataset.active=String(active(d));
    card.title=d.error || `Take ${number}`;
    const stamp=JSON.stringify([d.status,number,d.file,Boolean(d.settings)]);
    if(card.dataset.stamp!==stamp){
      card.dataset.stamp=stamp;card.replaceChildren();
      const open=button('','take-select',()=>{selectedDraft=d.id;render();});open.setAttribute('aria-label',`Take ${number} · ${ready?'Ready':d.status}`);
      if(ready){const img=document.createElement('img');img.src=fileURL(d.file);img.alt=`Take ${number}`;img.loading='lazy';open.append(img);}
      else{const placeholder=document.createElement('div');placeholder.className='take-placeholder';placeholder.textContent=d.status==='failed'?'Failed':d.status==='cancelled'?'Cancelled':d.status==='queued'?'Queued':'Generating…';open.append(placeholder);}
      const label=document.createElement('span');label.className='take-overlay';label.textContent=String(number).padStart(2,'0');open.append(label);card.append(open);
      if(d.settings){const reuse=button('Reuse Settings','take-reuse',event=>{event.stopPropagation();safe(()=>reuseTakeSettings(d.id));});reuse.setAttribute('aria-label',`Reuse settings from take ${number}`);card.append(reuse);}
    }
    card.querySelector('.take-select').setAttribute('aria-pressed',String(d.id===selectedDraft));window.DirectorMotion?.take(card,d);
  }
  for(const card of existing.values())card.remove();
  if(revealSelectedTake){
    revealSelectedTake=false;
    requestAnimationFrame(()=>{const selected=[...root.children].find(el=>el.dataset.draft===selectedDraft);if(selected)root.scrollTop=Math.max(0,selected.offsetTop-root.offsetTop+selected.offsetHeight-root.clientHeight);updatePendingIndicator();});
  }else requestAnimationFrame(updatePendingIndicator);
}
function updatePendingIndicator() {
  const root=$('takes'),bounds=root.getBoundingClientRect(),pending=[...root.querySelectorAll('[data-active="true"]')];
  const visible=pending.some(el=>{const r=el.getBoundingClientRect();return r.top<bounds.bottom-8&&r.bottom>bounds.top+8;});
  $('pending-indicator').hidden=!pending.length||visible;
}
$('takes').addEventListener('scroll',updatePendingIndicator,{passive:true});
window.addEventListener('resize',updatePendingIndicator);
function navigateImage(offset) {
  const ready=currentShot()?.drafts.filter(d=>d.status==='succeeded') || [];
  const index=ready.findIndex(d=>d.id===selectedDraft), next=ready[index+offset];
  if(!next)return;selectedDraft=next.id;revealSelectedTake=true;render();
}
$('previous-image').onclick=()=>navigateImage(-1);
$('next-image').onclick=()=>navigateImage(1);
async function refreshQueue() {
  queueState=await api('/queue');renderQueue();
}
function renderQueue() {
  $('queue-count').textContent=`${queueState.running} active · ${queueState.waiting} waiting`;
  window.DirectorQueue?.render();
}
async function safe(action) {try {await action();} catch(error) {toast(error.message);} }
function enhancerModels() {
  return (config?.enhancer?.models || []).filter(model=>model.kind==='dedicated'&&model.workflows?.includes('qwen21')).map(model=>{
    const compatible=(!model.workflows || model.workflows.includes($('workflow-model').value))&&(!model.reference_only||imageEdit||resolvedReferenceIds().length>0||uploadedReferenceIds.length>0);
    return {...model,ready:model.ready&&compatible,missing:compatible?model.missing:[...model.missing,'This enhancer requires reference images']};
  });
}
function selectedEnhancer() {return enhancerModels().find(model=>model.id===$('enhancer_model').value);}
function renderEnhancers(selected) {
  renderEnhancerDownloads();
  const models=enhancerModels(), control=$('enhancer_model'), previous=selected ?? control.value;
  const downloadOptions=window.DirectorModelDownloads?.options('qwen21','enhancer',[])||[];
  const stamp=JSON.stringify([models,previous,downloadOptions.map(o=>[o.value,o.textContent])]);
  if(control.dataset.stamp===stamp)return;
  control.dataset.stamp=stamp;
  const options=[new Option('Choose an enhancer model…','')];
  for(const model of models) {
    const option=new Option(model.label+(model.installed?' · '+model.file:' · Not installed')+(model.installed&&!model.ready?' · Unavailable':''),model.id);
    option.disabled=model.installed&&!model.ready;options.push(option);
    window.DirectorDropdowns.previews.enhancer_model ||= {};
    window.DirectorDropdowns.previews.enhancer_model[model.id]={hint:model.hint+(model.ready?'':' '+model.missing.join('; '))};
  }
  for(const option of downloadOptions)if(!options.some(o=>o.value===option.value))options.push(option);
  if(previous&&!options.some(option=>option.value===previous)) {const option=new Option(previous+' · No longer installed',previous);option.disabled=true;options.push(option);}
  control.replaceChildren(...options);control.value=previous;
  const box=$('image-enhancer-download');box.replaceChildren();window.DirectorModelDownloads?.decorate(box,control,'qwen21','enhancer');
}
function renderEnhancerDownloads() {
  const root=$('enhancer-download-links'), downloads=(config?.enhancer?.downloads || []).filter(group=>group.workflows.includes('qwen21'));
  const stamp=JSON.stringify(downloads);if(root.dataset.stamp===stamp)return;root.dataset.stamp=stamp;
  root.replaceChildren(...downloads.map(group=>{
    const box=document.createElement('div');box.className='enhancer-download-group';
    const label=document.createElement('strong');label.textContent=group.label;
    const links=document.createElement('div');
    for(const [text,url] of [['Model page ↗',group.page],...group.files.map(file=>[file.label+' download ↗','https://huggingface.co/'+group.repo+'/resolve/main/text_encoders/'+file.name+'?download=true'])]) {
      const a=document.createElement('a');a.textContent=text;a.href=url;a.target='_blank';a.rel='noreferrer';links.append(a);
    }
    box.append(label,links);return box;
  }));
}
$('enhancer_model').onchange=()=>{saveEnginePreferences();legacyEnhancer=false;if(!selectedEnhancer()?.ready)$('prompt_enhancer').checked=false;lock();};
$('prompt_enhancer').onchange=lock;
$('ratio').onchange=()=>{const hint=$('preview').querySelector('.aspect-hint');if(hint)hint.textContent=$('ratio').value;updateResolutionSize();};
$('megapixels').oninput=updateResolutionSize;
$('new-project').onclick=()=>{$('new-name').value='';$('project-dialog').showModal();};
$('project-form').onsubmit=event=>{
  if(event.submitter?.value!=='create')return;
  event.preventDefault();safe(async()=>{const p=await api('/projects','POST',{name:$('new-name').value});$('project-dialog').close();await projectList();await openProject(p.id);});
};
$('projects').onchange=()=>{if($('projects').value==='__new__'){$('projects').value=project?.id || '';$('new-project').click();window.DirectorDropdowns.sync();}else if($('projects').value)safe(()=>openProject($('projects').value));};
$('studies').onchange=()=>{const id=$('studies').value;if(id==='__new__'){$('studies').value=shotId;$('add-shot').click();}else if(id!==shotId)safe(()=>selectShot(id));};
let creatingAsset=false;
$('asset-new').onclick=()=>safe(async()=>{
  if(!project||busy||referenceUploadBusy||creatingAsset)return;
  creatingAsset=true;$('asset-new').disabled=true;
  try{await $('add-shot').onclick();}
  finally{creatingAsset=false;$('asset-new').disabled=!project||busy||referenceUploadBusy;}
});
$('add-shot').onclick=()=>safe(async()=>{await saveNotes(false);const s=await api(`/projects/${project.id}/shots`,'POST',{mode:creationMode});project.shots.push(s);shotId=s.id;selectedDraft=null;setEditor(s);render();project=await api(`/projects/${project.id}`);render();$('prompt').focus();});
$('save-shot').onclick=()=>safe(()=>saveNotes());
$('workflow-model').onchange=()=>{selectedModels={};$('steps').value=currentWorkflow()?.default_steps || 25;renderModels();render();};
$('model-format').onchange=()=>{selectedModels={};renderModels();saveEnginePreferences();render();};
function selectSettingsSection(mode){
  for(const name of ['images','video','connection'])$('settings-'+name).setAttribute('aria-selected',String(name===mode));
  $('image-model-settings').hidden=mode!=='images';$('video-model-settings').hidden=mode!=='video';$('connection-settings').hidden=mode!=='connection';
}
$('engine-settings').onclick=()=>{renderModels();selectSettingsSection(window.DirectorVideo?.active?'video':'images');$('models-dialog').showModal();};
for(const mode of ['images','video','connection'])$('settings-'+mode).onclick=()=>selectSettingsSection(mode);
$('close-models').onclick=()=>$('models-dialog').close();
$('refresh-enhancers').onclick=()=>safe(async()=>{config=await api('/config');renderModels();toast('Installed enhancers refreshed.');});
$('refresh-models').onclick=()=>safe(async()=>{config=await api('/config');populateWorkflows();renderModels();toast('Installed models refreshed.');});
$('shot-form').onsubmit=event=>{event.preventDefault();if(busy||referenceUploadBusy)return;safe(async()=>{
  const pid=project.id, sid=shotId, snapshot=settings(), count=Number($('batch-count').value);
  const signature=JSON.stringify([pid,sid,snapshot,count]);
  if(pendingSubmission?.signature!==signature)pendingSubmission={signature,request_id:submissionId()};
  busy=true;lock();
  try {
    const result=await api(`/projects/${pid}/shots/${sid}/generate`,'POST',{...snapshot,count,request_id:pendingSubmission.request_id});
    pendingSubmission=null;
    if(project?.id===pid){project=await api(`/projects/${pid}`);render();}
    await refreshQueue();toast(`${result.count} take${result.count===1?'':'s'} added to the queue.`);
  } finally {busy=false;lock();}
});};
async function refresh() {
  try {
    await refreshQueue();
    if(project) {const id=project.id;const result=await api(`/projects/${id}`);if(project.id===id){project=result;render();}}
  } catch(error) {$('connection').textContent='Studio connection lost';$('connection').className='connection';}
  setTimeout(refresh,1800);
}
async function connection() {
  try {config=await api('/config');$('connection').textContent=config.online?'Engine connected':'Engine offline';$('connection').className='connection '+(config.online?'online':'');$('connection').title=config.detail || 'Official Comfy SDK · local API proxy';$('output-dir').textContent=config.output_dir;populateWorkflows();refreshPresetImages();if(!$('models-dialog').open)renderModels();lock();}catch(error){config={...config,online:false};lock();}
  setTimeout(connection,15000);
}

function resolvedReferenceIds() {
  if(window.DirectorVideo?.active)return window.DirectorVideo.referenceIds();
  const handles=[...($('prompt').value || '').matchAll(/(?<![\w@])@([a-zA-Z0-9_]+)/g)].map(m=>m[1]);
  return [...new Set([...referenceIds,...(project?.assets || []).filter(a=>handles.includes(a.handle)).map(a=>a.id)])];
}
function renderCreationMode() {
  const assets=creationMode==='asset';
  $('tab-assets').setAttribute('aria-selected',String(assets));
  $('tab-video').setAttribute('aria-selected','false');
  $('creation-workspace').setAttribute('aria-labelledby','tab-assets');
  renderCharacterVisibility();
  $('editor-heading').textContent=currentShot()?.title || 'New asset';
  $('asset-new').disabled=!project||busy||referenceUploadBusy||creatingAsset;
  for(const action of ['rename','delete','browse'])$('asset-'+action).disabled=!project||busy||action!=='browse'&&!currentShot();
  $('title-label').textContent=assets?'Asset name':'Shot name';
  document.body.dataset.workspace=creationMode;
  $('add-shot').textContent=assets?'＋ New asset':'＋ Add shot';
  $('add-shot').setAttribute('aria-label',assets?'Add an asset study':'Add a shot');
  $('save-shot').textContent=assets?'Save asset notes':'Save shot notes';
  $('add-shot').title=assets?'Add an asset study':'Add a shot';
  document.body.classList.toggle('image-editing',Boolean(imageEdit));$('image-edit-banner').hidden=!imageEdit;if(imageEdit)$('image-edit-source').src=fileURL(imageEdit.file);
  renderEditPresets();
  if(!imageEdit)$('prompt').placeholder=assets?'Describe your character, prop or location. Type @ to use a reference.':'Describe the moment. Who, where, what is happening.';
  document.querySelector('.queue-help').textContent=assets?'Your free prompt and references are saved for each take. Save a favorite to the library.':'Your current prompt and settings are saved for each take. Keep editing while the queue runs.';
}
async function switchCreationMode(mode) {
  if(window.DirectorVideo?.active){await window.DirectorVideo.leave();if(creationMode===mode){render();return;}}
  if(creationMode===mode)return;
  await saveNotes(false);creationMode=mode;populateWorkflows();
  shotId=lastWorkspaceItem(mode,visibleStudies())?.id;selectedDraft=null;
  if(project&&!shotId){const s=await api(`/projects/${project.id}/shots`,'POST',{mode});project.shots.push(s);shotId=s.id;}
  if(currentShot())setEditor(currentShot());render();
}
function renderEditPresets(){
  const root=$('edit-preset-controls'),available=config?.image_edit_presets||[];
  const selected=available.find(p=>p.id===$('edit-preset').value);
  root.hidden=!imageEdit;
  const indicator=$('edit-preset-indicator');indicator.hidden=!imageEdit;
  if(!imageEdit)return;
  indicator.textContent=selected?.label||'Free edit';indicator.dataset.active=String(Boolean(selected));
  $('prompt').placeholder=selected?.hint||'Describe what you want to change…';
  const order=['a-pose','front','back','face','torso','side','legs','hand','character-sheet'];
  const choices=order.map(id=>available.find(p=>p.id===id)).filter(Boolean),menu=$('edit-preset-menu');
  const stamp=JSON.stringify(choices);if(menu.dataset.stamp!==stamp){menu.dataset.stamp=stamp;
    menu.replaceChildren(...choices.map(p=>{const item=button(p.label,'generation-choice edit-preset-option',()=>{
      $('edit-preset').value=$('edit-preset').value===p.id?'':p.id;
      pendingSubmission=null;renderEditPresets();
    });item.dataset.preset=p.id;return item;}));
  }
  for(const item of menu.children)item.setAttribute('aria-pressed',String(item.dataset.preset===$('edit-preset').value));
}
function referenceTile({thumbnail,source,label,onRemove}) {
  const tile=document.createElement('div');tile.className='reference-tile';
  const preview=button('','reference-tile-preview',()=>openImageViewer(source));
  preview.title='Open '+label;preview.setAttribute('aria-label','Open reference '+label);
  const image=document.createElement('img');image.src=thumbnail||source;image.alt=label;image.loading='lazy';
  const caption=document.createElement('span');caption.className='reference-tile-caption';caption.textContent=label;
  preview.append(image,caption);
  const remove=button('','reference-tile-remove',onRemove);remove.innerHTML=DirectorIcons.close;
  remove.title='Remove '+label;remove.setAttribute('aria-label','Remove reference '+label);
  tile.append(preview,remove);return tile;
}
function renderReferenceChips() {
  renderPresetReferences();
  const root=$('reference-chips'),ids=resolvedReferenceIds();
  const assets=ids.map(id=>project?.assets?.find(a=>a.id===id)).filter(Boolean);
  const uploads=uploadedReferenceIds.map(id=>project?.reference_images?.find(r=>r.id===id)).filter(Boolean);
  $('asset-reference-panel').hidden=!assets.length&&!uploads.length;
  $('asset-reference-count').textContent=String(assets.length+uploads.length);
  const stamp=JSON.stringify([project?.id,assets.map(a=>[a.id,a.handle,a.thumbnail,a.file]),uploads]);
  if(root.dataset.stamp===stamp)return;root.dataset.stamp=stamp;
  root.replaceChildren(...assets.map(asset=>referenceTile({
    thumbnail:fileURL(asset.thumbnail||asset.file),source:fileURL(asset.file||asset.thumbnail),label:'@'+asset.handle,
    onRemove:()=>{
      referenceIds=referenceIds.filter(x=>x!==asset.id);
      $('prompt').value=$('prompt').value.replace(new RegExp('(?<![\\w@])@'+asset.handle+'\\b','g'),asset.name);
      renderReferenceChips();renderModels();
    }
  })),...uploads.map(ref=>referenceTile({
    thumbnail:fileURL(ref.thumbnail||ref.file),source:fileURL(ref.file||ref.thumbnail),label:ref.name,
    onRemove:()=>safe(async()=>{uploadedReferenceIds=uploadedReferenceIds.filter(x=>x!==ref.id);renderReferenceChips();await saveNotes(false);})
  })));
}
let libraryReturnFocus=null;
function openLibrary(kind='all',tab='assets') {
  if(!$('asset-library').open)libraryReturnFocus=document.activeElement;
  window.DirectorLibrary?.setTab(tab,false);
  $('asset-library').hidden=false;if(!$('asset-library').open)$('asset-library').showModal();$('open-library').setAttribute('aria-expanded','true');
  if(kind!=='all')$('library-kind').value=kind;
  renderLibrary(true);window.DirectorDropdowns.sync();
}
function closeLibrary(focus=null) {if(typeof focus?.focus==='function')libraryReturnFocus=focus;$('asset-library').close();}
$('asset-library').addEventListener('close',()=>{$('asset-library').hidden=true;$('open-library').setAttribute('aria-expanded','false');(libraryReturnFocus?.isConnected?libraryReturnFocus:$('open-library')).focus();});
$('asset-library').addEventListener('click',event=>{if(event.target===$('asset-library')){const r=event.target.getBoundingClientRect();if(event.clientX<r.left||event.clientX>r.right||event.clientY<r.top||event.clientY>r.bottom)closeLibrary();}});
function useAsset(asset,replaceMention=false) {
  if(window.DirectorVideo?.active){window.DirectorVideo.useAsset(asset);renderLibrary(true);return;}
  if(!currentShot())return;
  if(!asset.file){toast('Generate or import an image for this asset first.');return;}
  const ids=resolvedReferenceIds();if(!ids.includes(asset.id)&&ids.length+uploadedReferenceIds.length+(imageEdit?1:0)>=10){toast(imageEdit?'Use up to 9 additional references while editing.':'Use up to 10 image references at a time.');return;}
  if(!referenceIds.includes(asset.id))referenceIds.push(asset.id);
  const prompt=$('prompt'),position=prompt.selectionStart;
  if(replaceMention){const before=prompt.value.slice(0,position).replace(/@([a-zA-Z0-9_]*)$/,'@'+asset.handle+' ');prompt.value=before+prompt.value.slice(position);prompt.focus();prompt.setSelectionRange(before.length,before.length);}
  else if(!new RegExp('(?<![\\w@])@'+asset.handle+'\\b').test(prompt.value)){prompt.value+=(prompt.value&&!/\s$/.test(prompt.value)?' ':'')+'@'+asset.handle+' ';}
  $('mention-suggestions').hidden=true;renderReferenceChips();renderModels();
}
function renderLibrary(force=false) {
  window.DirectorLibrary?.syncCounts();
  if(window.DirectorLibrary?.tab==='shots'){window.DirectorLibrary.renderShots(force);return;}
  if(!force&&$('library-items').querySelector('.asset-handle-input'))return;
  const source=librarySource?libraryAssets:project?.assets || [];
  $('library-count').textContent=String(project?.assets?.length || 0);
  if($('asset-library').hidden)return;
  const kind=$('library-kind').value,query=$('library-search').value.toLowerCase();
  const list=source.filter(a=>(kind==='all'||a.kind===kind)&&(a.name+' '+a.handle+' '+a.description).toLowerCase().includes(query));
  const stamp=JSON.stringify([project?.id,librarySource,kind,query,list,resolvedReferenceIds()]);if(!force&&stamp===libraryStamp)return;libraryStamp=stamp;
  if(!list.length){const p=document.createElement('p');p.className='library-empty';p.textContent=librarySource?'No matching assets in this project.':'No assets yet.';$('library-items').replaceChildren(p);return;}
  $('library-items').replaceChildren(...list.map(a=>{
    const card=document.createElement('article');card.className='asset-card'+(!window.DirectorVideo?.active&&a.source_shot_id===shotId?' is-current':'');
    const image=button('','asset-cover',()=>safe(async()=>{
      if(!a.source_shot_id)return;
      await saveNotes(false);const pid=librarySource || project.id;closeLibrary();
      if(project.id!==pid)await openProject(pid);
      await selectShot(a.source_shot_id);
      if(a.source_draft_id&&currentShot().drafts.some(d=>d.id===a.source_draft_id)){selectedDraft=a.source_draft_id;revealSelectedTake=true;render();}
    }));image.setAttribute('aria-label','Open @'+a.handle+' and its generation history');image.title='Open asset and all takes';
    if(a.thumbnail || a.file){const photo=document.createElement('img');photo.src=fileURL(a.thumbnail || a.file,librarySource || project.id);photo.alt='@'+a.handle;photo.loading='lazy';image.append(photo);}
    else{const placeholder=document.createElement('span');placeholder.className='asset-cover-empty';placeholder.textContent='＋ Create first image';image.append(placeholder);}
    const takes=document.createElement('span');takes.className='asset-cover-takes';takes.textContent=(a.take_count || 0)+' takes';image.append(takes);
    const identity=document.createElement('div');identity.className='asset-identity';
    const handle=document.createElement('strong');handle.className='asset-handle';handle.textContent='@'+a.handle;handle.title=a.description || a.kind;
    const kindIcon=document.createElement('span');kindIcon.className='ui-icon asset-kind-icon';kindIcon.setAttribute('aria-hidden','true');kindIcon.style.setProperty('--ui-icon',`url(/assets/icons/lucide/${({character:'user-round',prop:'box',location:'map-pin'})[a.kind] || 'layers'}.svg)`);
    identity.append(kindIcon,handle);
    if(!librarySource){
      const edit=button('✎','asset-edit',()=>editAssetHandle(a,identity));edit.setAttribute('aria-label','Edit @'+a.handle);edit.title='Edit handle';
      handle.ondblclick=()=>editAssetHandle(a,identity);handle.tabIndex=0;handle.onkeydown=event=>{if(event.key==='Enter'||event.key==='F2'){event.preventDefault();editAssetHandle(a,identity);}};
      identity.append(edit);
    }
    card.append(image,identity);
    const attached=!librarySource&&resolvedReferenceIds().includes(a.id);
    const use=button(librarySource?'＋ Copy to project':attached?'✓ Attached':'＋ Use reference','subtle',()=>safe(async()=>{
      if(librarySource){await api(`/projects/${project.id}/assets`,'POST',{source_project:librarySource,source_asset:a.id});project=await api(`/projects/${project.id}`);toast('Asset copied to this project.');renderLibrary(true);}
      else {useAsset(a);closeLibrary($(window.DirectorVideo?.active?'video-prompt':'prompt'));}
    }));use.disabled=attached || !a.file;
    const actions=document.createElement('div');actions.className='asset-actions';actions.append(use);
    if(a.file){
      const download=document.createElement('a');download.className='button icon-button library-asset-download';
      download.href=fileURL(a.file,librarySource||project.id);download.download=(a.name||a.handle).replace(/[<>:"/\\|?*\x00-\x1f]/g,'_')+'.png';
      download.title='Download PNG';download.setAttribute('aria-label','Download '+(a.name||a.handle));download.innerHTML=DirectorIcons.download;actions.append(download);
    }
    if(!librarySource){
      const remove=button('Delete','subtle',()=>safe(async()=>{
        if(!await confirmAssetDeletion(a))return;
        if(window.DirectorVideo?.active)await window.DirectorVideo.save();else await saveNotes(false);
        project=await api(`/projects/${project.id}/assets/${a.id}`,'DELETE');
        if(window.DirectorVideo?.active){window.DirectorVideo.syncReferences();renderLibrary(true);toast('Asset deleted.');return;}
        if(!currentShot()){
          shotId=visibleStudies()[0]?.id;selectedDraft=null;
          if(!shotId){const study=await api(`/projects/${project.id}/shots`,'POST',{mode:creationMode});project.shots.push(study);shotId=study.id;}
          setEditor(currentShot());
        }else{$('prompt').value=currentShot().prompt;referenceIds=referenceIds.filter(id=>id!==a.id);}
        render();renderLibrary(true);toast('Asset deleted.');
      }));actions.append(remove);
    }
    card.append(actions);return card;
  }));
  window.DirectorDropdowns.sync();
}
function editAssetHandle(asset,identity) {
  if(identity.querySelector('input'))return;
  const input=document.createElement('input');input.className='asset-handle-input';input.value='@'+asset.handle;input.maxLength=121;input.setAttribute('aria-label','Edit asset handle');
  const error=document.createElement('span');error.className='asset-rename-error';error.setAttribute('role','status');
  identity.replaceChildren(input,error);let saving=false,cancelled=false;
  const save=async()=>{
    if(saving||cancelled)return;
    if(input.value.trim()==='@'+asset.handle||input.value.trim()===asset.handle){cancelled=true;renderLibrary(true);return;}
    saving=true;input.disabled=true;
    try{if(window.DirectorVideo?.active)await window.DirectorVideo.save();else await saveNotes(false);project=await api(`/projects/${project.id}/assets/${asset.id}`,'PATCH',{handle:input.value});
      if(window.DirectorVideo?.active)window.DirectorVideo.syncReferences();
      const shot=currentShot();if(shot){$('prompt').value=shot.prompt;$('title').value=shot.title;}
      cancelled=true;render();renderReferenceChips();renderLibrary(true);toast('Asset handle updated.');
    }catch(problem){error.textContent=problem.message;input.disabled=false;input.focus();}finally{saving=false;}
  };
  input.onkeydown=event=>{if(event.key==='Enter'){event.preventDefault();save();}if(event.key==='Escape'){event.preventDefault();event.stopPropagation();cancelled=true;renderLibrary(true);}};
  input.onblur=save;input.focus();input.select();
}
let skipAssetDeleteConfirmation=false;
try{skipAssetDeleteConfirmation=sessionStorage.getItem('directors-cut-skip-delete')==='true';}catch{}
function confirmAssetDeletion(asset) {
  if(skipAssetDeleteConfirmation)return Promise.resolve(true);
  const dialog=$('delete-asset-dialog');if(dialog.open)return Promise.resolve(false);
  $('delete-asset-message').textContent=`Are you sure you want to delete “${asset.name}”?`;
  $('skip-delete-confirmation').checked=false;dialog.returnValue='cancel';
  return new Promise(resolve=>{
    dialog.addEventListener('close',()=>{
      const confirmed=dialog.returnValue==='delete';
      if(confirmed&&$('skip-delete-confirmation').checked){skipAssetDeleteConfirmation=true;try{sessionStorage.setItem('directors-cut-skip-delete','true');}catch{}}
      resolve(confirmed);
    },{once:true});dialog.showModal();
  });
}
function showAssetDialog(source=null) {
  assetSaveSource=source;$('asset-form').reset();$('asset-save-status').textContent='';
  $('asset-dialog-heading').textContent=source?'Save asset':'Import image';
  $('asset-upload-field').hidden=Boolean(source);$('asset-image').required=!source;
  $('asset-name').value=source&&creationMode==='asset'?currentShot()?.title||'':'';$('asset-name').placeholder='Asset name';
  $('overwrite-asset').hidden=true;$('confirm-save-asset').value=source&&creationMode==='asset'?'overwrite':'new';$('confirm-save-asset').textContent=source?'Save asset':'Import image';
  const kind=$('library-kind').value;$('asset-kind').value=source&&creationMode==='asset'?$('asset_kind').value:kind==='all'?'character':kind;
  if(source&&creationMode==='asset'){const snapshot=currentShot()?.drafts.find(d=>d.id===source.draft)?.settings;
    $('asset-kind').value=snapshot?.asset_kind || $('asset_kind').value;
    const kind=$('asset-kind').value;$('asset-description').value=characterDescription(snapshot?.[kind+'_traits'] || {},kind);
  }
  $('asset-dialog').showModal();window.DirectorDropdowns.sync();
}
function mentionQuery() {const p=$('prompt');return p.value.slice(0,p.selectionStart).match(/(?:^|\s)@([a-zA-Z0-9_]*)$/)?.[1];}
function mentionOptions() {const q=mentionQuery();return q===undefined?[]:(project?.assets || []).filter(a=>a.file&&(a.handle+' '+a.name).toLowerCase().includes(q.toLowerCase()));}
function revealMentionOption(menu,index){
  const item=menu.children[index];if(!item)return;
  const bounds=menu.getBoundingClientRect(),rect=item.getBoundingClientRect();
  if(rect.top<bounds.top+6)menu.scrollTop+=rect.top-bounds.top-6;
  else if(rect.bottom>bounds.bottom-6)menu.scrollTop+=rect.bottom-bounds.bottom+6;
}
function renderMentions() {
  const list=mentionOptions(),root=$('mention-suggestions');mentionIndex=0;
  root.hidden=!list.length;root.scrollTop=0;root.replaceChildren(...list.map((a,i)=>{
    const b=button('@'+a.handle+' · '+a.name,'mention-option',()=>useAsset(a,true));
    b.setAttribute('role','option');b.setAttribute('aria-selected',String(i===0));b.onmousedown=e=>e.preventDefault();return b;
  }));
}



let presetImageStamp='';
function refreshPresetImages() {
  const stamp=JSON.stringify(config?.preview_images || {});if(stamp===presetImageStamp)return;presetImageStamp=stamp;
  window.DirectorDropdowns.configure(config);
  for(const category of assetCategories())for(const value of category.options) {
    const id='character-'+category.id;window.DirectorDropdowns.previews[id] ||= {};
    window.DirectorDropdowns.previews[id][value]={hint:category.hints?.[value],image:config?.preview_images?.['asset-'+traitEditorKind+'-'+category.id]?.[value]};
  }
  window.DirectorDropdowns.sync();
}
function assetCategories(kind=traitEditorKind) {return config?.asset_categories?.[kind] || (kind==='character'?config?.character_categories:[]) || [];}
function captureAssetTraits() {
  assetTraitDrafts[traitEditorKind]=readCharacterTraits();
  return Object.fromEntries(['character','location','prop'].map(kind=>[kind+'_traits',structuredClone(assetTraitDrafts[kind] || {})]));
}
const PRESET_ICONS={
  character_type:'user-round',gender:'users-round',age:'calendar',build:'biceps-flexed',height:'ruler',proportions:'move-diagonal',heritage:'globe',skin_tone:'palette',face_shape:'scan-face',neck:'person-standing',eye_shape:'eye',eye_color:'eye',hairstyle:'scissors',hair_color:'brush',facial_features:'scan-face',facial_hair:'scissors',distinctive_features:'sparkles',wardrobe:'shirt',clothing_color:'palette',accessories:'gem',expression:'scan-face',pose:'camera',render_style:'paintbrush',
  location_type:'map-pin',world:'orbit',architecture:'landmark',scale:'expand',era:'hourglass',materials:'layers',time:'sun',weather:'cloud',atmosphere:'wind',set_dressing:'armchair',framing:'frame',lens_type:'aperture',sensor:'scan',lighting:'lightbulb',light_color:'palette',film:'film',grade:'palette',prop_type:'box',design:'shapes',material:'hammer',condition:'badge-check'
};
function presetIcon(category) {
  const icon=document.createElement('span');icon.className='preset-icon';icon.setAttribute('aria-hidden','true');
  icon.style.setProperty('--preset-icon',`url("/assets/icons/lucide/${PRESET_ICONS[category.id] || 'sparkles'}.svg")`);return icon;
}
function revealPresetOptions(box,scroller=$('editor-scroll')) {
  const header=box.querySelector('summary');
  if(!scroller||!header)return;
  const bounds=scroller.getBoundingClientRect(),rect=header.getBoundingClientRect();
  const previewHeight=Math.min(box.querySelector('.preset-card-grid').offsetHeight,250);
  const shift=Math.max(0,Math.min(rect.top-bounds.top-8,rect.bottom+previewHeight+16-bounds.bottom));
  scroller.scrollTo({top:scroller.scrollTop+shift,behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'instant':'smooth'});
}
function syncPresetCards(category) {
  const select=$('character-'+category.id),box=$('preset-'+category.id);if(!select||!box)return;
  const values=JSON.parse(select.dataset.values||'[]');
  for(const card of box.querySelectorAll('.preset-card'))card.setAttribute('aria-pressed',String(values.length?values.includes(card.dataset.value):card.dataset.value===select.value));
  box.querySelector('.preset-current').textContent=values.length>1?values.length+' selected':select.value==='__custom__'?'Custom':window.DirectorControls.presetLabel(select.value);
  box.classList.toggle('has-selection',Boolean(select.value));
  box.syncNumeric?.();box.closest('.asset-preset-group')?.syncGroup?.();
}
function resizeCustomPreset(field){
  if(field.hidden)return;
  field.style.height='auto';field.style.height=Math.min(320,Math.max(150,field.scrollHeight))+'px';
}
function updateCustomPreset(select,field,leaving=false){
  if(!field.value.trim()&&(leaving||field.dataset.hasText==='true')){
    field.value='';field.dataset.hasText='false';select.value='';field.hidden=true;
  }else field.dataset.hasText=String(Boolean(field.value.trim()));
  resizeCustomPreset(field);updateCharacterDescription();
}
const multiCharacterTraits=new Set(['accessories','facial_features','distinctive_features']);
const exclusiveCharacterTraits={accessories:[['Glasses','Sunglasses','Oversized surreal glasses'],['Small earrings','Statement earrings']],facial_features:[['High cheekbones','Soft cheeks','Exaggerated cheekbones'],['Strong jawline','Rounded jawline'],['Full lips','Thin lips'],['Broad nose','Narrow nose','Aquiline nose','Button nose','Oversized nose','Tiny nose'],['Thick eyebrows','Fine eyebrows']]};
function chooseCharacterPreset(category,select,value){
  if(traitEditorKind==='character'&&multiCharacterTraits.has(category.id)&&value&&value!=='__custom__'){
    let values=JSON.parse(select.dataset.values||'[]');if(!values.length&&select.value&&select.value!=='__custom__')values=[select.value];
    if(values.includes(value))values=values.filter(v=>v!==value);
    else{
      if(category.id==='accessories')values=value==='No accessories'?[]:values.filter(v=>v!=='No accessories');
      for(const group of exclusiveCharacterTraits[category.id]||[])if(group.includes(value))values=values.filter(v=>!group.includes(v));
      values.push(value);
    }
    select.dataset.values=JSON.stringify(values);select.value=values[0]||'';
  }else{select.dataset.values='[]';select.value=value;}
  select.dispatchEvent(new Event('change',{bubbles:true}));
}
let referenceUploadBusy=false;
function openReferenceUpload(role='reference'){
  if(!currentShot()||referenceUploadBusy)return;
  const input=$('reference-upload-file');input.dataset.role=role;input.dataset.project=project.id;input.dataset.study=shotId;input.value='';input.click();
}
function renderPresetReferences(){
  for(const root of document.querySelectorAll('.preset-upload-previews')){
    const refs=(project?.reference_images||[]).filter(ref=>uploadedReferenceIds.includes(ref.id)&&ref.reference_role===root.dataset.role);
    const stamp=JSON.stringify(refs.map(r=>r.id));if(root.dataset.stamp===stamp)continue;root.dataset.stamp=stamp;
    root.replaceChildren(...refs.map(ref=>{const item=document.createElement('div');item.className='preset-upload-preview';
      const image=document.createElement('img');image.src=fileURL(ref.thumbnail||ref.file);image.alt=ref.name;
      const remove=button('','icon-button',()=>safe(async()=>{uploadedReferenceIds=uploadedReferenceIds.filter(id=>id!==ref.id);renderReferenceChips();await saveNotes(false);}));remove.innerHTML=DirectorIcons.close;remove.setAttribute('aria-label','Remove '+ref.name);item.append(image,remove);return item;}));
  }
}
function buildCharacterControls() {
  const root=$('character-options'),categories=assetCategories();
  const stamp=JSON.stringify([traitEditorKind,categories]);if(!categories.length||root.dataset.stamp===stamp)return;root.dataset.stamp=stamp;
  $('preset-groups').hidden=true;$('preset-groups').replaceChildren();
  root.replaceChildren(...categories.map(category=>{
    const box=document.createElement('details');box.className='character-option preset-section';box.id='preset-'+category.id;
    const summary=document.createElement('summary');summary.className='preset-heading';
    const label=document.createElement('span');label.className='preset-label';label.textContent=category.label;
    const count=document.createElement('span');count.className='preset-option-count';count.textContent=String(category.options.length);count.title=category.options.length+' presets, plus Custom and No preference';
    const selected=document.createElement('span');selected.className='preset-current';
    const arrow=document.createElement('span');arrow.className='preset-chevron';arrow.innerHTML=window.DirectorIcons.chevron;arrow.setAttribute('aria-hidden','true');
    summary.append(presetIcon(category),label,count,selected,arrow);
    const select=document.createElement('input');select.type='hidden';select.id='character-'+category.id;select.value='';
    const options=[{label:'Custom',value:'__custom__'},{label:'No preference',value:''},...category.options.map(value=>({label:value,value}))];
    const custom=document.createElement('textarea');custom.id='character-custom-'+category.id;custom.className='custom-preset-text';custom.rows=6;custom.maxLength=500;custom.hidden=true;custom.placeholder='Your own '+category.label.toLowerCase()+'…';custom.setAttribute('aria-label','Custom '+category.label.toLowerCase());
    const grid=document.createElement('div');grid.className='preset-card-grid';grid.setAttribute('role','group');grid.setAttribute('aria-label',category.label+' options');
    grid.append(...options.map(option=>{
      const card=button('','preset-card',()=>{if(select.disabled)return;chooseCharacterPreset(category,select,option.value);});
      card.dataset.value=option.value;card.setAttribute('aria-pressed',String(!option.value));
      const visual=document.createElement('span');visual.className='preset-card-image';
      const url=config?.preview_images?.['asset-'+traitEditorKind+'-'+category.id]?.[option.value];
      if(option.value==='__custom__'||!option.value){visual.classList.add('preset-card-symbol');visual.textContent=option.value==='__custom__'?'+':'○';}
      else if(url){const img=document.createElement('img');img.src=url;img.alt='';img.loading='lazy';visual.append(img);img.onerror=()=>{img.remove();visual.append(presetIcon(category));};}
      else visual.append(presetIcon(category));
      const text=document.createElement('span');text.className='preset-card-label';text.textContent=window.DirectorControls.presetLabel(option.label);card.append(visual,text);return card;
    }));
    select.onchange=()=>{custom.hidden=select.value!=='__custom__';custom.dataset.hasText=String(Boolean(custom.value.trim()));updateCharacterDescription();if(!custom.hidden){resizeCustomPreset(custom);custom.focus({preventScroll:true});custom.scrollIntoView({block:'nearest',behavior:'smooth'});}};
    custom.oninput=()=>updateCustomPreset(select,custom);
    custom.onblur=()=>updateCustomPreset(select,custom,true);
    box.append(summary,select,custom,grid);
    const photoRole={wardrobe:'wardrobe',accessories:'prop',hairstyle:'hair',hair_color:'hair',face_shape:'identity',facial_features:'identity',render_style:'style',location_type:'background',prop_type:'prop'}[category.id];
    if(photoRole){const photo=button('＋ Image reference','preset-photo-reference',()=>openReferenceUpload(photoRole));const previews=document.createElement('div');previews.className='preset-upload-previews';previews.dataset.role=photoRole;box.insertBefore(photo,grid);box.insertBefore(previews,grid);}
    // Keep the clicked heading at the same position when a previous group closes.
    summary.addEventListener('click',event=>{
      if(select.disabled){event.preventDefault();return;}
      event.preventDefault();const opening=!box.open,scroller=$('editor-scroll'),top=summary.getBoundingClientRect().top;
      if(opening)for(const other of root.querySelectorAll('.preset-section[open]'))if(other!==box)other.open=false;
      box.open=opening;
      scroller.scrollTop+=summary.getBoundingClientRect().top-top;
      if(opening)requestAnimationFrame(()=>{resizeCustomPreset(custom);revealPresetOptions(box);});
    });
    return box;
  }));
  groupAssetPresets(root,categories);
}
function groupAssetPresets(root,categories){
  const specs=traitEditorKind==='character'?[
    ['Identity','character_type',['character_type','gender','age','heritage','skin_tone']],
    ['Body','build',['build','height','proportions','neck']],
    ['Face & eyes','face_shape',['face_shape','facial_features','eye_shape','eye_color','distinctive_features']],
    ['Hair','hairstyle',['hairstyle','hair_color','facial_hair']],
    ['Style & pose','wardrobe',['wardrobe','clothing_color','accessories','expression','pose','render_style']]
  ]:traitEditorKind==='location'?[
    ['Location','location_type',['location_type','world','architecture','scale','era']],
    ['Environment','atmosphere',['materials','time','weather','atmosphere','set_dressing']],
    ['Camera','pose',['sensor','lens_type','aperture','focal_length']],
    ['Direction','framing',['framing','film','render_style']],
    ['Lighting & color','lighting',['lighting','light_color','grade']]
  ]:[
    ['Object','prop_type',['prop_type','design','scale']],
    ['Surface & style','material',['material','condition','grade','render_style']]
  ];
  const ordered=[];
  for(const [title,icon,ids] of specs){
    const members=ids.map(id=>categories.find(c=>c.id===id)).filter(Boolean);if(!members.length)continue;
    const group=document.createElement('details');group.className='character-option preset-section video-camera-group asset-preset-group';
    const summary=document.createElement('summary');summary.className='preset-heading';
    const label=document.createElement('span');label.className='preset-label';label.textContent=title;
    const current=document.createElement('span');current.className='preset-current';
    const arrow=document.createElement('span');arrow.className='preset-chevron';arrow.innerHTML=window.DirectorIcons.chevron;summary.append(presetIcon({id:icon}),label,current,arrow);
    const body=document.createElement('div');body.className='video-camera-body';
    const tabs=document.createElement('div');tabs.className='video-camera-tabs';tabs.setAttribute('role','group');tabs.setAttribute('aria-label',title+' controls');
    const panel=document.createElement('div');panel.className='video-camera-panel';
    let active=members[0].id;
    for(const category of members){
      const box=$('preset-'+category.id);box.classList.add('asset-preset-subsection');box.open=true;box.querySelector(':scope > summary').hidden=true;panel.append(box);
      if(['aperture','focal_length'].includes(category.id))assetCameraSlider(box,category);
      const tab=button('','video-camera-tab',()=>{
        active=active===category.id?null:category.id;group.syncGroup();
        if(active){panel.classList.remove('camera-panel-enter');void panel.offsetWidth;panel.classList.add('camera-panel-enter');requestAnimationFrame(()=>panel.scrollIntoView({block:'nearest',behavior:'smooth'}));}
      });tab.dataset.category=category.id;tab.setAttribute('aria-controls',box.id);
      const name=document.createElement('span');name.textContent=category.label;const value=document.createElement('strong');tab.append(name,value);tabs.append(tab);
    }
    group.syncGroup=()=>{
      let count=0;panel.hidden=active===null;
      for(const tab of tabs.children){const id=tab.dataset.category,value=$('character-'+id).value;count+=Boolean(value);
        const values=JSON.parse($('character-'+id).dataset.values||'[]');tab.querySelector('strong').textContent=values.length>1?values.length+' selected':value==='__custom__'?'Custom':value||'Auto';tab.setAttribute('aria-pressed',String(id===active));tab.setAttribute('aria-expanded',String(id===active));tab.title=values.length?values.join(', '):tab.querySelector('strong').textContent;
        $('preset-'+id).hidden=id!==active;
      }
      current.textContent=count?count+' selected':'';group.classList.toggle('has-selection',count>0);
    };
    summary.onclick=event=>{
      event.preventDefault();if($('character-'+members[0].id).disabled)return;
      const opening=!group.open,scroller=$('editor-scroll'),top=summary.getBoundingClientRect().top;
      if(opening)for(const other of root.children)if(other!==group)other.open=false;
      group.open=opening;scroller.scrollTop+=summary.getBoundingClientRect().top-top;
      if(opening)requestAnimationFrame(()=>body.scrollIntoView({block:'nearest',behavior:'smooth'}));
    };
    body.append(tabs,panel);group.append(summary,body);ordered.push(group);
  }
  const leftovers=[...root.children];root.replaceChildren(...ordered,...leftovers);
}
function assetCameraSlider(box,category){
  const select=box.querySelector('input[type=hidden]'),grid=box.querySelector('.preset-card-grid');grid.hidden=true;
  const panel=document.createElement('div');panel.className='asset-camera-slider';box.append(panel);
  const aperture=category.id==='aperture',stops=[5,8,10,12,14,16,18,20,24,28,30,35,40,50,55,65,75,85,95,100,105,135,150,180,200,250,300,400,500];
  const position=mm=>Math.log(mm/5)/Math.log(100)*1000;
  const focal=n=>stops.reduce((best,mm)=>Math.abs(position(mm)-n)<Math.abs(position(best)-n)?mm:best);
  let stamp='';
  box.syncNumeric=()=>{
    if(panel.contains(document.activeElement)||stamp===select.value)return;stamp=select.value;panel.replaceChildren();
    const slider=document.createElement('div');
    window.DirectorControls.sliderChoices(slider,{kind:'camera',value:aperture?Math.max(0,category.options.indexOf(select.value||'f/4')):position(parseInt(select.value)||50),min:0,max:aperture?category.options.length-1:1000,step:aperture?1:'any',
      snapPoints:aperture?[]:stops.map(position),ticks:aperture?['f/0.7','f/1.4','f/2.8','f/5.6','f/11','f/32'].map(label=>({value:category.options.indexOf(label),label})):[5,16,50,150,500].map(mm=>({value:position(mm),label:mm+' mm'})),
      id:'asset-camera-'+category.id,caption:category.label,format:n=>aperture?category.options[n]:focal(n)+' mm',
      onChange:n=>{select.value=aperture?category.options[n]:focal(n)+'mm';select.dispatchEvent(new Event('change',{bubbles:true}));}});
    slider.classList.add('camera-inline-slider');
    const actions=document.createElement('div');actions.className='video-camera-choices';
    for(const [label,value] of [['Auto',''],['+ Custom','__custom__']]){const b=button(label,'generation-choice',()=>{b.blur();select.value=value;select.dispatchEvent(new Event('change',{bubbles:true}));});b.setAttribute('aria-pressed',String(select.value===value));actions.append(b);}
    panel.append(slider,actions);
  };
  // Ensure the first empty (Auto) state still builds its slider.
  stamp=null;box.syncNumeric();
}
function readCharacterTraits() {
  return Object.fromEntries(assetCategories().flatMap(category=>{
    const value=$('character-'+category.id)?.value || '',custom=$('character-custom-'+category.id)?.value || '';
    const values=JSON.parse($('character-'+category.id)?.dataset.values||'[]');
    return value||custom?[[category.id,{value,custom,...(values.length?{values}:{} )}]]:[];
  }));
}
function setCharacterEditor(traits) {
  buildCharacterControls();
  for(const category of assetCategories()) {
    const select=$('character-'+category.id),custom=$('character-custom-'+category.id);if(!select)continue;
    select.value=traits[category.id]?.value || '';custom.value=traits[category.id]?.custom || '';custom.hidden=select.value!=='__custom__';
    select.dataset.values=JSON.stringify(traits[category.id]?.values||[]);
    custom.dataset.hasText=String(Boolean(custom.value.trim()));requestAnimationFrame(()=>resizeCustomPreset(custom));
  }
  updateCharacterDescription();
}
function setAssetEditor(shot) {
  assetTraitDrafts=Object.fromEntries(['character','location','prop'].map(kind=>[kind,structuredClone(shot[kind+'_traits'] || {})]));
  traitEditorKind=$('asset_kind').value;setCharacterEditor(assetTraitDrafts[traitEditorKind]);
}
function characterDescription(traits=readCharacterTraits(),kind=traitEditorKind) {
  return assetCategories(kind).flatMap(category=>{
    const choice=traits[category.id],text=choice?.value==='__custom__'?choice.custom.trim():choice?.values?.length?choice.values.join(', '):choice?.value;
    const cue=choice?.value==='__custom__'?text:category.hints?.[text] || text;
    return cue?[category.label+': '+cue.replace(/\.$/,'')+'.']:[];
  }).join('\n');
}
function updateCharacterDescription() {
  const description=characterDescription(),count=Object.values(readCharacterTraits()).filter(choice=>choice.value==='__custom__'?choice.custom.trim():choice.value).length;
  $('character-count').textContent=count?count+' selected':'Optional details';
  $('character-prompt-preview').textContent=description || 'Choose a detail to start.';
  for(const category of assetCategories())syncPresetCards(category);
}
function renderCharacterVisibility() {
  const asset=creationMode==='asset';$('asset-type-control').hidden=!asset||Boolean(imageEdit);$('character-builder').hidden=!asset||Boolean(imageEdit);
  const kind=$('asset_kind').value,label={character:'Character',location:'Location',prop:'Prop'}[kind];
  $('character-heading').textContent=label+' studio';

  $('asset-description-toggle').textContent=label+' description';$('clear-character').setAttribute('aria-label','Reset '+kind+' options');$('clear-character').title='Reset '+kind+' options';
}
$('asset_kind').onchange=()=>{
  assetTraitDrafts[traitEditorKind]=readCharacterTraits();traitEditorKind=$('asset_kind').value;
  setCharacterEditor(assetTraitDrafts[traitEditorKind] || {});renderCharacterVisibility();window.DirectorDropdowns.sync();
};
$('clear-character').onclick=()=>{assetTraitDrafts[traitEditorKind]={};setCharacterEditor({});window.DirectorDropdowns.sync();};

$('asset-browse').onclick=()=>{if(project)openLibrary('all','assets');};
$('asset-rename').onclick=()=>safe(async()=>{
  const shot=currentShot();if(!shot)return;
  const value=await window.DirectorNavigator.rename(shot.title);if(!value||value===shot.title)return;
  await saveNotes(false);
  if(shot.asset_id){project=await api(`/projects/${project.id}/assets/${shot.asset_id}`,'PATCH',{handle:value});$('prompt').value=currentShot().prompt;$('title').value=currentShot().title;}
  else{$('title').value=value;shot.title=value;await saveNotes(false);}
  render();
});
$('asset-delete').onclick=()=>safe(async()=>{
  const shot=currentShot();if(!shot||!await confirmAssetDeletion({name:shot.title}))return;
  await saveNotes(false);project=await api(`/projects/${project.id}/shots/${shot.id}`,'DELETE');shotId=visibleStudies()[0]?.id;selectedDraft=null;imageEdit=null;
  if(!shotId){const next=await api(`/projects/${project.id}/shots`,'POST',{mode:'asset'});project=await api(`/projects/${project.id}`);shotId=next.id;}
  setEditor(currentShot());referenceIds=currentShot().reference_ids||[];render();toast('Asset deleted.');
});
$('models-dialog').addEventListener('close',()=>{saveEnginePreferences();lock();});

$('copy-prompt').onclick=()=>safe(async()=>{
  const text=$('prompt-used').textContent;if(!text)return;
  try{if(!navigator.clipboard?.writeText)throw new Error('HTTP clipboard');await navigator.clipboard.writeText(text);}
  catch{const field=document.createElement('textarea');field.value=text;field.style.cssText='position:fixed;left:-10000px';document.body.append(field);field.select();const copied=document.execCommand('copy');field.remove();if(!copied)throw new Error('Select the prompt text and copy it with Ctrl+C.');}
  toast('Prompt copied.');
});
function openImageViewer(src){
  if(!src)return;
  const image=$('viewer-image'),dialog=$('image-viewer');
  image.style.width='auto';
  image.onload=()=>{image.style.width=Math.min(image.naturalWidth,innerWidth*.92,innerHeight*.92*image.naturalWidth/image.naturalHeight)+'px';};
  image.src=src;if(image.complete&&image.naturalWidth)image.onload();
  if(!dialog.open)dialog.showModal();dialog.scrollTo(0,0);
}
function openViewer(){const source=$('preview').querySelector('img');if(source)openImageViewer(source.src);}
$('preview').onclick=openViewer;
$('preview').onkeydown=event=>{if(event.key==='Enter'||event.key===' '){event.preventDefault();openViewer();}};
$('image-viewer').onclick=event=>{if(event.target!==$('viewer-image'))$('image-viewer').close();};
function isDialogBackdrop(event,dialog){
  if(event.target!==dialog)return false;
  const rect=dialog.getBoundingClientRect();
  return event.clientX<rect.left||event.clientX>rect.right||event.clientY<rect.top||event.clientY>rect.bottom;
}
for(const dialog of document.querySelectorAll('dialog:not(#image-viewer)')){
  let startedOutside=false;
  dialog.addEventListener('pointerdown',event=>{startedOutside=isDialogBackdrop(event,dialog);});
  dialog.addEventListener('click',event=>{
    if(startedOutside&&isDialogBackdrop(event,dialog))dialog.close('cancel');
    startedOutside=false;
  });
}
$('tab-assets').onclick=()=>safe(()=>switchCreationMode('asset'));
$('open-library').onclick=()=>{$('asset-library').hidden?openLibrary('all',window.DirectorVideo?.active?'shots':'assets'):closeLibrary();};
$('close-library').onclick=closeLibrary;
$('attach-reference').onclick=()=>openReferenceUpload();
async function uploadReferenceFiles(files,projectId,studyId,role='reference'){
  if(referenceUploadBusy){toast('A reference is already uploading.');return;}
  if(!projectId||!studyId)return;
  const images=files.filter(file=>/^image\/(png|jpeg|webp)$/i.test(file.type)||(!file.type&&/\.(png|jpe?g|webp)$/i.test(file.name)));
  if(!images.length){toast('Choose PNG, JPEG or WebP images.');return;}
  if(project?.id===projectId&&shotId===studyId&&images.length+resolvedReferenceIds().length+uploadedReferenceIds.length+(imageEdit?1:0)>10){toast(imageEdit?'Use up to 9 additional references while editing.':'Use up to 10 image references at a time.');return;}
  referenceUploadBusy=true;lock();
  try{if(project?.id===projectId&&shotId===studyId)await saveNotes(false);
    for(const file of images){const data=new FormData();data.append('image',file);data.append('role',role);
      const response=await fetch(`/api/projects/${projectId}/shots/${studyId}/references`,{method:'POST',body:data}),result=await response.json();if(!response.ok)throw new Error(result.error||'Upload failed');
      if(project?.id===projectId){project=result;if(shotId===studyId)uploadedReferenceIds=[...(currentShot().upload_reference_ids||[])];render();}
    }toast(images.length===1?'Reference added.':'References added.');
  }finally{referenceUploadBusy=false;lock();}
}
$('reference-upload-file').onchange=()=>{
  const input=$('reference-upload-file'),files=[...input.files];input.value='';
  if(files.length)safe(()=>uploadReferenceFiles(files,input.dataset.project,input.dataset.study,input.dataset.role||'reference'));
};
async function uploadWebReference(url,projectId,studyId){
  if(project?.id===projectId&&shotId===studyId&&resolvedReferenceIds().length+uploadedReferenceIds.length+(imageEdit?1:0)>=10){toast(imageEdit?'Use up to 9 additional references while editing.':'Use up to 10 image references at a time.');return;}
  if(referenceUploadBusy){toast('A reference is already uploading.');return;}
  referenceUploadBusy=true;lock();
  try{
    if(project?.id===projectId&&shotId===studyId)await saveNotes(false);
    toast('Importing image reference…');
    const result=await api(`/projects/${projectId}/shots/${studyId}/references`,'POST',{url,role:'reference'});
    if(project?.id===projectId){project=result;if(shotId===studyId)uploadedReferenceIds=[...(currentShot().upload_reference_ids||[])];render();}
    toast('Reference added.');
  }finally{referenceUploadBusy=false;lock();}
}
function droppedImageURL(transfer){
  const uri=(transfer.getData('text/uri-list')||'').split(/\r?\n/).find(line=>line.trim()&&!line.startsWith('#'))?.trim();
  const html=transfer.getData('text/html');
  if(html){
    const image=new DOMParser().parseFromString(html,'text/html').querySelector('img');
    const src=image?.getAttribute('src');
    if(src){try{return new URL(src,uri||location.href).href;}catch{}}
  }
  return uri||transfer.getData('text/plain').trim();
}
// External files, browser image drags and clipboard bitmaps share asset references.
(() => {
  const overlay=document.createElement('div');overlay.id='reference-drop-zone';overlay.hidden=true;overlay.setAttribute('aria-hidden','true');
  overlay.innerHTML='<div><span class="reference-drop-icon" aria-hidden="true">＋</span><strong>Drop images to add references</strong><span>PNG · JPEG · WebP · Web images</span></div>';
  document.body.append(overlay);let depth=0,internalDrag=false;
  const fileDrag=event=>Array.from(event.dataTransfer?.types||[]).includes('Files');
  const imageDrag=event=>!internalDrag&&Array.from(event.dataTransfer?.types||[]).some(type=>['Files','text/html','text/uri-list'].includes(type));
  const available=()=>creationMode==='asset'&&!window.DirectorVideo?.active&&Boolean(currentShot())&&!referenceUploadBusy&&!document.querySelector('dialog[open]');
  function clear(){depth=0;overlay.hidden=true;document.body.classList.remove('reference-drop-active');}
  function show(){overlay.hidden=false;document.body.classList.add('reference-drop-active');}
  document.addEventListener('dragstart',()=>{internalDrag=true;});
  document.addEventListener('dragenter',event=>{if(!imageDrag(event))return;event.preventDefault();if(available()){depth++;show();}});
  document.addEventListener('dragover',event=>{if(!imageDrag(event))return;event.preventDefault();event.dataTransfer.dropEffect=available()?'copy':'none';if(available())show();else clear();});
  document.addEventListener('dragleave',event=>{if(overlay.hidden)return;depth=Math.max(0,depth-1);if(!depth||(!event.relatedTarget&&(event.target===document||event.target===document.documentElement)))clear();});
  document.addEventListener('drop',event=>{
    const isImage=imageDrag(event);if(!isImage&&!fileDrag(event)){clear();return;}
    event.preventDefault();const canUpload=available()&&isImage,files=Array.from(event.dataTransfer.files||[]),url=droppedImageURL(event.dataTransfer);clear();internalDrag=false;
    if(!canUpload)return;
    event.stopPropagation();const projectId=project.id,studyId=shotId;
    if(files.length){safe(()=>uploadReferenceFiles(files,projectId,studyId));return;}
    if(/^https?:\/\//i.test(url)){safe(()=>uploadWebReference(url,projectId,studyId));return;}
    if(/^data:image\/(png|jpeg|webp)[;,]/i.test(url)&&url.length<46*1024*1024){
      safe(async()=>{const blob=await (await fetch(url)).blob();await uploadReferenceFiles([new File([blob],'web-reference.'+(blob.type==='image/jpeg'?'jpg':blob.type.split('/')[1]),{type:blob.type})],projectId,studyId);});return;
    }
    toast('Copy the image with Ctrl+C, then paste it here with Ctrl+V, or save it first.');
  });
  document.addEventListener('paste',event=>{
    if(!available())return;
    const files=Array.from(event.clipboardData?.items||[]).filter(item=>item.kind==='file'&&/^image\/(png|jpeg|webp)$/i.test(item.type)).map(item=>item.getAsFile()).filter(Boolean);
    if(!files.length)return; // Ordinary pasted text keeps its normal behavior.
    event.preventDefault();const projectId=project.id,studyId=shotId;safe(()=>uploadReferenceFiles(files,projectId,studyId));
  });
  window.addEventListener('dragend',()=>{internalDrag=false;clear();});window.addEventListener('blur',()=>{internalDrag=false;clear();});
  document.addEventListener('visibilitychange',()=>{if(document.hidden){internalDrag=false;clear();}});
})();
$('library-kind').onchange=()=>renderLibrary(true);$('library-search').oninput=()=>renderLibrary(true);
$('library-source').onchange=()=>safe(async()=>{const version=++libraryLoadVersion;librarySource=$('library-source').value;libraryAssets=[];renderLibrary(true);if(librarySource){const assets=await api(`/projects/${librarySource}/assets`);if(version===libraryLoadVersion){libraryAssets=assets;renderLibrary(true);}}});
$('edit-image').onclick=startImageEdit;$('cancel-image-edit').onclick=()=>safe(stopImageEdit);
// Library drops are imports, never generation references. Dialog-local targets stay in the top layer.
function importImageName(file){return file.name.replace(/\.[^.]+$/,'').replace(/[_-]+/g,' ').slice(0,120)||'Imported image';}
function setImportFiles(files){
  const transfer=new DataTransfer();for(const file of files)transfer.items.add(file);
  $('asset-image').files=transfer.files;
}
$('asset-image').onchange=()=>{
  const files=[...$('asset-image').files];if(!files.length)return;
  if(!$('asset-name').value.trim())$('asset-name').value=importImageName(files[0]);
  $('asset-dialog-heading').textContent=files.length>1?`Import ${files.length} images`:'Import image';
  $('confirm-save-asset').textContent=files.length>1?'Import images':'Import image';
};
(() => {
  for(const id of ['asset-library','asset-dialog']){
    const dialog=$(id),overlay=document.createElement('div');overlay.className='library-drop-zone';overlay.hidden=true;overlay.setAttribute('aria-hidden','true');
    overlay.innerHTML='<div><span class="reference-drop-icon" aria-hidden="true">＋</span><strong>Drop images to import</strong><span>PNG · JPEG · WebP</span></div>';dialog.append(overlay);
    let depth=0;
    const filesDragged=event=>Array.from(event.dataTransfer?.types||[]).includes('Files');
    const allowed=()=>Boolean(project)&&!$('confirm-save-asset').disabled&&(id==='asset-library'?dialog.open&&dialog.dataset.tab==='assets'&&!$('asset-dialog').open:dialog.open&&!assetSaveSource);
    const clear=()=>{depth=0;overlay.hidden=true;};
    dialog.addEventListener('dragenter',event=>{if(!filesDragged(event))return;event.preventDefault();event.stopPropagation();if(allowed()){depth++;overlay.hidden=false;}});
    dialog.addEventListener('dragover',event=>{if(!filesDragged(event))return;event.preventDefault();event.stopPropagation();event.dataTransfer.dropEffect=allowed()?'copy':'none';overlay.hidden=!allowed();});
    dialog.addEventListener('dragleave',event=>{if(overlay.hidden)return;event.stopPropagation();depth=Math.max(0,depth-1);if(!depth||(!event.relatedTarget&&event.target===dialog))clear();});
    dialog.addEventListener('drop',event=>{
      if(!filesDragged(event))return;event.preventDefault();event.stopPropagation();const canImport=allowed();clear();if(!canImport)return;
      const files=Array.from(event.dataTransfer.files||[]).filter(file=>/^image\/(png|jpeg|webp)$/i.test(file.type)||(!file.type&&/\.(png|jpe?g|webp)$/i.test(file.name)));
      if(!files.length){toast('Choose PNG, JPEG or WebP images.');return;}
      if(files.some(file=>file.size>32*1024*1024)){toast('Choose images up to 32 MB each.');return;}
      if(id==='asset-library')showAssetDialog();
      setImportFiles(files);$('asset-image').onchange();$('asset-name').focus();$('asset-name').select();
    });
    dialog.addEventListener('close',clear);window.addEventListener('dragend',clear);window.addEventListener('blur',clear);
  }
})();
$('import-asset').onclick=()=>showAssetDialog();$('close-asset-dialog').onclick=()=>$('asset-dialog').close();
$('save-as-asset').onclick=()=>safe(async()=>{
  const study=currentShot(),asset=project?.assets?.find(a=>a.id===study?.asset_id);
  if(!study)return;
  if(!asset){showAssetDialog({project:project.id,shot:shotId,draft:selectedDraft});return;}
  const pid=project.id,source=study.id,draft=selectedDraft;
  $('save-as-asset').disabled=true;
  try{await saveNotes(false);await api(`/projects/${pid}/assets`,'POST',{save_action:'overwrite',shot_id:source,draft_id:draft,name:asset.name,kind:asset.kind,description:asset.description||''});
    if(project?.id===pid){project=await api(`/projects/${pid}`);render();renderLibrary(true);}toast('Asset cover updated.');
  }finally{lock();}
});
$('asset-form').onsubmit=event=>{event.preventDefault();safe(async()=>{
  const overwrite=Boolean(assetSaveSource&&creationMode==='asset');const linked=project?.assets?.find(a=>a.id===currentShot()?.asset_id);
  const pid=assetSaveSource?.project || project.id, fields={save_action:overwrite?'overwrite':'new',name:$('asset-name').value.trim()||linked?.name||currentShot()?.title,kind:$('asset-kind').value,description:$('asset-description').value};
  $('confirm-save-asset').disabled=true;$('overwrite-asset').disabled=true;$('asset-save-status').textContent='Saving image…';
  try {
    let asset;
    if(assetSaveSource){await saveNotes(false);asset=await api(`/projects/${pid}/assets`,'POST',{...fields,shot_id:assetSaveSource.shot,draft_id:assetSaveSource.draft});}
    else {
      const files=[...$('asset-image').files];if(!files.length)throw new Error('Choose an image.');
      for(let index=0;index<files.length;index++){
        $('asset-save-status').textContent=files.length>1?`Importing ${index+1} / ${files.length}…`:'Importing image…';
        const data=new FormData();for(const [key,value] of Object.entries(fields))data.append(key,key==='name'&&index>0?importImageName(files[index]):value);
        data.append('image',files[index]);const response=await fetch(`/api/projects/${pid}/assets`,{method:'POST',body:data});asset=await response.json();if(!response.ok)throw new Error(asset.error || 'Image import failed.');
        // On a later failure, retries contain only files that were not already imported.
        setImportFiles(files.slice(index+1));if(index+1<files.length)$('asset-name').value=importImageName(files[index+1]);
      }
    }
    if(project?.id===pid){project=await api(`/projects/${pid}`);if(currentShot()){$('title').value=currentShot().title;$('prompt').value=currentShot().prompt;}render();renderLibrary(true);}
    $('asset-dialog').close();toast('Asset saved. Use @'+asset.handle+' in your prompt.');
  } catch(error){$('asset-save-status').textContent=error.message;throw error;}
  finally{$('confirm-save-asset').disabled=false;$('overwrite-asset').disabled=false;}
});};
$('prompt').addEventListener('input',()=>{renderMentions();renderReferenceChips();renderModels();});
$('prompt').addEventListener('keydown',event=>{
  const root=$('mention-suggestions');if(root.hidden)return;
  if(event.key==='Escape'){root.hidden=true;event.preventDefault();return;}
  const options=mentionOptions();
  if(!options.length)return;
  if(event.key==='ArrowDown'||event.key==='ArrowUp'){event.preventDefault();mentionIndex=(mentionIndex+(event.key==='ArrowDown'?1:-1)+options.length)%options.length;[...root.children].forEach((el,i)=>el.setAttribute('aria-selected',String(i===mentionIndex)));revealMentionOption(root,mentionIndex);}
  if(event.key==='Enter'&&!event.ctrlKey&&options[mentionIndex]){event.preventDefault();useAsset(options[mentionIndex],true);}
});
$('prompt').addEventListener('blur',()=>{setTimeout(()=>{const menu=$('mention-suggestions');if(!menu.matches(':hover')&&!menu.contains(document.activeElement))menu.hidden=true;},150);});
$('mention-suggestions').addEventListener('mouseleave',()=>{if(document.activeElement!==$('prompt'))$('mention-suggestions').hidden=true;});
document.addEventListener('keydown',event=>{if(event.key==='Escape'&&!document.querySelector('dialog[open]:not(#asset-library)')&&!$('asset-library').hidden)closeLibrary();});
document.addEventListener('keydown',event=>{
  if(window.DirectorVideo?.active)return;
  if(event.key!=='Enter'||!event.ctrlKey||event.isComposing||document.querySelector('dialog[open]'))return;
  event.preventDefault();
  if(!event.repeat&&!$('generate').disabled)$('generate').click();
});
$('generate').title='Generate · Ctrl+Enter';$('generate').setAttribute('aria-keyshortcuts','Control+Enter');

window.DirectorDropdowns.sync();
lock();
safe(async()=>{
  config=await api('/config');
  for(const [id,values] of [['style',config.styles],['camera',config.cameras],['lens_type',config.lens_types],['sensor',config.sensors],['light_color',config.light_colors],['lighting',config.lighting],['film',config.films],['grade',config.grades]]) $(id).replaceChildren(...values.map(x=>new Option(x,x)));

  window.DirectorDropdowns.configure(config);
  populateWorkflows();
  const projects=await projectList(), previous=localStorage.getItem('openframe-project');
  if(projects.length)await openProject(projects.find(p=>p.id===previous)?.id || projects[0].id);
  lock();connection();refresh();document.dispatchEvent(new Event('director-ready'));
});

$('editor-heading').ondblclick=()=>$('asset-rename').onclick();
function setLibraryGridSize(){const value=Number($('library-grid-size').value);$('library-items').style.setProperty('--library-tile',value+'px');try{localStorage.setItem('directors-cut-library-size',String(value));}catch{}}
try{$('library-grid-size').value=localStorage.getItem('directors-cut-library-size')||'260';}catch{}
$('library-grid-size').oninput=setLibraryGridSize;setLibraryGridSize();

/* One live overview, using the existing queue poll; no extra timers or media loads. */
(() => {
  const dialog=$('generation-queue-dialog'),list=$('generation-queue-list'),rows=new Map(),stopping=new Set();
  const triggers=['open-generation-queue','queue-count','video-queue-status'];
  function control(icon,label,action){const b=document.createElement('button');b.type='button';b.className='queue-item-action';b.innerHTML=DirectorIcons[icon];b.title=label;b.setAttribute('aria-label',label);b.onclick=()=>safe(action);return b;}
  async function openTake(item){
    dialog.close();
    if(project?.id!==item.project_id){if(window.DirectorVideo?.active)await DirectorVideo.leave();await openProject(item.project_id);}
    const target=project.shots.find(s=>s.id===item.shot_id);
    if(!target)throw new Error('This shot is no longer available.');
    if(target.mode==='video')await DirectorVideo.selectShot(item.shot_id,item.id);
    else{await selectShot(item.shot_id);selectedDraft=item.id;revealSelectedTake=true;render();}
  }
  async function cancel(item){
    stopping.add(item.id);draw();
    try{await api(`/projects/${item.project_id}/shots/${item.shot_id}/drafts/${item.id}/cancel`,'POST',{});await refreshQueue();}
    catch(error){stopping.delete(item.id);draw();throw error;}
  }
  function makeRow(item){
    const row=document.createElement('article');row.className='generation-queue-item';row.dataset.take=item.id;
    const position=document.createElement('span');position.className='queue-position';
    const info=document.createElement('div');info.className='queue-item-info';
    const title=document.createElement('strong'),meta=document.createElement('span'),status=document.createElement('span');
    meta.className='queue-item-meta';status.className='queue-item-status';
    const meter=document.createElement('progress');meter.max=1;meter.setAttribute('aria-label','Generation progress');
    info.append(title,meta,status,meter);
    const open=control('right','Open take',()=>openTake(record.item)),stop=control('close','Cancel take',()=>cancel(record.item));
    const record={row,position,title,meta,status,meter,open,stop,item};row.append(position,info,open,stop);return record;
  }
  function draw(){
    const items=queueState.items||[],ids=new Set(items.map(i=>i.id)),total=items.length;
    $('global-queue-total').textContent=String(total);$('open-generation-queue').dataset.busy=String(total>0);
    $('open-generation-queue').setAttribute('aria-label',`Generation queue: ${queueState.running} active, ${queueState.waiting} waiting`);
    for(const id of stopping)if(!ids.has(id))stopping.delete(id);
    if(!dialog.open)return;
    $('generation-queue-summary').textContent=`${queueState.running} active · ${queueState.waiting} waiting`;
    for(const [id,record] of rows)if(!ids.has(id)){record.row.remove();rows.delete(id);}
    let empty=list.querySelector('.queue-empty');
    if(!total){if(!empty){empty=document.createElement('p');empty.className='queue-empty';empty.textContent='Your queue is clear.';list.append(empty);}return;}
    empty?.remove();
    for(const [index,item] of items.entries()){
      let r=rows.get(item.id);if(!r){r=makeRow(item);rows.set(item.id,r);}r.item=item;
      const waiting=Boolean(item.can_cancel),busy=stopping.has(item.id)||item.stage==='Stopping…';
      r.row.dataset.running=String(!waiting);r.position.textContent=waiting?String(item.position||index+1):'Now';
      r.title.textContent=item.title||'Untitled';r.meta.textContent=`${item.project_name} · Take ${item.take}${item.ratio?' · '+item.ratio:''}`;
      const progress=Math.max(0,Math.min(1,Number(item.progress)||0));
      r.status.textContent=busy?'Stopping…':waiting?'Waiting':`${item.stage||'Preparing'}${progress>0?' · '+Math.round(progress*100)+'%':''}`;
      r.meter.hidden=waiting||busy;if(progress>0)r.meter.value=progress;else r.meter.removeAttribute('value');
      r.stop.disabled=busy;r.stop.innerHTML=DirectorIcons[waiting?'close':'skip'];
      r.stop.title=waiting?'Remove from queue':'Skip current generation';r.stop.setAttribute('aria-label',r.stop.title);
      if(list.children[index]!==r.row)list.insertBefore(r.row,list.children[index]||null);
    }
  }
  async function open(){dialog.showModal();draw();await refreshQueue();}
  for(const id of triggers)$(id).onclick=()=>safe(open);
  $('close-generation-queue').innerHTML=DirectorIcons.close;
  $('close-generation-queue').onclick=()=>dialog.close();
  dialog.addEventListener('click',event=>{if(event.target!==dialog)return;const r=dialog.getBoundingClientRect();if(event.clientX<r.left||event.clientX>r.right||event.clientY<r.top||event.clientY>r.bottom)dialog.close();});
  window.DirectorQueue={render:draw};draw();
})();

