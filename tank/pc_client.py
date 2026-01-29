import keyboard
import paho.mqtt.client as mqtt
import os

BROKER = "192.168.1.76"
TOPIC = "pc/keyboard"

client = mqtt.Client()
client.connect(BROKER, 1883)
client.loop_start()

def send_key(event):
    if event.event_type == "down":
        os.system("clear")
        msg = f"press:{event.name}"
    elif event.event_type == "up":
        msg = f"release:{event.name}"
    print(f"Sending: {msg}")
    client.publish(TOPIC, msg)

keyboard.hook(send_key)
keyboard.wait("esc")
client.loop_stop()
client.disconnect()

