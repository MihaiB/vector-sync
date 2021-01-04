import commands
import files
import tempfile
import unittest


class TestInitReplica(unittest.TestCase):

    def test_init_replica(self):
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
