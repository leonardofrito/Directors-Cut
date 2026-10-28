/* Shared select-only combobox. Native selects remain the form's data source. */
(() => {
  const palettes = {
    Natural: ['#53634b','#899471','#c6bfa4','#d9c9ad','#7f6b59'],
    'Teal and orange': ['#143f49','#277c86','#82a6a0','#d69b63','#f5c088'],
    Warm: ['#5b3e41','#98574c','#c98b61','#e3b786','#f1d8b5'],
    Cool: ['#27364d','#405777','#6e8aa5','#a7b8ca','#d2d9de'],
    Muted: ['#555653','#777c73','#a1a18f','#bdb7a6','#d6cdbb'],
  };
  // Add { image: '/assets/previews/example.webp', hint: '...' } by control
  // ID and option value when real reference images are available.
  const previews = {
    lens: {'Natural perspective':{hint:'Balanced perspective'},'Large format · 50mm':{hint:'Shallow depth of field'},'Wide · 24mm':{hint:'Broad perspective, deep focus'},'Portrait · 85mm':{hint:'Soft background, tighter perspective'},'Anamorphic · 50mm':{hint:'Oval bokeh, horizontal flare'}},
    camera: {'Extreme wide':{hint:'Environment dominates the frame'},Wide:{hint:'Subject and surroundings'},Medium:{hint:'Closer staging and body language'},'Close-up':{hint:'Expression and small details'},'Extreme close-up':{hint:'A single striking detail'},'Over-the-shoulder':{hint:'Looking past another character'},POV:{hint:'The character’s point of view'},'Low angle':{hint:'Looking up at the subject'},'High angle':{hint:'Looking down on the subject'}},
    lighting: {'Natural light':{hint:'Available light, believable contrast'},'Golden hour':{hint:'Warm backlight, long shadows'},'Soft window':{hint:'Gentle directional light'},'Practical night':{hint:'Lamps and motivated night lighting'},'Hard sunlight':{hint:'Crisp shadows and strong contrast'},'Low-key studio':{hint:'Controlled light and deep shadows'}},
    film: {'Digital clean':{hint:'Clean image, minimal grain'},'Tungsten 500T':{hint:'Organic grain and highlight halation'},'Daylight 250D':{hint:'Fine grain, natural skin tones'},'Black and white':{hint:'Monochrome tonal separation'}},
    style: {Cinematic:{hint:'Composed lighting and subtle grain'},Photorealistic:{hint:'Natural materials and light'},'Storyboard sketch':{hint:'Ink lines and clear staging'},'Pencil drawing':{hint:'Graphite shading on paper'},Anime:{hint:'Linework and painted backgrounds'},'3D render':{hint:'Rendered materials and lighting'},Previsualization:{hint:'Simple forms and clear blocking'},'Concept art':{hint:'Painterly visual storytelling'}},
    grade: {Natural:{hint:'Balanced earth and skin tones'},'Teal and orange':{hint:'Teal shadows, warm highlights'},Warm:{hint:'Amber highlights and warm midtones'},Cool:{hint:'Blue shadows and restrained warmth'},Muted:{hint:'Lower saturation, lifted blacks'}},
  };
  const filmPalettes = {};
  const widgets = new Map();
  let activeWidget;
  const visualControls=new Set(['style','camera','lens_type','sensor','lighting','light_color','film','grade','ratio','f_stop']);

  function decorate(parent, select, option, compact=false) {
    if(['asset_kind','asset-kind','library-kind'].includes(select.id)){
      const icons={character:'user-round',prop:'box',location:'map-pin',all:'layers'};
      if(icons[option.value]){const icon=document.createElement('span');icon.className='ui-icon';icon.setAttribute('aria-hidden','true');icon.style.setProperty('--ui-icon',`url(/assets/icons/lucide/${icons[option.value]}.svg)`);parent.append(icon);}
    }
    const preview = previews[select.id]?.[option.value];
    const grid=!compact&&(select.dataset.previewGrid==='true'||visualControls.has(select.id));
    if(grid) {
      const tile=document.createElement('span');tile.className='option-tile';
      if(option.value==='__custom__'||!option.value){tile.classList.add('option-tile-symbol');tile.textContent=option.value==='__custom__'?'+':'○';}
      else if(preview?.image){const img=document.createElement('img');img.src=preview.image;img.alt='';img.loading='lazy';tile.append(img);}
      else{tile.classList.add('option-tile-pending');tile.textContent='Preparing preview…';}
      parent.append(tile);
    }
    const palette=(select.id==='grade'||select.id==='character-grade'?palettes:select.id==='film'||select.id==='character-film'?filmPalettes:{})[option.value];
    if (palette) {
      const swatch=document.createElement('span');swatch.className='grade-swatch';swatch.setAttribute('aria-hidden','true');
      for(const color of palette) {const bar=document.createElement('i');bar.style.backgroundColor=color;swatch.append(bar);}
      parent.append(swatch);
    }
    if(preview?.image&&!grid) {
      const image=document.createElement('img');image.className='option-preview';image.src=preview.image;image.alt='';parent.append(image);
    }
    const text=document.createElement('span');text.className='option-copy';
    const label=document.createElement('span');label.className='option-name';label.textContent=window.DirectorControls.presetLabel(option.label);text.append(label);
    if(!compact && preview?.hint&&!grid) {const hint=document.createElement('small');hint.textContent=preview.hint;text.append(hint);}
    parent.append(text);
  }

  class Dropdown {
    constructor(select) {
      this.select=select;this.stamp='';this.index=0;this.query='';this.lastKey=0;
      const label=Array.from(select.labels || []).map(l=>l.textContent.trim()).join(' ') || select.getAttribute('aria-label') || select.id;
      this.wrapper=document.createElement('div');this.wrapper.className='dropdown';this.wrapper.dataset.select=select.id;
      select.before(this.wrapper);this.wrapper.append(select);select.hidden=true;select.tabIndex=-1;select.setAttribute('aria-hidden','true');
      this.trigger=document.createElement('button');this.trigger.type='button';this.trigger.className='dropdown-trigger';this.trigger.id=select.id+'-trigger';this.trigger.setAttribute('role','combobox');this.trigger.setAttribute('aria-label',label);this.trigger.setAttribute('aria-haspopup','listbox');this.trigger.setAttribute('aria-expanded','false');
      this.popup=document.createElement('div');this.popup.id=select.id+'-listbox';this.popup.className='dropdown-popup';this.popup.setAttribute('popover','manual');this.popup.setAttribute('role','listbox');this.popup.setAttribute('aria-label',label);
      this.trigger.setAttribute('aria-controls',this.popup.id);this.wrapper.append(this.trigger,this.popup);
      for(const el of document.querySelectorAll(`label[for="${CSS.escape(select.id)}"]`))el.addEventListener('click',()=>this.trigger.focus());
      this.trigger.onclick=()=>this.opened?this.close():this.open();
      this.trigger.onkeydown=event=>this.keydown(event);
      this.popup.addEventListener('toggle',event=>{if(event.newState==='closed'){this.opened=false;this.trigger.setAttribute('aria-expanded','false');this.trigger.removeAttribute('aria-activedescendant');if(activeWidget===this)activeWidget=null;}});
      this.clickAway=event=>{if(this.opened&&!this.wrapper.contains(event.target))this.close();};document.addEventListener('pointerdown',this.clickAway);
      this.reposition=()=>{if(this.opened)this.position();};
      window.addEventListener('resize',this.reposition);window.addEventListener('scroll',this.reposition,true);
      this.observer=new MutationObserver(()=>this.sync());this.observer.observe(select,{childList:true,subtree:true,attributes:true,attributeFilter:['disabled','selected','label']});
      select.addEventListener('change',()=>this.sync());this.sync();
    }
    sync() {
      this.grid=this.select.dataset.previewGrid==='true'||visualControls.has(this.select.id);
      const stamp=JSON.stringify([this.select.value,this.select.disabled,this.grid,previews[this.select.id],Array.from(this.select.options).map(o=>[o.value,o.label,o.disabled])]);
      if(stamp===this.stamp)return;this.stamp=stamp;
      this.trigger.disabled=this.select.disabled;this.trigger.setAttribute('aria-disabled',String(this.select.disabled));
      this.trigger.replaceChildren();const option=this.select.selectedOptions[0];
      if(option)decorate(this.trigger,this.select,option,true);
      const arrow=document.createElement('span');arrow.className='dropdown-chevron';arrow.innerHTML='<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="1.8"><path d="m6 9 6 6 6-6"/></svg>';arrow.setAttribute('aria-hidden','true');this.trigger.append(arrow);
      this.options=Array.from(this.select.options);
      this.popup.classList.toggle('dropdown-image-grid',this.grid);
      this.popup.replaceChildren(...this.options.map((o,index)=>{
        const el=document.createElement('div');el.id=this.select.id+'-option-'+index;el.className='dropdown-option';el.setAttribute('role','option');el.setAttribute('aria-label',o.label);el.setAttribute('aria-selected',String(o.selected));el.setAttribute('aria-disabled',String(o.disabled));
        if(this.grid){el.classList.add('image-option');el.title=previews[this.select.id]?.[o.value]?.hint || o.label;}
        if(o.dataset.group&&this.options[index-1]?.dataset.group!==o.dataset.group)el.dataset.groupHeading=o.dataset.group;
        decorate(el,this.select,o);
        if(o.value==='__new__')el.classList.add('dropdown-create');
        const check=document.createElement('span');check.className='option-check';check.textContent=o.selected?'✓':'';check.setAttribute('aria-hidden','true');el.append(check);
        el.onpointermove=()=>{if(!o.disabled)this.highlight(index,false);};
        el.onmousedown=e=>e.preventDefault();el.onclick=()=>{if(!o.disabled)this.choose(index);};return el;
      }));
      if(this.opened){if(this.select.disabled)this.close();else{this.highlight(Math.max(0,this.select.selectedIndex));this.position();}}
    }
    position() {
      const rect=this.trigger.getBoundingClientRect();const width=Math.min(Math.max(rect.width,this.grid?340:this.select.id==='grade'?300:260),window.innerWidth-24);
      const below=window.innerHeight-rect.bottom-12,above=rect.top-12;const upward=below<220&&above>below;
      this.popup.style.width=width+'px';this.popup.style.maxHeight=Math.max(80,Math.min(this.grid?590:380,upward?above:below))+'px';
      this.popup.style.left=Math.max(12,Math.min(rect.left,window.innerWidth-width-12))+'px';
      this.popup.style.transformOrigin=upward?'bottom left':'top left';
      this.popup.style.top=(upward?Math.max(8,rect.top-this.popup.offsetHeight-7):rect.bottom+7)+'px';
    }
    open(index=this.select.selectedIndex) {
      if(this.select.disabled || !this.options.length)return;
      if(activeWidget && activeWidget!==this)activeWidget.close();activeWidget=this;
      this.popup.hidden=false;this.popup.showPopover();this.opened=true;this.trigger.setAttribute('aria-expanded','true');this.position();this.highlight(Math.max(0,index));window.DirectorControls?.openChoices(this.popup,true);
    }
    close() {if(!this.opened)return;this.opened=false;this.trigger.setAttribute('aria-expanded','false');this.trigger.removeAttribute('aria-activedescendant');if(activeWidget===this)activeWidget=null;window.DirectorControls.closeChoices(this.popup,()=>{if(!this.opened&&this.popup.matches(':popover-open'))this.popup.hidePopover();});}
    highlight(index,scroll=true) {
      this.index=index;
      Array.from(this.popup.children).forEach((el,i)=>el.classList.toggle('active-option',i===index));
      const el=this.popup.children[index];if(el){this.trigger.setAttribute('aria-activedescendant',el.id);if(scroll)el.scrollIntoView({block:'nearest'});}
    }
    choose(index) {
      const option=this.options[index];if(!option || option.disabled)return;
      this.select.value=option.value;this.select.dispatchEvent(new Event('change',{bubbles:true}));this.sync();this.trigger.focus();
    }
    keydown(event) {
      if(event.key==='Escape'){if(this.opened){event.preventDefault();event.stopPropagation();this.close();}return;}
      if(event.key==='Tab'){this.close();return;}
      if(['ArrowDown','ArrowUp','Home','End',...(this.grid?['ArrowLeft','ArrowRight']:[])].includes(event.key)) {
        event.preventDefault();if(!this.opened){this.open(event.key==='End'?this.options.length-1:event.key==='Home'?0:this.select.selectedIndex);return;}
        const step=event.key==='ArrowDown'?(this.grid?3:1):event.key==='ArrowUp'?(this.grid?-3:-1):event.key==='ArrowRight'?1:-1;
        let index=event.key==='Home'?0:event.key==='End'?this.options.length-1:Math.max(0,Math.min(this.options.length-1,this.index+step));
        while(this.options[index]?.disabled && index>0 && index<this.options.length-1)index+=step<0?-1:1;
        this.highlight(index);return;
      }
      if(event.key==='Enter'||event.key===' '){event.preventDefault();if(this.opened)this.choose(this.index);else this.open();return;}
      if(event.key.length===1&&!event.ctrlKey&&!event.metaKey&&!event.altKey) {
        event.preventDefault();const now=Date.now();this.query=now-this.lastKey>700?event.key:this.query+event.key;this.lastKey=now;
        const index=this.options.findIndex(o=>!o.disabled&&o.label.toLowerCase().startsWith(this.query.toLowerCase()));
        if(index>=0){if(!this.opened)this.open(index);else this.highlight(index);}
      }
    }
    destroy(){this.close();document.removeEventListener('pointerdown',this.clickAway);this.observer.disconnect();window.removeEventListener('resize',this.reposition);window.removeEventListener('scroll',this.reposition,true);}
  }
  window.DirectorDropdowns={previews,palettes,configure(config){
    Object.assign(palettes,config.palettes || {});
    Object.assign(filmPalettes,config.film_palettes || {});
    for(const [id,values] of Object.entries(config.preset_hints || {})) {
      previews[id] ||= {};
      for(const [value,hint] of Object.entries(values))previews[id][value]={...previews[id][value],hint};
    }
    for(const [id,values] of Object.entries(config.preview_images || {})){previews[id] ||= {};for(const [value,url] of Object.entries(values))previews[id][value]={...previews[id][value],image:url};}
    for(const widget of widgets.values())widget.stamp='';
    this.sync();
  },sync(){
    for(const [select,widget]of widgets){if(!select.isConnected){widget.destroy();widgets.delete(select);}}
    for(const select of document.querySelectorAll('select:not([data-inline-presets])')){if(!widgets.has(select))widgets.set(select,new Dropdown(select));widgets.get(select).sync();}
  }};
})();

// Shared visual generation controls for image assets and video.
(() => {
  const ratios=['16:9','5:4','4:3','3:2','1:1','2:3','3:4','4:5','9:16'];
  const button=(text,cls,callback)=>{const item=document.createElement('button');item.type='button';item.textContent=text;item.className=cls;item.onclick=callback;return item;};
  const reduce=matchMedia('(prefers-reduced-motion: reduce)'),popovers=new WeakMap();
  function popoverState(menu){
    if(!popovers.has(menu))popovers.set(menu,{animation:null,ratioAnimation:null,closing:false});
    return popovers.get(menu);
  }
  function cancelRatio(menu){
    const state=popoverState(menu);state.ratioAnimation?.cancel();state.ratioAnimation=null;
    menu.querySelector('.ratio-choice-morph')?.remove();
    menu.querySelectorAll('.ratio-source,.ratio-target').forEach(item=>item.classList.remove('ratio-source','ratio-target'));
  }
  function openChoices(menu,fresh=false){
    const state=popoverState(menu),visible=!fresh&&!menu.hidden;
    cancelRatio(menu);state.animation?.cancel();state.animation=null;state.closing=false;
    menu.hidden=false;menu.inert=false;
    if(reduce.matches||!menu.animate)return;
    const animation=menu.animate([
      {opacity:visible?.8:0,transform:visible?'translateY(3px) scale(.995)':'translateY(8px) scale(.98)'},
      {opacity:1,transform:'translateY(0) scale(1)'}
    ],{duration:visible?190:240,easing:'cubic-bezier(.16,1,.3,1)'});
    state.animation=animation;animation.onfinish=()=>{if(state.animation===animation)state.animation=null;};
  }
  function closeChoices(menu,onClosed){
    const state=popoverState(menu);cancelRatio(menu);
    if(menu.hidden||state.closing)return;
    const from=getComputedStyle(menu);const opacity=from.opacity,transform=from.transform;
    state.animation?.cancel();state.animation=null;state.closing=true;menu.inert=true;
    const finish=()=>{menu.hidden=true;menu.inert=false;state.closing=false;state.animation=null;onClosed?.();};
    if(reduce.matches||!menu.animate){finish();return;}
    const animation=menu.animate([{opacity,transform},{opacity:0,transform:'translateY(6px) scale(.985)'}],{duration:150,easing:'cubic-bezier(.4,0,1,1)',fill:'forwards'});
    state.animation=animation;animation.onfinish=()=>{if(state.animation!==animation)return;finish();animation.cancel();};
  }
  function chooseRatio(menu,item,value,onSelect){
    const state=popoverState(menu);
    if(menu.hidden||state.closing)return;
    // Finish the entrance before measuring so the travelling outline stays on the icons.
    state.animation?.finish();
    const previous=menu.querySelector('.video-ratio-option[aria-pressed="true"]');
    const from=(menu.querySelector('.ratio-choice-morph')||previous?.querySelector('.video-ratio-shape'))?.getBoundingClientRect();
    cancelRatio(menu);
    menu.querySelectorAll('.video-ratio-option').forEach(option=>option.setAttribute('aria-pressed',String(option===item)));
    onSelect(value);
    if(previous===item||!from||reduce.matches||!menu.animate)return;
    const to=item.querySelector('.video-ratio-shape').getBoundingClientRect(),bounds=menu.getBoundingClientRect();
    if(!from.width||!to.width)return;
    const outline=document.createElement('span');outline.className='ratio-choice-morph';outline.setAttribute('aria-hidden','true');
    outline.style.left=(from.left-bounds.left+menu.scrollLeft-menu.clientLeft)+'px';
    outline.style.top=(from.top-bounds.top+menu.scrollTop-menu.clientTop)+'px';
    outline.style.width=from.width+'px';outline.style.height=from.height+'px';
    previous?.classList.add('ratio-source');item.classList.add('ratio-target');menu.append(outline);
    const animation=outline.animate([
      {transform:'translate(0,0)',width:from.width+'px',height:from.height+'px'},
      {transform:`translate(${to.left-from.left}px,${to.top-from.top}px)`,width:to.width+'px',height:to.height+'px'}
    ],{duration:320,easing:'cubic-bezier(.16,1,.3,1)',fill:'forwards'});
    state.ratioAnimation=animation;
    animation.onfinish=()=>{if(state.ratioAnimation!==animation)return;cancelRatio(menu);};
  }
  function ratioChoices(menu,selected,onSelect){
    cancelRatio(menu);
    menu.className='generation-choice-menu video-choice-menu video-ratio-choices';menu.replaceChildren();
    menu.append(...ratios.map(value=>{
        const item=button('','generation-choice video-ratio-option',()=>chooseRatio(menu,item,value,onSelect));
        item.setAttribute('aria-pressed',String(selected===value));item.setAttribute('aria-label','Aspect ratio '+value);
        const [width,height]=value.split(':').map(Number),scale=34/Math.max(width,height);
        const stage=document.createElement('span');stage.className='video-ratio-stage';stage.setAttribute('aria-hidden','true');
        const shape=document.createElement('span');shape.className='video-ratio-shape';shape.style.width=(width*scale)+'px';shape.style.height=(height*scale)+'px';stage.append(shape);
        const text=document.createElement('span');text.textContent=value;item.append(stage,text);return item;
      }));
  }
  function sliderChoices(menu,{kind,value,min,max,step,ticks,id,onChange,caption:customCaption,format,snapPoints=[]}){
    menu.className='generation-choice-menu video-choice-menu video-slider-choices';menu.replaceChildren();const field={value:String(value)};
          const label=document.createElement('label'),output=document.createElement('output'),slider=document.createElement('input');
      const icon=document.createElement('span');icon.className='ui-icon';icon.setAttribute('aria-hidden','true');icon.style.setProperty('--ui-icon',`url(/assets/icons/lucide/${kind==='size'?'expand':kind==='camera'?'camera':'hourglass'}.svg)`);
      const caption=document.createElement('span');caption.textContent=customCaption||(kind==='size'?'Resolution':'Duration');label.append(icon,caption);
      slider.type='range';slider.id=id;slider.min=String(min);slider.max=String(max);slider.step=String(step);slider.value=field.value;label.htmlFor=slider.id;output.htmlFor=slider.id;
      const update=()=>{output.textContent=format?format(Number(field.value)):Number(field.value)+(kind==='size'?' MP':' s');slider.style.setProperty('--slider-progress',((Number(slider.value)-Number(slider.min))/(Number(slider.max)-Number(slider.min))*100)+'%');slider.setAttribute('aria-valuetext',format?format(Number(field.value)):Number(field.value)+(kind==='size'?' megapixels':' seconds'));};
      slider.setAttribute('aria-label',customCaption||(kind==='size'?'Resolution in megapixels':'Duration in seconds'));update();
      slider.oninput=()=>{
        const raw=Number(slider.value),snapped=snapPoints.length?snapPoints.reduce((best,n)=>Math.abs(n-raw)<Math.abs(best-raw)?n:best):raw;
        field.value=snapPoints.length?String(snapped):kind==='size'?(Math.round(raw*10)/10).toFixed(1):String(Math.round(raw));
        slider.value=field.value;update();onChange(Number(field.value));
      };
      if(snapPoints.length)slider.onkeydown=event=>{
        const delta=['ArrowRight','ArrowUp'].includes(event.key)?1:['ArrowLeft','ArrowDown'].includes(event.key)?-1:0;
        if(!delta)return;event.preventDefault();
        const nearest=snapPoints.reduce((best,n)=>Math.abs(n-Number(slider.value))<Math.abs(best-Number(slider.value))?n:best);
        slider.value=String(snapPoints[Math.max(0,Math.min(snapPoints.length-1,snapPoints.indexOf(nearest)+delta))]);slider.oninput();
      };
      const scale=document.createElement('div');scale.className='video-slider-scale';scale.setAttribute('aria-hidden','true');
      for(const entry of ticks){const value=typeof entry==='object'?entry.value:entry,tick=document.createElement('span');tick.textContent=typeof entry==='object'?entry.label:entry;tick.style.left=((Number(value)-Number(slider.min))/(Number(slider.max)-Number(slider.min))*100)+'%';scale.append(tick);}
      menu.append(label,output,slider,scale);
  }
  const presetLabel=value=>String(value || '').replace(/\bstoryboard sketch\b/gi,'Ink sketch');
  window.DirectorControls={ratioChoices,sliderChoices,presetLabel,openChoices,closeChoices};
})();
