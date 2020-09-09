import unittest
import sqlfs


class TestOperations(unittest.TestCase):

    def setUp(self):
        self.ops = sqlfs.Operations(':memory:', key='unused')
