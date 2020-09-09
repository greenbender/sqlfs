import subprocess
import unittest
import tempfile
import pathlib
import stat
import sys
import os


class _TestFileSystem:
    db_name = ':memory:'

    @classmethod
    def mount(cls):
        raise NotImplementedError()

    @classmethod
    def umount(cls):
        subprocess.run(['fusermount', '-u', cls.mnt], check=True)

    @classmethod
    def setUpClass(cls):
        cls.tmp = pathlib.Path(tempfile.mkdtemp())
        cls.mnt = cls.tmp / 'fs'
        cls.mnt.mkdir()
        if cls.db_name != ':memory:':
            cls.db_path = cls.tmp / cls.db_name
        cls.mount()

    @classmethod
    def tearDownClass(cls):
        cls.umount()
        if cls.db_name != ':memory:':
            if cls.db_path.is_file():
                cls.db_path.unlink()
        cls.mnt.rmdir()
        cls.tmp.rmdir()

    def _mounted(self):
        with open('/etc/mtab') as fd:
            for line in fd:
                fsname, mnt, fstype, _ = line.split(None, 3)
                if fstype == 'fuse.sqlfs' and mnt == os.fspath(self.mnt):
                    return True
        return False

    def test_mounted(self):
        self.assertTrue(self._mounted)
        self.assertTrue(self.mnt.joinpath('.').samefile(self.mnt))
        self.assertTrue(self.mnt.joinpath('..').samefile(self.tmp))

    def test_touch(self):
        touched = self.mnt / 'touched'
        touched.touch()
        self.assertTrue(touched.is_file())
        self.assertEqual(touched.lstat().st_size, 0)

    def test_mkdir(self):
        made = self.mnt / 'made'
        made.mkdir()
        self.assertTrue(made.is_dir())
        self.assertEqual(made.lstat().st_nlink, 2)
        sub = made / 'sub'
        sub.mkdir()
        self.assertTrue(sub.is_dir())
        self.assertEqual(made.lstat().st_nlink, 3)

    def test_link(self):
        linkfirst = self.mnt / 'linkfirst'
        linkfirst.touch()
        self.assertEqual(linkfirst.lstat().st_nlink, 1)
        linksecond = self.mnt / 'linksecond'
        if hasattr(linksecond, 'link_to'):
            linkfirst.link_to(linksecond)
        else:
            os.link(linkfirst, linksecond)
        self.assertEqual(linkfirst.lstat().st_nlink, 2)
        self.assertTrue(linkfirst.samefile(linksecond))

    def test_symlink(self):
        symtgt = self.mnt / 'symtgt'
        symtgt.touch()
        symlnkrel = self.mnt / 'symlnkrel'
        symlnkrel.symlink_to(symtgt.name)
        self.assertTrue(symlnkrel.is_symlink())
        self.assertEqual(symlnkrel.lstat().st_size, len(symtgt.name))
        self.assertTrue(os.path.samestat(symlnkrel.stat(), symtgt.stat()))
        symlnkabs = self.mnt / 'symlnkabs'
        symlnkabs.symlink_to(symtgt.resolve())
        self.assertTrue(symlnkabs.is_symlink())
        self.assertEqual(symlnkabs.lstat().st_size, len(str(symtgt.resolve())))
        self.assertTrue(os.path.samestat(symlnkabs.stat(), symtgt.stat()))

    def test_mknod(self):
        fifo = self.mnt / 'fifo'
        os.mkfifo(fifo)
        self.assertTrue(stat.S_ISFIFO(fifo.stat().st_mode))
        indata = b'abcdef'
        if os.fork() == 0:
            with open(fifo, 'wb') as infd:
                infd.write(indata)
            os._exit(0)
        else:
            with open(fifo, 'rb') as outfd:
                outdata = outfd.read(6)
        self.assertEqual(indata, outdata)

    def test_readdir(self):
        reader = self.mnt / 'reader'
        reader.mkdir()
        filenames = {'one', 'two', 'three', 'four'}
        for filename in filenames:
            reader.joinpath(filename).touch()
        for entry in reader.iterdir():
            filenames.remove(entry.name)
        self.assertFalse(filenames)


class TestMemoryFileSystem(_TestFileSystem, unittest.TestCase):

    @classmethod
    def mount(cls):
        subprocess.run([sys.executable, './sqlfs', cls.mnt], check=True)


class TestPersistFileSystem(_TestFileSystem, unittest.TestCase):
    db_name = 'fs.db'

    @classmethod
    def mount(cls):
        subprocess.run([sys.executable, './sqlfs', cls.db_path, cls.mnt], check=True)

    def test_unencrypted(self):
        with open(self.db_path, 'rb') as fd:
            self.assertEqual(b'SQLite', fd.read(6))


class TestEncryptedFileSystem(_TestFileSystem, unittest.TestCase):
    db_name = 'fs.db'

    @classmethod
    def mount(cls):
        cls.db_path = cls.tmp / 'fs.db'
        subprocess.run([sys.executable, './sqlfs', '-o', 'password=insecure', cls.db_path, cls.mnt], check=True)

    def test_encrypted(self):
        with open(self.db_path, 'rb') as fd:
            self.assertNotEqual(b'SQLite', fd.read(6))
