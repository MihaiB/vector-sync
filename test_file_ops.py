import contextlib
import file_ops
import hashlib
import io
import os, os.path
import tempfile
import unittest, unittest.mock
import versionvectors


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


class TestHashFile(unittest.TestCase):

    def test_files(self):
        with tempfile.NamedTemporaryFile() as f:
            self.assertEqual(file_ops.hash_file(f.name), hash_bytes(b''))

        with tempfile.NamedTemporaryFile() as f:
            f.write(b'test')
            f.flush()
            self.assertEqual(file_ops.hash_file(f.name), hash_bytes(b'test'))


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
                ({'subdir': {file_ops.META_FILE: b'error'}}, 'subdir'),
                ):
            with tempfile.TemporaryDirectory() as d:
                create_files(bad_tree, d)
                bad_path = os.path.join(d, parent, file_ops.META_FILE)
                with self.assertRaisesRegex(Exception,
                        f'^forbidden tree item: {bad_path}$'):
                    file_ops.hash_file_tree(d)

    def test_error_for_empty_dirs(self):
        with tempfile.TemporaryDirectory() as d:
            create_files({'f': b'', 'nes': {'ted': {}}}, d)
            bad_path = os.path.join(d, 'nes', 'ted')
            with self.assertRaisesRegex(Exception,
                    f'^forbidden empty directory: {bad_path}$'):
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
            with open(src_path, 'x', encoding='utf-8') as f:
                pass

            dest_path = os.path.join(d, 'm', '..', 'n', 'g')
            self.assertTrue(dest_path.index('/m/../n/') > 0)
            file_ops.copy_down(src_path, dest_path)
            # ‘os.makedirs('m/../n', exist_ok=True)’ creates dirs 'm' and 'n'.
            # Ensure the code under test only creates 'n'.
            self.assertEqual(set(os.listdir(d)), {'f', 'n'})


class TestInitFileTree(unittest.TestCase):

    def test_dir_does_not_exist(self):
        with tempfile.TemporaryDirectory() as d:
            bad_dirpath = os.path.join(d, 'a')
            with self.assertRaises(FileNotFoundError):
                file_ops.init_file_tree(dirpath=bad_dirpath, tree_id='A')

    def test_meta_file_exists(self):
        with tempfile.TemporaryDirectory() as d:
            meta_file_path = os.path.join(d, file_ops.META_FILE)
            with open(meta_file_path, 'x', encoding='utf-8') as f:
                pass
            with self.assertRaises(FileExistsError):
                file_ops.init_file_tree(dirpath=d, tree_id='My Tree')

    def test_init_file_tree(self):
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, 'book'), 'x', encoding='utf-8') as f:
                f.write('chapter')
            file_ops.init_file_tree(dirpath=d, tree_id='Main Library')

            got = file_ops.read_meta_data(os.path.join(d, file_ops.META_FILE))
            want = {
                'id': 'Main Library',
                'version_vector': {},
                'file_hashes': {},
            }
            self.assertEqual(got, want)


class TestReadTreeStatus(unittest.TestCase):

    def test_tree_unchanged_then_changed(self):
        tree = {
            'kitchen': {
                'sink': b'wash fruit',
                'fridge': b'store fruit',
            }
        }
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

            create_files({
                'cellar': {
                    'champagne': b'sparkling',
                },
            }, d)
            self.assertEqual(file_ops.read_tree_status(d), {
                'path': d,
                'id': md['id'],
                'pre_vv': md['version_vector'],
                'known_hashes': md['file_hashes'],
                'disk_hashes': {
                    'kitchen/sink': md['file_hashes']['kitchen/sink'],
                    'kitchen/fridge': md['file_hashes']['kitchen/fridge'],
                    'cellar/champagne': hash_bytes(b'sparkling'),
                },
                'post_vv': versionvectors.advance(md['id'],
                    md['version_vector']),
            })


class TestWriteMetaDataIfDifferent(unittest.TestCase):

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
            file_ops.write_meta_data_if_different(
                version_vector, file_hashes, ts)

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
                    'id': 'MyDir',
                    'file_hashes': {'documents': 'hash of text'},
                    'version_vector': {'Z': 12},
                }

            file_ops.write_meta_data_if_different(
                get_new_md()['version_vector'],
                get_new_md()['file_hashes'],
                get_ts())
            self.assertEqual(file_ops.read_meta_data(md_path), get_new_md())


class TestConfirmOverwriteTree(unittest.TestCase):

    def test_no_changes(self):
        for tree in (
                {},
                {
                    'fruit': {
                        'apple': b'different colors',
                        'banana': b'yellow',
                        'tomato': b'red',
                    },
                    'math': b'theorem',
                },
                ):
            with tempfile.TemporaryDirectory() as a:
                create_files(tree, a)
                file_ops.write_meta_data({
                    'id': 'A', 'version_vector': {}, 'file_hashes': {},
                }, os.path.join(a, file_ops.META_FILE))

                with tempfile.TemporaryDirectory() as b:
                    create_files(tree, b)
                    file_ops.write_meta_data({
                        'id': 'B', 'version_vector': {}, 'file_hashes': {},
                    }, os.path.join(b, file_ops.META_FILE))

                    self.assertTrue(file_ops.confirm_overwrite_tree(
                        read_from_ts=file_ops.read_tree_status(a),
                        write_to_ts=file_ops.read_tree_status(b)))

    def test_changes(self):
        read_from_tree = {
            'data': b'alternative',
            'glass': {'watch': b'face', 'window': b'pane'},
            'letter': b'private',

            'tomato': b'red',

            'Hg': b'mercury',
        }

        write_to_tree = {
            'data': b'original',
            'glass': b'water',
            'letter': {'a': b'alpha', 'b': b'beta'},

            'carrot': b'orange',

            'Hg': b'mercury',
        }

        with tempfile.TemporaryDirectory() as read_from_dir:
            create_files(read_from_tree, read_from_dir)
            file_ops.write_meta_data({
                'id': 'Pen', 'version_vector': {}, 'file_hashes': {},
            }, os.path.join(read_from_dir, file_ops.META_FILE))
            with tempfile.TemporaryDirectory() as write_to_dir:
                create_files(write_to_tree, write_to_dir)
                file_ops.write_meta_data({
                    'id': 'Paper', 'version_vector': {}, 'file_hashes': {},
                }, os.path.join(write_to_dir, file_ops.META_FILE))

                for answer, expected in {
                        '': False, 'n': False, 'x': False, 'Y': False,
                        'y': True,
                }.items():
                    with unittest.mock.patch('builtins.input', spec_set=True,
                            return_value=answer) as input_p:
                        stdout = io.StringIO()
                        with contextlib.redirect_stdout(stdout):
                            result = file_ops.confirm_overwrite_tree(
                                    read_from_ts=file_ops.read_tree_status(
                                        read_from_dir),
                                    write_to_ts=file_ops.read_tree_status(
                                        write_to_dir))
                        self.assertEqual(result, expected)
                        input_p.assert_called_once_with('Change Paper? [y/N] ')
                        self.assertEqual(stdout.getvalue(), '''• Add:
+ glass/watch
+ glass/window
+ letter
+ tomato

• Delete:
- carrot
- glass
- letter/a
- letter/b

• Overwrite:
≠ data

''')


class TestOverwriteTree(unittest.TestCase):

    def test_no_changes(self):
        for tree in (
                {},
                {
                    'fruit': {
                        'apple': b'different colors',
                        'banana': b'yellow',
                        'tomato': b'red',
                    },
                    'math': b'theorem',
                },
                ):
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

                    file_ops.overwrite_tree(
                        read_from_ts=file_ops.read_tree_status(a),
                        write_to_ts=file_ops.read_tree_status(b))

                    for p in a, b:
                        self.assertEqual(file_ops.hash_file_tree(p), hashes)
                    del p

    def test_changes(self):
        read_from_tree = {
            'data': b'alternative',
            'glass': {'watch': b'face', 'window': b'pane'},
            'letter': b'private',

            'tomato': b'red',

            'Hg': b'mercury',
        }

        write_to_tree = {
            'data': b'original',
            'glass': b'water',
            'letter': {'a': b'alpha', 'b': b'beta'},

            'carrot': b'orange',

            'Hg': b'mercury',
        }

        with tempfile.TemporaryDirectory() as read_from_dir:
            create_files(read_from_tree, read_from_dir)
            hashes = file_ops.hash_file_tree(read_from_dir)
            file_ops.write_meta_data({
                'id': 'Pen', 'version_vector': {}, 'file_hashes': {},
            }, os.path.join(read_from_dir, file_ops.META_FILE))
            with tempfile.TemporaryDirectory() as write_to_dir:
                create_files(write_to_tree, write_to_dir)
                file_ops.write_meta_data({
                    'id': 'Paper', 'version_vector': {}, 'file_hashes': {},
                }, os.path.join(write_to_dir, file_ops.META_FILE))

                file_ops.overwrite_tree(
                        read_from_ts=file_ops.read_tree_status(read_from_dir),
                        write_to_ts=file_ops.read_tree_status(write_to_dir))
                for p in read_from_dir, write_to_dir:
                    self.assertEqual(file_ops.hash_file_tree(p), hashes)
                del p


class TestSyncFileTrees(unittest.TestCase):

    def test_same_ids(self):
        md = {'id': 'MyFileTree', 'version_vector': {}, 'file_hashes': {}}
        with tempfile.TemporaryDirectory() as a:
            with tempfile.TemporaryDirectory() as b:
                for parent in a, b:
                    file_ops.write_meta_data(md,
                            os.path.join(parent, file_ops.META_FILE))
                with self.assertRaisesRegex(Exception,
                        '^Refusing to sync file trees with identical IDs.$'):
                    file_ops.sync_file_trees(a, b)

    def test_already_synchronized(self):
        tree = {
                'article': b'news\n',
                'front_page': {
                    'interview': b'dialogue',
                },
        }

        with tempfile.TemporaryDirectory() as a:
            with tempfile.TemporaryDirectory() as b:
                create_files(tree, a)
                create_files(tree, b)

                vv = {'C': 13}
                file_hashes = {
                    'article': hash_bytes(tree['article']),
                    'front_page/interview': hash_bytes(tree['front_page']['interview']),
                }

                file_ops.write_meta_data({
                    'id': 'Apricot',
                    'version_vector': vv,
                    'file_hashes': file_hashes,
                }, os.path.join(a, file_ops.META_FILE))

                file_ops.write_meta_data({
                    'id': 'Berry',
                    'version_vector': vv,
                    'file_hashes': file_hashes,
                }, os.path.join(b, file_ops.META_FILE))

                stdout = io.StringIO()
                with contextlib.redirect_stdout(stdout):
                    file_ops.sync_file_trees(a, b)
                self.assertEqual(stdout.getvalue(),
                        'Apricot and Berry are already synchronized.\n')

                self.assertEqual(file_ops.read_meta_data(
                    os.path.join(a, file_ops.META_FILE)),
                    {
                        'id': 'Apricot',
                        'version_vector': vv,
                        'file_hashes': file_hashes,
                    })
                self.assertEqual(file_ops.read_meta_data(
                    os.path.join(b, file_ops.META_FILE)),
                    {
                        'id': 'Berry',
                        'version_vector': vv,
                        'file_hashes': file_hashes,
                    })

                for x in a, b:
                    self.assertEqual(file_ops.hash_file_tree(x), file_hashes)
                del x

    def test_same_files_different_metadata(self):
        tree = {
                'article': b'news\n',
                'front_page': {
                    'interview': b'dialogue',
                },
        }

        with tempfile.TemporaryDirectory() as a:
            with tempfile.TemporaryDirectory() as b:
                create_files(tree, a)
                create_files(tree, b)

                file_hashes = {
                    'article': hash_bytes(tree['article']),
                    'front_page/interview': hash_bytes(tree['front_page']['interview']),
                }

                file_ops.write_meta_data({
                    'id': 'Apricot',
                    'version_vector': {'Grapes': 5},
                    'file_hashes': file_hashes,
                }, os.path.join(a, file_ops.META_FILE))

                file_ops.write_meta_data({
                    'id': 'Berry',
                    'version_vector': {'Tomatoes': 2},
                    'file_hashes': {'article': hash_bytes(tree['article'])},
                }, os.path.join(b, file_ops.META_FILE))

                stdout = io.StringIO()
                with contextlib.redirect_stdout(stdout):
                    file_ops.sync_file_trees(a, b)
                self.assertEqual(stdout.getvalue(),
                        'Synchronized Apricot and Berry.\n')

                vv_join = {'Grapes': 5, 'Tomatoes': 2, 'Berry': 1}

                self.assertEqual(file_ops.read_meta_data(
                    os.path.join(a, file_ops.META_FILE)),
                    {
                        'id': 'Apricot',
                        'version_vector': vv_join,
                        'file_hashes': file_hashes,
                    })
                self.assertEqual(file_ops.read_meta_data(
                    os.path.join(b, file_ops.META_FILE)),
                    {
                        'id': 'Berry',
                        'version_vector': vv_join,
                        'file_hashes': file_hashes,
                    })

                for x in a, b:
                    self.assertEqual(file_ops.hash_file_tree(x), file_hashes)
                del x

    def test_sync_changes(self):
        orig_tree = {
            'data': b'original',
            'glass': b'water',
            'letter': {'a': b'alpha', 'b': b'beta'},

            'carrot': b'orange',

            'Hg': b'mercury',
        }

        changed_tree = {
            'data': b'alternative',
            'glass': {'watch': b'face', 'window': b'pane'},
            'letter': b'private',

            'tomato': b'red',

            'Hg': b'mercury',
        }

        version_vector = {'Orig': 2, 'Changed': 4, 'Other': 7}

        def set_up(orig_dir, changed_dir):
            create_files(orig_tree, orig_dir)
            hashes = file_ops.hash_file_tree(orig_dir)
            file_ops.write_meta_data({
                'id': 'Orig',
                'version_vector': version_vector,
                'file_hashes': hashes,
            }, os.path.join(orig_dir, file_ops.META_FILE))

            create_files(changed_tree, changed_dir)
            file_ops.write_meta_data({
                'id': 'Changed',
                'version_vector': version_vector,
                'file_hashes': hashes,
            }, os.path.join(changed_dir, file_ops.META_FILE))

        def check(orig_dir, changed_dir, want_hashes):
            vv = versionvectors.advance('Changed', version_vector)

            self.assertEqual(file_ops.read_tree_status(orig_dir), {
                'path': orig_dir,
                'id': 'Orig',
                'pre_vv': vv,
                'known_hashes': want_hashes,
                'disk_hashes': want_hashes,
                'post_vv': vv,
            })
            self.assertEqual(file_ops.read_tree_status(changed_dir), {
                'path': changed_dir,
                'id': 'Changed',
                'pre_vv': vv,
                'known_hashes': want_hashes,
                'disk_hashes': want_hashes,
                'post_vv': vv,
            })

        def perform_test(*, flip_args):
            with tempfile.TemporaryDirectory() as orig_dir:
                with tempfile.TemporaryDirectory() as changed_dir:
                    set_up(orig_dir, changed_dir)
                    want_hashes = file_ops.hash_file_tree(changed_dir)
                    with unittest.mock.patch('builtins.input', spec_set=True,
                            return_value='y'):
                            with contextlib.redirect_stdout(io.StringIO()):
                                args = (orig_dir, changed_dir)
                                if flip_args:
                                    args = reversed(args)
                                file_ops.sync_file_trees(*args)
                    check(orig_dir, changed_dir, want_hashes)

        for flip in False, True:
            perform_test(flip_args=flip)
        del flip
