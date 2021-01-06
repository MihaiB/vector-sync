import commands
import main
import unittest, unittest.mock


class TestParseArgs(unittest.TestCase):

    @unittest.mock.patch('sys.stderr', spec_set=True)   # silence test output
    def test_no_args(self, stderr):
        with self.assertRaises(SystemExit):
            main.parse_args([])

    def test_init(self):
        args = main.parse_args(['init', 'my-tree-id'])
        self.assertIs(args.func, commands.init)
        self.assertEqual(args.id, 'my-tree-id')

    def test_sync(self):
        args = main.parse_args(['sync', 'path/to/other'])
        self.assertIs(args.func, commands.sync)
        self.assertEqual(args.path, 'path/to/other')
