#!/usr/bin/python

import fuse
from fuse import Fuse
fuse.fuse_python_api = (0,2)

from time import time

import stat    # for file properties
import os      # for filesystem modes (O_RDONLY, etc)
import errno   # for error number codes (ENOENT, etc)
import logging
from StringIO import StringIO
import nxt
import nxt.locator
import nxt.brick
from nxt.error import *


class NxtStat(fuse.Stat):
  def __init__(self):
    self.st_mode = 0
    self.st_ino = 0
    self.st_dev = 0
    self.st_nlink = 0
    self.st_uid = os.getuid()
    self.st_gid = os.getgid()
    self.st_size = 0
    self.st_atime = 0
    self.st_mtime = 0
    self.st_ctime = 0

class NxtFS(Fuse):
  """
  """

  def __init__(self, *args, **kw):
    Fuse.__init__(self, *args, **kw)
    
    logging.basicConfig(filename="nxt_fs.log",level=logging.DEBUG)
    logging.debug('Looking for a brick')

    self.file_cache = {}

    sock = nxt.locator.find_one_brick()
    logging.debug('Found %s, trying to connect..' % sock)
    self._brick = sock.connect()
    logging.info('Connected to %s' % sock)

  def getattr(self, path):
    logging.debug("getattr(%s)" % path)
    st = NxtStat()
    if path in ['/','.']:
      st.st_mode = stat.S_IFDIR | 0755
      st.st_nlink = 2
    else:
      try:
        handle,fname,size = self._brick.find_first(path[1:])
        st.st_mode = stat.S_IFREG | 0666
        st.st_nlink = 1
        st.st_size = size
      except Exception as e:
        logging.error(e)
        return -errno.ENOENT
      finally:
        try:
          self._brick.close(handle)
        except: pass
    return st

  def readdir(self, path, offset):
    logging.debug("readdir(%s)" % path)
    yield fuse.Direntry('.')
    yield fuse.Direntry('..')
    try:
      with nxt.brick.FileFinder(self._brick,'*.*') as f:
        for (fname, size) in f:
          yield fuse.Direntry(fname)
    except Exception as e:
      logging.error(e)


  def unlink(self, path):
    logging.debug("unlink(%s)"%path)
    try:
      self._brick.delete(path[1:])
    except Exception as e:
      logging.error(e)
      return -errno.ENOENT

  def mknode(self,path, mod, dev,*args):
    logging.debug("mknode(%s,...)"%path)
    try:
      handle = self._brick.open_write(path[1:],0)
      self._brick.close(handle)
    except Exception as e:
      logging.error(e)
      return -errno.ENOENT
  
  def open(self, path, flags,*args):
    logging.debug("open(%s,%i)"%(path,flags))
    buf = ""
    try:
      with nxt.brick.FileReader(self._brick, path[1:]) as f:
        for bytes in f:
          buf += bytes
        self.file_cache[path] = (StringIO(buf), flags)
    except FileNotFound as e:
      if flags & sys.O_CREATE:
        self.file_cache[path] = (StringIO(""),flags)
    except Exception as e:
      logging.error(e)
      return -errno.ENOENT
    return 0

  def write(self, path, buf, offset,*args):
    logging.debug("write(%s,...,%i)"%(path,offset))
    if path in self.file_cache:
      stio, flags = self.file_cache[path]
      stio.seek(offset)
      stio.write(buf)
      return len(buf)
    else:
      return -errno.ENOENT

  def read(self, path, size, offset,*args):
    logging.debug("read(%s,%i,%i)"%(path,size,offset))
    if path in self.file_cache:
      stio, flags = self.file_cache[path]
      stio.seek(offset)
      return stio.read(size)
    else:
      return -errno.ENOENT

  def flush(self, path,*args):
    logging.debug("flush(%s)"%path)
    try:
      if path in self.file_cache:
        stio, flags = self.file_cache[path]
        """TODO: We could optimize for append here """
        if flags & (os.O_WRONLY | os.O_RDWR | os.O_APPEND):
          with nxt.brick.FileWriter(self._brick, path[1:]) as f:
            for bytes in f:
              pass
    except Exception as e:
      logging.error(e)


  def release(self, path,*args):
    logging.debug("release(%s)"%path)
    if path in self.file_cache:
      del self.file_cache[path]

  def truncate(self, path, size,*args):
    logging.debug("truncate(%s)"%path)
    if path in self.file_cache:
      stio, flags = self.file_cache[path]
      stio.truncate(size)

  def mkdir(self, path, mode,*args):
    logging.debug("mkdir(%s)"%path)
    return 0

  def rmdir(self, path,*args):
    logging.debug("rmdir(%s)"%path)
    return 0

  def rename(self, pathfrom, pathto,*args):
    logging.debug("rename(%s,%s)"%(pathfrom,pathto))
    return 0

  def fsync(self, path, isfsyncfile,*args):
    logging.debug("fsync(%s)"%path)
    return self.flush(path)

  def getdir(self, path, *args):
    logging.debug("getdir(%s)"%path)
    return self.flush(path)



if __name__ == "__main__":
  usage=" Nxt Filesystem \n" + Fuse.fusage
  fs = NxtFS(version="%prog " + fuse.__version__,
             usage=usage,
             dash_s_do='setsingle')
  fs.multithreaded = 0
  fs.parse(errex=1)
  fs.main()

