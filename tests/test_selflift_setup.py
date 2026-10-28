import hashlib,io,json,tempfile,unittest,zipfile
from pathlib import Path
from unittest.mock import patch
from openframe import video,selflift,node_setup

class SelfLiftSetupTests(unittest.TestCase):
    def test_selflift_is_opt_in_and_preserves_model_references_audio_and_size(self):
        nodes={'SelfLiftH3Sampler':{'input':{'required':{'upscaler_model':[['none','h3_upscaler.safetensors']]}}}}
        for recipe in ['original','vsa','fast-omni']:
            normal=video.settings(dict(video_preset=recipe,prompt='Keep <Picture 1> invisible.',ratio='16:9',megapixels=.4,seed=12))
            graph,_=video.build_graph(normal,'test',nodes)
            self.assertEqual(graph['125']['class_type'],'SamplerCustomAdvanced')
            enhanced=video.settings({**normal,'selflift':True})
            changed,_=video.build_graph(enhanced,'test',nodes)
            self.assertEqual(changed['125']['class_type'],'SelfLiftH3Sampler')
            self.assertEqual(changed['125']['inputs']['model'],video.template(recipe)['126']['inputs']['model'])
            self.assertEqual(changed['136'],graph['136'])
            self.assertEqual(changed['121']['inputs']['samples'],['125',0])
            self.assertEqual(changed['122']['inputs']['samples'],['125',0])
            self.assertEqual(changed['124']['inputs']['steps'],8)
            self.assertEqual(changed['123']['inputs']['sampler_name'],'euler')
            self.assertEqual(changed['125']['inputs']['transition_step'],4)
            self.assertEqual(changed['125']['inputs']['rho'],0)
    def test_missing_node_is_actionable_and_no_upscaler_uses_pixel_anchor(self):
        data=video.settings(dict(prompt='A person waits.',selflift=True,seed=1))
        with self.assertRaisesRegex(ValueError,'Install the optional SelfLift'):video.build_graph(data,'test',{})
        graph,_=video.build_graph(data,'test',{'SelfLiftH3Sampler':{}})
        self.assertEqual(graph['125']['inputs']['upscaler_model'],'none')
        self.assertEqual(graph['125']['inputs']['rho'],.6)
        with self.assertRaises(ValueError):video.settings(dict(selflift='yes'))
    def test_node_archive_rejects_path_traversal(self):
        data=io.BytesIO()
        with zipfile.ZipFile(data,'w') as z:z.writestr('pack/../../escape.py','bad')
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaises(ValueError):node_setup.unpack(data.getvalue(),Path(folder))
    def test_environment_and_existing_node_discovery_do_not_fall_back_to_app_python(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)/'ComfyUI';root.mkdir();(root/'main.py').touch()
            settings={'comfy_root':str(root),'comfy_url':'http://127.0.0.1:8188'}
            with patch.object(node_setup.cfg,'current',return_value=settings):
                with self.assertRaisesRegex(ValueError,'Python was not found'):node_setup.engine_paths()
                python=root/'.venv/bin/python';python.parent.mkdir(parents=True);python.touch()
                self.assertEqual(node_setup.engine_paths(),(root,python))
                target=root/'custom_nodes/comfyui-selflift';target.mkdir(parents=True)
                pack=next(p for p in node_setup.PACKS if p['id']=='selflift')
                self.assertEqual(node_setup.installed_directory(root,pack),target)
                settings['comfy_url']='http://192.168.1.9:8188'
                with self.assertRaisesRegex(ValueError,'this PC only'):node_setup.engine_paths()

if __name__=='__main__':unittest.main()
