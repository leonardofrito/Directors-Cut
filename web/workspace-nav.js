(() => {
  const dialog=document.getElementById('workspace-browser'),grid=document.getElementById('workspace-browser-grid'),search=document.getElementById('workspace-browser-search');
  let options=null;
  function draw(){
    if(!options)return;
    const term=search.value.trim().toLowerCase(),items=options.items.filter(item=>item.title.toLowerCase().includes(term));
    grid.replaceChildren(...items.map(item=>{
      const card=document.createElement('button');card.type='button';card.className='workspace-item'+(item.id===options.current?' selected':'');card.setAttribute('aria-current',String(item.id===options.current));
      const media=document.createElement(item.video?'video':'img');
      if(item.file){media.src=fileURL(item.file)+(item.video?'#t=0.1':'');if(item.video){media.muted=true;media.preload='metadata';}else{media.alt='';media.loading='lazy';}card.append(media);}
      else{const placeholder=document.createElement('span');placeholder.className='workspace-item-empty';placeholder.textContent=item.video?'No takes yet':'No images yet';card.append(placeholder);}
      const name=document.createElement('strong');name.textContent=item.title;const count=document.createElement('span');count.textContent=item.count+' takes';card.append(name,count);
      card.onclick=()=>{const action=options.onSelect;dialog.close();safe(()=>action(item.id));};return card;
    }));
    if(!items.length){const empty=document.createElement('p');empty.textContent='No items found.';grid.append(empty);}
  }
  search.oninput=draw;
  const size=document.getElementById('workspace-browser-size');
  function resize(){grid.style.setProperty('--library-tile',size.value+'px');try{localStorage.setItem('directors-cut-browser-size',size.value);}catch{}}
  try{size.value=localStorage.getItem('directors-cut-browser-size')||'220';}catch{}
  size.oninput=resize;resize();
  document.getElementById('workspace-browser-close').onclick=()=>dialog.close();
  document.getElementById('workspace-browser-new').onclick=()=>{const action=options.onNew;dialog.close();safe(action);};
  const rename=document.getElementById('workspace-rename'),name=document.getElementById('workspace-rename-input');
  name.addEventListener('keydown',event=>{if(event.key==='Enter'){event.preventDefault();if(name.value.trim())rename.close('save');}});
  window.DirectorNavigator={
    open(data){options=data;document.getElementById('workspace-browser-heading').textContent=data.title;document.getElementById('workspace-browser-new').textContent=data.newLabel;search.value='';draw();dialog.showModal();search.focus();},
    rename(value){if(rename.open)return Promise.resolve(null);name.value=value;rename.returnValue='cancel';rename.showModal();name.focus();name.select();return new Promise(resolve=>rename.addEventListener('close',()=>resolve(rename.returnValue==='save'?name.value.trim():null),{once:true}));}
  };
})();
