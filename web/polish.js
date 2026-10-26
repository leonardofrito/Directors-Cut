/* Interaction feedback uses CSS transforms/opacity; no animation framework or canvas. */
(() => {
  const tracked=new Set();
  const mediaObserver=new IntersectionObserver(entries=>{
    for(const {target,isIntersecting} of entries){
      if(isIntersecting&&!target.getAttribute('src')){target.src=target.dataset.lazyVideo;target.preload='metadata';target.load();}
      else if(!isIntersecting&&target.getAttribute('src')){target.pause();target.removeAttribute('src');target.preload='none';target.load();}
    }
  },{rootMargin:'60px'});
  function pruneVideos(){for(const video of tracked)if(!video.isConnected){mediaObserver.unobserve(video);video.pause();video.removeAttribute('src');video.load();tracked.delete(video);}}
  window.DirectorMotion={observeVideo(video){tracked.add(video);mediaObserver.observe(video);},pruneVideos};
  const icons={
    'previous-image':'left','next-image':'right','video-previous':'left','video-next':'right',
    'close-library':'close','close-models':'close','projects-close':'close','shot-player-close':'close',
    'shot-player-previous':'left','shot-player-next':'right',
  };
  for(const [id,name] of Object.entries(icons)){const el=$(id);if(el){el.innerHTML=DirectorIcons[name];el.classList.add('icon-button');}}
  for(const id of ['asset-new','video-new'])$(id).innerHTML=DirectorIcons.plus;
  for(const id of ['asset-rename','video-rename']){const el=$(id);if(el)el.innerHTML=DirectorIcons.pencil;}
  for(const id of ['asset-browse','video-browse']){const el=$(id);if(el){el.innerHTML=DirectorIcons.chevron;el.setAttribute('aria-controls','asset-library');}}
  for(const id of ['asset-delete','video-delete']){const el=$(id);if(el)el.innerHTML=DirectorIcons.trash;}
  const save=$('save-as-asset')?.querySelector('svg');if(save)save.outerHTML=DirectorIcons.save;
  for(const id of ['clear-character','video-reset-presets']){const reset=$(id);if(reset)reset.innerHTML=DirectorIcons.reset+'<span>Reset</span>';}
  const attach=$('attach-reference');if(attach)attach.innerHTML=DirectorIcons.image+'<span>Image reference</span>';
  for(const id of ['prompt','video-prompt']){
    const field=$(id),composer=field.closest('.prompt-composer');let timer;
    field.addEventListener('input',()=>{composer.classList.add('is-writing');clearTimeout(timer);timer=setTimeout(()=>composer.classList.remove('is-writing'),450);});
  }
  function enhance(root){
    if(!(root instanceof Element))return;
    const targets=selector=>[...(root.matches(selector)?[root]:[]),...root.querySelectorAll(selector)];
    for(const edit of targets('.asset-edit:not([data-icon])')){edit.dataset.icon='true';edit.innerHTML=DirectorIcons.pencil;}
    for(const action of targets('.asset-actions>button')){
      if(action.textContent.trim()==='Delete'){action.innerHTML=DirectorIcons.trash;action.title='Delete asset';action.setAttribute('aria-label','Delete asset');action.classList.add('icon-button');}
    }
    for(const image of targets('.preview>img')){image.classList.remove('media-arrival');requestAnimationFrame(()=>image.classList.add('media-arrival'));}
  }
  enhance(document.body);
  const observer=new MutationObserver(records=>{for(const record of records){if(record.type==='attributes')enhance(record.target);else for(const node of record.addedNodes)enhance(node);}pruneVideos();});
  observer.observe(document.body,{childList:true,subtree:true,attributes:true,attributeFilter:['src']});
})();
