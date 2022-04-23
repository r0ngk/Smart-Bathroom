from paho.mqtt import client as mqtt_client
import time
import json

hostname = "test.mosquitto.org"
port = 1883
topic = "Bathroom/shower"

client = mqtt_client.Client()
client.connect(hostname, port=port)

while True:
    time.sleep(10)
    client.publish(topic, json.dumps({'shower_token' : "start"}))
    time.sleep(70)
    client.publish(topic, json.dumps({'shower_token' : "end"}))
    time.sleep(240)