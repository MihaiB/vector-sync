import main
import unittest, unittest.mock


@unittest.mock.patch('sys.stderr', spec_set=True)   # silence test output
class TestParseArgs(unittest.TestCase):

    def test_no_args(self, stderr):
        with self.assertRaises(SystemExit):
            main.parse_args([])

    def test_bad_command(self, stderr):
        with self.assertRaises(SystemExit):
            main.parse_args(['bad-cmd'])

    @unittest.mock.patch('commands.init_replica')
    def test_init(self, init_replica, stderr):
        main.parse_args(['init', 'MyReplica'])
        init_replica.assert_called_once_with('MyReplica', '.')

    @unittest.mock.patch('commands.sync')
    def test_sync(self, sync, stderr):
        main.parse_args(['sync', 'path/to/other'])
        sync.assert_called_once_with('.', 'path/to/other')
