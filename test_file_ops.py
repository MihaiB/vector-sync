import file_ops
import hashlib
import json
import os, os.path
import tempfile
import unittest


def hash_bytes(b):
    """
    Computes the hexdigest of the bytes.

    >>> hash_bytes(b'')
    'cf83e1357eefb8bdf1542850d66d8007d620e4050b5715dc83f4a921d36ce9ce47d0d13c5d85f2b0ff8318d2877eec2f63b931bd47417a81a538327af927da3e'
    >>> hash_bytes(b'hello\\n')
    'e7c22b994c59d9cf2b48e549b1e24666636045930d3da7c1acb299d1c3b7f931f94aae41edda2c2b207a36e10f8bcb8d45223e54878f5b316e7ce3b6bc019629'
    """
    h = file_ops.new_hash_obj()
    h.update(b)
    return h.hexdigest()


def create_files(tree, root_path):
    """
    Create tree in root_path.

    Keys are elements in the directory.
    If a value is a bytes object a file is created with that content.
    Else a directory is created. The value is the tree for that directory.
    """
    for name, value in tree.items():
        path = os.path.join(root_path, name)
        if isinstance(value, bytes):
            with open(path, 'xb') as f:
                f.write(value)
        else:
            os.mkdir(path)
            create_files(value, path)


class TestHashFile(unittest.TestCase):

    def test_files(self):
        with tempfile.NamedTemporaryFile() as f:
            self.assertEqual(file_ops.hash_file(f.name), hash_bytes(b''))

        with tempfile.NamedTemporaryFile() as f:
            f.write(b'test')
            f.flush()
            self.assertEqual(file_ops.hash_file(f.name), hash_bytes(b'test'))


class TestHashFileTree(unittest.TestCase):

    def test_missing_dir(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(FileNotFoundError):
                file_ops.hash_file_tree(os.path.join(d, 'subdir'))

    def test_error_for_file(self):
        with tempfile.NamedTemporaryFile() as f:
            with self.assertRaises(NotADirectoryError):
                file_ops.hash_file_tree(f.name)

    def test_error_for_extra_meta_file_descendants(self):
        for bad_tree, parent in (
                ({file_ops.META_FILE: {}}, ''),
                ({file_ops.META_FILE: {'a': b''}, 'top': b''}, ''),
                ({'subdir': {file_ops.META_FILE: b''}}, 'subdir'),
                ({'x': {'y': {file_ops.META_FILE: b'nested'}}},
                    os.path.join('x', 'y')),
                ):
            with tempfile.TemporaryDirectory() as d:
                create_files(bad_tree, d)
                bad_path = os.path.join(d, parent, file_ops.META_FILE)
                with self.assertRaisesRegex(Exception,
                        f'^forbidden tree item: {json.dumps(bad_path)}$'):
                    file_ops.hash_file_tree(d)

    def test_error_for_empty_dirs(self):
        with tempfile.TemporaryDirectory() as d:
            create_files({'f': b'', 'nes': {'ted': {}}}, d)
            bad_path = os.path.join(d, 'nes', 'ted')
            with self.assertRaisesRegex(Exception,
                    f'^forbidden empty directory: {json.dumps(bad_path)}$'):
                file_ops.hash_file_tree(d)

    def test_accepts_empty_dir(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(file_ops.hash_file_tree(d), {})

    def test_accepts_dir_with_only_metafile(self):
        with tempfile.TemporaryDirectory() as d:
            filepath = os.path.join(d, file_ops.META_FILE)
            with open(filepath, 'w', encoding='utf-8') as f:
                    pass
            self.assertEqual(file_ops.hash_file_tree(d), {})

    def test_hash_a_tree(self):
        tree = {
            file_ops.META_FILE: 'ignore me'.encode('utf-8'),
            'upcoming': 'chores\nsleep\n'.encode('utf-8'),
            'projects': {
                'zero': b'',
                'kitchen': 'tiles'.encode('utf-8'),
                'bike': {
                    'diagram': 'wheel'.encode('utf-8'),
                    'checklist': 'check'.encode('utf-8'),
                },
                'charles': {
                    'robert': 'darwin'.encode('utf-8'),
                },
            },
            'password': 'secret'.encode('utf-8'),
            'diary': 'dear diary'.encode('utf-8'),
            'photos': {
                'summer': {
                    'beach': 'sun'.encode('utf-8'),
                    'hotel': 'garden'.encode('utf-8'),
                },
            },
        }

        with tempfile.TemporaryDirectory() as d:
            create_files(tree, d)

            self.assertEqual(file_ops.hash_file_tree(d), {
                'upcoming': hash_bytes(tree['upcoming']),
                'projects/zero': hash_bytes(tree['projects']['zero']),
                'projects/kitchen': hash_bytes(tree['projects']['kitchen']),
                'projects/bike/diagram': hash_bytes(tree['projects']['bike']['diagram']),
                'projects/bike/checklist': hash_bytes(tree['projects']['bike']['checklist']),
                'projects/charles/robert': hash_bytes(tree['projects']['charles']['robert']),
                'password': hash_bytes(tree['password']),
                'diary': hash_bytes(tree['diary']),
                'photos/summer/beach': hash_bytes(tree['photos']['summer']['beach']),
                'photos/summer/hotel': hash_bytes(tree['photos']['summer']['hotel']),
            })
