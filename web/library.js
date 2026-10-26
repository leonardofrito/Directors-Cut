/* One place to browse project assets and video shots. */
(() => {
  let tab='assets',projects=[],shotStamp='',playback=[],playIndex=0;
  const iconButton=(name,label,action)=>{const b=button('','icon-button',action);b.innerHTML=DirectorIcons[name];b.title=label;b.setAttribute('aria-label',label);return b;};
  function syncCounts(){
    $('library-assets-total').textContent=project?.assets?.length||0;
    $('library-shots-total').textContent=project?.shots.filter(s=>s.mode==='video').length||0;
    $('library-count').textContent=String((project?.assets?.length||0)+(project?.shots.filter(s=>s.mode==='video').length||0));
    $('project-picker-name').textContent=project?.name||'Projects';
  }
  function setTab(value,draw=true){
    if(tab!==value)$('library-search').value='';
    tab=value;shotStamp='';libraryStamp='';
    $('asset-library').dataset.tab=tab;
    for(const name of ['assets','shots'])$('library-tab-'+name).setAttribute('aria-pressed',String(tab===name));
    $('library-new').textContent=tab==='shots'?'＋ New shot':'＋ New asset';
    $('library-play').hidden=tab!=='shots';$('import-asset').hidden=tab!=='assets';
    for(const id of ['library-source','library-kind'])$(id).closest('.library-filter').hidden=tab!=='assets';
    $('library-search').placeholder=tab==='shots'?'Search shots…':'Search assets…';
    if(draw){$('library-search').value='';renderLibrary(true);}
    syncCounts();
  }
  const videoShots=()=>project?.shots.filter(s=>s.mode==='video')||[];
  const latest=shot=>shot.drafts.find(d=>d.id===shot.approved?.draft_id&&d.status==='succeeded'&&d.file)||shot.drafts.filter(d=>d.status==='succeeded'&&d.file).at(-1);
  async function openShot(id){closeLibrary();await DirectorVideo.selectShot(id);}
  async function deleteShot(shot){
    if(!await confirmAssetDeletion({name:shot.title}))return;
    await DirectorVideo.deleteShot(shot.id);window.render();renderLibrary(true);toast('Shot deleted.');
  }
  function renderShots(force=false){
    if($('asset-library').hidden)return;
    const term=$('library-search').value.trim().toLowerCase(),shots=videoShots().filter(s=>(s.title+' '+s.prompt).toLowerCase().includes(term));
    const stamp=JSON.stringify([project?.id,term,shots.map(s=>[s.id,s.title,s.approved?.draft_id,s.drafts.map(d=>[d.id,d.status,d.file,d.audio_applied_at])])]);
    if(!force&&stamp===shotStamp)return;shotStamp=stamp;
    $('library-play').disabled=!videoShots().some(latest);
    $('library-items').replaceChildren(...shots.map(shot=>{
      const take=latest(shot),card=document.createElement('article');card.className='asset-card shot-card'+(take&&shot.approved?.draft_id===take.id?' approved-shot':'');
      const cover=button('','asset-cover',()=>safe(()=>openShot(shot.id)));cover.title='Open shot';cover.setAttribute('aria-label','Open '+shot.title);
      if(take){
        const video=document.createElement('video');video.muted=true;video.playsInline=true;video.preload='none';video.dataset.lazyVideo=fileURL(take.file)+'#t=0.1';cover.append(video);window.DirectorMotion?.observeVideo(video);
        const play=iconButton('play','Play '+shot.title,()=>playShots(shot.id,false));play.classList.add('shot-card-play');card.append(play);
      }else{const empty=document.createElement('span');empty.className='asset-cover-empty';empty.textContent=shot.drafts.some(active)?'Generating…':'No takes yet';cover.append(empty);}
      const count=document.createElement('span');count.className='asset-cover-takes';count.textContent=shot.drafts.filter(d=>d.status==='succeeded').length+' takes'+(take&&shot.approved?.draft_id===take.id?' · Approved':'');cover.append(count);
      const identity=document.createElement('div');identity.className='asset-identity';
      const title=document.createElement('strong');title.className='asset-handle';title.textContent=shot.title;
      const rename=iconButton('pencil','Rename '+shot.title,()=>safe(async()=>{
        const name=await DirectorNavigator.rename(shot.title);if(!name||name===shot.title)return;
        await DirectorVideo.save();const current=project.shots.find(s=>s.id===shot.id);await api(`/projects/${project.id}/shots/${shot.id}`,'PUT',{...current,title:name});
        project=await api(`/projects/${project.id}`);render();renderLibrary(true);
      }));title.ondblclick=rename.onclick;identity.append(title,rename);
      const actions=document.createElement('div');actions.className='asset-actions';
      const open=button('Open shot','subtle',()=>safe(()=>openShot(shot.id)));
      actions.append(open);
      const approved=shot.drafts.find(d=>d.id===shot.approved?.draft_id&&d.status==='succeeded'&&d.file);
      if(approved){
        const download=document.createElement('a');download.className='button library-approved-download';
        download.href=fileURL(approved.file,project.id)+'?v='+encodeURIComponent(approved.audio_applied_at||approved.id);
        download.download=shot.title.replace(/[<>:"/\\|?*\x00-\x1f]/g,'_')+'.mp4';
        download.title='Download approved take';download.setAttribute('aria-label','Download approved take: '+shot.title);
        download.innerHTML=DirectorIcons.download+'<span>Download</span>';actions.append(download);
      }
      actions.append(iconButton('trash','Delete '+shot.title,()=>safe(()=>deleteShot(shot))));card.append(cover,identity,actions);return card;
    }));
    if(!shots.length){const empty=document.createElement('p');empty.className='library-empty';empty.textContent=term?'No matching shots.':'No shots yet.';$('library-items').append(empty);}
    window.DirectorMotion?.pruneVideos();
  }
  function playShots(id=null,sequence=true){
    playback=videoShots().filter(latest).map(s=>({id:s.id,title:s.title,file:latest(s).file,revision:latest(s).audio_applied_at||''}));
    if(!sequence)playback=playback.filter(s=>s.id===id);
    if(!playback.length)return;playIndex=Math.max(0,playback.findIndex(s=>s.id===id));
    $('video-preview').querySelector('video')?.pause();
    if(!$('shot-player-dialog').open)$('shot-player-dialog').showModal();showPlayback();
  }
  function showPlayback(){
    const shot=playback[playIndex];if(!shot)return;
    $('shot-player-stage').querySelector('video')?.pause();
    $('shot-player-title').textContent=shot.title;$('shot-player-position').textContent=`${playIndex+1} / ${playback.length}`;
    $('shot-player-previous').disabled=playIndex===0;$('shot-player-next').disabled=playIndex===playback.length-1;
    const player=DirectorPlayer.create(fileURL(shot.file)+(shot.revision?'?v='+encodeURIComponent(shot.revision):''),{autoplay:true,loop:playIndex===playback.length-1,onEnded:()=>{if(playIndex<playback.length-1){playIndex++;showPlayback();}}});$('shot-player-stage').replaceChildren(player);
  }
  $('shot-player-close').onclick=()=>$('shot-player-dialog').close();
  $('shot-player-dialog').addEventListener('close',()=>{const video=$('shot-player-stage').querySelector('video');if(video){video.pause();video.removeAttribute('src');video.load();}$('shot-player-stage').replaceChildren();playback=[];});
  for(const [name,delta] of [['previous',-1],['next',1]])$('shot-player-'+name).onclick=()=>{playIndex=Math.max(0,Math.min(playback.length-1,playIndex+delta));showPlayback();};
  $('shot-player-edit').onclick=()=>{const id=playback[playIndex]?.id;$('shot-player-dialog').close();if(id)safe(()=>openShot(id));};
  $('library-play').onclick=()=>playShots();
  for(const name of ['assets','shots'])$('library-tab-'+name).onclick=()=>setTab(name);
  $('library-new').onclick=()=>safe(async()=>{
    closeLibrary();
    if(tab==='shots'){const before=videoShots().length;await DirectorVideo.enter();if(before)await DirectorVideo.newShot();}
    else{await switchCreationMode('asset');await $('add-shot').onclick();}
  });
  let coverUploading=null;
  function drawProjects(){
    const term=$('projects-search').value.trim().toLowerCase();
    $('projects-grid').replaceChildren(...projects.filter(p=>p.name.toLowerCase().includes(term)).map(p=>{
      const card=document.createElement('article');card.className='project-card'+(p.id===project?.id?' selected':'');
      const open=button('','project-open',()=>safe(async()=>{$('projects-dialog').close();if(project?.id!==p.id)await openProject(p.id);}));
      const mark=button('','project-card-mark',()=>{
        if(coverUploading)return;
        const input=$('project-cover-file');input.dataset.project=p.id;input.value='';input.click();
      });mark.title=p.cover_image?'Change project cover':'Add project cover';mark.setAttribute('aria-label',mark.title+': '+p.name);mark.disabled=Boolean(coverUploading);
      if(p.cover_image){const image=document.createElement('img');image.src=fileURL(p.cover_image,p.id)+'?v='+encodeURIComponent(p.cover_revision||'');image.alt='';image.loading='lazy';image.draggable=false;mark.append(image);}
      else mark.innerHTML=DirectorIcons.image;
      const text=document.createElement('span'),name=document.createElement('strong'),count=document.createElement('small');name.textContent=p.name;count.textContent=`${p.asset_count||0} assets · ${p.shot_count||0} shots`;text.append(name,count);open.append(text);
      const remove=iconButton('trash','Delete '+p.name,()=>safe(async()=>{remove.disabled=true;try{await deleteProject(p);}finally{remove.disabled=false;}}));remove.classList.add('project-remove');card.append(mark,open,remove);return card;
    }));
    if(!$('projects-grid').children.length){const empty=document.createElement('p');empty.className='library-empty';empty.textContent='No projects found.';$('projects-grid').append(empty);}
  }
  async function deleteProject(p){
    const dialog=$('delete-project-dialog');$('delete-project-message').textContent=`Delete “${p.name}”?`;dialog.returnValue='cancel';dialog.showModal();
    const confirmed=await new Promise(resolve=>dialog.addEventListener('close',()=>resolve(dialog.returnValue==='delete'),{once:true}));if(!confirmed)return;
    const current=project?.id===p.id;
    if(current){await DirectorVideo.save();await saveNotes(false);}
    await api(`/projects/${p.id}`,'DELETE',{confirm_name:p.name});
    if(current){
      if(DirectorVideo.active)await DirectorVideo.leave();
      project=null;shotId=null;selectedDraft=null;referenceIds=[];uploadedReferenceIds=[];imageEdit=null;libraryStamp='';
      $('title').value='';$('prompt').value='';$('takes').replaceChildren();$('preview').replaceChildren();$('download').hidden=true;$('prompt-inspector').hidden=true;
      $('image-position').textContent='No images yet';$('take-count').textContent='0';$('generation-status').textContent='';$('image-info').textContent='';
      const remaining=await projectList();
      if(remaining.length)await openProject(remaining[0].id);
      else{render();$('projects-dialog').close();$('new-project').click();}
    }else await projectList();
    drawProjects();toast('Project deleted.');
  }
  $('project-cover-file').onchange=()=>safe(async()=>{
    const input=$('project-cover-file'),file=input.files[0],pid=input.dataset.project;input.value='';
    if(!file||!pid||coverUploading)return;
    if(file.size>32*1024*1024){toast('Choose a cover image up to 32 MB.');return;}
    coverUploading=pid;drawProjects();
    try{
      const data=new FormData();data.append('image',file);
      const response=await fetch(`/api/projects/${pid}/cover`,{method:'POST',body:data}),result=await response.json();
      if(!response.ok)throw new Error(result.error||'Cover upload failed.');
      projects=projects.map(p=>p.id===pid?{...p,cover_image:result.cover_image,cover_revision:result.cover_revision}:p);
      if(project?.id===pid)Object.assign(project,{cover_image:result.cover_image,cover_revision:result.cover_revision});
      toast('Project cover updated.');
    }finally{coverUploading=null;drawProjects();}
  });
  $('project-picker').onclick=()=>safe(async()=>{await projectList();$('projects-search').value='';drawProjects();$('projects-dialog').showModal();$('projects-search').focus();});
  $('projects-close').onclick=()=>$('projects-dialog').close();$('projects-search').oninput=drawProjects;
  $('projects-new').onclick=()=>{$('projects-dialog').close();$('new-project').click();};
  window.DirectorLibrary={get tab(){return tab;},setTab,syncCounts,renderShots,setProjects(value){projects=value;if($('projects-dialog').open)drawProjects();}};
})();
