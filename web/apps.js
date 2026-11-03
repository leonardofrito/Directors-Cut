(() => {
  let id='asset-creation',switching=false,previousProject=null,studioReady=false;
  document.addEventListener('director-ready',()=>{studioReady=true;});
  const menu=document.getElementById('app-switcher');
  const names={'asset-creation':'Asset Creation','directors-cut':'Director’s Cut','second-take':'Second Take'};
  async function select(next){
    if(switching||next===id)return;
    if(!studioReady){toast('Loading your projects…');return;}
    if(window.DirectorSwap?.busy){toast('Wait for the upload to finish.');return;}
    switching=true;
    try{
      if(DirectorVideo.active)await DirectorVideo.leave();else await saveNotes(false);
      if(next==='second-take'){
        previousProject=project?.system_workspace?previousProject:project?.id;
        project=await api('/second-take/session','POST',{});
      }else if(project?.system_workspace){
        project=null;shotId=null;selectedDraft=null;
        const list=await projectList(),restore=list.find(p=>p.id===previousProject)||list[0];
        if(restore)await openProject(restore.id);
      }
      id=next;document.body.dataset.studioApp=id;
      if(id==='directors-cut'){librarySource='';libraryAssets=[];document.getElementById('library-source').value='';libraryStamp='';}
      document.getElementById('app-name').textContent=names[id];document.title=names[id];
      menu.open=false;
      menu.querySelectorAll('[data-app]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.app===id)));
      if(id==='asset-creation')await switchCreationMode('asset');else await DirectorVideo.enter();
      window.render();
    }finally{switching=false;}
  }
  menu.querySelectorAll('[data-app]').forEach(b=>{b.setAttribute('aria-label',names[b.dataset.app]);b.onclick=()=>safe(()=>select(b.dataset.app));});
  document.addEventListener('click',event=>{if(!menu.contains(event.target))menu.open=false;});
  document.addEventListener('keydown',event=>{if(event.key==='Escape')menu.open=false;});
  document.body.dataset.studioApp=id;
  window.DirectorApps={get id(){return id;},select};
})();
