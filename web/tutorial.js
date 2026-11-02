/* Optional Bank of Ideas walkthrough; every GPU run remains an explicit user click. */
(()=>{
  let walkthrough=null,timer=null,busy=false;
  const panel=document.createElement('aside');panel.id='getting-started';panel.hidden=true;panel.setAttribute('aria-label','Bank of Ideas tutorial');
  const top=document.createElement('div');top.className='tutorial-heading';
  const title=document.createElement('strong'),close=button('','icon-button',stop);close.innerHTML=DirectorIcons.close;close.setAttribute('aria-label','Close tutorial');top.append(title,close);
  const text=document.createElement('p'),action=button('Start','primary',()=>safe(next));panel.append(top,text,action);document.body.append(panel);
  const help=button('Tutorial','subtle',()=>safe(start));help.id='start-tutorial';document.getElementById('engine-settings').before(help);
  const example=button('Bank of Ideas','subtle',()=>safe(async()=>{await openExample();}));example.id='open-bank-example';document.getElementById('projects-new').before(example);
  function highlight(selector){document.querySelectorAll('.tutorial-target').forEach(el=>el.classList.remove('tutorial-target'));if(selector)document.querySelector(selector)?.classList.add('tutorial-target');}
  function stop(){panel.hidden=true;clearInterval(timer);timer=null;highlight(null);walkthrough=null;}
  async function openExample(){
    const result=await api('/examples/bank-of-ideas/open','POST',{});
    if($('projects-dialog').open)$('projects-dialog').close();
    await projectList();await openProject(result.id);return result;
  }
  function show(){
    if(!walkthrough)return;
    if(project?.id!==walkthrough.project){stop();return;}
    panel.hidden=false;action.disabled=busy;
    if(walkthrough.step===0){title.textContent='Make Bank of Ideas yours';text.textContent='Create a person, then cast them in an existing bank scene. The original film stays intact.';action.textContent='Create an actor';highlight('#asset-new');}
    if(walkthrough.step===1){
      const asset=project.assets?.find(a=>a.source_shot_id===walkthrough.study&&a.file);walkthrough.asset=asset?.id;
      title.textContent='1 · Create your actor';text.textContent=asset?'Your actor is ready. Next, replace @juanito in a copy of a bank shot.':'Choose presets or write a prompt, generate an image and set its cover. Give your actor a name you can recognize.';action.textContent='Use this actor in the bank';action.disabled=busy||!asset;highlight(asset?'#save-as-asset':'#generate');
    }
    if(walkthrough.step===2){
      const shot=project.shots.find(s=>s.id===walkthrough.shot),done=shot?.drafts.some(d=>d.status==='succeeded'&&d.file);
      title.textContent='2 · Generate your scene';text.textContent=done?'Your version is ready. Approve a take, then open Library → Shots to order and export your sequence.':'The bank reference stays; @juanito has been replaced with your actor. Review the prompt, then Generate. This starts at 0.4 MP.';action.textContent=done?'Finish':'Show Generate';highlight(done?'#video-approve':'#video-generate');walkthrough.done=done;
    }
  }
  async function start(){
    if(busy)return;busy=true;
    try{const sample=await openExample();if(DirectorVideo.active)await DirectorVideo.leave();walkthrough={project:sample.id,step:0};clearInterval(timer);timer=setInterval(()=>{if(!panel.hidden)show();},1500);show();}
    finally{busy=false;show();}
  }
  async function next(){
    if(!walkthrough||busy)return;busy=true;show();
    try{
      if(walkthrough.step===0){
        await switchCreationMode('asset');const previous=currentShot()?.id;await $('asset-new').onclick();
        if(currentShot()?.id===previous)throw new Error('Finish the current action before creating your actor.');
        $('asset_kind').value='character';$('asset_kind').dispatchEvent(new Event('change'));
        walkthrough.study=currentShot().id;walkthrough.step=1;$('prompt').focus();
      }else if(walkthrough.step===1){
        const actor=project.assets.find(a=>a.id===walkthrough.asset&&a.file);if(!actor)return;
        await saveNotes(false);
        const original=project.shots.find(s=>s.id===project.tutorial?.template_shot)||project.shots.find(s=>s.mode==='video'&&s.reference_ids?.includes(project.assets.find(a=>a.handle==='juanito')?.id));
        if(!original)throw new Error('The example bank shot is missing.');
        const old=project.assets.find(a=>a.handle==='juanito');
        const prompt=original.prompt.replace(/@juanito\b/g,'@'+actor.handle).replace(/\bJuanito\b/g,'the character');
        const settings={...original,title:'My actor · Bank of Ideas',prompt,megapixels:.4,reference_ids:original.reference_ids.map(id=>id===old?.id?actor.id:id),motion_reference_id:'',audio_reference_id:'',output_audio_id:'',prompt_enhancer:false};
        delete settings.drafts;delete settings.approved;delete settings.id;
        const shot=await api(`/projects/${project.id}/shots`,'POST',{mode:'video',settings});project=await api(`/projects/${project.id}`);await DirectorVideo.selectShot(shot.id);walkthrough.shot=shot.id;walkthrough.step=2;
      }else if(walkthrough.done){stop();toast('Your cast. Your scene.');}
      else{$('video-generate').focus({preventScroll:true});}
    }finally{busy=false;show();}
  }
  window.DirectorTutorial={start,openExample};
})();
