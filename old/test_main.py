import main
import unittest, unittest.mock


@unittest.mock.patch('sys.stderr', spec_set=True)   # silence test output
class TestParseArgs(unittest.TestCase):

    def testNoArgs(self, stderr):
        with self.assertRaises(SystemExit):
            main.parseArgs([])

    def testBadCommand(self, stderr):
        with self.assertRaises(SystemExit):
            main.parseArgs(['bad-cmd'])

    @unittest.mock.patch('commands.init')
    def testInit(self, init, stderr):
        main.parseArgs(['init', 'MyReplica'])
        init.assert_called_once_with('MyReplica')

    @unittest.mock.patch('commands.sync')
    def testSync(self, sync, stderr):
        main.parseArgs(['sync', 'path/to/other'])
        sync.assert_called_once_with('path/to/other')
