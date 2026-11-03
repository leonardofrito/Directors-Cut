"""CPU-only integration checks for segmented swap padding, assembly and cancellation."""
import asyncio, copy, json, shutil, tempfile, unittest, wave
from pathlib import Path
from types import SimpleNamespace
from openframe import swap_cuts
from openframe.motion_reference import run_ffmpeg
from openframe.sequence import probe
from openframe.provider import GenerationCancelled

class CutSwapTest(unittest.IsolatedAsyncioTestCase):
    async def test_regenerate_one_cut_preserves_original_and_deduplicates(self):
        await self.check_regenerate_recipe(False)

    async def test_regenerate_selflift_cut(self):
        await self.check_regenerate_recipe(True)

    async def test_queue_multiple_cut_revisions(self):
        await self.check_regenerate_recipe(True,queue_more=True)

    async def check_regenerate_recipe(self,selflift,queue_more=False):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);(root/'shots/shot').mkdir(parents=True);parts=[]
            workflow={'129':{'class_type':'RandomNoise','inputs':{'noise_seed':7}},'92':{'inputs':{'filename_prefix':'old'}},'136':{'inputs':{'prompt':'Original cut direction'}}}
            if selflift:
                del workflow['129'];workflow['125']={'class_type':'SelfLiftH3Sampler','inputs':{'seed':7}}
            for i in range(1,4):
                prefix=f'shots/shot/old.part{i:02}'
                part=dict(index=i,workflow=prefix+'.json',output=prefix+'.mp4',generated=prefix+'.raw.mp4',status='succeeded',frames=96,generation_frames=107,start_frame=(i-1)*96,end_frame=i*96)
                (root/part['workflow']).write_text(json.dumps(workflow));(root/part['output']).write_bytes(('cut'+str(i)).encode());(root/part['generated']).write_bytes(('raw'+str(i)).encode());parts.append(part)
            (root/'shots/shot/old.json').write_text(json.dumps(workflow))
            original=dict(id='old',number=1,status='succeeded',workflow='shots/shot/old.json',file='old.mp4',settings={},swap_segments=parts)
            project={'shots':[{'id':'shot','studio_app':'second-take','drafts':[original]}]}
            store=SimpleNamespace(load=lambda pid:copy.deepcopy(project),shot=lambda p,sid:p['shots'][0],file=lambda pid,path:root/path,save=lambda p:project.update(p))
            studio=SimpleNamespace(store=store,queue=asyncio.Queue(),queue_serial=0)
            async def body():return dict(index=2,seed=42,prompt='Corrected cut direction',request_id='one-cut-test')
            request=SimpleNamespace(app={'studio':studio},match_info=dict(project='test',shot='shot',draft='old'),json=body)
            response=await swap_cuts.regenerate(request);created=json.loads(response.text)
            self.assertEqual([p['status'] for p in created['swap_segments']],['succeeded','queued','succeeded'])
            self.assertEqual(json.loads((root/created['swap_segments'][1]['workflow']).read_text())['125' if selflift else '129']['inputs']['seed' if selflift else 'noise_seed'],42)
            for i in (0,2):self.assertEqual((root/created['swap_segments'][i]['output']).read_bytes(),(root/parts[i]['output']).read_bytes())
            self.assertEqual(json.loads((root/created['swap_segments'][1]['workflow']).read_text())['136']['inputs']['prompt'],'Corrected cut direction')
            self.assertEqual(json.loads((root/parts[1]['workflow']).read_text())['136']['inputs']['prompt'],'Original cut direction')
            self.assertEqual((root/parts[1]['output']).read_bytes(),b'cut2');self.assertEqual(studio.queue.qsize(),1)
            again=json.loads((await swap_cuts.regenerate(request)).text);self.assertEqual(again['id'],created['id']);self.assertEqual(studio.queue.qsize(),1)
            if queue_more:
                async def another_body():return dict(index=1,seed=43,prompt='Another queued cut',request_id='second-cut-test')
                request.json=another_body
                second=json.loads((await swap_cuts.regenerate(request)).text)
                self.assertEqual(studio.queue.qsize(),2)
                self.assertNotEqual(second['id'],created['id'])
                self.assertEqual(second['swap_segments'][0]['status'],'queued')
                details=json.loads((await swap_cuts.describe(request)).text)
                self.assertEqual([len(p['versions']) for p in details['parts']],[2,2,1])
                self.assertEqual(details['parts'][1]['versions'][-1]['status'],'queued')
                self.assertEqual(original['swap_segments'][1]['status'],'succeeded')
                return
            # Simulate the one completed inference, then choose that version for assembly.
            completed=project['shots'][0]['drafts'][-1];completed['status']='succeeded';completed['swap_segments'][1]['status']='succeeded'
            (root/completed['swap_segments'][1]['output']).write_bytes(b'new-cut2')
            details=json.loads((await swap_cuts.describe(request)).text)
            self.assertEqual([len(p['versions']) for p in details['parts']],[1,2,1])
            self.assertEqual(details['parts'][1]['versions'][1]['prompt'],'Corrected cut direction')
            async def finish_body():return dict(finish=True,choices={'2':completed['id']},request_id='finish-test')
            request.json=finish_body
            joined=json.loads((await swap_cuts.regenerate(request)).text)
            self.assertTrue(all(p['status']=='succeeded' for p in joined['swap_segments']))
            self.assertEqual((root/joined['swap_segments'][1]['output']).read_bytes(),b'new-cut2')
            self.assertEqual((root/joined['swap_segments'][0]['output']).read_bytes(),b'cut1')
            self.assertEqual(studio.queue.qsize(),2)
            response=await swap_cuts.describe(request)
            self.assertEqual(len(json.loads(response.text)['parts'][1]['versions']),2)
            text='Use @hero with @video1 and @audio1. Leave @unknown alone.'
            compiled=swap_cuts.compiled_prompt(text,['hero'])
            self.assertEqual(compiled,'Use <Picture 1> with <Video 1> and <Audio 1>. Leave @unknown alone.')
            self.assertEqual(swap_cuts.editable_prompt(compiled,['hero']),text)
    def test_compact_appearance_graph(self):
        from unittest.mock import patch
        from openframe import video_prompt
        graph={'136':{'inputs':{'prompt':'Replace original A with <Picture 1>.'}},'h3_reference_0':{'class_type':'LoadImage','inputs':{'image':'a.png'}}}
        status=dict(ready=True,vision=True,default='vision',files=['vision'])
        with patch.object(video_prompt,'availability',return_value=status):
            self.assertTrue(video_prompt.attach_swap_appearances(graph,'Replace original A with <Picture 1>.',dict(reference_ids=['a'],swap_roles=['character'],swap_people_map={'p1':'a'}),{}))
        self.assertEqual(graph['dc_swap_look_0']['inputs']['max_length'],128)
        self.assertEqual(graph['136']['inputs']['prompt'],['dc_swap_compact_prompt',0])
        self.assertEqual(swap_cuts.cut_prompt(graph),'Replace original A with <Picture 1>.')
        self.assertNotIn('dc_video_full',graph)

    def test_legacy_environment_removed(self):
        graph={'136':{'inputs':{'prompt':['dc_swap_bg_prompt',0],'ref_images.ref_image_0':['a',0],'ref_images.ref_image_1':['b',0],'ref_images.ref_image_2':['bank',0]}},'dc_swap_bg_full':{'inputs':{'string_a':'Replace the setting with a bank.\nPer-shot cast placement:\nPerson one is foreground.\nThis input is one shot.'}},'dc_swap_bg_fit':{'inputs':{'image':['bank',0]}}}
        swap_cuts.remove_legacy_environment(graph,2)
        self.assertFalse(any(k.startswith('dc_swap_bg_') for k in graph))
        self.assertEqual(len([k for k in graph['136']['inputs'] if k.startswith('ref_images.')]),2)
        prompt=graph['136']['inputs']['prompt']
        self.assertIn('Preserve the original setting',prompt)
        self.assertIn('Person one is foreground.',prompt)
        self.assertNotIn('bank',prompt)
        self.assertNotIn('<Picture 3>',prompt)

    async def test_detect_pad_resume_assemble_and_cancel(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);src=root/'source.mp4'
            await run_ffmpeg('-f','lavfi','-i','color=c=red:s=128x128:r=24:d=5','-f','lavfi','-i','color=c=blue:s=128x128:r=24:d=2','-f','lavfi','-i','color=c=green:s=128x128:r=24:d=5','-f','lavfi','-i','sine=frequency=440:sample_rate=48000:duration=12','-filter_complex','[0:v][1:v][2:v]concat=n=3:v=1:a=0[v]','-map','[v]','-map','3:a','-c:v','libx264','-threads','2','-c:a','aac','-y',src)
            prepared={'file':'source.mp4'}
            project={'id':'test','shots':[]}
            store=SimpleNamespace(file=lambda pid,name:root/name,load=lambda pid:copy.deepcopy(project),shot=lambda p,sid:p['shots'][0])
            (root/'references/swap').mkdir(parents=True)
            parts=await swap_cuts.prepare_parts(store,project,prepared)
            self.assertEqual([(p['start_frame'],p['end_frame']) for p in parts],[(0,120),(120,168),(168,288)])
            for p in parts:
                self.assertTrue(p['id'])
                self.assertGreaterEqual(p['generation_frames'],96)
                self.assertEqual(p['generation_frames']%17,5)
                self.assertEqual((await probe(root/p['file']))['frames'],p['generation_frames'])
                with wave.open(str(root/p['audio_file']),'rb') as audio:
                    self.assertAlmostEqual(audio.getnframes()/audio.getframerate(),p['generation_frames']/24,delta=.05)
            plan=[]
            for p in parts:
                graph=f'part{p["index"]}.json';(root/graph).write_text(json.dumps({'source':str(root/p['file'])}),encoding='utf-8')
                plan.append({**p,'workflow':graph,'output':f'out{p["index"]}.mp4','generated':f'gen{p["index"]}.mp4','status':'queued'})
            draft={'id':'take','status':'running','file':'final.mp4','swap_segments':plan,'settings':{'swap_prepared':prepared}}
            project['shots']=[{'drafts':[copy.deepcopy(draft)]}]
            calls=[]
            async def generate(graph,target,update,existing_id=None):
                calls.append(existing_id)
                await update(job_id=existing_id or f'job{len(calls)}',status='running',sampling=True,sampling_step=4,sampling_steps=8)
                shutil.copy2(graph['source'],target)
            async def update(**changes):project['shots'][0]['drafts'][0].update(copy.deepcopy(changes))
            studio=SimpleNamespace(store=store,provider=SimpleNamespace(generate=generate))
            await swap_cuts.generate(studio,'test','shot',draft,update)
            info=await probe(root/'final.mp4')
            self.assertEqual(info['frames'],288);self.assertTrue(info['audio']);self.assertEqual(len(calls),3)
            resumed=copy.deepcopy(project['shots'][0]['drafts'][0]);await swap_cuts.generate(studio,'test','shot',resumed,update)
            self.assertEqual(len(calls),3) # completed pieces are reused, never regenerated
            project['shots'][0]['drafts'][0]['cancel_requested']=True
            with self.assertRaises(GenerationCancelled):await swap_cuts.generate(studio,'test','shot',resumed,update)
            self.assertEqual(len(calls),3)
            project['shots'][0]['drafts'][0]['cancel_requested']=False
            # Resume an existing in-flight job, then honor cancellation before following segments.
            interrupted=copy.deepcopy(draft);interrupted['swap_segments'][0]['job_id']='existing-job'
            async def cancel_after_update(**changes):
                await update(**changes)
                if changes.get('job_id')=='existing-job':project['shots'][0]['drafts'][0]['cancel_requested']=True
            with self.assertRaises(GenerationCancelled):await swap_cuts.generate(studio,'test','shot',interrupted,cancel_after_update)
            self.assertEqual(calls[-1],'existing-job');self.assertEqual(len(calls),4)


class HotfixSwapTest(unittest.IsolatedAsyncioTestCase):
    def test_modular_prompt_one_to_six(self):
        from openframe import character_swap
        for n in range(1,7):
            refs=[str(i) for i in range(n)]
            project={'assets':[dict(id=i,handle='actor'+i) for i in refs]}
            mapping={'p'+str(i+1):ident for i,ident in enumerate(refs)}
            people=[dict(id=k,matched=True,label='performer '+k) for k in mapping]
            text=character_swap.default_direction(project,refs,mapping,people)
            self.assertEqual(text.count('Replace the original'),n)
            self.assertEqual(text.count(character_swap.PROMPT_TAIL),1)
            self.assertIn('original video\'s background',text)
            for i in refs:self.assertIn('@actor'+i,text)
            for a in project['assets']:a['file']='actor.png'
            project['swap_sources']=[{'id':'source','duration':4,'width':32,'height':32}]
            settings=dict(reference_ids=refs,swap_source_id='source',swap_full_duration=True,swap_start=0,swap_end=4,swap_roles=['character']*n,swap_direction_enabled=False,swap_direction='')
            character_swap.resolve(project,settings)
            self.assertEqual(len(settings['prompt'].splitlines()),n+1)
            self.assertTrue(settings['swap_direction_enabled'])
            self.assertIn('<Picture '+str(n)+'>',settings['prompt'])

        with self.assertRaisesRegex(ValueError,'six'):
            character_swap.settings({'reference_ids':[str(i) for i in range(7)]})

    async def test_rtx_processes_cuts_and_joins_audio(self):
        from openframe.server import Studio
        from openframe import rtx_upscale
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);(root/'shots/s').mkdir(parents=True)
            source=root/'source.mp4'
            await run_ffmpeg('-f','lavfi','-i','color=c=red:s=32x32:r=24:d=2','-f','lavfi','-i','sine=frequency=440:duration=2','-c:v','libx264','-c:a','aac','-threads','1','-shortest','-y',source)
            original=dict(id='old',number=1,status='succeeded',file='source.mp4',settings={'studio_app':'second-take','duration':2,'prompt':'Original'},swap_segments=[{'frames':20},{'frames':28}])
            project={'id':'p','shots':[{'id':'s','mode':'video','studio_app':'second-take','title':'Swap','drafts':[original]}]}
            store=SimpleNamespace(load=lambda pid:copy.deepcopy(project),shot=lambda p,sid:p['shots'][0],file=lambda pid,path:root/path,save=lambda p:project.update(p))
            async def nodes():return {k:{} for k in rtx_upscale.REQUIRED}
            async def devices():return [dict(type='cuda',name='RTX fixture')]
            uploads=[]
            async def upload(p,refs):
                uploads.extend(ref['file'] for ref in refs)
                return [dict(comfy_image=str(root/ref['file'])) for ref in refs]
            studio=SimpleNamespace(store=store,upscale_locks={},queue=asyncio.Queue(),queue_serial=0,nodes=nodes,gpu_devices=devices,upload_references=upload)
            request=SimpleNamespace(match_info={'project':'p','shot':'s','draft':'old'})
            response=await Studio.upscale_video(studio,request);draft=json.loads(response.text)
            self.assertEqual(len(draft['swap_segments']),2);self.assertEqual(len(uploads),2)
            self.assertNotIn('source.mp4',uploads)
            self.assertEqual(draft['settings']['swap_prepared']['file'],'source.mp4')
            self.assertEqual(studio.queue.qsize(),1)
            lengths=[]
            async def generate(graph,target,update,job_id=None):
                self.assertIn('rtx_upscale',graph);self.assertFalse(any(n.get('class_type')=='TextGenerate' for n in graph.values()))
                path=graph['rtx_load']['inputs']['file'];lengths.append((await probe(path))['frames'])
                await update(status='running',stage='RTX test')
                await run_ffmpeg('-i',path,'-vf','scale=64:64','-an','-c:v','libx264','-threads','1','-y',target)
            studio.provider=SimpleNamespace(generate=generate)
            async def update(**changes):project['shots'][0]['drafts'][-1].update(copy.deepcopy(changes))
            await swap_cuts.generate(studio,'p','s',draft,update)
            result=await probe(root/draft['file'])
            self.assertEqual(lengths,[20,28]);self.assertEqual(result['frames'],48)
            self.assertEqual((result['width'],result['height']),(64,64));self.assertTrue(result['audio'])
            self.assertTrue(source.is_file())

if __name__=='__main__':unittest.main()

