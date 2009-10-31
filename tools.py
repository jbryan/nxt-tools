#! /usr/bin/env python

import pygtk
import gtk

class NXTToolBox:
	def __init__(self):
		"Initialise the application." 
		builder = gtk.Builder()
		builder.add_from_file("tool-ui.glade")
		dic = {
				"on_quit_button_clicked"        : gtk.mainquit,
				"on_exit1_activate"             : gtk.mainquit,
				}
		builder.connect_signals(dic)
		self.main_window = builder.get_object("main_window")
		self.main_window.show()

	def start(self):
		gtk.main()

def main ():
	app = NXTToolBox()
	app.start()

if __name__ == '__main__': main ()

