/* Visual person selection. Recognition stays local; mappings persist in take settings. */
(()=>{
  const dialog=document.createElement('dialog');dialog.className='people-dialog';dialog.setAttribute('aria-label','Choose people to replace');
  dialog.innerHTML='<header><h2>Choose people</h2><button type="button" class="icon-button people-close" aria-label="Close people">'+DirectorIcons.close+'</button></header><p class="people-status" role="status"></p><div class="people-content" hidden><div class="people-visual"><div class="people-stage"><div class="people-frame"><img alt="People detected in the source shot"><div class="people-boxes"></div></div></div><nav class="people-shots" aria-label="Source shots"></nav></div><div class="people-list"></div></div><footer><button type="button" class="subtle people-cancel" hidden>Cancel identification</button><button type="button" class="subtle people-retry" hidden>Try again</button><button type="button" class="primary people-apply" hidden>Use selections</button></footer>';
  document.body.append(dialog);const q=s=>dialog.querySelector(s);let data=null,mapping={},shot=0,selected=null,picking=null,token=0,timer=null,resolve=null,context=null,openedAt=0;
  q('.people-status').insertAdjacentHTML('beforebegin','<div class="people-scanning" aria-hidden="true"><span></span><span></span><span></span><i></i></div>');
  q('.people-status').insertAdjacentHTML('afterend','<div class="people-metrics" hidden><div><span class="people-elapsed"></span><strong class="people-steps"></strong></div><progress class="people-work" hidden></progress><p class="people-freshness"></p></div>');
  const clock=seconds=>{const n=Math.max(0,Math.floor(seconds));return Math.floor(n/60)+':'+String(n%60).padStart(2,'0');};
  const snapshot=()=>DirectorSwap.capture({});
  const same=()=>project?.id===context?.pid&&snapshot().swap_source_id===context?.source;
  const stop=()=>{token++;clearTimeout(timer);};
  function close(){const job=data?.id,pid=context?.pid,busy=!['succeeded','failed','cancelled'].includes(data?.status);stop();dialog.close();if(busy&&job&&pid)api(`/projects/${pid}/people/${job}/cancel`,'POST',{}).catch(()=>{});const done=resolve;resolve=null;done?.(false);picking=null;}
  q('.people-close').onclick=close;dialog.oncancel=e=>{e.preventDefault();close();};dialog.onclick=e=>{if(e.target===dialog){const r=dialog.getBoundingClientRect();if(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom)close();}};
  function applyDefaults(){
    const s=snapshot(),valid=new Set(data.people.map(p=>p.id));mapping=s.swap_analysis_id===data.id?Object.fromEntries(Object.entries(s.swap_people_map||{}).filter(([p,a])=>valid.has(p)&&s.reference_ids.includes(a))):{};
    if(!selected)selected=data.people.find(p=>p.matched)?.id||null;
    if(!Object.keys(mapping).length)data.people.filter(p=>p.matched).sort((a,b)=>Number(a.id.slice(1))-Number(b.id.slice(1))).slice(0,s.reference_ids.filter((id,i)=>s.swap_roles[i]!=='background').length).forEach((p,i)=>mapping[p.id]=s.reference_ids.filter((id,j)=>s.swap_roles[j]!=='background')[i]);
  }
  function draw(){
    if(!dialog.open||!same())return;
    const ready=data?.status==='succeeded';dialog.classList.toggle('is-busy',!['succeeded','failed','cancelled'].includes(data?.status));q('.people-content').hidden=!ready;q('.people-apply').hidden=!ready;q('.people-retry').hidden=!['failed','cancelled'].includes(data?.status);q('.people-cancel').hidden=ready||['failed','cancelled'].includes(data?.status);
    q('.people-status').textContent=ready?'Select a person, then choose their replacement.':data?.error||data?.stage||'Finding people…';
    const busy=!['succeeded','failed','cancelled'].includes(data?.status);q('.people-metrics').hidden=!busy;
    if(busy){const now=Date.now()/1000;q('.people-elapsed').textContent='Elapsed '+clock(now-(data?.started_at||openedAt));const step=data?.step,total=data?.steps,hasSteps=Number.isFinite(step)&&Number.isFinite(total)&&total>0;const meter=q('.people-work');meter.hidden=!hasSteps;if(hasSteps){meter.max=total;meter.value=step;}q('.people-steps').textContent=hasSteps?(data.current_node==='5'?'Frame ':'Step ')+step+' / '+total:'';const last=data?.last_progress_at;q('.people-freshness').textContent=last?'Last progress '+clock(now-last)+' ago'+(now-last>=45?' · Waiting for the next engine update.':''):'Waiting for detailed engine progress. Loading models may take a while.';}
    if(!ready)return;
    q('.people-apply').disabled=!Object.keys(mapping).length;
    const sourceShot=data.shots[Math.min(shot,data.shots.length-1)];if(!sourceShot){q('.people-status').textContent='No visible people found. Try another part of the video.';return;}
    const image=q('.people-frame>img');image.onload=()=>q('.people-frame').style.setProperty('--frame-ratio',String(image.naturalWidth/image.naturalHeight));image.src=fileURL(sourceShot.image,context.pid);
    q('.people-shots').replaceChildren(...data.shots.map((s,i)=>{const b=button(String(i+1),'subtle',()=>{shot=i;draw();});b.setAttribute('aria-label','Shot '+(i+1));b.setAttribute('aria-pressed',String(i===shot));return b;}));
    q('.people-boxes').replaceChildren(...sourceShot.boxes.map(box=>{const b=button('','people-target-box',()=>{selected=box.person;draw();});b.style.left=box.x*100+'%';b.style.top=box.y*100+'%';b.style.width=box.width*100+'%';b.style.height=box.height*100+'%';const person=data.people.find(p=>p.id===box.person);const label=person?.matched?'Person '+person.id.slice(1):'Unmatched';b.setAttribute('aria-label','Select '+label);b.setAttribute('aria-pressed',String(selected===box.person));b.classList.toggle('is-mapped',Boolean(mapping[box.person]));const text=document.createElement('span');text.textContent=label;b.append(text);return b;}));
    q('.people-list').replaceChildren(...data.people.map((person,i)=>{const card=document.createElement('section');card.className='people-person';card.classList.toggle('is-selected',person.id===selected);const identity=button('','people-identity',()=>{selected=person.id;const where=data.shots.findIndex(s=>s.boxes.some(b=>b.person===person.id));if(where>=0)shot=where;draw();});const photo=document.createElement('img');photo.src=fileURL(person.thumbnail,context.pid);photo.alt='';const title=document.createElement('strong');title.textContent=person.matched?'Person '+person.id.slice(1):'Unmatched person';identity.append(photo,title);card.append(identity);
      const options=document.createElement('div');options.className='people-replacements';const keep=button('Keep original','subtle',()=>{delete mapping[person.id];selected=person.id;draw();});keep.setAttribute('aria-pressed',String(!mapping[person.id]));options.append(keep);
      for(const id of snapshot().reference_ids.filter((id,i)=>snapshot().swap_roles[i]!=='background')){const a=project.assets.find(a=>a.id===id);if(!a)continue;const b=button('','people-reference',()=>{mapping[person.id]=id;selected=person.id;draw();});b.setAttribute('aria-label','Replace person '+(i+1)+' with @'+a.handle);b.setAttribute('aria-pressed',String(mapping[person.id]===id));const img=document.createElement('img');img.src=fileURL(a.thumbnail||a.file);img.alt='';const name=document.createElement('span');name.textContent='@'+a.handle;b.append(img,name);options.append(b);}
      const more=button('Choose asset','subtle',()=>{picking=person.id;safe(()=>DirectorSwap.openPicker());});options.append(more);card.append(options);return card;}));
  }
  async function poll(ident,current){
    try{if(current!==token||!dialog.open||!same())return;data=await api(`/projects/${context.pid}/people/${ident}`);if(current!==token)return;if(data.status==='succeeded')applyDefaults();draw();if(!['succeeded','failed','cancelled'].includes(data.status))timer=setTimeout(()=>poll(ident,current),2000);}
    catch(e){q('.people-status').textContent=e.message;q('.people-freshness').textContent='Connection lost. The analysis may still be running in the engine.';q('.people-retry').hidden=false;q('.people-cancel').hidden=false;}
  }
  async function begin(){
    stop();openedAt=Date.now()/1000;const current=token,s=snapshot();context={pid:project.id,source:s.swap_source_id};data={status:'preparing',stage:'Finding people…'};q('.people-content').hidden=true;draw();
    try{const pid=context.pid;await DirectorVideo.save();if(current!==token)return;const response=await api(`/projects/${pid}/shots/${DirectorVideo.currentShot.id}/people`,'POST',s);if(current!==token||!same()){if(response.id&&!['succeeded','failed','cancelled'].includes(response.status))await api(`/projects/${pid}/people/${response.id}/cancel`,'POST',{});return;}data=response;if(data.status==='succeeded')applyDefaults();draw();if(!['succeeded','failed','cancelled'].includes(data.status))timer=setTimeout(()=>poll(data.id,current),1500);}
    catch(e){data={status:'failed',error:e.message};draw();}
  }
  async function open(){if(!snapshot().swap_source_id)throw new Error('Choose a video first.');if(!dialog.open)dialog.showModal();shot=0;selected=null;await begin();}
  q('.people-retry').onclick=()=>safe(begin);q('.people-cancel').onclick=close;
  q('.people-apply').onclick=()=>{if(!same()||!Object.keys(mapping).length)return;DirectorSwap.setPeople(data.id,mapping,data.people);stop();dialog.close();const done=resolve;resolve=null;done?.(true);};
  window.DirectorSwapPeople={open,get picking(){return picking;},bind(asset){if(!picking||!data)return;mapping[picking]=asset;picking=null;draw();},async prepareGeneration(){
    const s=snapshot();if(!s.swap_source_id)return false;
    if(s.swap_analysis_id&&Object.keys(s.swap_people_map||{}).length){const r=await api(`/projects/${project.id}/shots/${DirectorVideo.currentShot.id}/people`,'POST',s);if(r.status==='succeeded'&&r.id===s.swap_analysis_id)return true;}
    const answer=new Promise(done=>resolve=done);await open();return answer;
  }};
})();
