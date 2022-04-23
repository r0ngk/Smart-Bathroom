#from sense_hat import SenseHat
from sense_emu import SenseHat
from paho.mqtt import client as mqtt_client
import time
import threading
import vlc

sense = SenseHat()

B = (0, 0, 0)
G = (0, 255, 0)

state_init = 0
state_measure = 1
state_shower = 2
state = state_init

roomTemp = 0
roomHumid = 0
showerTime = 60
waterTemp = 40
time_prev = time.time()
sys_start = True

broker = "test.mosquitto.org"
port = 1883
topic_water_temp = "Bathroom/Mqtt"

def publish(client,topic,msg):
    print(msg)
    client.publish(topic, payload=msg)

def connect_broker(client):
    #client.username_pw_set("username","pw")
    client.connect(broker, port)

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


def measure(client):
    global roomTemp
    global roomHumid
    global state

    roomTemp = sense.get_temperature
    roomHumid = sense.get_humidity()
    topic = "Bathroom/Ventilation"
    if roomHumid > 80:
        # set ventliation
        publish(client, topic, "turn on")
    else:
        publish(client, topic, "turn off")
    state = state_init

    if True:
        state = state_shower


def shower(client):
    time_start = time.time()
    timer = timerThread(1, "timer", showerTime, time_start, client)
    tempAdjust = waterTempThread(1, "tempAjust", client)
    music = vlc.MediaPlayer("song.mp3")
    music.play()
    timer.start()
    tempAdjust.start()
    while True:
        time.sleep(10)


class timerThread (threading.Thread):
    def __init__(self, threadID, name, time2count, time_start, client):
        threading.Thread.__init__(self)
        self.threadID = threadID
        self.name = name
        self.time2count = time2count
        self.time_start = time_start
        self.heaterSetted = False
        self.client = client
        self.topic = "Bathroom/heater"

    def run(self):
        while True:
            time_left = int(self.time2count - (time.time() - self.time_start))
            time_scaled = time_left / self.time2count * 64
            pixels = [G if i < time_scaled else B for i in range(64)]
            sense.set_pixels(pixels)
            #refresh rate
            time.sleep(0.5)
            if time_left < 0:
                break
            if time_left  == 30 and not self.heaterSetted:
                publish(self.client, self.topic, "turn on heater")
                self.heaterSetted = True
            

        while True:
            time.sleep(1)
            sense.set_pixels([G for i in range(64)])
            time.sleep(1)
            sense.set_pixels([B for i in range(64)])


class waterTempThread (threading.Thread):
    def __init__(self, threadID, name, client):
        threading.Thread.__init__(self)
        self.threadID = threadID
        self.name = name
        self.client = client
        self.topic = "Bathroom/water-temp"

    def run(self):
        while True:
            if sense.get_temperature() < waterTemp - 2:
                publish(self.client, self.topic, "water temperature is too low")
            elif sense.get_temperature() > waterTemp + 2:
                publish(self.client, self.topic, "water temperature is too high")

            time.sleep(3)

        
def run():
    
    client = mqtt_client.Client() # create client object
    connect_broker(client)
    
    while True:
        if state == 0:
            init()
        elif state == 1:
            measure(client)
        elif state == 2:
            shower(client)


if __name__ == '__main__':
    run()
