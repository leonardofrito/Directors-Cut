/* A small nondestructive four-track editor. Media playback is native HTML5. */
(()=>{
  const FPS=24,GUTTER=64,tracks=['V2','V1','A1','A2'];
  let pid=null,edit=null,sources=[],selected=null,head=0,playing=false,linked=true,pps=44,drag=null,frame=0,started=0,startHead=0;
  let undo=[],redo=[],dirty=false,saving=null,saveTimer=null,exporting=false,sourceDrag=null;
  const id=()=>globalThis.crypto?.randomUUID?.()||'clip-'+Date.now().toString(36)+'-'+Math.random().toString(36).slice(2);
  const clone=value=>structuredClone(value),key=c=>c.shot_id+':'+c.take_id,source=c=>sources.find(s=>s.key===key(c));
  const dialog=document.createElement('dialog');dialog.id='timeline-editor';dialog.setAttribute('aria-label','Timeline editor');
  dialog.innerHTML=`<div class="timeline-heading"><h2>Timeline</h2><span class="timeline-project"></span><span class="timeline-save-state" role="status"></span><button type="button" class="subtle timeline-save">Save</button><button type="button" class="icon-button timeline-close" aria-label="Close timeline">${DirectorIcons.close}</button></div>
    <div class="timeline-upper"><div class="timeline-bin" aria-label="Source shots"></div><div class="timeline-monitor"><div class="timeline-stage" aria-label="Timeline preview"></div><div class="timeline-transport"><button type="button" class="icon-button timeline-play" aria-label="Play timeline">${DirectorIcons.play}</button><output class="timeline-clock">00:00:00:00</output><input class="timeline-seek" type="range" min="0" max="1" step="1" value="0" aria-label="Timeline position"><button type="button" class="subtle timeline-export-mp4">Export MP4</button><button type="button" class="subtle timeline-export-resolve">DaVinci</button></div></div></div>
    <div class="timeline-toolbar"><button type="button" class="subtle timeline-undo" aria-label="Undo edit">Undo</button><button type="button" class="subtle timeline-redo" aria-label="Redo edit">Redo</button><button type="button" class="subtle timeline-link" aria-pressed="true">Link A/V</button><button type="button" class="subtle timeline-split">Split</button><button type="button" class="icon-button timeline-remove" aria-label="Remove selected clip">${DirectorIcons.trash}</button><span class="timeline-inspector"></span><label class="timeline-zoom">Zoom<input type="range" min="20" max="140" value="44" aria-label="Timeline zoom"></label></div>
    <div class="timeline-scroll"><div class="timeline-content"><div class="timeline-ruler" aria-label="Seek in timeline"></div>${tracks.map(t=>`<div class="timeline-lane" data-track="${t}" aria-label="${t} track"><strong class="timeline-track-label">${t}</strong></div>`).join('')}<div class="timeline-playhead"><i></i></div></div></div><div class="timeline-message" role="status"></div>`;
  document.body.append(dialog);
  const $=selector=>dialog.querySelector(selector),nodes=new Map(),lanes=Object.fromEntries(tracks.map(t=>[t,$(`.timeline-lane[data-track="${t}"]`)]));
  const slots=Object.fromEntries(tracks.map(track=>{
    const media=document.createElement(track[0]==='V'?'video':'audio');media.preload='metadata';media.playsInline=true;media.muted=track[0]==='V';media.hidden=true;
    if(track[0]==='V'){media.className='timeline-preview-video';media.style.zIndex=track==='V2'?'2':'1';$('.timeline-stage').append(media);}else dialog.append(media);
    media.addEventListener('loadedmetadata',()=>{if(dialog.open)synchronize(true);});return [track,{media,clip:null}];
  }));
  const duration=()=>Math.max(0,...(edit?.clips||[]).map(c=>c.start+c.duration));
  function clock(value){const f=Math.max(0,Math.floor(value)),seconds=Math.floor(f/FPS);return `${String(Math.floor(seconds/3600)).padStart(2,'0')}:${String(Math.floor(seconds/60)%60).padStart(2,'0')}:${String(seconds%60).padStart(2,'0')}:${String(f%FPS).padStart(2,'0')}`;}
  function pause(){playing=false;cancelAnimationFrame(frame);for(const slot of Object.values(slots))slot.media.pause();$('.timeline-play').innerHTML=DirectorIcons.play;$('.timeline-play').setAttribute('aria-label','Play timeline');}
  function synchronize(force=false){
    for(const track of tracks){
      const slot=slots[track],media=slot.media,clip=edit?.clips.find(c=>c.track===track&&head>=c.start&&head<c.start+c.duration);
      if(!clip){media.pause();media.hidden=true;slot.clip=null;continue;}
      const s=source(clip);if(!s)continue;
      const time=(clip.source_in+head-clip.start)/FPS;
      if(slot.clip!==clip.id){media.pause();media.src=fileURL(s.file,pid);slot.clip=clip.id;media.load();force=true;}
      media.hidden=track[0]!=='V';if(track[0]==='A')media.volume=clip.gain;
      if(force||Math.abs(media.currentTime-time)>.14){try{media.currentTime=time;}catch{}}
      if(playing&&media.paused)media.play().catch(()=>{if(track[0]==='A')$('.timeline-message').textContent='Press Play to enable audio playback.';});else if(!playing)media.pause();
    }
    $('.timeline-playhead').style.left=(GUTTER+head/FPS*pps)+'px';$('.timeline-clock').textContent=clock(head);$('.timeline-seek').max=String(Math.max(1,duration()));$('.timeline-seek').value=String(Math.round(head));
  }
  function seek(value){head=Math.max(0,Math.min(duration(),value));startHead=head;started=performance.now();synchronize(true);}
  function play(){
    if(!duration())return;if(head>=duration())head=0;playing=true;startHead=head;started=performance.now();$('.timeline-play').innerHTML=DirectorIcons.pause;$('.timeline-play').setAttribute('aria-label','Pause timeline');synchronize(true);
    const tick=now=>{if(!playing)return;head=Math.min(duration(),startHead+(now-started)/1000*FPS);synchronize();if(head>=duration()){pause();return;}frame=requestAnimationFrame(tick);};frame=requestAnimationFrame(tick);
  }
  function valid(){
    for(const c of edit.clips){const s=source(c);if(!s||c.start<0||c.source_in<0||c.duration<1||c.source_in+c.duration>Math.round(s.duration*FPS)||c.start+c.duration>FPS*7200)return false;}
    for(const track of tracks){let end=0;for(const c of edit.clips.filter(c=>c.track===track).sort((a,b)=>a.start-b.start)){if(c.start<end)return false;end=c.start+c.duration;}}
    return true;
  }
  function remember(before){undo.push(before);if(undo.length>30)undo.shift();redo=[];}
  function commit(before){
    if(!valid()){edit=before;$('.timeline-message').textContent='Use another track for overlaps, and keep trims inside the source clip.';render();return;}
    if(JSON.stringify(before.clips)===JSON.stringify(edit.clips)){render();return;}
    remember(before);dirty=true;$('.timeline-message').textContent='';render();clearTimeout(saveTimer);saveTimer=setTimeout(()=>safe(save),450);
  }
  async function save(){
    clearTimeout(saveTimer);if(saving)await saving;if(!dirty)return;
    const snapshot=clone(edit);$('.timeline-save-state').textContent='Saving…';
    saving=(async()=>{try{const stored=await api(`/projects/${pid}/timeline`,'PUT',snapshot);edit.revision=stored.revision;if(project?.id===pid)project.editor_timeline=clone(stored);if(JSON.stringify(edit.clips)===JSON.stringify(snapshot.clips))dirty=false;$('.timeline-save-state').textContent=dirty?'Unsaved':'Saved';}catch(error){$('.timeline-save-state').textContent='Not saved';throw error;}})();
    try{await saving;}finally{saving=null;}
    if(dirty)await save();
  }
  function selectedClips(){const clip=edit.clips.find(c=>c.id===selected);return clip?(linked&&clip.link?edit.clips.filter(c=>c.link===clip.link):[clip]):[];}
  function setSelected(identifier){selected=identifier;const c=edit.clips.find(c=>c.id===identifier);if(c&&(head<c.start||head>=c.start+c.duration))seek(c.start);paint();inspector();}
  function inspector(){
    const root=$('.timeline-inspector'),c=edit?.clips.find(c=>c.id===selected);root.replaceChildren();$('.timeline-split').disabled=!c;$('.timeline-remove').disabled=!c;
    if(!c)return;
    for(const [field,label] of [['start','Start'],['source_in','In'],['duration','Length']]){
      const wrap=document.createElement('label');wrap.textContent=label;const input=document.createElement('input');input.type='number';input.min=field==='duration'?String(1/FPS):'0';input.step=String(1/FPS);input.value=(c[field]/FPS).toFixed(3);input.setAttribute('aria-label',label+' seconds');
      input.onchange=()=>{const before=clone(edit),next=Math.round(Number(input.value)*FPS);if(Number.isFinite(next)){const delta=next-c[field];for(const item of selectedClips())item[field]+=delta;commit(before);}else render();};wrap.append(input);root.append(wrap);
    }
    const type=document.createElement('select');type.dataset.inlinePresets='true';type.setAttribute('aria-label','Clip track');for(const track of tracks.filter(t=>t[0]===c.track[0]))type.append(new Option(track,track));type.value=c.track;
    type.onchange=()=>{const before=clone(edit);for(const item of selectedClips())item.track=item.track[0]+type.value[1];commit(before);};root.append(type);
  }
  function paint(){
    const width=GUTTER+Math.max(12,duration()/FPS+4)*pps;$('.timeline-content').style.width=width+'px';
    for(const [identifier,node] of nodes)if(!edit.clips.some(c=>c.id===identifier)){node.remove();nodes.delete(identifier);}
    for(const clip of edit.clips){
      let node=nodes.get(clip.id);
      if(!node){
        node=document.createElement('div');node.className='timeline-clip';node.dataset.clip=clip.id;node.tabIndex=0;node.setAttribute('role','button');
        const left=document.createElement('span');left.className='timeline-trim timeline-trim-left';left.dataset.edge='left';left.setAttribute('aria-hidden','true');
        const label=document.createElement('span');label.className='timeline-clip-label';const right=left.cloneNode();right.className='timeline-trim timeline-trim-right';right.dataset.edge='right';
        node.append(left,label,right);node.onpointerdown=event=>beginDrag(event,clip.id);node.onkeydown=event=>{if(event.key==='Enter'){event.preventDefault();setSelected(clip.id);}};nodes.set(clip.id,node);
      }
      if(node.parentElement!==lanes[clip.track])lanes[clip.track].append(node);
      node.style.left=(GUTTER+clip.start/FPS*pps)+'px';node.style.width=Math.max(4,clip.duration/FPS*pps)+'px';node.classList.toggle('timeline-audio',clip.track[0]==='A');node.classList.toggle('selected',clip.id===selected);node.setAttribute('aria-pressed',String(clip.id===selected));
      const label=(source(clip)?.title||'Shot')+(clip.track[0]==='A'?' · audio':'');node.querySelector('.timeline-clip-label').textContent=label;node.title=`${label}\n${clock(clip.start)} → ${clock(clip.start+clip.duration)}\nSource in ${clock(clip.source_in)}`;
    }
    synchronize();
  }
  function render(){
    paint();inspector();$('.timeline-undo').disabled=!undo.length;$('.timeline-redo').disabled=!redo.length;
    const ruler=$('.timeline-ruler');ruler.replaceChildren();const seconds=Math.max(12,Math.ceil(duration()/FPS)+4),step=Math.max(pps<30?2:1,Math.ceil(seconds/500));
    for(let s=0;s<=seconds;s+=step){const tick=document.createElement('span');tick.style.left=(GUTTER+s*pps)+'px';tick.textContent=s+'s';ruler.append(tick);}
    $('.timeline-save-state').textContent=dirty?'Unsaved':edit.revision?'Saved':'Ready';
  }
  function snap(value,group){
    const points=[0,Math.round(head),...edit.clips.filter(c=>!group.includes(c.id)).flatMap(c=>[c.start,c.start+c.duration])];let best=value,dist=6/pps*FPS;
    for(const point of points)if(Math.abs(point-value)<dist){best=point;dist=Math.abs(point-value);}return Math.round(best);
  }
  function beginDrag(event,identifier){
    if(event.button!==0)return;event.preventDefault();pause();setSelected(identifier);
    const before=clone(edit),group=selectedClips().map(c=>c.id),target=edit.clips.find(c=>c.id===identifier),edge=event.target.dataset.edge||'move';drag={before,group,target:identifier,edge,x:event.clientX};
    const move=ev=>{
      if(!drag)return;const base=before.clips.find(c=>c.id===identifier),original=before.clips.filter(c=>group.includes(c.id));let delta=Math.round((ev.clientX-drag.x)/pps*FPS);
      if(edge==='move'){
        delta=snap(base.start+delta,group)-base.start;delta=Math.max(delta,-Math.min(...original.map(c=>c.start)));
        const lane=tracks.find(t=>{const r=lanes[t].getBoundingClientRect();return ev.clientY>=r.top&&ev.clientY<=r.bottom;});
        for(const c of edit.clips.filter(c=>group.includes(c.id))){const b=original.find(x=>x.id===c.id);c.start=b.start+delta;if(lane&&lane[0]===base.track[0])c.track=b.track[0]+lane[1];}
      }else if(edge==='left'){
        delta=snap(base.start+delta,group)-base.start;delta=Math.max(delta,-Math.min(...original.map(c=>Math.min(c.start,c.source_in))));delta=Math.min(delta,Math.min(...original.map(c=>c.duration-1)));
        for(const c of edit.clips.filter(c=>group.includes(c.id))){const b=original.find(x=>x.id===c.id);c.start=b.start+delta;c.source_in=b.source_in+delta;c.duration=b.duration-delta;}
      }else{
        delta=snap(base.start+base.duration+delta,group)-base.start-base.duration;delta=Math.max(delta,-Math.min(...original.map(c=>c.duration-1)));delta=Math.min(delta,Math.min(...original.map(c=>Math.round(source(c).duration*FPS)-c.source_in-c.duration)));
        for(const c of edit.clips.filter(c=>group.includes(c.id))){const b=original.find(x=>x.id===c.id);c.duration=b.duration+delta;}
      }
      const scroll=$('.timeline-scroll'),r=scroll.getBoundingClientRect();if(ev.clientX>r.right-24)scroll.scrollLeft+=16;else if(ev.clientX<r.left+GUTTER+24)scroll.scrollLeft-=16;paint();
    };
    const end=()=>{window.removeEventListener('pointermove',move);window.removeEventListener('pointerup',end);window.removeEventListener('pointercancel',cancel);drag=null;commit(before);};
    const cancel=()=>{edit=before;end();};window.addEventListener('pointermove',move);window.addEventListener('pointerup',end,{once:true});window.addEventListener('pointercancel',cancel,{once:true});
  }
  function add(s,track='V1',at=duration()){
    pause();const before=clone(edit),link=id(),length=Math.max(1,Math.round(s.duration*FPS));
    const insert=t=>{const c={id:id(),shot_id:s.shot_id,take_id:s.take_id,track:t,start:at,source_in:0,duration:length,gain:1,link};edit.clips.push(c);selected=c.id;};
    if(track[0]==='A'){if(s.audio)insert(track);else toast('This take has no audio.');}else{insert(track);if(linked&&s.audio)insert('A'+track[1]);}commit(before);
  }
  function fillBin(){
    $('.timeline-bin').replaceChildren(...sources.filter(s=>s.preferred).map(s=>{
      const b=button('','timeline-source',()=>add(s));b.draggable=true;b.title='Add to end, or drag onto a track';
      const name=document.createElement('strong');name.textContent=s.title;const detail=document.createElement('span');detail.textContent=s.duration.toFixed(2)+'s · +';b.append(name,detail);
      b.ondragstart=e=>{sourceDrag=s;e.dataTransfer.setData('application/x-directors-cut-source',s.key);e.dataTransfer.effectAllowed='copy';};b.ondragend=()=>sourceDrag=null;return b;
    }));
  }
  for(const track of tracks){lanes[track].ondragover=e=>{if(sourceDrag){e.preventDefault();e.dataTransfer.dropEffect='copy';}};lanes[track].ondrop=e=>{if(!sourceDrag)return;e.preventDefault();const rect=$('.timeline-content').getBoundingClientRect(),at=Math.max(0,snap((e.clientX-rect.left-GUTTER)/pps*FPS,[]));add(sourceDrag,track,at);sourceDrag=null;};}
  $('.timeline-ruler').onpointerdown=event=>{
    pause();const update=e=>{const rect=$('.timeline-content').getBoundingClientRect();seek(Math.round((e.clientX-rect.left-GUTTER)/pps*FPS));};update(event);
    const end=()=>{window.removeEventListener('pointermove',update);window.removeEventListener('pointerup',end);};window.addEventListener('pointermove',update);window.addEventListener('pointerup',end,{once:true});
  };
  $('.timeline-play').onclick=()=>playing?pause():play();$('.timeline-seek').oninput=()=>{pause();seek(Number($('.timeline-seek').value));};
  $('.timeline-link').onclick=()=>{linked=!linked;$('.timeline-link').setAttribute('aria-pressed',String(linked));};
  $('.timeline-remove').onclick=()=>{const before=clone(edit),remove=new Set(selectedClips().map(c=>c.id));edit.clips=edit.clips.filter(c=>!remove.has(c.id));selected=null;pause();commit(before);};
  $('.timeline-split').onclick=()=>{pause();const before=clone(edit),rightLink=id(),cut=Math.round(head);for(const c of selectedClips()){if(cut<=c.start||cut>=c.start+c.duration)continue;const offset=cut-c.start;edit.clips.push({...c,id:id(),link:linked?rightLink:'',start:cut,source_in:c.source_in+offset,duration:c.duration-offset});c.duration=offset;}commit(before);};
  function history(from,to){if(!from.length)return;pause();to.push(clone(edit));const restored=from.pop();restored.revision=edit.revision;edit=restored;dirty=true;render();clearTimeout(saveTimer);saveTimer=setTimeout(()=>safe(save),450);}
  $('.timeline-undo').onclick=()=>history(undo,redo);$('.timeline-redo').onclick=()=>history(redo,undo);$('.timeline-zoom input').oninput=e=>{pps=Number(e.target.value);render();};$('.timeline-save').onclick=()=>safe(save);
  async function close(){pause();await save();dialog.close();}
  $('.timeline-close').onclick=()=>safe(close);dialog.addEventListener('cancel',e=>{e.preventDefault();safe(close);});dialog.addEventListener('close',()=>{pause();for(const s of Object.values(slots)){s.media.removeAttribute('src');s.media.load();s.clip=null;}});
  dialog.addEventListener('click',e=>{if(e.target!==dialog)return;const r=dialog.getBoundingClientRect();if(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom)safe(close);});
  dialog.addEventListener('keydown',e=>{
    if(e.target.matches('input,textarea,select'))return;
    if(e.code==='Space'){e.preventDefault();playing?pause():play();}
    if(e.key==='Delete'||e.key==='Backspace'){e.preventDefault();$('.timeline-remove').click();}
    if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==='z'){e.preventDefault();history(e.shiftKey?redo:undo,e.shiftKey?undo:redo);}
  });
  async function exportTimeline(format){
    if(exporting)return;await save();exporting=true;const projectId=pid,message=$('.timeline-message');
    try{
      let job=await api(`/projects/${projectId}/sequence/exports`,'POST',{format});
      while(job.status==='queued'||job.status==='running'){
        message.textContent=`Exporting timeline… ${job.completed} / ${job.total}`;await new Promise(resolve=>setTimeout(resolve,1200));job=await api(`/projects/${projectId}/sequence/exports/${job.id}`);
      }
      if(job.status!=='succeeded')throw new Error(job.error||'Export cancelled.');
      const link=document.createElement('a');link.href=fileURL(job.download,projectId);link.download=job.name;link.textContent='Download '+(format==='mp4'?'MP4':'DaVinci timeline');link.className='button';message.replaceChildren(link);link.click();
    }finally{exporting=false;}
  }
  $('.timeline-export-mp4').onclick=()=>safe(()=>exportTimeline('mp4'));$('.timeline-export-resolve').onclick=()=>safe(()=>exportTimeline('resolve'));
  async function open({play:autoplay=false}={}){
    if(dialog.open)return;if(!project)return;await DirectorVideo.save();if(!DirectorVideo.active)await saveNotes(false);
    document.querySelector('#video-preview video')?.pause();pid=project.id;const result=await api(`/projects/${pid}/timeline`);sources=result.sources;edit=result.timeline;selected=null;head=0;undo=[];redo=[];dirty=false;nodes.clear();for(const lane of Object.values(lanes))lane.querySelectorAll('.timeline-clip').forEach(n=>n.remove());
    $('.timeline-project').textContent=project.name;$('.timeline-message').textContent='';if(document.getElementById('asset-library').open)closeLibrary();dialog.showModal();fillBin();render();if(autoplay)play();
  }
  window.DirectorTimeline={open,save};
  document.addEventListener('visibilitychange',()=>{if(document.hidden&&playing)pause();});
})();
