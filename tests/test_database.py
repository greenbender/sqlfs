import unittest
import sqlfs


class TestDatabase(unittest.TestCase):

    def setUp(self):
        self.db = sqlfs.Database(':memory:')

    def test_init_tables(self):
        self.assertEqual(1, self.db.conn.execute('SELECT COUNT(*) FROM inode').fetchone()[0])
        self.assertEqual(2, self.db.conn.execute('SELECT COUNT(*) FROM link').fetchone()[0])
        self.assertEqual(0, self.db.conn.execute('SELECT COUNT(*) FROM block').fetchone()[0])
