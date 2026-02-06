import uuid
import sys
import threading
import time
import RPi.GPIO as GPIO
import paho.mqtt.client as mqtt

import InfraLib
from move import move, setup as move_setup, motorStop
from LED import LED, fiesta
from RPIservo import PCA9685Controller, ServoController

TANK_ID = uuid.getnode()

# --- MQTT Config ---
BROKER = "192.168.1.76"
TOPIC = "pc/keyboard"

# --- GPIO Pins (BCM mode) ---
LINE_PIN_MIDDLE = 16  
IR_RECEIVER = 22      

# ------------ Line Sensor ------------
def sensor_setup():
    GPIO.setup(LINE_PIN_MIDDLE, GPIO.IN)

def read_line_sensor():
    return GPIO.input(LINE_PIN_MIDDLE)

def line_sensor_loop(stop_event):
    while not stop_event.is_set():
        if read_line_sensor() == 0:
            print("PAPER detected")
        time.sleep(0.1)

# ------------ IR Sensor ------------
def ir_setup():
    GPIO.setup(IR_RECEIVER, GPIO.IN)

def ir_loop():
    while True:
        received = InfraLib.getSignal(IR_RECEIVER)
        if received != None:
            print(received)

# --- Initialize Hardware ---
led = LED()
hw = PCA9685Controller()
sc = ServoController(hw)
sc.start()
sc.resume()
time.sleep(1)
sc.pause()
sensor_setup()
ir_setup()

servo_step = 5
camera_servo = 11
cannon_servo = 12

sc.move_angle(camera_servo, 90)
sc.move_angle(cannon_servo, 90)

# --- MQTT Message Handler ---
def on_message(client, userdata, msg):
    key = msg.payload.decode()
    input_data = key.split(":")
    if len(input_data) != 2:
        print(f"Invalid message: {key}")
        return
    action = input_data[0]
    key = input_data[1]
    print(f"{action} -> {key}")
    if action == "press":
        match key:
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
            case "f":
                InfraLib.IRBlast(TANK_ID, "LASER")
            case "q":
                new_angle = max(sc.current_angle[camera_servo] - servo_step, 0)
                sc.move_angle(camera_servo, new_angle)
            case "d":
                new_angle = min(sc.current_angle[camera_servo] + servo_step, 180)
                sc.move_angle(camera_servo, new_angle)
            case "z":
                new_angle = max(sc.current_angle[cannon_servo] - servo_step, 0)
                sc.move_angle(cannon_servo, new_angle)
            case "s":
                new_angle = min(sc.current_angle[cannon_servo] + servo_step, 180)
                sc.move_angle(cannon_servo, new_angle)
            case "esc":
                print("Exiting...")
                raise KeyboardInterrupt
    elif action == "release":
        match key:
            case "up" | "down" | "left" | "right":
                motorStop()

# --- Main Program ---
def main():
    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BCM)

    stop_event = threading.Event()

    # Start background threads
    line_thread = threading.Thread(target=line_sensor_loop, args=(stop_event,), daemon=True)

    ir_thread = threading.Thread(target=ir_loop, args=(), daemon=True)

    line_thread.start()
    ir_thread.start()

    # Setup MQTT
    client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2)
    try:
        client.connect(BROKER, 1883)
    except Exception as e:
        print(f"MQTT connection failed: {e}")
        sys.exit(1)
    client.subscribe(TOPIC)
    client.on_message = on_message

    move_setup()
    print("Waiting for commands sir...")

    try:
        client.loop_forever()
    except KeyboardInterrupt:
        print("\nCtrl+C or ESC detected. Stopping everything...")
    finally:
        stop_event.set()
        line_thread.join(timeout=1)
        ir_thread.join(timeout=1)

        sc.stop()
        sc.join()
        hw.stop_all()

        motorStop()

        GPIO.cleanup()

        client.disconnect()
        print("Clean exit complete.")

if __name__ == "__main__":
    main()

