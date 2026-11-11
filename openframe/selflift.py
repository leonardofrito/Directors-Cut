"""Optional two-resolution H3 sampling; original recipes remain unchanged when off."""
from .catalog import names

def availability(nodes):
    files=names(nodes,'SelfLiftH3Sampler','upscaler_model')
    return {'ready':'SelfLiftH3Sampler' in nodes,'upscalers':[f for f in files if f!='none'],
            'source':'https://github.com/facok/comfyui-SelfLift','experimental':True}

def attach(graph,saved,nodes):
    if not saved.get('selflift'):return
    if nodes is not None and 'SelfLiftH3Sampler' not in nodes:
        raise ValueError('Install the optional SelfLift node in Engine settings → Connection, then restart ComfyUI.')
    files=availability(nodes or {})['upscalers']
    upscaler=next((f for f in files if 'h3' in f.lower()),'none')
    positive=graph['126']['inputs']['conditioning']
    latent=graph['125']['inputs'].get('latent_image',['136',1])
    graph['dc_selflift_negative']={'class_type':'ConditioningZeroOut','inputs':{'conditioning':positive}}
    graph['125']={'class_type':'SelfLiftH3Sampler','inputs':dict(
        model=graph['126']['inputs']['model'],positive=positive,negative=['dc_selflift_negative',0],
        vae=['119',0],latent_image=latent,sampler=['123',0],sigmas=['124',0],
        seed=saved['seed'],cfg=1.0,transition_step=4,lowres_scale=.5,
        rho=0.0 if upscaler!='none' else .6,w_min=1.0,w_max=1.0,
        upscaler_model=upscaler,highres_tiling=False,upscaler_unload=True)}
    graph['123']['inputs']['sampler_name']='euler'
