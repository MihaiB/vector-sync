import contextlib
import files
import io
import itertools
import os, os.path
import shutil
import tempfile
import unittest
import unittest.mock


class TestMetaFile(unittest.TestCase):

    def testStartsWithDot(self):
        self.assertTrue(files.metaFile.startswith('.'))

    def testDoesNotEndWithDot(self):
        self.assertFalse(files.metaFile.endswith('.'))

    def testDoesNotContainPathSeparator(self):
        self.assertEqual(files.metaFile.find(os.sep), -1)


class TestGetTreeHash(unittest.TestCase):

    def setUp(self):
        self.tmpDir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpDir.cleanup)

    def setTree(self, tree, rootDir=None):
        """
        Create tree in rootDir (by default self.tmpDir.name).

        Keys are elements in the directory.
        If a value is a bytes object a file is created with that content.
        Else a directory is created. The value is the tree for that directory.
        """
        if rootDir is None:
            rootDir = self.tmpDir.name
        for name, value in tree.items():
            path = os.path.join(rootDir, name)
            if isinstance(value, bytes):
                with open(path, 'xb') as f:
                    f.write(value)
            else:
                os.mkdir(path)
                self.setTree(value, path)

    def check(self, expected):
        self.assertEqual(files.getTreeHash(self.tmpDir.name), expected)

    def testEmpty(self):
        self.setTree({})
        self.check({})

    def testOnlyMetaFile(self):
        tree = {}
        tree[files.metaFile] = b'hello\n'
        self.setTree(tree)
        self.check({})

    def testOnlyMetaDir(self):
        tree = {}
        tree[files.metaFile] = {
            'hello': {
                'world': 'test'.encode('utf-8'),
            },
        }
        self.setTree(tree)
        self.check({})

    def testFilesAndDirs(self):
        tree = {
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
        tree[files.metaFile] = 'ignore me'.encode('utf-8')
        self.setTree(tree)

        expected = {
            'upcoming': files.hashBytes(tree['upcoming']),
            'projects/zero': files.hashBytes(tree['projects']['zero']),
            'projects/kitchen': files.hashBytes(tree['projects']['kitchen']),
            'projects/bike/diagram': files.hashBytes(tree['projects']['bike']['diagram']),
            'projects/bike/checklist': files.hashBytes(tree['projects']['bike']['checklist']),
            'projects/charles/robert': files.hashBytes(tree['projects']['charles']['robert']),
            'password': files.hashBytes(tree['password']),
            'diary': files.hashBytes(tree['diary']),
            'photos/summer/beach': files.hashBytes(tree['photos']['summer']['beach']),
            'photos/summer/hotel': files.hashBytes(tree['photos']['summer']['hotel']),
        }

        self.check(expected)


@unittest.mock.patch('os.removedirs', spec_set=True)
@unittest.mock.patch('os.listdir', spec_set=True)
@unittest.mock.patch('os.remove', spec_set=True)
class TestDeleteUp(unittest.TestCase):

    def testNoDir(self, removeP, listdirP, removedirsP):
        path = 'myfile'
        files.deleteUp(path)

        removeP.assert_called_once_with(path)
        listdirP.assert_not_called()
        removedirsP.assert_not_called()

    def testDirNotEmpty(self, removeP, listdirP, removedirsP):
        path = 'path/to/secret.file'
        listdirP.return_value = ['dummy.file']
        files.deleteUp(path)

        removeP.assert_called_once_with(path)
        listdirP.assert_called_once_with('path/to')
        removedirsP.assert_not_called()

    def testDirBecomesEmpty(self, removeP, listdirP, removedirsP):
        path = 'my/other/trunk/letters'
        listdirP.return_value = []
        files.deleteUp(path)

        removeP.assert_called_once_with(path)
        listdirP.assert_called_once_with('my/other/trunk')
        removedirsP.assert_called_once_with('my/other/trunk')


class TestCopyDown(unittest.TestCase):

    def setUp(self):
        makedirsP = unittest.mock.patch('os.makedirs', spec_set=True)
        self.makedirsMock = makedirsP.start()
        self.addCleanup(makedirsP.stop)

        copyfileP = unittest.mock.patch('shutil.copyfile',
                spec_set=True)
        self.copyfileMock = copyfileP.start()
        self.addCleanup(copyfileP.stop)

    def testNoDir(self):
        src, dest = 'the/source', 'the-dest-file'
        files.copyDown(src, dest)
        self.makedirsMock.assert_not_called()
        self.copyfileMock.assert_called_once_with(src, dest)

    def testWithDir(self):
        src, dest = 'my/source', 'my/dest/file'
        files.copyDown(src, dest)
        self.makedirsMock.assert_called_once_with('my/dest', exist_ok=True)
        self.copyfileMock.assert_called_once_with(src, dest)


class TestConfirmTreeChange(unittest.TestCase):

    @unittest.mock.patch('builtins.input', spec_set=True)
    def testWithoutChange(self, stdin):
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            result = files.confirmTreeChange(
                    files.TreeChange(delete=set(), overwrite=set(), add=set()),
                    'X')
        self.assertEqual(stdout.getvalue(), '')
        stdin.assert_not_called()
        self.assertEqual(result, True)

    @unittest.mock.patch('builtins.input', spec_set=True)
    def testWithChange(self, stdin):
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            files.confirmTreeChange(files.TreeChange(delete={'bad', 'old'},
                overwrite={'mutant', 'altered'}, add={'hello', 'hola'}), 'R')
        self.assertEqual(stdout.getvalue(), '''• New files:
+ hello
+ hola

• Deleted files:
− bad
− old

• Changed files:
≠ altered
≠ mutant

''')
        stdin.assert_called_once_with('Make changes to R? [y/N] ')

    @unittest.mock.patch('sys.stdout', spec_set=True)   # silence output
    def testInput(self, stdout):
        treeChange = files.TreeChange(delete=set(), overwrite=set(), add={'a'})
        for answer, expected in {
                '': False, 'n': False, 'x': False, 'smth': False, 'yes': False,
                'y': True, 'Y': True,
                }.items():
            with unittest.mock.patch('builtins.input', spec_set=True,
                    return_value=answer):
                confirmed = files.confirmTreeChange(treeChange, 'my-replica')
            self.assertEqual(confirmed, expected)


@unittest.mock.patch('files.copyDown', spec_set=True)
@unittest.mock.patch('files.deleteUp', spec_set=True)
class TestApplyTreeChange(unittest.TestCase):

    def testNoChanges(self, deleteUpP, copyDownP):
        files.applyTreeChange(files.TreeChange(delete=set(), overwrite=set(),
            add=set()), src='s', dest='d')
        deleteUpP.assert_not_called()
        copyDownP.assert_not_called()

    def testChanges(self, deleteUpP, copyDownP):
        files.applyTreeChange(files.TreeChange(delete={'bin/trash', 'rubbish'},
                overwrite={'news', 'report/month'},
                add={'bowl/fruit', 'bowl/sugar', 'kitchen/cup/water'}),
                src='my/src', dest='some/dest/path')
        call = unittest.mock.call

        calls = list(map(call,
            ['some/dest/path/bin/trash', 'some/dest/path/rubbish']))
        deleteUpP.assert_has_calls(calls, any_order=True)
        self.assertEqual(deleteUpP.call_count, len(calls))

        calls = list(itertools.starmap(call, [
            ('my/src/news', 'some/dest/path/news'),
            ('my/src/report/month', 'some/dest/path/report/month'),
            ('my/src/bowl/fruit', 'some/dest/path/bowl/fruit'),
            ('my/src/bowl/sugar', 'some/dest/path/bowl/sugar'),
            ('my/src/kitchen/cup/water', 'some/dest/path/kitchen/cup/water'),
            ]))
        copyDownP.assert_has_calls(calls, any_order=True)
        self.assertEqual(copyDownP.call_count, len(calls))
