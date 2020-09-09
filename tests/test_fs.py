import subprocess
import unittest
import functools
import tempfile
import pathlib
import signal
import time
import stat
import sys
import os


def skipUnmounted(func):
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        if not self.mounted():
            self.skipTest('File system not mounted')
        else:
            return func(self, *args, **kwargs)
    return wrapper


class _TestFileSystem:
    memory = True
    sqlfs_args = []
    _mounted = False

    @classmethod
    def mounted(cls):
        if cls._mounted:
            return True
        with open('/etc/mtab') as fd:
            for line in fd:
                fsname, mnt, fstype, _ = line.split(None, 3)
                if fstype == 'fuse.sqlfs' and mnt == os.fspath(cls.mnt):
                    cls._mounted = True
                    return True
        return False

    @classmethod
    def setUpClass(cls):
        cls.tmp = pathlib.Path(tempfile.mkdtemp())
        cls.mnt = cls.tmp / 'fs'
        cls.mnt.mkdir()
        cmd = [sys.executable, './sqlfs', '-f']
        cmd.extend(cls.sqlfs_args)
        if not cls.memory:
            cls.db_path = cls.tmp / 'fs.db'
            cmd.append(str(cls.db_path))
        cmd.append(str(cls.mnt))
        cls.sqlfs = subprocess.Popen(
            cmd,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        wait = 2.0
        while not cls.mounted() and wait >= 0:
            time.sleep(0.1)
            wait -= 0.1

    @classmethod
    def tearDownClass(cls):
        if cls.mounted():
            subprocess.run(['fusermount', '-u', cls.mnt])
        else:
            cls.sqlfs.send_signal(signal.SIGINT)
        cls.sqlfs.wait(timeout=10)
        if not cls.memory and cls.db_path.is_file():
            cls.db_path.unlink()
        cls.mnt.rmdir()
        cls.tmp.rmdir()

    def test_mounted(self):
        self.assertTrue(self.mounted())

    @skipUnmounted
    def test_created(self):
        self.assertTrue(self.mnt.joinpath('.').samefile(self.mnt))
        self.assertTrue(self.mnt.joinpath('..').samefile(self.tmp))

    @skipUnmounted
    def test_touch(self):
        touched = self.mnt / 'touched'
        touched.touch()
        self.assertTrue(touched.is_file())
        self.assertEqual(touched.lstat().st_size, 0)

    @skipUnmounted
    def test_mkdir(self):
        made = self.mnt / 'made'
        made.mkdir()
        self.assertTrue(made.is_dir())
        self.assertEqual(made.lstat().st_nlink, 2)
        sub = made / 'sub'
        sub.mkdir()
        self.assertTrue(sub.is_dir())
        self.assertEqual(made.lstat().st_nlink, 3)

    @skipUnmounted
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

    @skipUnmounted
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

    @skipUnmounted
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

    @skipUnmounted
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
    pass


class TestPersistFileSystem(_TestFileSystem, unittest.TestCase):
    memory = False

    @skipUnmounted
    def test_unencrypted(self):
        with open(self.db_path, 'rb') as fd:
            self.assertEqual(b'SQLite', fd.read(6))


class TestEncryptedFileSystem(_TestFileSystem, unittest.TestCase):
    memory = False
    sqlfs_args = ['-o', 'password=insecure']

    @skipUnmounted
    def test_encrypted(self):
        with open(self.db_path, 'rb') as fd:
            self.assertNotEqual(b'SQLite', fd.read(6))
