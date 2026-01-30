from move import move, setup, motorStop
from LED import LED, fiesta
import paho.mqtt.client as mqtt
import sys
from RPIservo import PCA9685Controller, ServoController
import time

BROKER = "192.168.1.76"
TOPIC = "pc/keyboard"

# Initialize hardware
led = LED()
hw = PCA9685Controller()
sc = ServoController(hw)
sc.start()
sc.resume()  # Resume to run init mode once
time.sleep(1)  # Give time for init to complete
sc.pause()  # Pause thread to avoid interference

# Servo config
servo_step = 5
camera_servo = 11  # channel for camera
cannon_servo = 12  # channel for cannon

# Initialize servos (after init, but override if needed)
sc.move_angle(camera_servo, 90)
sc.move_angle(cannon_servo, 90)

def on_message(client, userdata, msg):
    key = msg.payload.decode()
    input_data = key.split(":")
    if len(input_data) != 2:
        print(f"Invalid message: {key}")
        return
    action = input_data[0]
    key = input_data[1]
    print(f"key received: {key} {input_data}")
    if action == "press":
        match key:
            # Tank movement (swapped up/down for intuitive control: up=forward, down=backward)
            case "up":
                move(100, "forward", "don't turn")
            case "down":
                move(100, "backward", "don't turn")
            case "left":
                move(100, "backward", "right")
            case "right":
                move(100, "backward", "left")
            case "space":
                fiesta(led)
            # Camera servo
            case "q":
                new_angle = max(sc.current_angle[camera_servo] - servo_step, 0)
                sc.move_angle(camera_servo, new_angle)
            case "d":
                new_angle = min(sc.current_angle[camera_servo] + servo_step, 180)
                sc.move_angle(camera_servo, new_angle)
            # Cannon servo
            case "z":
                new_angle = max(sc.current_angle[cannon_servo] - servo_step, 0)
                sc.move_angle(cannon_servo, new_angle)
            case "s":
                new_angle = min(sc.current_angle[cannon_servo] + servo_step, 180)
                sc.move_angle(cannon_servo, new_angle)
            # Exit
            case "esc":
                print("Exiting...")
                sc.stop()  # stop servo thread
                sc.join()
                hw.stop_all()  # stop all servos
                client.disconnect()
                sys.exit(0)
    elif action == "release":
        match key:
            case "up" | "down" | "left" | "right":
                motorStop()

# Setup MQTT
client = mqtt.Client(callback_api_version=2)
try:
    client.connect(BROKER, 1883)
except Exception as e:
    print(f"MQTT connection failed: {e}")
    sys.exit(1)
client.subscribe(TOPIC)
client.on_message = on_message
setup()
print("waiting for commands sir")
client.loop_forever()
