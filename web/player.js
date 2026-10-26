/* A bounded native-video player with app controls; no playback timers or library. */
(() => {
  const clock=value=>{const seconds=Math.max(0,Math.floor(Number(value)||0));return Math.floor(seconds/60)+':'+String(seconds%60).padStart(2,'0');};
  function create(src,{autoplay=false,loop=true,onEnded=null}={}){
    const root=document.createElement('div');root.className='studio-player';
    const video=document.createElement('video');video.playsInline=true;video.preload='metadata';video.loop=loop;video.src=src;
    const toggle=button('','studio-player-toggle',()=>{if(video.paused)play(false);else video.pause();});
    const anchor=document.createElement('div');anchor.className='studio-player-play-anchor';anchor.append(toggle);
    let lastPlaybackIcon=null,lastSoundIcon=null,lastAudibleVolume=1,revealTimer=null;
    function clearReveal(){clearTimeout(revealTimer);root.classList.remove('near-play');}
    root.addEventListener('pointermove',event=>{
      if(video.paused||event.pointerType==='touch')return;
      const rect=root.getBoundingClientRect(),radius=toggle.offsetWidth/2+24;
      const near=Math.hypot(event.clientX-rect.left-rect.width/2,event.clientY-rect.top-rect.height/2)<=radius;
      clearTimeout(revealTimer);root.classList.toggle('near-play',near);
      if(near)revealTimer=setTimeout(()=>root.classList.remove('near-play'),1000);
    });
    root.addEventListener('pointerleave',clearReveal);
    video.addEventListener('play',clearReveal);video.addEventListener('pause',clearReveal);
    const controls=document.createElement('div');controls.className='studio-player-controls';
    const transport=button('','studio-player-transport',()=>toggle.click());
    const time=document.createElement('span');time.className='studio-player-time';
    const seek=document.createElement('input');seek.type='range';seek.min='0';seek.max='100';seek.step='.1';seek.value='0';seek.disabled=true;seek.setAttribute('aria-label','Seek video');
    const sound=button('','studio-player-sound',()=>{
      if(video.muted||video.volume===0){video.muted=false;if(video.volume===0)video.volume=lastAudibleVolume;}else video.muted=true;
      sync();
    });
    const volumeGroup=document.createElement('div');volumeGroup.className='studio-player-volume';
    const popup=document.createElement('div');popup.className='studio-player-volume-popup';
    const volumeCard=document.createElement('div');volumeCard.className='studio-player-volume-card';
    const volume=document.createElement('input');volume.type='range';volume.className='studio-player-volume-slider';volume.min='0';volume.max='100';volume.step='1';volume.value='100';volume.setAttribute('aria-label','Volume');volume.setAttribute('aria-orientation','vertical');
    const volumeValue=document.createElement('output');volumeValue.className='studio-player-volume-value';
    volume.oninput=()=>{const level=Number(volume.value)/100;if(level>0)lastAudibleVolume=level;video.volume=level;video.muted=level===0;sync();};
    volumeCard.append(volumeValue,volume);popup.append(volumeCard);volumeGroup.append(sound,popup);

    const fullscreen=button('','studio-player-fullscreen',async()=>{
      try{
        if(document.fullscreenElement===root)await document.exitFullscreen();
        else if(document.webkitFullscreenElement===root)await document.webkitExitFullscreen();
        else if(root.requestFullscreen)await root.requestFullscreen();
        else if(root.webkitRequestFullscreen)await root.webkitRequestFullscreen();
        else if(video.webkitEnterFullscreen)video.webkitEnterFullscreen();
      }catch{toast('Fullscreen could not be opened.');}
    });
    fullscreen.hidden=!(root.requestFullscreen&&document.fullscreenEnabled!==false||root.webkitRequestFullscreen&&document.webkitFullscreenEnabled!==false||video.webkitEnterFullscreen);
    function syncFullscreen(){
      const expanded=document.fullscreenElement===root||document.webkitFullscreenElement===root||Boolean(video.webkitDisplayingFullscreen);
      fullscreen.title=expanded?'Exit fullscreen':'Fullscreen';fullscreen.setAttribute('aria-label',fullscreen.title);fullscreen.setAttribute('aria-pressed',String(expanded));
      fullscreen.innerHTML='<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="'+(expanded?'M8 3v5H3M16 3v5h5M8 21v-5H3M16 21v-5h5':'M8 3H3v5M16 3h5v5M3 16v5h5M21 16v5h-5')+'"/></svg>';
    }
    for(const event of ['fullscreenchange','webkitfullscreenchange'])root.addEventListener(event,syncFullscreen);
    for(const event of ['webkitbeginfullscreen','webkitendfullscreen'])video.addEventListener(event,syncFullscreen);
    syncFullscreen();

    function sync(){
      root.classList.toggle('is-playing',!video.paused);
      if(lastPlaybackIcon!==video.paused){lastPlaybackIcon=video.paused;toggle.innerHTML=video.paused?DirectorIcons.play:DirectorIcons.pause;transport.innerHTML=toggle.innerHTML;}
      toggle.title=video.paused?'Play video':'Pause video';toggle.setAttribute('aria-label',toggle.title);toggle.tabIndex=video.paused?0:-1;
      transport.title=toggle.title;transport.setAttribute('aria-label',toggle.title);
      time.textContent=clock(video.currentTime)+' / '+clock(video.duration);
      const duration=Number.isFinite(video.duration)&&video.duration>0;
      seek.disabled=!duration;if(duration)seek.value=String(video.currentTime/video.duration*100);
      seek.style.setProperty('--played',seek.value+'%');
      const silent=video.muted||video.volume===0;
      if(lastSoundIcon!==silent){lastSoundIcon=silent;sound.innerHTML=silent?'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" aria-hidden="true"><path d="m11 5-6 4H2v6h3l6 4ZM16 9l6 6M22 9l-6 6"/></svg>':'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" aria-hidden="true"><path d="m11 5-6 4H2v6h3l6 4ZM15 8a6 6 0 0 1 0 8M18 4a11 11 0 0 1 0 16"/></svg>';}
      sound.title=silent?'Unmute':'Mute';sound.setAttribute('aria-label',sound.title);sound.setAttribute('aria-pressed',String(silent));
      const level=Math.round((video.muted?0:video.volume)*100);volume.value=String(level);volumeValue.textContent=level+'%';volume.style.setProperty('--volume',level+'%');
    }
    async function play(automatic){
      try{await video.play();}catch{
        if(automatic){video.muted=true;try{await video.play();}catch{ /* Browser leaves the large Play control available. */ }}
      }sync();
    }
    seek.oninput=()=>{if(Number.isFinite(video.duration)&&video.duration>0)video.currentTime=Number(seek.value)/100*video.duration;sync();};
    for(const event of ['play','pause','timeupdate','loadedmetadata','durationchange','volumechange','ended'])video.addEventListener(event,sync);
    if(onEnded)video.addEventListener('ended',onEnded);
    video.onclick=()=>toggle.click();
    controls.append(transport,time,seek,volumeGroup,fullscreen);root.append(video,anchor,controls);sync();
    if(autoplay)video.addEventListener('canplay',()=>{if(root.isConnected)play(true);},{once:true});
    return root;
  }
  window.DirectorPlayer={create};
})();
