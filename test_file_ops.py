import file_ops
import os, os.path
import tempfile
import unittest


class TestWriteMetaData(unittest.TestCase):

    def test_error_for_dir(self):
        with tempfile.TemporaryDirectory() as d:
            md = {'id': 'A', 'version_vector': {}, 'file_hashes': {}}
            with self.assertRaises(IsADirectoryError):
                file_ops.write_meta_data(md, d)

    def test_write_and_overwrite(self):
        with tempfile.TemporaryDirectory() as d:
            filepath = os.path.join(d, 'some-file')

            md1 = {'id': 'A', 'version_vector': {'USB': 3}, 'file_hashes': {}}
            file_ops.write_meta_data(md1, filepath)
            with open(filepath, encoding='utf-8') as f:
                self.assertEqual(f.read(), '''{
  "file_hashes": {},
  "id": "A",
  "version_vector": {
    "USB": 3
  }
}''')

            md2 = {'id': 'B', 'version_vector': {}, 'file_hashes': {'a/b': 'h'}}
            file_ops.write_meta_data(md2, filepath)
            with open(filepath, encoding='utf-8') as f:
                self.assertEqual(f.read(), '''{
  "file_hashes": {
    "a/b": "h"
  },
  "id": "B",
  "version_vector": {}
}''')


class TestReadMetaData(unittest.TestCase):

    def test_write_read(self):
        def get_md():
            return {
                'id': 'Backup',
                'file_hashes': {'path/to/file': 'the hash'},
                'version_vector': {'Computer': 3, 'Remote': 8},
            }
        with tempfile.NamedTemporaryFile() as f:
            file_ops.write_meta_data(get_md(), f.name)
            self.assertEqual(file_ops.read_meta_data(f.name), get_md())
