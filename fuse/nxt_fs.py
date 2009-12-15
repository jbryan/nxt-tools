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


#logging.basicConfig(filename="nxt_fs.log",level=logging.DEBUG)

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
  A Fuse based file system that allows for cached random access to 
  files on a Lego(r) NXT brick.
  """

  def __init__(self, *args, **kw):
    Fuse.__init__(self, *args, **kw)

    self.file_cache = {}
    self.mounttime = int(time())

    logging.debug('Looking for a brick')

    sock = nxt.locator.find_one_brick()
    logging.debug('Found %s, trying to connect..' % sock)
    self._brick = sock.connect()
    logging.info('Connected to %s' % sock)

  def getattr(self, path, *args):
    logging.debug("getattr(%s,%s)" % (path,str(args)))
    st = NxtStat()
    st.st_atime = self.mounttime
    st.st_ctime = self.mounttime
    st.st_mtime = self.mounttime
    if path in ['/','.']:
      st.st_mode = stat.S_IFDIR | 0755
      st.st_nlink = 2
    elif path in self.file_cache:
      try:
        st.st_size = len(self.file_cache[path][0].buf)
        st.st_mode = stat.S_IFREG | 0666
        st.st_nlink = 1
      except Exception as e:
        logging.error(e)
        return -errno.ENOENT
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
          if "/" + fname not in self.file_cache:
            yield fuse.Direntry(fname)
    except Exception as e:
      logging.error(e)

    for fname in self.file_cache.keys():
      yield fuse.Direntry(fname[1:])


  def unlink(self, path):
    logging.debug("unlink(%s)"%path)
    try:
      self._brick.delete(path[1:])
    except Exception as e:
      logging.error(e)
      return -errno.ENOENT

  def mknod(self,path, mod, dev,*args):
    logging.debug("mknod(%s,...)"%path)
    if path not in self.file_cache:
      self.file_cache[path] = (StringIO(""),os.O_CREAT)
    return 0
  
  def open(self, path, flags, *mode):
    logging.debug("open(%s,%i,%s)"%(path,flags,str(mode)))
    if path not in self.file_cache:
      buf = ""
      try:
        with nxt.brick.FileReader(self._brick, path[1:]) as f:
          for bytes in f:
            buf += bytes
          self.file_cache[path] = (StringIO(buf), flags)
          logging.debug("read %i bytes" % len(buf))
      except Exception as e:
        logging.error(e)
        return -errno.ENOENT
    else:
      stio, old_flags = self.file_cache[path]
      self.file_cache[path] = (stio, old_flags | flags)
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
      logging.debug("file is open and being read")
      stio, flags = self.file_cache[path]
      stio.seek(offset)
      return stio.read(size)
    else:
      return -errno.ENOENT

  def flush(self, path,*args):
    logging.debug("flush(%s)"%path)
    return 0

  def _send_file(self, path, file):
    with nxt.brick.FileWriter(self._brick, path, file) as f:
      for bytes in f:
        pass


  def release(self, path,*args):
    logging.debug("release(%s)"%path)
    if path in self.file_cache:
      ret = self.fsync(path,False)
      del self.file_cache[path]
    return ret

  def truncate(self, path, size,*args):
    logging.debug("truncate(%s)"%path)
    if path in self.file_cache:
      stio, flags = self.file_cache[path]
      stio.truncate(size)
    return 0

  def mkdir(self, path, mode,*args):
    logging.debug("mkdir(%s)"%path)
    return -errno.ENOSYS

  def rmdir(self, path,*args):
    logging.debug("rmdir(%s)"%path)
    return -errno.ENOSYS

  def rename(self, pathfrom, pathto,*args):
    logging.debug("rename(%s,%s)"%(pathfrom,pathto))
    ret = self.open(pathfrom, os.O_RDWR)
    if ret < 0: return ret

    attr = self.getattr(pathto)
    if hasattr(attr,'st_size'):
      return -errno.EEXIST
    
    #move the file in memory
    self.file_cache[pathto] = self.file_cache[pathfrom]
    del(self.file_cache[pathfrom])

    #Here we have a dilemma.  Should we flush the new file out
    #first and then delete the old, or should we delete the old
    #first?  The first method provides protects against 
    #potential data loss, but the second doesn't require there
    #to be significant amounts of free space on the nxt
    #For now we will go with the first, but I may change my mind.

    ret = self.release(pathto)
    if ret < 0: return ret
    return self.unlink(pathfrom)


  def fsync(self, path, isfsyncfile,*args):
    logging.debug("fsync(%s)"%path)
    try:
      if path in self.file_cache:
        stio, flags = self.file_cache[path]
        """TODO: We could optimize for append here """
        if flags & (os.O_WRONLY | os.O_RDWR | os.O_APPEND):
          logging.debug("file is open and being flushed")
          try:
            self._send_file(path[1:],stio)
          except:
            self._brick.delete(path[1:])
            self._send_file(path[1:],stio)
        else:
          logging.debug("File was read only, so nothing to sync")
    except Exception as e:
      logging.error(e)
      return -errno.EIO
    return 0

  def getdir(self, path, *args):
    logging.debug("getdir(%s)"%path)
    return -errno.ENOSYS



if __name__ == "__main__":
  usage=" Nxt Filesystem \n" + Fuse.fusage
  fs = NxtFS(version="%prog " + fuse.__version__,
             usage=usage,
             dash_s_do='setsingle')
  fs.multithreaded = 0
  fs.parse(errex=1)
  fs.main()

