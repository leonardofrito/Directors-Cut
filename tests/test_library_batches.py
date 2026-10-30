import json
import tempfile
import unittest
from types import SimpleNamespace

from openframe.server import Studio
from openframe.storage import Store


class LibraryBatchTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = Store(self.temp.name)
        self.project = self.store.create('Batch fixture')
        self.project['assets'] = [dict(id=i, name=i, handle=i, source_shot_id=i) for i in ('a', 'b')]
        self.project['shots'] = [dict(id=i, mode='asset', drafts=[], reference_ids=[], prompt='') for i in ('a', 'b')]
        self.project['shots'].append(dict(id='video', mode='video', drafts=[], reference_ids=['a', 'b'], prompt='Use @a and @b'))
        self.store.save(self.project)

    async def call(self, ids):
        async def body():
            return {'ids': ids}
        request = SimpleNamespace(match_info={'project': self.project['id']}, json=body)
        return await Studio.batch_assets(SimpleNamespace(store=self.store), request)

    async def test_batch_archives_studies_and_cleans_references(self):
        await self.call(['a', 'b', 'a'])
        project = self.store.load(self.project['id'])
        self.assertEqual(project['assets'], [])
        self.assertEqual([s['id'] for s in project['shots']], ['video'])
        self.assertEqual(len(project['archived_assets']), 2)
        self.assertEqual(len(project['archived_shots']), 2)
        self.assertEqual(project['shots'][0]['reference_ids'], [])
        self.assertEqual(project['shots'][0]['prompt'], 'Use a and b')

    async def test_active_asset_aborts_entire_batch(self):
        self.project['shots'][1]['drafts'] = [dict(status='running')]
        self.store.save(self.project)
        with self.assertRaises(ValueError):
            await self.call(['a', 'b'])
        project = self.store.load(self.project['id'])
        self.assertEqual(len(project['assets']), 2)
        self.assertNotIn('archived_assets', project)

    async def test_unknown_asset_aborts_entire_batch(self):
        with self.assertRaises(ValueError):
            await self.call(['a', 'missing'])
        self.assertEqual(len(self.store.load(self.project['id'])['assets']), 2)


if __name__ == '__main__':
    unittest.main()
