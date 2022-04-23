#from sense_hat import SenseHat
from sense_emu import SenseHat
from paho.mqtt import client as mqtt_client
import time
import threading
import vlc
import json

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
time_heaterStart = 0
sys_start = True
fan_on = False
shower_start = False
shower_end = False


def publish(client,topic,msg): # msg is a dict object
    client.publish(topic, payload=json.dumps(msg))

def createMqttClient():
    
    broker = "test.mosquitto.org"
    port = 1883

    
    def on_connect(client, userdata, flags, rc):
        print("Connection result: " + str(rc))
        if rc == 0:
            client.subscribe("Bathroom/shower")

    def on_message(client, userdata, message):
        msg = json.loads(message.payload.decode("utf-8"))
        global shower_start
        global shower_end
        if  msg['shower_token'] == "start":
            shower_start = True
        elif msg['shower_token'] == "end":
            shower_end = True
            
    def on_disconnect(client, userdata, rc):
        if rc != 0:
            print("Disconnected unexpectedly")
    # create client object
    client = mqtt_client.Client()
    #client.username_pw_set("username","pw")
    client.on_connect = on_connect
    client.on_message = on_message
    client.on_disconnect = on_disconnect
    client.connect(broker, port)
    return client


def init(client):
    global sys_start
    global state
    global time_prev
    global shower_start
    # measure data when system start
    if sys_start == True:
        state = state_measure
        sys_start = False
        return

    if shower_start:
        state = state_shower
        shower_start = False
        return
    # try to record enviroments every 10 sec
    time_now = time.time()
    if time_now - time_prev > 10:
        state = state_measure
        time_prev = time_now
    # check if heater should be closed
    if time_heaterStart != 0 and time_now - time_heaterStart > 20+30:
        publish(client, "Bathroom/heater", {"power_on" : False})
        time_heaterStart = 0
    
    #function execute every ~1 sec
    time.sleep(1)

def measure(client):
    global roomTemp
    global roomHumid
    global state
    global fan_on

    roomTemp = sense.get_temperature
    roomHumid = sense.get_humidity()
    topic = "Bathroom/ventilation"
    # turn on ventaliation if humidity is high
    if roomHumid > 80 and not fan_on:
        # set ventliation
        publish(client, topic, {"power_on" : True})
        fan_on = True
    elif roomHumid <= 80 and fan_on:
        publish(client, topic, {"power_on" : False})
        fan_on = False
        
    state = state_init



def shower(client):
    global shower_end
    global state
    global fan_on
    # turn on ventilation
    if not fan_on:
        publish(client, "Bathroom/Ventilation", {"power_on" : True})
        fan_on = True

    time_start = time.time()
    # initialize thread and music player
    timer = timerThread(1, "timer", showerTime, time_start, client)
    tempAdjust = waterTempThread(1, "tempAjust", client)
    player = vlc.MediaPlayer("song.mp3")
    # start threads
    player.play()
    timer.start()
    tempAdjust.start()
    # check token
    while not shower_end:
        time.sleep(3)
    player.stop()
    timer.join()
    tempAdjust.join()
    # consume the token
    shower_end = False
    state = state_init
    

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
        global shower_end
        while not shower_end:
            time_left = int(self.time2count - (time.time() - self.time_start))
            time_scaled = time_left / self.time2count * 64
            pixels = [G if i < time_scaled else B for i in range(64)]
            sense.set_pixels(pixels)
            #refresh rate
            time.sleep(0.5)
            if time_left < 0:
                break
            if time_left  == 30 and not self.heaterSetted:
                publish(self.client, self.topic, {'power_on' : True})
                global time_heaterStart
                time_heaterStart = time.time()
                self.heaterSetted = True
            
        # blink if time's up
        while not shower_end:
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
        global shower_end
        while not shower_end:
            if sense.get_temperature() < waterTemp - 3:
                publish(self.client, self.topic, {'water_temp2low': True})
            elif sense.get_temperature() > waterTemp + 3:
                publish(self.client, self.topic, {'water_temp2high' : True})

            time.sleep(3)


class subscribeThread(threading.Thread):
    def __init__(self, threadID, name, client):
        threading.Thread.__init__(self)
        self.threadID = threadID
        self.name = name
        self.client = client

    def run(self):
        self.client.loop_forever()
        
def run():
    
    client = createMqttClient() # create client object
    listener = subscribeThread(1,"listener",client)
    listener.start()
    
    while True:
        if state == 0:
            init(client)
        elif state == 1:
            measure(client)
        elif state == 2:
            shower(client)


if __name__ == '__main__':
    run()
