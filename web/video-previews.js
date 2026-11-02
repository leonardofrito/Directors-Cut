/* Small, silent looping movement examples. No hover or GPU rendering in the UI. */
(()=>{
  let catalog={movement:{}},lastFetch=0,pending=false;
  const sliderWidgets=new Set();
  function sliderPreview(input,key){
    const panel=document.createElement('div');panel.className='camera-slider-preview';panel.hidden=true;
    const video=document.createElement('video');video.muted=true;video.defaultMuted=true;video.setAttribute('muted','');video.loop=true;video.playsInline=true;video.autoplay=true;video.preload='none';video.setAttribute('aria-label','Camera preset video preview');panel.append(video);
    input.closest('.camera-inline-slider').before(panel);
    const widget={input,update(){
      const value=parseFloat((input.getAttribute('aria-valuetext')||'').replace(/^f\//,''));
      const available=Object.entries(catalog[key]||{}).map(([label,url])=>({label,url,n:parseFloat(label.replace(/^f\//,''))})).filter(x=>Number.isFinite(x.n));
      if(!available.length||!Number.isFinite(value)||!input.isConnected)return;
      const sample=available.reduce((best,item)=>Math.abs(item.n-value)<Math.abs(best.n-value)?item:best);
      panel.hidden=false;video.setAttribute('aria-label',sample.label+' video preview');
      if(video.dataset.previewSrc!==sample.url){
        video.dataset.previewSrc=sample.url;
        if(visible.has(video)){video.src=sample.url;video.load();if(!document.hidden)video.play().catch(()=>{});}
      }
    }};
    sliderWidgets.add(widget);clips.add(video);observer.observe(video);
    video.addEventListener('loadeddata',()=>{if(visible.has(video)&&!document.hidden&&video.isConnected)video.play().catch(()=>{});});
    input.addEventListener('input',widget.update);input.addEventListener('keydown',widget.update);
    input.addEventListener('wheel',event=>{event.preventDefault();if(!event.deltaY)return;input.focus({preventScroll:true});
      const keyName=event.deltaY<0?'ArrowRight':'ArrowLeft';
      if(input.onkeydown)input.onkeydown({key:keyName,preventDefault(){}});
      else{input.value=String(Math.max(Number(input.min),Math.min(Number(input.max),Number(input.value)+(event.deltaY<0?1:-1))));input.dispatchEvent(new Event('input',{bubbles:true}));}
      widget.update();
    },{passive:false});
    widget.update();refresh();
  }
  const clips=new Set(),visible=new WeakSet();
  const observer=new IntersectionObserver(entries=>{
    for(const {target:video,isIntersecting} of entries){
      if(isIntersecting){visible.add(video);if(!video.src)video.src=video.dataset.previewSrc;if(!document.hidden)video.play().catch(()=>{});}
      else{visible.delete(video);video.pause();}
    }
  },{threshold:.08});
  function prune(){for(const widget of sliderWidgets)if(!widget.input.isConnected)sliderWidgets.delete(widget);for(const video of clips)if(!video.isConnected){observer.unobserve(video);video.pause();video.removeAttribute('src');video.load();clips.delete(video);}}
  function decorate(button,key,value){
    if(!['movement','framing','tempo','camera','sensor','lens','aperture','focal_length'].includes(key)||!value||value.startsWith('custom:'))return;
    button.dataset.motionPreset=value;button.dataset.previewCategory=key;
    const url=catalog[key]?.[value];
    if(!url||button.dataset.previewUrl===url)return;
    button.classList.add('video-movement-card');
    const video=document.createElement('video');video.muted=true;video.defaultMuted=true;video.loop=true;video.playsInline=true;video.autoplay=true;video.preload='none';video.setAttribute('aria-hidden','true');video.tabIndex=-1;video.dataset.previewSrc=url;
    if(catalog.poster)video.poster=catalog.poster;
    const label=document.createElement('span');label.className='video-movement-caption';label.textContent=value;
    button.replaceChildren(video,label);button.dataset.previewUrl=url;clips.add(video);observer.observe(video);
  }
  async function refresh(){
    if(pending||Date.now()-lastFetch<30000)return;pending=true;lastFetch=Date.now();
    try{
      const response=await fetch('/assets/video-presets/index.json',{cache:'no-cache'});if(!response.ok)return;
      const next=await response.json();if(!next||typeof next.movement!=='object')return;
      // This manifest is local application media, never arbitrary remote URLs.
      for(const key of ['movement','framing','tempo','camera','sensor','lens','aperture','focal_length'])next[key]=Object.fromEntries(Object.entries(next[key]||{}).filter(([,url])=>typeof url==='string'&&/^\/assets\/video-presets\/[a-z0-9-]+\.webm$/.test(url)));
      catalog=next;for(const widget of sliderWidgets)widget.update();
      document.querySelectorAll('button[data-motion-preset]').forEach(button=>decorate(button,button.dataset.previewCategory||'movement',button.dataset.motionPreset));
    }catch{}finally{pending=false;prune();}
  }
  document.addEventListener('visibilitychange',()=>{for(const video of clips){if(document.hidden)video.pause();else if(visible.has(video))video.play().catch(()=>{});}if(!document.hidden)refresh();});
  setInterval(()=>{if(!document.hidden&&!document.getElementById('video-workspace')?.hidden)refresh();prune();},30000);
  window.DirectorVideoPreviews={decorate(button,key,value){decorate(button,key,value);refresh();},sliderPreview,refresh};refresh();
})();
