
import struct

class RSO(object):

  def __init__(self, sample_rate=8000, data = []):
    self.sample_rate = sample_rate
    self.data = data

  def dump(self):
    return self.header() + self.body()

  def header(self):
    header = struct.pack("<H",1)
    header += struct.pack(">HHH",len(self.data),self.sample_rate,0)
    return header

  def body(self):
    return struct.pack("<%iB" %len(self.data),*self.data)
