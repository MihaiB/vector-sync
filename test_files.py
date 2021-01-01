import files
import os, os.path
import unittest


class TestMetaFileName(unittest.TestCase):

    def testDot(self):
        # Contains only one dot ‘.’ and it is the first character.
        self.assertEqual(files.META_FILE_NAME.rfind('.'), 0)

    def testLengthAboveOne(self):
        self.assertTrue(len(files.META_FILE_NAME) > 1)

    def testDoesNotContainPathSeparator(self):
        self.assertEqual(files.META_FILE_NAME.find(os.sep), -1)
