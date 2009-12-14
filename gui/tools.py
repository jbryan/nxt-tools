#! /usr/bin/env python

import pygtk
import gtk
import nxt.brick
import nxt.locator

class NXTToolBox(object):
  def __init__(self):
    "Initialise the application." 
    self.builder = gtk.Builder()
    self.builder.add_from_file("tool-ui.glade")
    dic = {
      "on_exit_activate"                    : gtk.main_quit,
      "on_open_connect_dialog_activate"     : self.open_connect,
    }
    self.builder.connect_signals(dic)
    self.main_window = self.builder.get_object("main_window")
    self.main_window.show()

  def start(self):
    gtk.main()

  def open_connect(self,event):
    #finder = nxt.locator.find_bricks()
    list = self.builder.get_object("nxtstore")
    #for sock in finder:
      #list.append((sock.host,"blah"))
    for i in range(1,20):
      list.append(str(i))

    self.builder.get_object("connect_dialog").show()
    

def main ():
  app = NXTToolBox()
  app.start()

if __name__ == '__main__': main ()

