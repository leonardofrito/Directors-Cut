/* Optional, pinned workflow dependencies. No model inference or engine restarts. */
(()=>{
 let result,refreshing=false;const by=id=>document.getElementById(id);
 async function refresh(){
  if(refreshing)return;refreshing=true;
  try{
   result=await api('/engine/nodes');by('node-automatic').checked=Boolean(result.preferences.automatic);
   for(const id of ['gguf','vsa','selflift'])by('node-'+id).checked=result.preferences.optional.includes(id);
   const busy=['queued','installing'].includes(result.job.status),selected=['kjnodes',...result.preferences.optional];by('node-install').disabled=busy||Boolean(result.install_error)||result.packs.filter(p=>selected.includes(p.id)).every(p=>p.installed);
   by('node-setup-status').textContent=result.job.message||result.install_error||'Only missing packs are installed. Existing node versions stay unchanged.';
   by('node-packs').replaceChildren(...result.packs.map(pack=>{
    const row=document.createElement('div');row.className='node-pack-row';const link=document.createElement('a');link.href='https://github.com/'+pack.repo;link.target='_blank';link.rel='noopener noreferrer';link.textContent=pack.folder;
    const state=document.createElement('span');state.textContent=pack.loaded?'Loaded':pack.installed?'On disk · restart ComfyUI':'Not installed';row.append(link,state);return row;
   }));
   const devices=config?.hardware?.devices||[],apple=devices.some(d=>d.backend==='mps'),amd=devices.some(d=>d.backend==='rocm'||/AMD|Radeon/i.test(d.name||''));
   by('platform-model-note').textContent=apple?'Apple Silicon: this workflow uses ComfyUI / PyTorch MPS. MLX weights need a separate compatible engine and cannot replace these files. BF16/GGUF may be used where supported; CUDA-specific INT8/NVFP4 kernels are not portable to Metal.':amd?'AMD: use a compatible ROCm/DirectML ComfyUI installation. Standard/GGUF weights do not need a Linux-specific edition; individual quantized kernels and attention nodes must support AMD.':'Model compatibility follows the ComfyUI computer, not your browser. Windows/Linux can share weights; GPU kernels and custom nodes still need to support your hardware. MLX is not used by this PyTorch workflow.';
  }catch(error){by('node-setup-status').textContent=error.message;}
  finally{refreshing=false;}
 }
 async function save(){
  const optional=['gguf','vsa','selflift'].filter(id=>by('node-'+id).checked);
  await api('/engine/nodes','PUT',{automatic:by('node-automatic').checked,optional});
  const packs=['kjnodes',...optional];if(by('node-automatic').checked&&result?.packs.some(p=>packs.includes(p.id)&&!p.installed))await api('/engine/nodes/install','POST',{packs});await refresh();
 }
 document.addEventListener('DOMContentLoaded',()=>{
  const section=document.createElement('section');section.className='workflow-node-settings';section.innerHTML='<h3>Workflow nodes</h3><label class="node-choice"><input id="node-automatic" type="checkbox">Automatically install missing nodes when Director’s Cut starts</label><p class="control-help">Downloads pinned node packs into the configured local ComfyUI and installs their requirements in its own Python. Restart ComfyUI after new nodes are installed.</p><div class="node-optional"><label><input id="node-gguf" type="checkbox"> GGUF</label><label><input id="node-vsa" type="checkbox"> VSA</label><label><input id="node-selflift" type="checkbox"> SelfLift</label></div><div id="node-packs"></div><div class="node-actions"><button id="node-install" type="button">Install missing nodes</button><button id="node-refresh" type="button">Refresh</button></div><p id="node-setup-status" class="control-help" role="status"></p><p id="platform-model-note" class="control-help"></p>';
  by('connection-settings').append(section);
  for(const id of ['automatic','gguf','vsa','selflift'])by('node-'+id).onchange=()=>safe(save);
  by('node-install').onclick=()=>safe(async()=>{await api('/engine/nodes/install','POST',{packs:['kjnodes',...['gguf','vsa','selflift'].filter(id=>by('node-'+id).checked)]});await refresh();});by('node-refresh').onclick=refresh;
  by('settings-connection').addEventListener('click',refresh);
  by('video-selflift').addEventListener('change',()=>safe(async()=>{const enabled=by('video-selflift').checked;await refresh();by('node-selflift').checked=enabled;await save();}));
  setInterval(()=>{if(result&&(['queued','installing'].includes(result.job.status)||by('models-dialog').open&&!by('connection-settings').hidden))refresh();},2500);
 });
})();
