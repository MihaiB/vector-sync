import contextlib
import files
import io
import os, os.path
import shutil
import tempfile
import unittest
import unittest.mock


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
        tree = {
            files.META_FILE: b'hello\n',
        }
        self.set_tmp_dir_tree(tree)
        self.check({})

    def test_only_meta_dir(self):
        tree = {
            files.META_FILE: {
                'hello': {
                    'world': 'test'.encode('utf-8'),
                },
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
                    files.META_FILE: {
                        'ignored-file': 'ignored-content'.encode('utf-8'),
                    },
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


@unittest.mock.patch('os.removedirs', spec_set=True)
@unittest.mock.patch('os.listdir', spec_set=True)
@unittest.mock.patch('os.remove', spec_set=True)
class TestDeleteUp(unittest.TestCase):

    def test_no_dir(self, remove_p, listdir_p, removedirs_p):
        path = 'myfile'
        files.delete_up(path)

        remove_p.assert_called_once_with(path)
        listdir_p.assert_not_called()
        removedirs_p.assert_not_called()

    def test_dir_not_empty(self, remove_p, listdir_p, removedirs_p):
        path = 'path/to/secret.file'
        listdir_p.return_value = ['dummy.file']
        files.delete_up(path)

        remove_p.assert_called_once_with(path)
        listdir_p.assert_called_once_with('path/to')
        removedirs_p.assert_not_called()

    def test_dir_becomes_empty(self, remove_p, listdir_p, removedirs_p):
        path = 'my/other/trunk/letters'
        listdir_p.return_value = []
        files.delete_up(path)

        remove_p.assert_called_once_with(path)
        listdir_p.assert_called_once_with('my/other/trunk')
        removedirs_p.assert_called_once_with('my/other/trunk')


class TestCopyDown(unittest.TestCase):

    def setUp(self):
        makedirs_p = unittest.mock.patch('os.makedirs', spec_set=True)
        self.makedirs_mock = makedirs_p.start()
        self.addCleanup(makedirs_p.stop)

        copyfile_p = unittest.mock.patch('shutil.copyfile',
                spec_set=True)
        self.copyfile_mock = copyfile_p.start()
        self.addCleanup(copyfile_p.stop)

    def test_no_dir(self):
        src, dest = 'the/source', 'the-dest-file'
        files.copy_down(src, dest)
        self.makedirs_mock.assert_not_called()
        self.copyfile_mock.assert_called_once_with(src, dest)

    def test_with_dir(self):
        src, dest = 'my/source', 'my/dest/file'
        files.copy_down(src, dest)
        self.makedirs_mock.assert_called_once_with('my/dest', exist_ok=True)
        self.copyfile_mock.assert_called_once_with(src, dest)


class TestConfirmTreeChange(unittest.TestCase):

    @unittest.mock.patch('builtins.input', spec_set=True)
    def test_without_change(self, stdin):
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            result = files.confirm_tree_change(
                    {'delete': set(), 'copy': set()}, 'X')
        self.assertEqual(stdout.getvalue(), '')
        stdin.assert_not_called()
        self.assertEqual(result, True)

    @unittest.mock.patch('builtins.input', spec_set=True)
    def test_with_change(self, stdin):
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            files.confirm_tree_change({'delete': {'bad', 'old'},
                'copy': {'mutant', 'altered', 'hello', 'hola'}}, 'R')
        self.assertEqual(stdout.getvalue(), '''• Delete:
- bad
- old

• Copy:
+ altered
+ hello
+ hola
+ mutant

''')
        stdin.assert_called_once_with('Change R? [y/N] ')

    @unittest.mock.patch('sys.stdout', spec_set=True)   # silence output
    def test_input(self, stdout):
        tree_change = {'delete': set(), 'copy': {'a'}}
        for answer, expected in {
                '': False, 'n': False, 'x': False, 'smth': False, 'yes': False,
                'y': True, 'Y': False,
                }.items():
            with unittest.mock.patch('builtins.input', spec_set=True,
                    return_value=answer):
                confirmed = files.confirm_tree_change(tree_change, 'a-replica')
            self.assertEqual(confirmed, expected)


@unittest.mock.patch('files.copy_down', spec_set=True)
@unittest.mock.patch('files.delete_up', spec_set=True)
class TestApplyTreeChange(unittest.TestCase):

    def test_no_changes(self, delete_up_p, copy_down_p):
        files.apply_tree_change({'delete': set(), 'copy': set()},
            src='s', dest='d')
        delete_up_p.assert_not_called()
        copy_down_p.assert_not_called()

    def test_changes(self, delete_up_p, copy_down_p):
        files.apply_tree_change({
            'delete': {'bin/trash', 'rubbish'},
            'copy': {
                'news', 'report/month',
                'bowl/fruit', 'bowl/sugar', 'kitchen/cup/water',
            },
        }, src='my/src', dest='some/dest/path')
        call = unittest.mock.call

        calls = [call(x) for x in
            ('some/dest/path/bin/trash', 'some/dest/path/rubbish')]
        delete_up_p.assert_has_calls(calls, any_order=True)
        self.assertEqual(delete_up_p.call_count, len(calls))

        calls = [call(*pair) for pair in (
            ('my/src/news', 'some/dest/path/news'),
            ('my/src/report/month', 'some/dest/path/report/month'),
            ('my/src/bowl/fruit', 'some/dest/path/bowl/fruit'),
            ('my/src/bowl/sugar', 'some/dest/path/bowl/sugar'),
            ('my/src/kitchen/cup/water', 'some/dest/path/kitchen/cup/water'),
        )]
        copy_down_p.assert_has_calls(calls, any_order=True)
        self.assertEqual(copy_down_p.call_count, len(calls))
