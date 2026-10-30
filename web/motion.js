/* Small, event-driven motion. Only visible generation surfaces keep looping. */
(() => {
  const motion=window.DirectorMotion,reduce=matchMedia('(prefers-reduced-motion: reduce)');
  // Animate the enclosing box itself, rather than only fading in its contents.
  const expansions=new WeakMap(),pendingExpansions=new WeakMap();
  document.addEventListener('click',event=>{
    const heading=event.target.closest('summary.preset-heading');
    const tab=event.target.closest('.video-camera-tab');
    const box=heading?.parentElement||tab?.closest('.video-camera-group');
    if(!box||reduce.matches||!box.animate)return;
    const from=box.getBoundingClientRect().height;
    expansions.get(box)?.cancel();
    cancelAnimationFrame(pendingExpansions.get(box));
    pendingExpansions.set(box,requestAnimationFrame(()=>{
      pendingExpansions.delete(box);
      if(!box.isConnected)return;
      const to=box.getBoundingClientRect().height;
      if(Math.abs(to-from)<2)return;
      const animation=box.animate([{height:from+'px'},{height:to+'px'}],{
        duration:340,easing:'cubic-bezier(.22,.75,.25,1)'
      });
      expansions.set(box,animation);
      animation.onfinish=()=>{if(expansions.get(box)===animation)expansions.delete(box);};
    }));
  },true);
  const active=d=>d&&['queued','submitting','pending','running','downloading'].includes(d.status);
  function amount(d){
    // Encoder/model-loading progress is per-node, not image-generation progress.
    if(!d.sampling)return null;
    if(d.sampling&&Number(d.sampling_steps)>0)return Math.max(0,Math.min(1,Number(d.sampling_step||0)/Number(d.sampling_steps)));
    return Number(d.progress)>0?Math.max(0,Math.min(1,Number(d.progress))):null;
  }
  function reflectProgress(root,d){
    const task=String(d.id||'')+':'+String(d.job_id||'');
    if(root.dataset.lightTask!==task){root.dataset.lightTask=task;root.style.setProperty('--task-progress','0');}
    const value=amount(d);
    // Keep the last sampling extent while decoding/saving; never use another node's 0–100.
    if(value!==null)root.style.setProperty('--task-progress',String(value));
  }
  function label(d){return d.status==='queued'?'Queued':d.status==='submitting'?'Preparing':d.status==='downloading'?(d.stage==='Applying final audio'?d.stage:'Saving'):d.sampling?'Sampling':d.stage||'Generating';}
  const counters=new WeakMap();
  function count(el,target){
    const state=counters.get(el);if(state?.target===target)return;
    if(state?.frame)cancelAnimationFrame(state.frame);
    const from=state?.value??(parseInt(el.textContent)||0),next={target,value:from,frame:0};counters.set(el,next);
    if(reduce.matches||target<from){el.textContent=target+'%';next.value=target;return;}
    const start=performance.now();
    const tick=now=>{const t=Math.min(1,(now-start)/240);next.value=Math.round(from+(target-from)*(1-(1-t)**3));el.textContent=next.value+'%';if(t<1)next.frame=requestAnimationFrame(tick);};next.frame=requestAnimationFrame(tick);
  }
  motion.progress=(root,d,compact=false)=>{
    if(!root||!d)return;
    let meter=root.querySelector(':scope>.generation-meter');
    if(!meter){meter=document.createElement('span');meter.className='generation-meter';meter.innerHTML='<span class="generation-meter-stage"></span><strong class="generation-meter-value"></strong><span class="generation-meter-steps"></span><span class="generation-meter-track"><i></i></span>';root.replaceChildren(meter);}
    meter.classList.toggle('compact',compact);const value=amount(d),percent=meter.querySelector('.generation-meter-value');
    meter.querySelector('.generation-meter-stage').textContent=label(d);
    if(value!==null&&d.status!=='queued'){count(percent,Math.round(value*100));percent.hidden=false;}else percent.hidden=true;
    meter.querySelector('.generation-meter-steps').textContent=d.sampling&&d.sampling_steps?`${d.sampling_step||0} / ${d.sampling_steps} steps`:'';
    const track=meter.querySelector('.generation-meter-track');track.classList.toggle('indeterminate',value===null||d.status==='queued');track.firstElementChild.style.transform=`scaleX(${value??.3})`;
    track.setAttribute('role','progressbar');track.setAttribute('aria-label',label(d));track.setAttribute('aria-valuemin','0');track.setAttribute('aria-valuemax','100');
    if(value!==null)track.setAttribute('aria-valuenow',String(Math.round(value*100)));else track.removeAttribute('aria-valuenow');
  };
  const surfaces=new Set(),activity=new IntersectionObserver(entries=>{for(const {target,isIntersecting} of entries)target.classList.toggle('motion-offscreen',!isIntersecting);});
  function observe(el){if(!surfaces.has(el)){surfaces.add(el);activity.observe(el);}}
  function beamMaterial(root){
    if(root.querySelector(':scope>.generation-beam'))return;
    const layer=document.createElement('span');layer.className='generation-beam';layer.setAttribute('aria-hidden','true');
    const halo=document.createElement('span');halo.className='generation-beam-halo';
    const core=document.createElement('span');core.className='generation-beam-core';
    const sparks=document.createElement('span');sparks.className='generation-beam-particles';
    const total=root.classList.contains('generation-live')?24:9;
    for(let i=0;i<total;i++){
      const spark=document.createElement('i');
      spark.style.cssText=`left:${(7+i*37.1)%96}%;--spark-duration:${3+(i%7)*.34}s;--spark-delay:${-i*.43}s;--spark-size:${1+(i%3)*.5}px;--spark-drift:${(i*11)%23-11}px`;
      sparks.append(spark);
    }
    // Identical tracks, clipped around the moving beam, brighten only at intersections.
    const crossings=sparks.cloneNode(true);crossings.classList.add('generation-beam-crossings');
    const particleField=(name,count)=>{
      const field=document.createElement('span');field.className=name;
      for(let i=0;i<count;i++){
        const dust=document.createElement('i');
        dust.style.cssText=`left:${2+(i*61.8034)%96}%;--flight-duration:${1.15+(i%7)*.19}s;--flight-delay:${-i*.237}s;--flight-size:${1+(i%3)*.45}px;--flight-length:${2+i%5}px;--scatter-factor:${((i*37)%101-50)/50};--distance-factor:${.45+(i%5)*.19};--eject-direction:${i%2?1:-1};--flight-angle:${(i*47)%140-70}deg`;
        field.append(dust);
      }
      return field;
    };
    const large=root.classList.contains('generation-live');
    const trail=particleField('generation-beam-trail',large?18:8);
    const bursts=particleField('generation-beam-bursts',large?16:8);
    layer.append(halo,sparks,crossings,trail,bursts,core);root.append(layer);
  }
  motion.generation=(root,d)=>{
    if(!root)return;const running=Boolean(active(d));root.dataset.phase=d?.status||'idle';root.classList.toggle('generation-live',running);root.querySelector('p').hidden=running;
    if(!running){root.querySelector('.generation-meter-host')?.remove();root.querySelector('.generation-beam')?.remove();return;}
    observe(root);beamMaterial(root);reflectProgress(root,d);
    let host=root.querySelector('.generation-meter-host');if(!host){host=document.createElement('span');host.className='generation-meter-host';root.append(host);}motion.progress(host,d);
  };
  motion.take=(card,d)=>{
    if(!d)return;card.dataset.active=String(active(d));const placeholder=card.querySelector('.take-placeholder');if(!placeholder||!active(d))return;
    observe(card);let stage=placeholder.querySelector('.take-stage');
    if(!stage){placeholder.replaceChildren();stage=document.createElement('span');stage.className='take-stage';const percent=document.createElement('strong');percent.className='take-percent';placeholder.append(stage,percent);}
    stage.textContent=label(d);const value=amount(d),percent=placeholder.querySelector('.take-percent');percent.textContent=value!==null&&d.status!=='queued'?Math.round(value*100)+'%':'';
    beamMaterial(placeholder);reflectProgress(card,d);
  };
  const groups='.video-camera-tabs,.video-camera-choices,.library-tabs,.settings-tabs,.workspace-tabs [role=tablist],.generation-controls,.advanced-tabs';
  const previous=new WeakMap(),states=new WeakMap(),observed=new Set();let frame=0;
  const resize=new ResizeObserver(()=>schedule());
  function selection(el){
    if(!el.isConnected||!el.getClientRects().length)return;
    if(!observed.has(el)){observed.add(el);resize.observe(el);}
    el.classList.add('selection-motion');
    const chosen=[...el.children].filter(b=>b.matches('button[aria-pressed="true"],button[aria-selected="true"],button[aria-expanded="true"]'));
    if(chosen.length!==1){el.classList.remove('selection-visible');return;}
    const selected=chosen[0],rect={x:selected.offsetLeft,y:selected.offsetTop,w:selected.offsetWidth,h:selected.offsetHeight,r:parseFloat(getComputedStyle(selected).borderTopLeftRadius)||0};
    const stamp=JSON.stringify(rect);if(states.get(el)===stamp&&el.classList.contains('selection-visible'))return;
    const anchor=el.matches('.video-camera-choices')?(el.closest('.video-camera-panel')||el):el,old=previous.get(anchor);
    const place=r=>{for(const [key,value] of Object.entries(r))el.style.setProperty('--selection-'+key,value+'px');};
    if(!states.has(el)&&old&&!reduce.matches){place(old);el.classList.add('selection-visible');getComputedStyle(el,'::before').transform;}
    place(rect);el.classList.add('selection-visible');states.set(el,stamp);previous.set(anchor,rect);
  }
  function update(){frame=0;document.querySelectorAll(groups).forEach(selection);for(const el of surfaces)if(!el.isConnected){activity.unobserve(el);surfaces.delete(el);}for(const el of observed)if(!el.isConnected){resize.unobserve(el);observed.delete(el);}}
  function schedule(){if(!frame)frame=requestAnimationFrame(update);}
  const observer=new MutationObserver(records=>{if(records.some(r=>r.type==='attributes'||r.target instanceof Element&&(r.target.closest(groups)||r.target.matches('.video-camera-panel,#character-options,#video-preset-options'))))schedule();});observer.observe(document.body,{childList:true,subtree:true,attributes:true,attributeFilter:['aria-pressed','aria-selected','aria-expanded','open']});
  document.addEventListener('input',event=>{
    const slider=event.target;if(!slider.matches('input[type=range]'))return;
    const parent=slider.closest('.video-slider-choices');if(!parent)return;
    const p=(Number(slider.value)-Number(slider.min))/(Number(slider.max)-Number(slider.min))*100;
    const ticks=[...parent.querySelectorAll('.video-slider-scale>span')],nearest=ticks.reduce((best,t)=>Math.abs(parseFloat(t.style.left)-p)<Math.abs(parseFloat(best.style.left)-p)?t:best,ticks[0]);
    ticks.forEach(t=>t.classList.toggle('nearest-tick',t===nearest));

  });
  document.addEventListener('pointerup',schedule);window.addEventListener('resize',schedule);schedule();
  // Interaction feedback lives on the control, with no delayed action or JS idle loop.
  const pressTimers=new WeakMap();
  function press(button,event){
    if(!button||button.disabled||button.matches('.video-ratio-option')||reduce.matches)return;
    if(getComputedStyle(button).position==='static')button.classList.add('press-anchor');
    const rect=button.getBoundingClientRect();button.style.setProperty('--press-x',(event?.clientX?event.clientX-rect.left:rect.width/2)+'px');button.style.setProperty('--press-y',(event?.clientY?event.clientY-rect.top:rect.height/2)+'px');
    clearTimeout(pressTimers.get(button));button.classList.remove('press-feedback');
    requestAnimationFrame(()=>{if(!button.isConnected)return;button.classList.add('press-feedback');pressTimers.set(button,setTimeout(()=>button.classList.remove('press-feedback'),430));});
  }
  document.addEventListener('pointerdown',event=>press(event.target.closest('button'),event));
  document.addEventListener('click',event=>{if(event.detail===0)press(event.target.closest('button'));});
  let hoverFrame=0,hoverTarget=null,hoverPoint=null;
  document.addEventListener('pointermove',event=>{
    const button=event.target.closest('.video-camera-tab,.preset-card,.media-upload-control,.generation-controls>button,#project-picker,#engine-settings,#generate,#video-generate,#save-as-asset,#edit-image');if(!button||reduce.matches)return;
    hoverTarget=button;hoverPoint={x:event.clientX,y:event.clientY};
    if(!hoverFrame)hoverFrame=requestAnimationFrame(()=>{hoverFrame=0;if(!hoverTarget?.isConnected)return;const r=hoverTarget.getBoundingClientRect();hoverTarget.style.setProperty('--hover-x',(hoverPoint.x-r.left)+'px');hoverTarget.style.setProperty('--hover-y',(hoverPoint.y-r.top)+'px');});
  },{passive:true});
  function visibility(){document.body.classList.toggle('page-asleep',document.hidden);}
  document.addEventListener('visibilitychange',visibility);visibility();
})();
