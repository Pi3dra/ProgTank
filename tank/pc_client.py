from pynput import keyboard
import paho.mqtt.client as mqtt

BROKER = "RASPBERRY_PI_IP"   # e.g. 192.168.1.50
TOPIC = "pc/keyboard"

client = mqtt.Client()
client.connect(BROKER, 1883)
client.loop_start()

print("Sending key presses (ESC to quit)")

def on_press(key):
    try:
        msg = f"press:{key.char}"
    except AttributeError:
        msg = f"press:{key.name}"
    client.publish(TOPIC, msg)

def on_release(key):
    try:
        msg = f"release:{key.char}"
    except AttributeError:
        msg = f"release:{key.name}"
    client.publish(TOPIC, msg)

    if key == keyboard.Key.esc:
        print("Exiting")
        client.loop_stop()
        client.disconnect()
        return False

with keyboard.Listener(
    on_press=on_press,
    on_release=on_release
) as listener:
    listener.join()

