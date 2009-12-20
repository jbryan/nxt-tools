
#!/usr/bin/python

import fuse
from fuse import Fuse
fuse.fuse_python_api = (0,2)

from time import time

import stat    # for file properties
import os      # for filesystem modes (O_RDONLY, etc)
import os.path
import errno   # for error number codes (ENOENT, etc)
import logging
from StringIO import StringIO
import nxt
import nxt.locator
import nxt.brick
from nxt.error import *

from nxt_fs import *


#logging.basicConfig(filename="nxt_fs.log",level=logging.DEBUG)

class NxtSysFile(object):
  def __init__(self,brick):
    self.brick = brick
  
class NxtRunningProgram(NxtSysFile):
  path = "/sys/running_program"
  def __init__(self,brick):
    NxtSysFile.__init__(self,brick)

  def read(self):
    try:
      return self.brick.get_current_program_name() +"\n"
    except Exception as e:
      logging.debug(e)
      return ""

  def write(self,data):
    try:
      prg_file = os.path.basename(data.strip())
      logging.debug("Executin file: '%s'"%prg_file)
      self.brick.start_program(prg_file)
    except Exception as e:
      logging.error(e)
      self.brick.stop_program()

class NxtPlayingSound(NxtSysFile):
  path = "/sys/play_sound"
  def __init__(self, brick):
    NxtSysFile.__init__(self,brick)

  def write(self,data):
    snd_file = os.path.basename(data.strip())
    logging.debug("Playing file: '%s'"%snd_file)
    self.brick.play_sound_file(False,snd_file)

class NxtBatteryLevel(NxtSysFile):
  path = "/sys/battery_level"
  def __init__(self, brick):
    NxtSysFile.__init__(self,brick)

  def read(self):
    return str(self.brick.get_battery_level()) + "\n"

class NxtDeviceInfo(NxtSysFile):
  path = "/sys/device_info"
  def __init__(self, brick):
    NxtSysFile.__init__(self,brick)

  def read(self):
    return str(self.brick.get_device_info()) + "\n"

class NxtFirmwareVirsion(NxtSysFile):
  path = "/sys/firmware_version"
  def __init__(self, brick):
    NxtSysFile.__init__(self,brick)

  def read(self):
    return str(self.brick.get_firmware_version()) + "\n"

class NxtSysFS(NxtFS):
  """
  A Fuse based file system that extends the nxt filesystem to include
  a sysfs type interface.
  """

  def __init__(self, *args, **kw):
    NxtFS.__init__(self, *args, **kw)
    #I am not happy with the following approach for creating 
    #new file handlers .. but for now it works.  I'd prefer them
    #to self register rather than scan the class tree
    files = [ 
      cls(self._brick) for cls in NxtSysFile.__subclasses__() 
    ]
    self.sys_files = dict([(f.path,f) for f in files])

  def getattr(self, path, *args):
    logging.debug("getattr(%s,%s)" % (path,str(args)))

    st = NxtStat()
    st.st_atime = self.mounttime
    st.st_ctime = self.mounttime
    st.st_mtime = self.mounttime

    if path == "/sys":
      st.st_mode = stat.S_IFDIR | 0755
      st.st_nlink = 2
      return st
    elif path in self.sys_files:
      file = self.sys_files[path]
      st.st_mode = stat.S_IFREG 
      if hasattr(file,"read"):
        st.st_mode |= 0444
      if hasattr(file,"write"):
        st.st_mode |= 0222
      st.st_size = 4096 #just big enough the we can always read it
      st.st_nlink = 1
      return st
    else:
      return super(NxtSysFS,self).getattr(path,*args)



  def readdir(self, path, offset):
    logging.debug("readdir(%s)" % path)

    if path == "/":
      for entry in super(NxtSysFS,self).readdir(path,offset):
        yield entry
      yield fuse.Direntry("sys")
    elif path == "/sys":
      try:
        yield fuse.Direntry(".")
        yield fuse.Direntry("..")
        for fname in self.sys_files.iterkeys():
          yield fuse.Direntry(os.path.basename(fname))
      except Exception as e:
        logging.error(e)

  def open(self,path, flags, *mode):
    logging.debug("open(%s,%i,%s)"%(path,flags,str(mode)))
    if path in self.sys_files:
      if hasattr(self.sys_files[path], 'read'):
        buf = self.sys_files[path].read()
      else:
        buf = ""
      self.file_cache[path] = (StringIO(buf), flags)
      return 0
    else:
      return super(NxtSysFS,self).open(path,flags,*mode)

  def _send_file(self, path, stio):
    if path in self.sys_files:
      try:
        stio.seek(0)
        self.sys_files[path].write(stio.buf)
      except Exception as e:
        logging.error(e)
    else:
      super(NxtSysFS,self)._send_file(path,stio)
    


if __name__ == "__main__":
  usage=" Nxt Filesystem with /sys support \n" + Fuse.fusage
  fs = NxtSysFS(version="%prog " + fuse.__version__,
             usage=usage,
             dash_s_do='setsingle')
  fs.multithreaded = 0
  fs.parse(errex=1)
  fs.main()

