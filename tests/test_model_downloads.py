import hashlib,os,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from openframe import model_downloads as md
class Content:
 def __init__(self,data):self.data=data
 async def iter_chunked(self,_):yield self.data
class Response:
 def __init__(self,data,offset,total):
  self.status=206 if offset else 200;self.headers={'Content-Range':f'bytes {offset}-{total-1}/{total}'};self.content=Content(data[offset:])
 def raise_for_status(self):pass
 async def __aenter__(self):return self
 async def __aexit__(self,*_):pass
class Session:
 def __init__(self,data):self.data=data;self.headers=[];self.urls=[]
 async def __aenter__(self):return self
 async def __aexit__(self,*_):pass
 def get(self,url,headers):
  self.urls.append(url);self.headers.append(headers);offset=int(headers.get('Range','bytes=0-').split('=')[1].split('-')[0]);return Response(self.data,offset,len(self.data))
class DownloadTests(unittest.IsolatedAsyncioTestCase):
 async def asyncSetUp(self):
  self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name);(self.root/'models').mkdir()
  self.env=patch.dict(os.environ,{'OPENFRAME_COMFY_ROOT':str(self.root),'OPENFRAME_MODELS_DIR':str(self.root/'models'),'OPENFRAME_COMFY_URL':'http://127.0.0.1:8188'});self.env.start()
  self.row={'id':'test','filename':'model.safetensors','folder':'diffusion_models','repo':'Comfy-Org/test','path':'model.safetensors','size':4,'sha256':hashlib.sha256(b'abcd').hexdigest()}
  self.allow=patch.dict(md.BY_ID,{'test':self.row});self.allow.start();self.manager=md.ModelDownloads()
 async def asyncTearDown(self):await self.manager.close();self.allow.stop();self.env.stop();self.temp.cleanup()
 async def test_resume_verifies_and_publishes(self):
  self.row['revision']='verified-commit'
  path=md.destination(self.row);path.parent.mkdir();partial=path.with_name('.'+path.name+'.download.part');partial.write_bytes(b'a');session=Session(b'abcd')
  with patch.object(md.aiohttp,'ClientSession',return_value=session):
   await self.manager.start('test');await self.manager.tasks['test']
  self.assertIn('/resolve/verified-commit/model.safetensors',session.urls[0]);self.assertEqual(path.read_bytes(),b'abcd');self.assertFalse(partial.exists());self.assertEqual(session.headers,[{'Range':'bytes=1-'}]);self.assertEqual(self.manager.jobs['test']['status'],'installed')
 async def test_bad_hash_never_installs(self):
  with patch.object(md.aiohttp,'ClientSession',return_value=Session(b'xxxx')):
   await self.manager.start('test');await self.manager.tasks['test']
  self.assertFalse(md.destination(self.row).exists());self.assertEqual(self.manager.jobs['test']['status'],'failed')
 async def test_encoder_download_waits_for_required_vision_companion(self):
  companion={**self.row,'id':'vision','filename':'mmproj.gguf','folder':'text_encoders'}
  self.row['dependencies']=['vision']
  with patch.dict(md.BY_ID,{'vision':companion}),patch.object(md.aiohttp,'ClientSession',return_value=Session(b'abcd')):
   await self.manager.start('test');await self.manager.tasks['test']
   self.assertEqual(self.manager.jobs['vision']['status'],'installed')
   self.assertEqual(self.manager.jobs['test']['status'],'installed')
   self.assertTrue(md.destination(companion).is_file())
 async def test_existing_encoder_is_preserved_while_adding_missing_companion(self):
  companion={**self.row,'id':'vision','filename':'mmproj.gguf','folder':'text_encoders'}
  target=md.destination(self.row);target.parent.mkdir();target.write_bytes(b'abcd');self.row['dependencies']=['vision']
  session=Session(b'abcd')
  with patch.dict(md.BY_ID,{'vision':companion}),patch.object(md.aiohttp,'ClientSession',return_value=session):
   await self.manager.start('test');await self.manager.tasks['test']
   self.assertEqual(len(session.urls),1);self.assertEqual(target.read_bytes(),b'abcd')
   self.assertEqual(self.manager.jobs['test']['status'],'installed')
 async def test_existing_file_and_unknown_id_are_preserved(self):
  path=md.destination(self.row);path.parent.mkdir();path.write_bytes(b'existing')
  with self.assertRaises(ValueError):await self.manager.start('test')
  with self.assertRaises(ValueError):await self.manager.start('https://example.com/model')
  self.assertEqual(path.read_bytes(),b'existing')
 async def test_installed_gguf_uses_gguf_loader_lists(self):
  nodes={'UnetLoaderGGUF':{'input':{'required':{'unet_name':[['models/test.gguf']]}}},'CLIPLoaderGGUF':{'input':{'required':{'clip_name':[['encoder.gguf']]}}}}
  self.assertEqual(md.installed({**self.row,'filename':'test.gguf'},nodes),'models/test.gguf')
  self.assertEqual(md.installed({**self.row,'filename':'encoder.gguf','folder':'text_encoders'},nodes),'encoder.gguf')
 async def test_destination_cannot_escape_model_folder(self):
  with self.assertRaises(ValueError):md.destination({**self.row,'filename':'../../escape.safetensors'})
if __name__=='__main__':unittest.main()
