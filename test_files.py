import files
import os, os.path
import tempfile
import unittest


class TestMetaFile(unittest.TestCase):

    def test_dots(self):
        # The name starts with a dot, has no other dots, has length > 1.
        self.assertEqual(files.META_FILE.rfind('.'), 0)
        self.assertTrue(len(files.META_FILE) > 1)

    def test_does_not_contain_path_separator(self):
        self.assertEqual(files.META_FILE.find(os.sep), -1)


class TestHashFileTree(unittest.TestCase):

    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp_dir.cleanup)

    def set_tree(self, tree, root_dir):
        """
        Create tree in root_dir.

        Keys are elements in the directory.
        If a value is a bytes object a file is created with that content.
        Else a directory is created. The value is the tree for that directory.
        """
        for name, value in tree.items():
            path = os.path.join(root_dir, name)
            if isinstance(value, bytes):
                with open(path, 'xb') as f:
                    f.write(value)
            else:
                os.mkdir(path)
                self.set_tree(value, path)

    def set_tmp_dir_tree(self, tree):
        self.set_tree(tree, self.tmp_dir.name)

    def check(self, expected):
        self.assertEqual(files.hash_file_tree(self.tmp_dir.name), expected)

    def test_empty(self):
        self.set_tmp_dir_tree({})
        self.check({})

    def test_only_meta_file(self):
        tree = {}
        tree[files.META_FILE] = b'hello\n'
        self.set_tmp_dir_tree(tree)
        self.check({})

    def test_only_meta_dir(self):
        tree = {}
        tree[files.META_FILE] = {
            'hello': {
                'world': 'test'.encode('utf-8'),
            },
        }
        self.set_tmp_dir_tree(tree)
        self.check({})

    def test_files_and_dirs(self):
        tree = {
            files.META_FILE: 'ignore me'.encode('utf-8'),
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
        self.set_tmp_dir_tree(tree)

        expected = {
            'upcoming': files.hash_bytes(tree['upcoming']),
            'projects/zero': files.hash_bytes(tree['projects']['zero']),
            'projects/kitchen': files.hash_bytes(tree['projects']['kitchen']),
            'projects/bike/diagram': files.hash_bytes(tree['projects']['bike']['diagram']),
            'projects/bike/checklist': files.hash_bytes(tree['projects']['bike']['checklist']),
            'projects/charles/robert': files.hash_bytes(tree['projects']['charles']['robert']),
            'password': files.hash_bytes(tree['password']),
            'diary': files.hash_bytes(tree['diary']),
            'photos/summer/beach': files.hash_bytes(tree['photos']['summer']['beach']),
            'photos/summer/hotel': files.hash_bytes(tree['photos']['summer']['hotel']),
        }

        self.check(expected)
