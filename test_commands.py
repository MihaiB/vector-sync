import commands
import contextlib
import files
import io
import unittest, unittest.mock


class TestInit(unittest.TestCase):

    @unittest.mock.patch('files.setMetaData', spec_set=True)
    def testInit(self, setMetaData):
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            commands.init('NewDump')
        setMetaData.assert_called_once_with(files.MetaData('NewDump', {}, {}),
                '.')
        self.assertEqual(stdout.getvalue(),
                'Initialized new empty replica NewDump.\n')


class TestSyncTree(unittest.TestCase):

    def setUp(self):
        self.syncResult = commands.SyncResult({},
                {'a/b': files.hashBytes(b'Ab'),
                    'c/d': files.hashBytes(b'e')}, 'w')
        self.syncInput = commands.SyncInput(replicaRoot='rr', replicaID='K',
                versionVector={},
                treeHash={'my/fi-le': files.hashBytes(b'm')})

        getP = unittest.mock.patch('files.getTreeChange', spec_set=True)
        self.getM = getP.start()
        self.addCleanup(getP.stop)
        self.dummyTreeChange = unittest.mock.Mock(spec_set=files.TreeChange(
            delete=set(), overwrite=set(), add=set()))
        self.getM.return_value = self.dummyTreeChange

        confirmP = unittest.mock.patch('files.confirmTreeChange',
                spec_set=True)
        self.confirmM = confirmP.start()
        self.addCleanup(confirmP.stop)

        applyP = unittest.mock.patch('files.applyTreeChange', spec_set=True)
        self.applyM = applyP.start()
        self.addCleanup(applyP.stop)

    def testNotConfirmed(self):
        self.confirmM.return_value = False

        with self.assertRaisesRegex(Exception, '^canceled$'):
            commands.syncTree(self.syncResult, self.syncInput)

        self.getM.assert_called_once_with(self.syncInput.treeHash,
                self.syncResult.treeHash)
        self.confirmM.assert_called_once_with(self.dummyTreeChange, 'K')
        self.applyM.assert_not_called()

    def testConfirmed(self):
        self.confirmM.return_value = True

        commands.syncTree(self.syncResult, self.syncInput)

        self.getM.assert_called_once_with(self.syncInput.treeHash,
                self.syncResult.treeHash)
        self.confirmM.assert_called_once_with(self.dummyTreeChange, 'K')
        self.applyM.assert_called_once_with(self.dummyTreeChange,
                src=self.syncResult.treeRoot, dest=self.syncInput.replicaRoot)


class TestSync(unittest.TestCase):

    def setUp(self):
        self.pathA, self.pathB = '.', 'some/other/b'

        sampleSyncInput = commands.SyncInput(replicaRoot='', replicaID='',
                versionVector={}, treeHash={})
        self.dummySyncInputA = unittest.mock.Mock(spec_set=sampleSyncInput)
        self.dummySyncInputA.replicaID = 'F'
        self.dummySyncInputB = unittest.mock.Mock(spec_set=sampleSyncInput)
        self.dummySyncInputB.replicaID = 'G'

        getSyncInputP = unittest.mock.patch('commands.getSyncInput',
                spec_set=True)
        self.getSyncInputM = getSyncInputP.start()
        self.addCleanup(getSyncInputP.stop)
        def getSyncInputSideEffect(path):
            return {
                    self.pathA: self.dummySyncInputA,
                    self.pathB: self.dummySyncInputB,
            }[path]
        self.getSyncInputM.side_effect = getSyncInputSideEffect

        self.dummySyncResult = unittest.mock.Mock(
                spec_set=commands.SyncResult({}, {}, ''))
        self.dummySyncResult.versionVector = {'R': 5}
        self.dummySyncResult.treeHash = {'myf': files.hashBytes(b'fmy')}
        getSyncResultP = unittest.mock.patch('commands.getSyncResult',
                spec_set=True)
        self.getSyncResultM = getSyncResultP.start()
        self.addCleanup(getSyncResultP.stop)
        self.getSyncResultM.return_value = self.dummySyncResult

        syncTreeP = unittest.mock.patch('commands.syncTree', spec_set=True)
        self.syncTreeM = syncTreeP.start()
        self.addCleanup(syncTreeP.stop)

        setMetaDataP = unittest.mock.patch('files.setMetaData', spec_set=True)
        self.setMetaDataM = setMetaDataP.start()
        self.addCleanup(setMetaDataP.stop)

    @unittest.mock.patch('sys.stdout', spec_set=True)   # silence output
    def testSync(self, stdout):
        commands.sync(self.pathB)

        calls = list(map(unittest.mock.call, [self.pathA, self.pathB]))
        self.getSyncInputM.assert_has_calls(calls, any_order=True)
        self.assertEqual(self.getSyncInputM.call_count, len(calls))

        self.getSyncResultM.assert_called_once_with(
                self.dummySyncInputA, self.dummySyncInputB)

        calls = list(map(
            lambda i: unittest.mock.call(
                syncResult=self.dummySyncResult, syncInput=i),
            [self.dummySyncInputA, self.dummySyncInputB]))
        self.syncTreeM.assert_has_calls(calls, any_order=True)
        self.assertEqual(self.syncTreeM.call_count, len(calls))

        calls = list(map(
            lambda i: unittest.mock.call(
                files.MetaData(replicaID=i.replicaID,
                    versionVector=self.dummySyncResult.versionVector,
                    treeHash=self.dummySyncResult.treeHash),
                i.replicaRoot, overwrite=True),
            [self.dummySyncInputA, self.dummySyncInputB]))
        self.setMetaDataM.assert_has_calls(calls, any_order=True)
        self.assertEqual(self.setMetaDataM.call_count, len(calls))
