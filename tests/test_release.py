"""Packaging invariants; all checks are CPU-only."""
import os,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import AsyncMock,patch
from types import SimpleNamespace
from openframe import paths,engine_connection as ec,engine_config as cfg

class ReleaseTests(unittest.IsolatedAsyncioTestCase):
 def test_frozen_user_data_never_uses_extraction_directory(self):
  with tempfile.TemporaryDirectory() as tmp,patch.object(sys,'frozen',True,create=True),patch.dict(os.environ,{},clear=True),patch.object(Path,'home',return_value=Path(tmp)):
   for system,folder in [('win32','DirectorsCut'),('darwin','DirectorsCut'),('linux','directors-cut')]:
    with self.subTest(system=system),patch.object(sys,'platform',system):
     result=paths.user_data_root();self.assertTrue(result.is_relative_to(Path(tmp)));self.assertEqual(result.name,folder);self.assertNotEqual(result,paths.RESOURCE_ROOT)
 def test_explicit_data_override_survives_binary_location(self):
  with tempfile.TemporaryDirectory() as tmp,patch.dict(os.environ,{'OPENFRAME_DATA':tmp}):self.assertEqual(paths.user_data_root(),Path(tmp).resolve())
 async def test_frozen_proxy_dispatches_to_same_executable_without_python_flag(self):
  with tempfile.TemporaryDirectory() as tmp:
   connection=ec.Connection();process=SimpleNamespace(returncode=None,terminate=lambda:None,wait=AsyncMock(),kill=lambda:None)
   with patch.object(cfg,'ROOT',Path(tmp)),patch.object(sys,'frozen',True,create=True),patch.object(ec.asyncio,'create_subprocess_exec',new=AsyncMock(return_value=process)) as spawn,patch.object(connection,'proxy_ready',new=AsyncMock(return_value=True)):
    connection.process,connection.log,_=await connection.start_proxy({'comfy_url':'http://127.0.0.1:9234'})
    self.assertEqual(spawn.call_args.args[:3],(sys.executable,'--internal-proxy','run'));self.assertNotIn('-c',spawn.call_args.args)
   await connection.close()
