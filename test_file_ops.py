import contextlib
import file_ops
import hashlib
import io
import json
import os, os.path
import tempfile
import unittest, unittest.mock
import versionvectors


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

    >>> with tempfile.TemporaryDirectory() as d:
    ...     create_files([], d)
    Traceback (most recent call last):
    ValueError: create_files tree is not dict
    """
    if type(tree) is not dict:
        raise ValueError('create_files tree is not dict')

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


class TestInitFileTree(unittest.TestCase):

    def test_dir_does_not_exist(self):
        with tempfile.TemporaryDirectory() as d:
            bad_treepath = os.path.join(d, 'a')
            with self.assertRaises(FileNotFoundError):
                file_ops.init_file_tree(treepath=bad_treepath, tree_id='A')

    def test_meta_file_exists(self):
        with tempfile.TemporaryDirectory() as d:
            meta_file_path = os.path.join(d, file_ops.META_FILE)
            with open(meta_file_path, 'x', encoding='utf-8') as f:
                pass
            with self.assertRaises(FileExistsError):
                file_ops.init_file_tree(treepath=d, tree_id='My Tree')

    def test_init_file_tree(self):
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, 'book'), 'x', encoding='utf-8') as f:
                f.write('chapter')
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                file_ops.init_file_tree(treepath=d, tree_id='Main Library')

            got = file_ops.read_meta_data(os.path.join(d, file_ops.META_FILE))
            want = {
                'id': 'Main Library',
                'version_vector': {},
                'file_hashes': {},
            }
            self.assertEqual(got, want)

            self.assertEqual(stdout.getvalue(),
                    f'Initialized "Main Library" in {json.dumps(d)}.\n')


class TestDeleteUp(unittest.TestCase):

    def test_missing_path(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(FileNotFoundError):
                file_ops.delete_up(os.path.join(d, 'child'))

    def test_error_for_dir(self):
        with tempfile.TemporaryDirectory() as d:
            child_dir = os.path.join(d, 'child_dir')
            os.mkdir(child_dir)
            with open(os.path.join(d, 'file'), 'x', encoding='utf-8') as f:
                pass

            with self.assertRaises(IsADirectoryError):
                file_ops.delete_up(child_dir)

    def test_dir_not_empty(self):
        with tempfile.TemporaryDirectory() as d:
            parent = os.path.join(d, 'a', 'b', 'c')
            os.makedirs(parent)
            x_path, y_path = (os.path.join(parent, name) for name in ('x', 'y'))
            for file_path in x_path, y_path:
                with open(file_path, 'x', encoding='utf-8') as f:
                    pass

            file_ops.delete_up(x_path)
            self.assertFalse(os.path.exists(x_path))
            self.assertTrue(os.path.exists(y_path))

    def test_remove_empty_parents(self):
        with tempfile.TemporaryDirectory() as a:
            with open(os.path.join(a, 'z'), 'x', encoding='utf-8') as f:
                pass
            parent = os.path.join(a, 'b', 'c', 'd')
            os.makedirs(parent)
            child = os.path.join(parent, 'e')
            with open(child, 'x', encoding='utf-8') as f:
                pass

            self.assertEqual(set(os.listdir(a)), {'b', 'z'})
            file_ops.delete_up(child)
            self.assertEqual(os.listdir(a), ['z'])


class TestCopyDown(unittest.TestCase):

    def test_copy_to_dir(self):
        with tempfile.TemporaryDirectory() as a:
            with tempfile.TemporaryDirectory() as b:
                x_path, y_path = os.path.join(a, 'x'), os.path.join(b, 'y')

                msg = 'secret'
                with open(x_path, 'x', encoding='utf-8') as f:
                    f.write(msg)
                file_ops.copy_down(x_path, y_path)
                with open(y_path, encoding='utf-8') as f:
                    self.assertEqual(f.read(), msg)

                # test overwriting an existing file

                revised = 'untold'
                with open(x_path, 'w', encoding='utf-8') as f:
                    f.write(revised)
                file_ops.copy_down(x_path, y_path)
                with open(y_path, encoding='utf-8') as f:
                    self.assertEqual(f.read(), revised)

    def test_creates_parent_dirs(self):
        with tempfile.TemporaryDirectory() as a:
            with tempfile.TemporaryDirectory() as m:
                x_path = os.path.join(a, 'x')
                y_path = os.path.join(m, 'n', 'o', 'p', 'y')
                msg = 'nested'

                with open(x_path, 'x', encoding='utf-8') as f:
                    f.write(msg)
                file_ops.copy_down(x_path, y_path)
                with open(y_path, encoding='utf-8') as f:
                    self.assertEqual(f.read(), msg)

    def test_winding_path(self):
        with tempfile.TemporaryDirectory() as d:
            src_path = os.path.join(d, 'f')
            msg = 'story'
            with open(src_path, 'x', encoding='utf-8') as f:
                f.write(msg)

            dest_path = os.path.join(d, 'm', '..', 'n', 'g')
            self.assertTrue(dest_path.index('/m/../n/') > 0)
            file_ops.copy_down(src_path, dest_path)
            # ‘os.makedirs('m/../n', exist_ok=True)’ creates dirs 'm' and 'n'.
            # Ensure the code under test only creates 'n'.
            self.assertEqual(set(os.listdir(d)), {'f', 'n'})

            with open(os.path.realpath(dest_path), encoding='utf-8') as f:
                self.assertEqual(f.read(), msg)


class TestReadTreeStatus(unittest.TestCase):

    def test_missing_dir(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(FileNotFoundError):
                file_ops.read_tree_status(os.path.join(d, 'subdir'))

    def test_missing_meta_file(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(FileNotFoundError):
                file_ops.read_tree_status(d)

    def test_tree_unchanged(self):
        tree = {'kitchen': {'sink': b'wash fruit', 'fridge': b'store fruit'}}
        with tempfile.TemporaryDirectory() as d:
            create_files(tree, d)
            md = {
                'id': 'notepad',
                'version_vector': {'cabinet': 7},
                'file_hashes': {
                    'kitchen/sink': hash_bytes(tree['kitchen']['sink']),
                    'kitchen/fridge': hash_bytes(tree['kitchen']['fridge']),
                },
            }
            file_ops.write_meta_data(md, os.path.join(d, file_ops.META_FILE))

            self.assertEqual(file_ops.read_tree_status(d), {
                'path': d,
                'id': md['id'],
                'pre_vv': md['version_vector'],
                'known_hashes': md['file_hashes'],
                'disk_hashes': md['file_hashes'],
                'post_vv': md['version_vector'],
            })

    def test_tree_changed(self):
        tree = {'kitchen': {'sink': b'wash fruit', 'fridge': b'store fruit'}}
        with tempfile.TemporaryDirectory() as d:
            create_files(tree, d)
            md = {
                'id': 'notepad',
                'version_vector': {'cabinet': 7},
                'file_hashes': {
                    'kitchen/sink': hash_bytes(tree['kitchen']['sink']),
                    'kitchen/fridge': hash_bytes(tree['kitchen']['fridge']),
                    'cellar/champagne': hash_bytes(b'sparkling'),
                },
            }
            file_ops.write_meta_data(md, os.path.join(d, file_ops.META_FILE))

            self.assertEqual(file_ops.read_tree_status(d), {
                'path': d,
                'id': md['id'],
                'pre_vv': md['version_vector'],
                'known_hashes': md['file_hashes'],
                'disk_hashes': {
                    'kitchen/sink': hash_bytes(tree['kitchen']['sink']),
                    'kitchen/fridge': hash_bytes(tree['kitchen']['fridge']),
                },
                'post_vv': versionvectors.advance(md['id'],
                    md['version_vector']),
            })


class TestConfirm(unittest.TestCase):

    def test_yes(self):
        for answer in 'y', 'Y':
            with unittest.mock.patch('builtins.input', spec_set=True,
                    return_value=answer) as input_p:
                self.assertTrue(file_ops.confirm('Tidy up?'))
                input_p.assert_called_once_with('Tidy up? [y/N] ')

    def test_no(self):
        for answer in '', 'n', 'N', 'x':
            with unittest.mock.patch('builtins.input', spec_set=True,
                    return_value=answer):
                self.assertFalse(file_ops.confirm('some text'))


class TestEnsureMetaData(unittest.TestCase):

    def test_no_change(self):
        with tempfile.TemporaryDirectory() as d:
            version_vector = {'A': 17}
            file_hashes = {'diary': 'hash of entries'}
            ts = {
                'path': os.path.join(d, 'non', 'existent'),
                'id': 'MyTree',
                'pre_vv': version_vector,
                'known_hashes': file_hashes,
                'disk_hashes': {'shopping list': 'hash of food names'},
                'post_vv': {'B': 3},
            }
            self.assertFalse(file_ops.ensure_meta_data(
                version_vector, file_hashes, ts))

    def test_change(self):
        with tempfile.TemporaryDirectory() as d:
            md_path = os.path.join(d, file_ops.META_FILE)
            def get_old_md():
                return {
                    'id': 'MyDir',
                    'file_hashes': {'diary': 'hash of entries'},
                    'version_vector': {'A': 2},
                }
            file_ops.write_meta_data(get_old_md(), md_path)

            def get_ts():
                return {
                    'path': d,
                    'id': get_old_md()['id'],
                    'pre_vv': get_old_md()['version_vector'],
                    'known_hashes': get_old_md()['file_hashes'],
                    'disk_hashes': {},
                    'post_vv': {},
                }
            def get_new_md():
                return {
                    'id': get_old_md()['id'],
                    'file_hashes': {'documents': 'hash of text'},
                    'version_vector': {'Z': 12},
                }

            self.assertTrue(file_ops.ensure_meta_data(
                get_new_md()['version_vector'],
                get_new_md()['file_hashes'],
                get_ts()))
            self.assertEqual(file_ops.read_meta_data(md_path), get_new_md())


class TestFormatTreeChange(unittest.TestCase):

    def test_no_change(self):
        for fh in {}, {'a/b/c': 'hash', 'y/z': 'some hash'}:
            self.assertEqual('', file_ops.format_tree_change(fh, fh))

    def test_change(self):
        a = {
            'Hg': hash_bytes(b'mercury'),
            'carrot': hash_bytes(b'orange'),
            'data': hash_bytes(b'original'),
            'glass': hash_bytes(b'water'),
            'letter/a': hash_bytes(b'alpha'),
            'letter/b': hash_bytes(b'beta'),
            'new\nline': hash_bytes(b'\r\n'),
        }

        z = {
            'Hg': hash_bytes(b'mercury'),
            'data': hash_bytes(b'alternative'),
            'glass/watch': hash_bytes(b'face'),
            'glass/window': hash_bytes(b'pane'),
            'letter': hash_bytes(b'private'),
            'new\nline': hash_bytes(b'\n'),
            'tomato': hash_bytes(b'red'),
        }

        want = '''• Add:
+ "glass/watch"
+ "glass/window"
+ "letter"
+ "tomato"

• Delete:
- "carrot"
- "glass"
- "letter/a"
- "letter/b"

• Overwrite:
≠ "data"
≠ "new\\nline"'''

        self.assertEqual(file_ops.format_tree_change(a, z), want)


class TestEnsureFiles(unittest.TestCase):

    def test_no_changes(self):
        tree = {
            'fruit': {
                'apple': b'different colors',
                'tomato': b'red',
            },
        }

        with tempfile.TemporaryDirectory() as a:
            create_files(tree, a)
            hashes = file_ops.hash_file_tree(a)
            file_ops.write_meta_data({
                'id': 'A', 'version_vector': {}, 'file_hashes': {},
            }, os.path.join(a, file_ops.META_FILE))

            with tempfile.TemporaryDirectory() as b:
                create_files(tree, b)
                file_ops.write_meta_data({
                    'id': 'B', 'version_vector': {}, 'file_hashes': {},
                }, os.path.join(b, file_ops.META_FILE))

                with unittest.mock.patch('builtins.input',
                        spec_set=True) as input_p:
                    self.assertFalse(file_ops.ensure_files(
                        read_from_ts=file_ops.read_tree_status(a),
                        write_to_ts=file_ops.read_tree_status(b),
                    ))
                    input_p.assert_not_called()

                for p in a, b:
                    self.assertEqual(file_ops.hash_file_tree(p), hashes)
                del p

    @unittest.mock.patch('sys.stdout', spec_set=True)   # silence test output
    def test_cancel_changes(self, stdout):
        read_from_tree = {
            'Hg': b'mercury',
            'data': b'alternative',
            'glass': {'watch': b'face', 'window': b'pane'},
            'letter': b'private',
            'tomato': b'red',
        }

        write_to_tree = {
            'Hg': b'mercury',
            'carrot': b'orange',
            'data': b'original',
            'glass': b'water',
            'letter': {'a': b'alpha', 'b': b'beta'},
        }

        with tempfile.TemporaryDirectory() as read_from_dir:
            create_files(read_from_tree, read_from_dir)
            read_hashes = file_ops.hash_file_tree(read_from_dir)
            file_ops.write_meta_data({
                'id': 'Pen', 'version_vector': {}, 'file_hashes': {},
            }, os.path.join(read_from_dir, file_ops.META_FILE))
            with tempfile.TemporaryDirectory() as write_to_dir:
                create_files(write_to_tree, write_to_dir)
                write_hashes = file_ops.hash_file_tree(write_to_dir)
                file_ops.write_meta_data({
                    'id': 'Paper', 'version_vector': {}, 'file_hashes': {},
                }, os.path.join(write_to_dir, file_ops.META_FILE))

                read_from_ts = file_ops.read_tree_status(read_from_dir)
                write_to_ts = file_ops.read_tree_status(write_to_dir)
                with unittest.mock.patch('builtins.input', spec_set=True,
                        return_value='n') as input_p:
                    with self.assertRaisesRegex(Exception,
                            '^canceled by the user$'):
                        file_ops.ensure_files(read_from_ts=read_from_ts,
                                write_to_ts=write_to_ts)
                    input_p.assert_called_once_with('Change "Paper"? [y/N] ')

                self.assertEqual(file_ops.hash_file_tree(read_from_dir),
                        read_hashes)
                self.assertEqual(file_ops.hash_file_tree(write_to_dir),
                        write_hashes)

    def test_approve_changes(self):
        read_from_tree = {
            'Hg': b'mercury',
            'data': b'alternative',
            'glass': {'watch': b'face', 'window': b'pane'},
            'letter': b'private',
            'tomato': b'red',
        }

        write_to_tree = {
            'Hg': b'mercury',
            'carrot': b'orange',
            'data': b'original',
            'glass': b'water',
            'letter': {'a': b'alpha', 'b': b'beta'},
        }

        with tempfile.TemporaryDirectory() as read_from_dir:
            create_files(read_from_tree, read_from_dir)
            read_hashes = file_ops.hash_file_tree(read_from_dir)
            file_ops.write_meta_data({
                'id': 'Pen', 'version_vector': {}, 'file_hashes': {},
            }, os.path.join(read_from_dir, file_ops.META_FILE))
            with tempfile.TemporaryDirectory() as write_to_dir:
                create_files(write_to_tree, write_to_dir)
                write_hashes = file_ops.hash_file_tree(write_to_dir)
                file_ops.write_meta_data({
                    'id': 'Paper', 'version_vector': {}, 'file_hashes': {},
                }, os.path.join(write_to_dir, file_ops.META_FILE))

                stdout = io.StringIO()
                with contextlib.redirect_stdout(stdout):
                    with unittest.mock.patch('builtins.input', spec_set=True,
                            return_value='y') as input_p:
                        read_from_ts = file_ops.read_tree_status(read_from_dir)
                        write_to_ts = file_ops.read_tree_status(write_to_dir)
                        self.assertTrue(file_ops.ensure_files(
                            read_from_ts=read_from_ts,
                            write_to_ts=write_to_ts))
                        input_p.assert_called_once_with(
                                'Change "Paper"? [y/N] ')
                self.assertEqual(stdout.getvalue(), '''• Add:
+ "glass/watch"
+ "glass/window"
+ "letter"
+ "tomato"

• Delete:
- "carrot"
- "glass"
- "letter/a"
- "letter/b"

• Overwrite:
≠ "data"

''')

                for p in read_from_dir, write_to_dir:
                    self.assertEqual(file_ops.hash_file_tree(p), read_hashes)
                del p
