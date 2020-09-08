import unittest
import tempfile
import shutil
import os
import sqlfs


class TestDatabase:

    def test_init_tables(self):
        self.assertEqual(1, self.db.conn.execute('SELECT COUNT(*) FROM inode').fetchone()[0])
        self.assertEqual(2, self.db.conn.execute('SELECT COUNT(*) FROM link').fetchone()[0])
        self.assertEqual(0, self.db.conn.execute('SELECT COUNT(*) FROM block').fetchone()[0])


class TestOperations:
    pass


class TestDatabaseMemory(TestDatabase, unittest.TestCase):

    def setUp(self):
        self.db = sqlfs.Database(':memory:')


class TestDatabaseFile(TestDatabase, unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        db_path = os.path.join(self.tmpdir, 'fs.db')
        self.db = sqlfs.Database(db_path)

    def tearDown(self):
        shutil.rmtree(self.tmpdir)


class TestOperationsMemory(TestOperations, unittest.TestCase):

    def setUp(self):
        self.ops = sqlfs.Operations(':memory:', key='unused')


class TestOperationsFile(TestOperations, unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        db_path = os.path.join(self.tmpdir, 'fs.db')
        self.ops = sqlfs.Operations(db_path, key='unused')

    def tearDown(self):
        shutil.rmtree(self.tmpdir)
