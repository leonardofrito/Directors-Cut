"""Optional video direction and a local, general-purpose video prompt rewriter."""
import re

from .catalog import names
from .presets import FRAMING, LIGHTING, GRADE, PALETTES, SENSORS, F_STOPS
from .enhancer import THINKING_PATTERN, UNUSABLE_CAPTION
from .prompt_guides import runtime_guidance
from . import video_optics

GENRES = {name: text for name,text in [
    ('Epic','Epic scale, heroic visual storytelling and grand compositions.'),('Drama','Intimate dramatic staging with emotionally readable performances.'),
    ('Noir','Film-noir visual language: strong shadows, mystery and restrained staging.'),('Comedy','Comic timing, clear reactions and visually readable physical humor.'),
    ('Horror','Suspenseful horror atmosphere, controlled reveals and unsettling negative space.'),('Action','Legible action choreography and energetic cinematic staging.'),
    ('General','Balanced cinematic storytelling without a specific genre treatment.') ]}
TEMPO = {'Chaotic':'Chaotic editing with rapid cuts; keep action and identities understandable.',
    'Many cuts':'Use several purposeful shot changes within the available duration.',
    'Dynamic':'Dynamic pacing with motivated cuts and changing shot sizes.',
    'Calm':'Calm pacing, sustained observations and few cuts.',
    'Single shot':'One continuous unbroken shot. No cuts, transitions or montage.'}
CAMERA = {'8mm film':'8mm motion-picture film texture, organic grain and slight gate weave.',
    '35mm film':'35mm cinema film texture with restrained organic grain.',
    'Modern digital':'Modern digital cinema capture with clean detail and stable exposure.',
    'DV camcorder':'Consumer DV camcorder capture, interlaced-era video texture and handheld immediacy.'}
LENSES = {'Clean':'Clean neutral optics, restrained distortion and flare.', 'Sharp':'Crisp modern optics and high microcontrast.',
    'Anamorphic':'Anamorphic optics, oval bokeh and horizontal highlight flares.',
    'Vintage anamorphic':'Vintage anamorphic optics with softer edges, oval bokeh and organic flares.',
    'Warm vintage':'Warm vintage lens rendering with gentle contrast and soft highlight bloom.',
    'Halation vintage':video_optics.LENSES['Halation vintage']}
MOVES = {
    'Arc left':'Camera arcs left around the subject, maintaining subject distance and framing.',
    'Arc right':'Camera arcs right around the subject, maintaining subject distance and framing.',
    'Orbit':'Smooth camera orbit around the subject; the environment shifts in parallax.',
    'Slider left':'Short lateral camera slide to the left with gentle foreground parallax.',
    'Slider right':'Short lateral camera slide to the right with gentle foreground parallax.',
    'Dolly in':'Physical dolly move forward toward the subject; perspective changes naturally.',
    'Dolly out':'Physical dolly move backward away from the subject, revealing more environment.',
    'Dolly zoom':'Dolly backward while zooming in to hold subject size, stretching background perspective.',
    'Crash zoom in':'A sudden fast optical zoom toward the subject, ending on a tight composition.',
    'Crash zoom out':'A sudden fast optical zoom out, rapidly revealing the surrounding scene.',
    'Helicopter':'Sweeping helicopter-style aerial tracking, with broad spatial parallax.',
    'Robot arm':'Precise robotic camera-arm movement with controlled changes in height and angle.',
    'Slow push':'Very slow, almost imperceptible push toward the subject.',
    'Crane up':'Camera cranes upward, smoothly revealing the scene from increasing height.',
    'Crane down':'Camera cranes downward toward the subjects, smoothly lowering its viewpoint.',
    'POV':'First-person point of view with movement motivated by the viewpoint character.',
    'Handheld':'Natural handheld camera movement with small human imperfections, without excessive shake.',
    'Rack focus':'Camera position stays fixed while focus shifts between foreground and background subjects.',
    'Tilt down':'Camera tilts downward from a fixed position to reveal the subject or ground.',
    'Tilt up':'Camera tilts upward from a fixed position to reveal the subject or overhead space.',
    'Pan left':'Camera pans left from a fixed position, following the action.',
    'Pan right':'Camera pans right from a fixed position, following the action.',
    'Tracking':'Camera tracks alongside the moving subject, matching its speed.',
    'Whip pan':'A quick whip pan with motion blur that resolves into a clear composition.',
    'Snorricam':'Body-mounted camera faces the character; their torso stays stable while the background moves.',
    'Static':'Locked-off camera. No pan, tilt, zoom, dolly or handheld movement.'}
LIGHTS = {**LIGHTING, 'Practical':'Visible practical lamps motivate the scene lighting.',
    'Window':'Directional light from a nearby window with natural falloff.',
    'Overhead':'Overhead lighting with defined downward facial and environmental shadows.',
    'Soft cross':'Soft crossed key and fill lighting with gentle dimensional separation.',
    'Contre-jour':'Strong backlighting toward the camera, with controlled silhouettes and edge separation.'}
VIDEO_FRAMING = {name: FRAMING[name] for name in (
    'Extreme wide','Wide','Full body','Cowboy shot','Medium','Close-up','Extreme close-up',
    'Over-the-shoulder','POV','Low angle','High angle','Bird’s-eye','Dutch angle','Symmetrical')}
CATEGORIES = [
    ('genre','Genre',GENRES),('era','Film era',{str(y):f'Visual production design and cinematic treatment evocative of the {y}s; preserve explicitly specified wardrobe and setting.' for y in range(1960,2030,10)}),
    ('tempo','Pacing / cuts',TEMPO),('camera','Camera',CAMERA),('sensor','Sensor',SENSORS),('lens','Lens',LENSES),
    ('aperture','Aperture',{f'f/{stop}':f'Aperture f/{stop}, '+('very shallow depth of field and soft background bokeh.' if float(stop)<2.8 else 'moderate depth of field with readable subject separation.' if float(stop)<8 else 'deep focus and a clearly readable environment.') for stop in F_STOPS}),
    ('focal_length','Focal length',{f'{mm}mm':f'Focal length: {mm}mm.' for mm in sorted(set(range(5,501,5))|{8,12,14,16,18,24,28})}),
    ('framing','Framing',FRAMING),('palette','Color palette',GRADE),('lighting','Lighting',LIGHTS),('movement','Camera movement',MOVES)]


def catalog():
    return [dict(key=key,label=label,options=[name for name in (VIDEO_FRAMING if key=='framing' else options) if not (key=='lens' and name=='Halation vintage')],palettes=PALETTES if key=='palette' else {}) for key,label,options in CATEGORIES if key not in ('lighting','sensor','camera')]


def validate(value):
    if not isinstance(value,dict) or any(key not in {c[0] for c in CATEGORIES} for key in value):
        raise ValueError('Invalid video direction presets.')
    for key,label,options in CATEGORIES:
        selected=value.get(key,'')
        if not isinstance(selected,str) or len(selected)>1007 or selected and selected not in options and not selected.startswith('custom:'):
            raise ValueError('Unknown video '+label.lower()+' preset.')
    return {key:value[key] for key,_,_ in CATEGORIES if key not in ('lighting','sensor','camera') and value.get(key) and not (key=='lens' and value[key]=='Halation vintage')}


def direction(value):
    lines=[]
    for key,label,options in CATEGORIES:
        if key in ('lighting','sensor','camera'):
            continue
        selected=value.get(key,'')
        if key=='lens' and selected=='Halation vintage':continue
        text=selected[7:].strip() if selected.startswith('custom:') else options.get(selected,'')
        if selected and not selected.startswith('custom:'):
            if key=='camera':text=video_optics.CAMERA.get(selected,text)
            elif key=='lens':text=video_optics.LENSES.get(selected,text)
            elif key=='aperture':text=video_optics.aperture(selected)
            elif key=='focal_length':text=video_optics.focal(selected)
        if text:lines.append(label+': '+text if selected.startswith('custom:') else text)
    return '\n'.join(lines)


def apply_direction(prompt, value):
    """Keep optical descriptions in the visual scene, not after its audio sections."""
    optics={key:selected for key,selected in value.items() if key in ('lens','aperture','focal_length') and not selected.startswith('custom:') and not (key=='lens' and selected=='Halation vintage')}
    if optics:
        text='Photographic treatment: '+direction(optics)
        section=re.search(r'(?im)^detailed_description\s*:\s*\n',prompt)
        if section:
            prompt=prompt[:section.end()]+text+'\n\n'+prompt[section.end():]
        else:
            prompt=text+'\n\n'+prompt
    remaining=direction({key:selected for key,selected in value.items() if key not in optics})
    if remaining:prompt+='\n\nVideo direction:\n'+remaining
    return prompt


def availability(nodes):
    files=[file for file in names(nodes,'CLIPLoader','clip_name') if re.search(r'qwen3[._]5[_-]4b.*\.safetensors$',file,re.I)]
    required=('TextGenerate','CLIPLoader','PreviewAny','PrimitiveStringMultiline','StringTrim','RegexMatch','RegexReplace','ComfySwitchNode','StringConcatenate')
    missing=['Node: '+key for key in required if key not in nodes]
    if 'stable_diffusion' not in names(nodes,'CLIPLoader','type'):
        missing.append('CLIPLoader type: stable_diffusion')
    return dict(ready=bool(files) and not missing,files=files,missing=missing,default=files[0] if files else '',quality_tested=False,
                vision=all(key in nodes for key in ('BatchImagesNode','ResizeAndPadImage')))


def attach_swap_appearances(graph,prompt,saved,nodes):
    """Bounded visual captions; never rewrite the source-person assignment or action."""
    status=availability(nodes or {});selected=saved.get('enhancer_model') or status['default']
    if not status['ready'] or not status['vision'] or selected not in status['files']:return False
    refs=saved.get('reference_ids',[]);mapping=list(saved.get('swap_people_map',{}).values());previous=None
    graph['dc_swap_look_clip']=dict(class_type='CLIPLoader',inputs=dict(clip_name=selected,type='stable_diffusion',device='default'))
    for i,role in enumerate(saved.get('swap_roles',[])):
        if role!='character' or f'h3_reference_{i}' not in graph:continue
        label=f'<Subject {mapping.index(refs[i])+1}>' if refs[i] in mapping else f'<Picture {i+1}>'
        key=f'dc_swap_look_{i}'
        graph[key+'_fit']=dict(class_type='ResizeAndPadImage',inputs=dict(image=[f'h3_reference_{i}',0],target_width=512,target_height=512,padding_color='black',interpolation='area'))
        graph[key]=dict(class_type='TextGenerate',_meta=dict(title=f'Describing replacement character {i+1}'),inputs=dict(clip=['dc_swap_look_clip',0],image=[key+'_fit',0],prompt='Describe only this character appearance in 25–45 English words: build, skin, face, hair, distinctive features, clothing colors and accessories. Preserve exaggerated anatomy. Ignore the studio, background, pose and camera. Do not describe actions or invent features. Output one short description only.',max_length=128,sampling_mode='off',thinking=False,use_default_template=True,mtp='off'))
        graph[key+'_clean']=dict(class_type='RegexReplace',inputs=dict(string=[key,0],regex_pattern=THINKING_PATTERN,replace='',case_insensitive=True,multiline=False,dotall=True,count=0))
        graph[key+'_trim']=dict(class_type='StringTrim',inputs=dict(string=[key+'_clean',0],mode='Both'))
        graph[key+'_bad']=dict(class_type='RegexMatch',inputs=dict(string=[key+'_trim',0],regex_pattern=UNUSABLE_CAPTION,case_insensitive=True,multiline=False,dotall=False))
        graph[key+'_safe']=dict(class_type='ComfySwitchNode',inputs=dict(switch=[key+'_bad',0],on_true='Use the complete visible appearance in the reference image.',on_false=[key+'_trim',0]))
        graph[key+'_label']=dict(class_type='StringConcatenate',inputs=dict(string_a=f'{label} appearance from <Picture {i+1}>: ',string_b=[key+'_safe',0],delimiter=''))
        graph[key+'_join']=dict(class_type='StringConcatenate',inputs=dict(string_a=previous or '',string_b=[key+'_label',0],delimiter='\n'))
        previous=[key+'_join',0]
    if not previous:return False
    graph['dc_swap_compact_prompt']=dict(class_type='StringConcatenate',inputs=dict(string_a=previous,string_b=prompt,delimiter='\n\n'))
    graph['136']['inputs']['prompt']=['dc_swap_compact_prompt',0]
    graph['dc_enhanced_preview']=dict(class_type='PreviewAny',inputs=dict(source=['dc_swap_compact_prompt',0]))
    return True

def attach(graph,prompt,selected,seed,duration,nodes,image_nodes=()):
    status=availability(nodes)
    if not status['ready'] or selected not in status['files']:
        raise ValueError('Choose an installed Qwen3.5 4B video prompt enhancer in Engine settings.')
    system=(f'Rewrite the supplied request as an executable {duration}-second MiniMax H3 REF2VA prompt. '
        'Output only these six sections: subject_definitions, summary, retention_analysis, detailed_description, overall_soundscape, non_diegetic_music. '
        'Preserve every reference tag and its assigned role exactly. Preserve subject count, invisible bodies, exaggerated anatomy, clothing, medium and all explicit constraints. '
        'Never normalize unusual characters. Do not invent extra subjects or dialogue. Keep quoted dialogue exactly in its original language. '
        'Describe feasible sequential actions, camera position and movement, lighting and sound. Budget actions and speech for the duration. '
        'Honor selected direction presets, especially single shot (no cuts) or the requested pacing. '
        'Do not invent a setting, wardrobe, props or actions absent from the request. Leave unspecified details unspecified. '
        'For requested edits, explicitly say REPLACE the source target with the assigned picture design; a statement that someone drives or holds an object does not express replacement. '
        'For a vehicle/object replacement, replace the complete geometry, silhouette, body and cabin, not just color or texture. Use source motion only for trajectory and timing. Requested edits override preservation of that target; preserve unrelated elements. '
        'Do not infer background details from images you cannot see. Do not output reasoning, thinking tags or commentary.')
    if image_nodes and status['vision']:
        system=system.replace('Do not infer background details from images you cannot see.',
            'Attached images are in <Picture N> order. Ignore their square padding. Inspect each image separately and read its assigned role from the request. For a replacement vehicle or product, describe its visible three-dimensional proportions, body shape, cabin/openings and materials, not only color. Multiple reference views may depict ONE object; never animate collage panels. Describe visible environment layout, depth, materials and light when useful, citing the picture in a stable Subject definition. Keep the grounded setting and identities across cuts. Do not turn an environment reference into a first frame or flat pasted background. Preserve unusual anatomy and exact invisibility constraints; never invent a head or skin for an invisible character.')
    system+='\n\nModel-specific prompting reference:\n'+runtime_guidance('h3')
    unusable=UNUSABLE_CAPTION
    trigger=next((tag for tag in ('body_swap:','motion_transfer:') if prompt.lstrip().startswith(tag)),None)
    if trigger:
        system+='\nBegin with the exact task marker '+trigger+' before the six sections.'
        unusable+=r'|\A(?!\s*'+re.escape(trigger)+r')[\s\S]*\Z'
    tags=list(dict.fromkeys(re.findall(r'<(?:Picture|Video|Audio|Subject)\s+\d+>',prompt)))
    for required in tags+['subject_definitions','summary','retention_analysis','detailed_description','overall_soundscape','non_diegetic_music']:
        unusable+=r'|\A(?![\s\S]*'+re.escape(required)+r')[\s\S]*\Z'
    if re.search(r'invisible|invisível',prompt,re.I):
        unusable+=r'|\A(?![\s\S]*(?:invisible|invisível))[\s\S]*\Z'
    graph.update({
        'dc_video_enhancer_clip':dict(class_type='CLIPLoader',inputs=dict(clip_name=selected,type='stable_diffusion',device='default')),
        'dc_video_enhancer_system':dict(class_type='PrimitiveStringMultiline',inputs=dict(value=system)),
        'dc_video_enhancer':dict(class_type='TextGenerate',inputs={'clip':['dc_video_enhancer_clip',0],'prompt':prompt,'max_length':2048 if duration<=8 else 3072,
            'sampling_mode':'on','sampling_mode.temperature':.5,'sampling_mode.top_k':20,'sampling_mode.top_p':.9,'sampling_mode.min_p':0,
            'sampling_mode.repetition_penalty':1.05,'sampling_mode.seed':seed,'sampling_mode.presence_penalty':0,'thinking':False,
            'use_default_template':True,'mtp':'off','system_prompt':['dc_video_enhancer_system',0]}),
        'dc_video_clean':dict(class_type='RegexReplace',inputs=dict(string=['dc_video_enhancer',0],regex_pattern=THINKING_PATTERN,replace='',case_insensitive=True,multiline=False,dotall=True,count=0)),
        'dc_video_trim':dict(class_type='StringTrim',inputs=dict(string=['dc_video_clean',0],mode='Both')),
        'dc_expansion_preview':dict(class_type='PreviewAny',inputs=dict(source=['dc_video_trim',0])),
        'dc_video_unusable':dict(class_type='RegexMatch',inputs=dict(string=['dc_video_trim',0],regex_pattern=unusable,case_insensitive=True,multiline=False,dotall=False)),
        'dc_video_full':dict(class_type='StringConcatenate',inputs=dict(string_a=['dc_video_trim',0],string_b='Authoritative scene, dialogue and reference constraints (take priority over any conflicting expansion):\n'+prompt,delimiter='\n\n')),
        'dc_video_prompt':dict(class_type='ComfySwitchNode',inputs=dict(switch=['dc_video_unusable',0],on_true=prompt,on_false=['dc_video_full',0])),
        'dc_enhanced_preview':dict(class_type='PreviewAny',inputs=dict(source=['dc_video_prompt',0]))})
    graph['136']['inputs']['prompt']=['dc_video_prompt',0]
    if image_nodes and status['vision']:
        for i,key in enumerate(image_nodes):
            graph[f'dc_video_ref_fit_{i}']=dict(class_type='ResizeAndPadImage',inputs=dict(image=[key,0],target_width=512,target_height=512,padding_color='black',interpolation='area'))
        graph['dc_video_enhancer_images']=dict(class_type='BatchImagesNode',inputs={f'images.image{i}':[f'dc_video_ref_fit_{i}',0] for i in range(len(image_nodes))})
        graph['dc_video_enhancer']['inputs']['image']=['dc_video_enhancer_images',0]
