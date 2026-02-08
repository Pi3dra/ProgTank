import keyboard
import paho.mqtt.client as mqtt
import os
import subprocess
import sys

BROKER = "192.168.1.76"
TOPIC = "pc/keyboard"

# Launch QR camera script
qr_process = subprocess.Popen([sys.executable, "qrcode.py"])

client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2)
client.connect(BROKER, 1883)
client.loop_start()

def send_key(event):
    if event.event_type == "down":
        os.system("clear")
        msg = f"press:{event.name}"
    elif event.event_type == "up":
        msg = f"release:{event.name}"
    else:
        return

    print(f"Sending: {msg}")
    client.publish(TOPIC, msg)

keyboard.hook(send_key)
print("Keyboard active — ESC to quit")

keyboard.wait("esc")

print("Shutting down...")
client.loop_stop()
client.disconnect()

qr_process.terminate()
qr_process.wait()

