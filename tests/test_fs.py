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
    def test_statvfs(self):
        stat0 = os.statvfs(self.mnt)
        self.mnt.joinpath('statvfs').write_bytes(b'a' * stat0.f_bsize * 2)
        stat1 = os.statvfs(self.mnt)
        self.assertEqual(stat0.f_blocks + 2, stat1.f_blocks)
        self.assertEqual(stat0.f_files + 1, stat1.f_files)

    @skipUnmounted
    def test_readdir(self):
        readdir = self.mnt / 'readdir'
        readdir.mkdir()
        filenames = {'one', 'two', 'three', 'four'}
        for filename in filenames:
            readdir.joinpath(filename).touch()
        for entry in readdir.iterdir():
            filenames.remove(entry.name)
        self.assertFalse(filenames)

    @skipUnmounted
    def test_unlink(self):
        unlinked = self.mnt / 'unlinked'
        unlinked.touch()
        self.assertTrue(unlinked.exists())
        unlinked.unlink()
        self.assertFalse(unlinked.exists())

    @skipUnmounted
    def test_access_after_unlink(self):
        accessor = self.mnt / 'accessor'
        with open(accessor, 'w') as fd:
            fd.write('abcdef')
            self.assertTrue(fd.tell(), 6)
            self.assertTrue(accessor.exists())
            accessor.unlink()
            self.assertFalse(accessor.exists())
            fd.write('ghijkl')
            self.assertEqual(fd.tell(), 12)

    @skipUnmounted
    def test_open(self):
        with self.assertRaises(FileNotFoundError):
            open(self.mnt / 'openr', 'r')
        with self.assertRaises(FileNotFoundError):
            open(self.mnt / 'openr+', 'r+')
        openw = self.mnt / 'openw'
        with open(openw, 'w') as fd:
            self.assertTrue(openw.exists())
            fd.write('abcdef')
        self.assertEqual(openw.stat().st_size, 6)
        with open(openw, 'w+') as fd:
            self.assertTrue(openw.exists())
        self.assertEqual(openw.stat().st_size, 0)
        with open(openw, 'a') as fd:
            fd.write('abcdef')
        self.assertEqual(openw.stat().st_size, 6)
        with open(openw, 'a+') as fd:
            fd.write('ghijkl')
        self.assertEqual(openw.stat().st_size, 12)
        openx = self.mnt / 'openx'
        with open(openx, 'x') as fd:
            self.assertTrue(openx.exists())
        with self.assertRaises(FileExistsError):
            open(openx, 'x')
        with self.assertRaises(FileExistsError):
            open(openx, 'x+')

    @skipUnmounted
    def test_write(self):
        bs = os.statvfs(self.mnt).f_bsize
        writer = self.mnt / 'writer'
        with open(writer, 'wb') as fd:
            fd.write(b'a' * bs)
        self.assertEqual(writer.stat().st_size, bs)
        self.assertEqual(writer.read_bytes(), b'a' * bs)
        with open(writer, 'r+b') as fd:
            fd.seek(-1, os.SEEK_END)
            fd.write(b'bbb')
        self.assertEqual(writer.stat().st_size, bs + 2)
        self.assertEqual(writer.read_bytes(), b'a' * (bs - 1) + b'bbb')
        with open(writer, 'r+b') as fd:
            fd.seek(1, os.SEEK_SET)
            fd.write(b'c' * bs)
        self.assertEqual(writer.stat().st_size, bs + 2)
        self.assertEqual(writer.read_bytes(), b'a' + b'c' * bs + b'b')

    @skipUnmounted
    def test_read(self):
        bs = os.statvfs(self.mnt).f_bsize
        reader = self.mnt / 'reader'
        reader.write_bytes(b'a' * (bs - 10) + b'b' * 10 + b'c' * 10 + b'd' * (bs - 20) + b'e' * 10 + b'f' * 10)
        with open(reader, 'rb') as fd:
            self.assertEqual(fd.read(0), b'')
            self.assertEqual(fd.read(10), b'a' * 10)
            fd.seek(bs - 11, os.SEEK_SET)
            self.assertEqual(fd.read(22), b'a' + b'b' * 10 + b'c' * 10 + b'd')
            fd.seek(bs - 1, os.SEEK_SET)
            self.assertEqual(fd.read(1), b'b')
            self.assertEqual(fd.read(1), b'c')
            fd.seek(bs - 1, os.SEEK_SET)
            self.assertEqual(fd.read(bs + 2), b'b' + b'c' * 10 + b'd' * (bs - 20) + b'e' * 10 + b'f')
            self.assertEqual(fd.read(30), b'f' * 9)
            self.assertEqual(fd.read(5), b'')

    @skipUnmounted
    def test_sparse(self):
        stat0 = os.statvfs(self.mnt)
        sparse = self.mnt / 'sparse'
        with self.assertRaises(FileNotFoundError):
            os.truncate(sparse, 50)
        sparse.touch()
        mb100 = 1024 * 1024 * 1024
        os.truncate(sparse, mb100)
        stat1 = os.statvfs(self.mnt)
        self.assertEqual(sparse.stat().st_size, mb100)
        self.assertEqual(stat0.f_blocks, stat1.f_blocks)
        self.assertEqual(stat0.f_files + 1, stat1.f_files)
        with open(sparse, 'rb') as fd:
            self.assertEqual(fd.read(10), b'\x00' * 10)


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
