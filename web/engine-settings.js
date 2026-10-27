/* Paths are on the studio server, including when the browser is on another PC. */
(()=>{
 const byId=id=>document.getElementById(id);let loaded=false;
 function message(text,error=false){const el=byId('engine-connection-status');el.textContent=text;el.dataset.error=String(error);}
 function form(settings){
  for(const key of ['comfy_url','comfy_root','models_dir','proxy_url'])byId('engine-'+key).value=settings[key]||'';
  byId('engine-shared').checked=Boolean(settings.shared_filesystem);
  byId('engine-external').checked=settings.proxy_managed===false;
  byId('engine-proxy-fields').hidden=!byId('engine-external').checked;
 }
 function values(){return Object.fromEntries([...['comfy_url','comfy_root','models_dir','proxy_url'].map(key=>[key,byId('engine-'+key).value.trim()]),['shared_filesystem',byId('engine-shared').checked],['proxy_mode',byId('engine-external').checked?'external':'managed']]);}
 function hardware(result){
  const el=byId('engine-hardware');el.replaceChildren();
  if(!result.online){el.textContent='ComfyUI is offline. Start it, then test the address.';return;}
  el.textContent=result.hardware.devices.map(d=>`${d.name} · ${d.backend.toUpperCase()}${d.vram_total?' · '+(d.vram_total/1024**3).toFixed(1)+' GB':''}`).join('\n')||'Connected · CPU';
  byId('engine-backend-note').textContent='GPU support comes from your ComfyUI installation. Quantized models and custom nodes need compatible kernels; downloading a file does not guarantee it can run on this GPU.';
 }
 async function action(button,task){button.disabled=true;try{await task();}catch(error){message(error.message,true);}finally{button.disabled=false;}}
 async function load(){
  const result=await api('/engine');form(result.settings);hardware(result);loaded=true;
  message(result.online?'Connected'+(result.download_error?' · '+result.download_error:' · Model download folder ready.'):result.error||'Not connected.',!result.online);
 }
 async function discover(){
  message('Looking for ComfyUI…');const result=await api('/engine/discover');
  const list=byId('engine-detected');list.replaceChildren();
  for(const install of result.installations){
   const button=document.createElement('button');button.type='button';button.className='engine-install';
   const title=document.createElement('strong'),path=document.createElement('span');title.textContent=install.name+' · '+install.kind;path.textContent=install.root;button.append(title,path);
   button.onclick=()=>{byId('engine-comfy_root').value=install.root;byId('engine-models_dir').value=install.models_dir;message('Folder selected. Save connection to apply.');};list.append(button);
  }
  for(const server of result.servers){
   const button=document.createElement('button');button.type='button';button.className='engine-install';button.textContent=server.url+' · Online';
   button.onclick=()=>{byId('engine-comfy_url').value=server.url;byId('engine-external').checked=false;byId('engine-proxy-fields').hidden=true;hardware(server);message('Address selected. Save connection to apply.');};list.append(button);
  }
  message(result.installations.length||result.servers.length?'Select a detected folder/address, or enter your own below.':'Nothing detected. Enter the ComfyUI address and data folder below.');
 }
 document.addEventListener('DOMContentLoaded',()=>{
  byId('settings-connection').addEventListener('click',()=>action(byId('engine-detect'),async()=>{if(!loaded)await load();}));
  byId('engine-detect').onclick=event=>action(event.currentTarget,discover);
  byId('engine-test').onclick=event=>action(event.currentTarget,async()=>{message('Testing…');const result=await api('/engine/test','POST',{comfy_url:values().comfy_url});hardware(result);message(result.online?'ComfyUI responded. Save connection to apply.':result.error,!result.online);});
  byId('engine-save').onclick=event=>action(event.currentTarget,async()=>{
   const selected=values();message('Saving folders…');
   await api('/engine/folders','PUT',selected);
   await window.DirectorModelDownloads?.refresh();
   message('Folders saved. Connecting…');
   let result;
   try{result=await api('/engine','PUT',selected);}
   catch(error){message('Folders saved. Generation connection is not ready: '+error.message,true);return;}
   form(result.settings);hardware(result);
   config=await api('/config');populateWorkflows();renderModels();window.DirectorModelDownloads?.refresh();
   message('Connection saved.');toast('ComfyUI connection updated.');
  });
  byId('engine-external').onchange=()=>{byId('engine-proxy-fields').hidden=!byId('engine-external').checked;};
 });
 document.addEventListener('director-ready',async()=>{
  try{
   const app=await api('/app');
   if(app.packaged||app.can_quit){
    const footer=document.createElement('div');footer.className='engine-app-actions';
    const version=document.createElement('span');version.textContent='Director’s Cut '+app.version;
    const legal=document.createElement('a');legal.href='/api/app/legal/third-party';legal.target='_blank';legal.rel='noopener';legal.textContent='Licenses';
    const folder=document.createElement('button');folder.type='button';folder.textContent='Open data folder';folder.onclick=()=>safe(()=>api('/app/open-data','POST',{}));
    footer.append(version,legal,folder);
    if(app.can_quit){
     const quit=document.createElement('button');quit.type='button';quit.textContent='Quit app';
     const quick=byId('quit-app');quick.hidden=false;
     const exit=()=>safe(async()=>{
      quit.disabled=true;quick.disabled=true;
      try{
       if(project){if(window.DirectorVideo?.active)await DirectorVideo.save();else await saveNotes(false);}
       await api('/app/quit','POST',{});
       quit.textContent='App closed';quick.querySelector('span').textContent='Closed';
       toast('Director’s Cut closed. You can close this tab.');
      }catch(error){quit.disabled=false;quick.disabled=false;throw error;}
     });
     quit.onclick=exit;quick.onclick=exit;footer.append(quit);
    }
    byId('models-dialog').append(footer);
   }
   if(location.hash==='#setup'){
    byId('engine-settings').click();selectSettingsSection('connection');await load();await action(byId('engine-detect'),discover);
    history.replaceState(null,'',location.pathname+location.search);
   }
  }catch(error){console.warn('App launcher information unavailable:',error.message);}
 });
})();
