#!/usb/bin/env python

import cwiid
import nxt
import nxt.motor
from nxt.motor import *
import nxt.locator

from threading import Event


class WiiNxtController(object):
  BTN_EVENTS = {
    0: { 
      'stop': ([PORT_B,PORT_C],)
    },
    cwiid.BTN_UP: { 
      'drive': (100,[PORT_B,PORT_C])
    },
    cwiid.BTN_DOWN: { 
      'drive': (-100,[PORT_B,PORT_C])
    },
    cwiid.BTN_LEFT: { 
      'drive': (100,[PORT_B,])
    },
    cwiid.BTN_RIGHT: { 
      'drive': (100,[PORT_C,])
    },
    cwiid.BTN_1 | cwiid.BTN_2: {
      'exit': ()
    }
  }

  def __init__(self,wii,brick):
    self.wii = wii
    self.brick = brick
    self.wii.mesg_callback = self.handle
    self.quit = Event()

    self.load_motors()

  def load_motors(self):
    self.motors = [Motor(self.brick,m) for m in xrange(0,3)]
    for motor in self.motors:
      motor.get_output_state

  def handle(self,msg_list,time):
    for msg in msg_list:
      type, data = msg
      if type == 1 and data in self.BTN_EVENTS:
        actions = self.BTN_EVENTS[data]
        for act,args in actions.iteritems():
          try:
            if not self.quit.is_set():
              getattr(self,act)(*args)
          except Exception as e:
            print "Could not execute %s with %s" %(act,str(args))
            print e


  def run(self):
    # do some setup
    self.wii.rpt_mode = cwiid.RPT_BTN
    self.wii.enable(cwiid.FLAG_MESG_IFC)

    # for the quit signal
    self.quit.wait()

    #close out
    self.wii.close()
    self.brick.sock.close()

  def exit(self):
    for motor in self.motors:
      motor.power = 0
      motor.run_state = RUN_STATE_IDLE
      motor.mode = MODE_IDLE
      motor.set_output_state()

    self.quit.set()

  def stop(self,mtrs):
    for m in mtrs:
      self.motors[m].run_state = RUN_STATE_IDLE
      #self.motors[m].mode = MODE_IDLE
      self.motors[m].power = 0
      self.motors[m].set_output_state()

  def drive(self, power, mtrs):
    for m in mtrs:
      self.motors[m].mode = MODE_MOTOR_ON
      self.motors[m].power = power
      self.motors[m].regulation = REGULATION_MOTOR_SYNC
      self.motors[m].run_state = RUN_STATE_RUNNING
      self.motors[m].set_output_state()





if __name__ == "__main__":
  # try and connect to the wii
  print "Press 1+2 on wiimote"
  wii = cwiid.Wiimote()
  print "Connected to wii."
  print "Searching for a brick."
  sock = nxt.locator.find_one_brick()
  print "Found brick: %s" % sock
  brick = sock.connect()
  WiiNxtController(wii,brick).run()
  
