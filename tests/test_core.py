import json
from pathlib import Path
import tempfile
import unittest

from PIL import Image

from openframe.provider import build_graph
from openframe.storage import Store


class ProjectTests(unittest.TestCase):
    def setUp(self):
        test_root = Path(__file__).resolve().parent.parent / '.runtime' / 'tests'
        test_root.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=test_root)
        self.addCleanup(self.temp.cleanup)
        self.store = Store(self.temp.name)
        self.project = self.store.create('First Light / Opening')
        self.shot = self.store.add_shot(self.project)

    def test_reopen_preserves_prompt_and_previous_shots(self):
        self.shot['prompt'] = 'A misty lake at sunrise.'
        self.store.save(self.project)
        self.store.add_shot(self.project)
        reopened = Store(self.temp.name).load(self.project['id'])
        self.assertEqual(reopened['shots'][0]['prompt'], 'A misty lake at sunrise.')
        self.assertEqual(len(reopened['shots']), 2)

    def test_path_escape_is_rejected(self):
        for value in ['../escape', 'C:/outside', '..\\escape']:
            with self.assertRaises(ValueError):
                self.store.folder(value)
        with self.assertRaises(ValueError):
            self.store.file(self.project['id'], '../../outside.png')


if __name__ == '__main__':
    unittest.main()
