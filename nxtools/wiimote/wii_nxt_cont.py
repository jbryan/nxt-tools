#!/usb/bin/env python

import cwiid
import nxt
import nxt.motor
import math
from nxt.motor import *
import nxt.locator

from time import time, sleep
from threading import Event


class WiiNxtController(object):
  # button event mappings.  This should be moved
  # to a configuration file.
  drive_motors = [PORT_B,PORT_C]
  BTN_EVENTS = {
    0: { 
      'stop': ()
    },
    cwiid.BTN_UP: { 
      'drive_reg': (100,0)
    },
    cwiid.BTN_DOWN: { 
      'drive_reg': (-100,0)
    },
    cwiid.BTN_LEFT: { 
      'drive_reg': (100,100)
    },
    cwiid.BTN_RIGHT: { 
      'drive_reg': (100,-100)
    },
    cwiid.BTN_RIGHT | cwiid.BTN_UP: {
      'drive_reg': (100,-30),
    },
    cwiid.BTN_LEFT | cwiid.BTN_UP: {
      'drive_reg': (100,30),
    },
    cwiid.BTN_RIGHT | cwiid.BTN_DOWN: {
      'drive_reg': (-100,-30),
    },
    cwiid.BTN_LEFT | cwiid.BTN_DOWN: {
      'drive_reg': (-100,30),
    },
    cwiid.BTN_1 | cwiid.BTN_2: {
      'exit': ()
    },
    cwiid.BTN_A: {
      'toggle_acc': ()
    },
    cwiid.BTN_B: {
      'play_sound': ('! Attention.rso',)
    },
  }




  def __init__(self,wii,brick):
    self.wii = wii
    self.brick = brick
    self.wii.mesg_callback = self.handle
    self.quit = Event()

    self.last_motor_command = time()
    self.last_roll = 0
    self.last_pitch = 0

    self.load_motors()
    self.call_zero,self.call_one = self.wii.get_acc_cal(cwiid.EXT_NONE)

  def load_motors(self):
    self.motors = [Motor(self.brick,m) for m in xrange(0,3)]
    for motor in self.motors:
      motor.get_output_state

  def handle(self,msg_list,timestamp):
    for msg in msg_list:
      type, data = msg
      if type == 1 and data in self.BTN_EVENTS:
        actions = self.BTN_EVENTS[data]
        # for each function name and arguments
        for act,args in actions.iteritems():
          try:
            # if we haven't quit yet, do the action
            # the quit check avoids a potential
            # race
            if not self.quit.is_set():
              getattr(self,act)(*args)
          except Exception as e:
            print "Could not execute %s with %s" %(act,str(args))
            print e
      elif type == 2:
        if ((time()-self.last_motor_command) > 0.05):
          roll,pitch = self.get_roll_pitch(data)

          diff_r = abs(self.last_roll - roll)
          diff_p = abs(self.last_pitch - pitch)

          if (diff_r > 0.2 or diff_p > 0.2):
            self.last_roll,self.last_pitch = roll, pitch
            power = roll/(math.pi/2)*150
            turn_ratio = max(-100,min(100,(pitch/(math.pi/2)*100)))

            left = power - turn_ratio
            right = power + turn_ratio

            left = max(-100,min(100,left))
            right = max(-100,min(100,right))
            # put the left/right motor powers into a 
            # dict of MOTOR_NUM => power
            motor_power = dict(zip(self.drive_motors,(left,right)))
            #print power, turn_ratio
            self.drive_unreg(motor_power)




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
    try:
      for motor in self.motors:
        motor.power = 0
        motor.run_state = RUN_STATE_IDLE
        motor.mode = MODE_IDLE
        motor.set_output_state()
    except:
      pass
    self.quit.set()

  def stop(self):
    for m in self.drive_motors:
      #self.motors[m].run_state = RUN_STATE_IDLE
      self.motors[m].mode = MODE_IDLE
      self.motors[m].power = 0
      self.motors[m].set_output_state()
      
    self.last_motor_command = time()

  def drive_reg(self, power, turn_ratio):
    for m in self.drive_motors:
      self.brick.reset_motor_position(m,True)
      self.motors[m].mode = MODE_MOTOR_ON | MODE_REGULATED
      self.motors[m].power = power
      self.motors[m].turn_ratio = turn_ratio
      self.motors[m].regulation = REGULATION_MOTOR_SYNC
      self.motors[m].run_state = RUN_STATE_RUNNING
      self.motors[m].set_output_state()
      
    self.last_motor_command = time()

  def drive_unreg(self, motor_power):
    for m, power in motor_power.iteritems():
      self.brick.reset_motor_position(m,True)
      self.motors[m].mode = MODE_MOTOR_ON 
      self.motors[m].power = power
      self.motors[m].turn_ratio = 0
      self.motors[m].run_state = RUN_STATE_RUNNING
      self.motors[m].set_output_state()

    self.last_motor_command = time()

  def play_sound(self, file):
    self.brick.play_sound_file(False, file)

  def toggle_acc(self):
    rpt_mode = self.wii.state['rpt_mode']
    self.wii.rpt_mode = rpt_mode ^ cwiid.RPT_ACC

  def get_roll_pitch(self,data):
    x,y,z = data
    #normalize acc data
    a_x = float(x - self.call_zero[0])/(self.call_one[0] - self.call_zero[0])
    a_y = float(y - self.call_zero[1])/(self.call_one[1] - self.call_zero[1])
    a_z = float(z - self.call_zero[2])/(self.call_one[2] - self.call_zero[2])

    if (a_z != 0):
      roll = math.atan(float(a_x)/a_z)
    else:
      roll = math.pi/2

    if (a_z <= 0):
      roll += math.pi * math.copysign(1,a_x)

    if (a_z != 0):
      pitch = math.atan(float(a_y)/a_z)
    else:
      pitch = math.pi/2

    if (a_z <= 0):
      pitch += math.pi * math.copysign(1,a_y)

    return roll,pitch




if __name__ == "__main__":
  # try and connect to the wii
  print "Press 1+2 on wiimote"
  wii = cwiid.Wiimote()
  print "Connected to wii."
  print "Searching for a brick."
  sock = nxt.locator.find_one_brick()
  print "Found brick: %s" % sock
  try:
    brick = sock.connect()
  except:
    # Sometimes, we need to wait a bit so the bt layer catches up
    print "First connect attempt failed, waiting 2 secs."
    sleep(2)
    brick = sock.connect()
  print "Connected to nxt ... starting remote control."
  WiiNxtController(wii,brick).run()
  
