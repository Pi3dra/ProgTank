from move import move, setup, motorStop
from LED import LED, fiesta, fiesta_off
import paho.mqtt.client as mqtt

BROKER = "10.86.165.33"
TOPIC = "pc/keyboard"
led = LED()

def on_message(client, userdata, msg):
    key = msg.payload.decode()
    input_data = key.split(":")
    print(f"key received: {key} {input_data}") 
    if (input_data[0] == "press"):
        if (input_data[1] == "up"):
            move(100, 'backward', "don't turn")
        if (input_data[1] == "down"):
            move(100, 'forward' , "don't turn")
        if (input_data[1] == "left"):
            move(100, 'backward', "right")
        if (input_data[1] == "right"):
            move(100, 'backward', "left")
        if (input_data[1] == "space"):
            fiesta(led)
    elif (input_data[0] == "release"):
        motorStop()

client = mqtt.Client()
client.connect(BROKER, 1883)
client.subscribe(TOPIC)
client.on_message = on_message
setup()

print("waiting for commands sir")
client.loop_forever()
