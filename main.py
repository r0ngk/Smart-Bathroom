from sense_hat import SenseHat
import time
import threading

sense = SenseHat()

B = (0, 0, 0)
G = (0, 255, 0)

state_init = 0
state_measure = 1
state_shower = 2
state = state_init

roomTemp = 0 
roomHumid = 0
showerTime = 10
time_prev = time.time()

sys_start = True


def init():
    global sys_start
    global state
    global time_prev
    # measure data when system start
    if sys_start == True:
      state = state_measure
      sys_start = False
      return
    
    time_now = time.time()
    if time_now - time_prev > 5:
      state = state_measure
      time_prev = time_now



def measure():
    global roomTemp
    global roomHumid
    global state
    
    roomTemp = sense.get_temperature
    roomHumid = sense.get_humidity()
    if roomHumid > 80:
      # set ventliation
      print('set ventliation')
    else:
      print('turn off ventilation')
    state = state_init
    
    if True:
       state = state_shower
       


def shower():
    time_start = time.time()
    timer = timerThread(1, "timer", showerTime, time_start)
    timer.start()


class timerThread (threading.Thread):
    def __init__(self, threadID, name, time2count, time_start):
        threading.Thread.__init__(self)
        self.threadID = threadID
        self.name = name
        self.time2count = time2count
        self.time_start = time_start
        
    def run(self):
      while True:
        time_left = self.time2count - (time.time() - self.time_start)
        time_scaled = time_left/ self.time2count * 64
        pixels = [G if i < time_scaled else B for i in range(64)]
        sense.set_pixels(pixels)
        if time_left < 0:
          break
      
      while True:
        time.sleep(1)
        sense.set_pixels([G for i in range(64)])
        time.sleep(1)
        sense.set_pixels([B for i in range(64)])

 

def run():
  while True:
    
    if state == 0:
      init()
    elif state == 1:
      measure()
    elif state == 2:
      shower()
      
        
    
if __name__ == '__main__':
    print('success')
    run()

