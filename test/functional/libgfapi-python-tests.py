#  Copyright (c) 2012-2015 Red Hat, Inc.
#  This file is part of libgfapi-python project
#  (http://review.gluster.org/#/q/project:libgfapi-python)
#  which is a subproject of GlusterFS ( www.gluster.org)
#
#  This file is licensed to you under your choice of the GNU Lesser
#  General Public License, version 3 or any later version (LGPLv3 or
#  later), or the GNU General Public License, version 2 (GPLv2), in all
#  cases as published by the Free Software Foundation.


import unittest
import os
import types
import errno

from gluster import gfapi
from test import get_test_config
from ConfigParser import NoSectionError, NoOptionError

config = get_test_config()
if config:
    try:
        HOST = config.get('func_test', 'gfs_host')
    except (NoSectionError, NoOptionError):
        HOST = 'gfshost'
    try:
        VOLNAME = config.get('func_test', 'gfs_volname')
    except (NoSectionError, NoOptionError):
        VOLNAME = 'test'
else:
    HOST = 'gfshost'
    VOLNAME = 'test'


class BinFileOpsTest(unittest.TestCase):

    vol = None
    path = None
    data = None

    @classmethod
    def setUpClass(cls):
        cls.vol = gfapi.Volume(HOST, VOLNAME)
        cls.vol.set_logging("/dev/null", 7)
        ret = cls.vol.mount()
        if ret == 0:
            # Cleanup volume
            cls.vol.rmtree("/", ignore_errors=True)
        else:
            raise Exception("Initializing volume %s:%s failed." %
                            (HOST, VOLNAME))

    @classmethod
    def tearDownClass(cls):
        cls.vol.rmtree("/", ignore_errors=True)
        cls.vol = None

    def setUp(self):
        self.data = bytearray([(k % 128) for k in range(0, 1024)])
        self.path = self._testMethodName + ".io"
        with self.vol.open(self.path, os.O_CREAT | os.O_WRONLY | os.O_EXCL,
                           0644) as fd:
            fd.write(self.data)

    def test_bin_open_and_read(self):
        with self.vol.open(self.path, os.O_RDONLY) as fd:
            self.assertTrue(isinstance(fd, gfapi.File))
            buf = fd.read(len(self.data))
            self.assertFalse(isinstance(buf, types.IntType))
            self.assertEqual(buf, self.data)


class FileOpsTest(unittest.TestCase):

    vol = None
    path = None
    data = None

    @classmethod
    def setUpClass(cls):
        cls.vol = gfapi.Volume(HOST, VOLNAME)
        cls.vol.set_logging("/dev/null", 7)
        ret = cls.vol.mount()
        if ret == 0:
            # Cleanup volume
            cls.vol.rmtree("/", ignore_errors=True)
        else:
            raise Exception("Initializing volume %s:%s failed." %
                            (HOST, VOLNAME))

    @classmethod
    def tearDownClass(cls):
        cls.vol.rmtree("/", ignore_errors=True)
        cls.vol = None

    def setUp(self):
        self.data = "gluster is awesome"
        self.path = self._testMethodName + ".io"
        with self.vol.open(self.path, os.O_CREAT | os.O_WRONLY | os.O_EXCL,
                           0644) as fd:
            rc = fd.write(self.data)
            self.assertEqual(rc, len(self.data))
            ret = fd.fsync()
            self.assertEqual(ret, 0)
            self.assertEqual(fd.originalpath, self.path)

    def tearDown(self):
        self.path = None
        self.data = None

    def test_open_and_read(self):
        with self.vol.open(self.path, os.O_RDONLY) as fd:
            self.assertTrue(isinstance(fd, gfapi.File))
            buf = fd.read(len(self.data))
            self.assertFalse(isinstance(buf, types.IntType))
            self.assertEqual(buf.value, self.data)

    def test_open_file_not_exist(self):
        try:
            f = self.vol.open("filenotexist", os.O_WRONLY)
        except OSError as e:
            self.assertEqual(e.errno, errno.ENOENT)
        else:
            f.close()
            self.fail("Expected a OSError with errno.ENOENT")

    def test_create_file_already_exists(self):
        try:
            f = self.vol.open("newfile", os.O_CREAT)
            f.close()
            g = self.vol.open("newfile", os.O_CREAT | os.O_EXCL)
        except OSError as e:
            self.assertEqual(e.errno, errno.EEXIST)
        else:
            g.close()
            self.fail("Expected a OSError with errno.EEXIST")

    def test_write_file_dup_lseek_read(self):
        try:
            f = self.vol.open("dune", os.O_CREAT | os.O_EXCL | os.O_RDWR)
            f.write("I must not fear. Fear is the mind-killer.")
            fdup = f.dup()
            self.assertTrue(isinstance(fdup, gfapi.File))
            f.close()
            ret = fdup.lseek(0, os.SEEK_SET)
            self.assertEqual(ret, 0)

            buf = fdup.read(15)
            self.assertEqual(buf.value, "I must not fear")

            ret = fdup.lseek(29, os.SEEK_SET)
            self.assertEqual(ret, 29)

            buf = fdup.read(11)
            self.assertEqual(buf.value, "mind-killer")

            fdup.close()
        except OSError as e:
            self.fail(e.message)

    def test_chmod(self):
        stat = self.vol.stat(self.path)
        orig_mode = oct(stat.st_mode & 0777)
        self.assertEqual(orig_mode, '0644L')
        ret = self.vol.chmod(self.path, 0600)
        self.assertEqual(ret, 0)
        stat = self.vol.stat(self.path)
        new_mode = oct(stat.st_mode & 0777)
        self.assertEqual(new_mode, '0600L')

    def test_exists(self):
        e = self.vol.exists(self.path)
        self.assertTrue(e)

    def test_exists_false(self):
        e = self.vol.exists("filedoesnotexist")
        self.assertFalse(e)

    def test_getsize(self):
        size = self.vol.getsize(self.path)
        self.assertEqual(size, len(self.data))

    def test_isfile(self):
        isfile = self.vol.isfile(self.path)
        self.assertTrue(isfile)

    def test_isdir_false(self):
        isdir = self.vol.isdir(self.path)
        self.assertFalse(isdir)

    def test_symlink(self):
        link = self._testMethodName + ".link"
        ret = self.vol.symlink(self.path, link)
        self.assertEqual(ret, 0)
        islink = self.vol.islink(link)
        self.assertTrue(islink)

    def test_islink_false(self):
        islink = self.vol.islink(self.path)
        self.assertFalse(islink)

    def test_lstat(self):
        sb = self.vol.lstat(self.path)
        self.assertFalse(isinstance(sb, types.IntType))
        self.assertEqual(sb.st_size, len(self.data))

    def test_rename(self):
        newpath = self.path + ".rename"
        ret = self.vol.rename(self.path, newpath)
        self.assertEqual(ret, 0)
        self.assertRaises(OSError, self.vol.lstat, self.path)

    def test_stat(self):
        sb = self.vol.stat(self.path)
        self.assertFalse(isinstance(sb, types.IntType))
        self.assertEqual(sb.st_size, len(self.data))

    def test_unlink(self):
        ret = self.vol.unlink(self.path)
        self.assertEqual(ret, 0)
        self.assertRaises(OSError, self.vol.lstat, self.path)

    def test_xattr(self):
        key1, key2 = "hello", "world"
        ret1 = self.vol.setxattr(self.path, "trusted.key1", key1, len(key1))
        self.assertEqual(ret1, 0)
        ret2 = self.vol.setxattr(self.path, "trusted.key2", key2, len(key2))
        self.assertEqual(ret2, 0)

        xattrs = self.vol.listxattr(self.path)
        self.assertFalse(isinstance(xattrs, types.IntType))
        self.assertTrue(set(["trusted.key1", "trusted.key2"]) <= set(xattrs))

        buf = self.vol.getxattr(self.path, "trusted.key1", 32)
        self.assertFalse(isinstance(buf, types.IntType))
        self.assertEqual(buf, "hello")

        ret3 = self.vol.removexattr(self.path, "trusted.key1")
        self.assertEqual(ret3, 0)

        xattrs = self.vol.listxattr(self.path)
        self.assertFalse(isinstance(xattrs, types.IntType))
        self.assertTrue(["trusted.key1"] not in xattrs)


class DirOpsTest(unittest.TestCase):

    data = None
    dir_path = None
    testfile = None

    @classmethod
    def setUpClass(cls):
        cls.vol = gfapi.Volume(HOST, VOLNAME)
        cls.vol.set_logging("/dev/null", 7)
        cls.vol.mount()
        ret = cls.vol.mount()
        if ret == 0:
            # Cleanup volume
            cls.vol.rmtree("/", ignore_errors=True)
        else:
            raise Exception("Initializing volume %s:%s failed." %
                            (HOST, VOLNAME))
        cls.testfile = "testfile"

    @classmethod
    def tearDownClass(cls):
        cls.vol.rmtree("/", ignore_errors=True)
        cls.vol = None
        cls.testfile = None

    def setUp(self):
        self.data = "gluster is awesome"
        self.dir_path = self._testMethodName + "_dir"
        self.vol.mkdir(self.dir_path, 0755)
        for x in range(0, 3):
            f = os.path.join(self.dir_path, self.testfile + str(x))
            with self.vol.open(f, os.O_CREAT | os.O_WRONLY | os.O_EXCL,
                               0644) as fd:
                rc = fd.write(self.data)
                self.assertEqual(rc, len(self.data))
                ret = fd.fdatasync()
                self.assertEqual(ret, 0)

    def tearDown(self):
        self.dir_path = None
        self.data = None

    def test_isdir(self):
        isdir = self.vol.isdir(self.dir_path)
        self.assertTrue(isdir)

    def test_isfile_false(self):
        isfile = self.vol.isfile(self.dir_path)
        self.assertFalse(isfile)

    def test_listdir(self):
        dir_list = self.vol.listdir(self.dir_path)
        dir_list.sort()
        self.assertEqual(dir_list, ["testfile0", "testfile1", "testfile2"])

    def test_makedirs(self):
        name = self.dir_path + "/subd1/subd2/subd3"
        self.vol.makedirs(name, 0755)
        self.assertTrue(self.vol.isdir(name))

    def test_statvfs(self):
        sb = self.vol.statvfs("/")
        self.assertFalse(isinstance(sb, types.IntType))
        self.assertEqual(sb.f_namemax, 255L)
        # creating a dir, checking Total number of free inodes
        # is reduced
        self.vol.makedirs("statvfs_dir1", 0755)
        sb2 = self.vol.statvfs("/")
        self.assertTrue(sb2.f_ffree < sb.f_ffree)

    def test_rmtree(self):
        """
        by testing rmtree, we are also testing unlink and rmdir
        """
        f = os.path.join(self.dir_path, self.testfile + "1")
        self.vol.rmtree(self.dir_path, True)
        self.assertRaises(OSError, self.vol.lstat, f)
        self.assertRaises(OSError, self.vol.lstat, self.dir_path)
