
import struct
import os
import tempfile
import sys
from subprocess import Popen,PIPE

class RSO(object):

  def __init__(self, sample_rate=8000, body=""):
    self.sample_rate = sample_rate
    self.body = body

  def dump(self):
    return self.header() + self.body

  def write(self, fname):
    with file(fname, "w") as f:
      f.write(self.dump())

  def header(self):
    header = struct.pack("<H",1)
    header += struct.pack(">HHH",len(self.body),self.sample_rate,0)
    return header


  def set_body_from_list(self, l):
    self.body = struct.pack("<%iB" %len(l),*l)

  def set_body_from_text(self, text):
    args = ["gst-launch","fdsrc","fd=0","!","festival","!","wavparse","!", 
            "audioconvert","!",
            "audioresample","quality=10","!","audio/x-raw-int,rate=%i"%self.sample_rate,"!",  
            "audioconvert","!","audio/x-raw-int,channels=1,width=8,depth=8,signed=false","!",  
            "fdsink", "fd=2"]

    p = Popen(args,stdin=PIPE,stdout=PIPE,stderr=PIPE)

    junk,self.body = p.communicate(text)
    return junk

  def set_body_from_file(self, file):
    args = ["gst-launch","filesrc","location=%s"%file,"!","decodebin","!", 
            "audioconvert","!", 
            "audioresample","quality=10","!","audio/x-raw-int,rate=%i"%self.sample_rate,"!",  
            "audioconvert","!","audio/x-raw-int,channels=1,width=8,depth=8,signed=false","!",  
            "fdsink", "fd=2"]

    p = Popen(args,stdout=PIPE,stderr=PIPE)

    junk,self.body = p.communicate()
    return junk


    
      

    

if __name__ == "__main__":
  fin = sys.argv[1]
  fout = sys.argv[2]
  r = RSO()
  if os.path.isfile(fin):
    r.set_body_from_file(fin)
  else:
    r.set_body_from_text(fin)
  r.write(fout)


  
