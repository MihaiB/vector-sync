import commands
import files
import tempfile
import unittest, unittest.mock


class TestInitReplica(unittest.TestCase):

    @unittest.mock.patch('sys.stdout', spec_set=True)   # silence test output
    def test_init_replica(self, stdout):
        def check(path):
            self.assertEqual(files.read_meta_data(path), {
                'replicaID': 'FirstReplica',
                'versionVector': {},
                'hashTree': {},
            })

        with tempfile.TemporaryDirectory() as d:
            commands.init_replica('FirstReplica', d)
            check(d)
            with self.assertRaises(FileExistsError):
                commands.init_replica('A', d)
            check(d)
