import uuid
import sys
import threading
import time
import RPi.GPIO as GPIO
import paho.mqtt.client as mqtt

import InfraLib
from move import move, setup as move_setup, motorStop
from LED import LED, fiesta

# ------------------------
# Global shutdown event
# ------------------------
shutdown_event = threading.Event()

# ------------------------
# Tank ID
# ------------------------
TANK_ID = uuid.getnode()

# ------------------------
# GPIO Setup
# ------------------------
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)

LINE_PIN_MIDDLE = 16
IR_RECEIVER = 22

# ------------------------
# MQTT Config
# ------------------------
CONTROLLER_BROKER = "192.168.1.76"
CONTROLLER_TOPIC = "pc/keyboard"

GAME_BROKER = "192.168.1.76"
GAME_TOPIC_PREFIX = "tanks"

# ------------------------
# Sensors
# ------------------------
def sensor_setup():
    GPIO.setup(LINE_PIN_MIDDLE, GPIO.IN)

def read_line_sensor():
    return GPIO.input(LINE_PIN_MIDDLE)

def line_sensor_loop(stop_event):
    last_state = None  

    while not stop_event.is_set():
        current_state = read_line_sensor()

        if last_state is None:
            last_state = current_state
            time.sleep(0.05)
            continue

        if last_state == 1 and current_state == 0:
            if game_client:
                game_client.publish(
                    f"{GAME_TOPIC_PREFIX}/{TANK_ID}/flag",
                    "ENTER_FLAG_AREA"
                )

        elif last_state == 0 and current_state == 1:
            if game_client:
                game_client.publish(
                    f"{GAME_TOPIC_PREFIX}/{TANK_ID}/flag",
                    "EXIT_FLAG_AREA"
                )

        last_state = current_state
        time.sleep(0.05)

def ir_setup():
    GPIO.setup(IR_RECEIVER, GPIO.IN)

def ir_loop(stop_event):
    while not stop_event.is_set():
        received = InfraLib.getSignal(IR_RECEIVER)
        if received is not None:
            #weapon = str(received)[:4]

            #shooter_id_hex = str(received)[4:]
            #shooter_id_dec = str(int(shooter_id_hex, 16))  

            #payload = f"{weapon}{shooter_id_dec}"

            #print(f"IR received: {received} -> payload sent: {payload}")

            game_client.publish(
                f"{GAME_TOPIC_PREFIX}/{TANK_ID}/shots",
                f"SHOT_BY {received}"
            )

# ------------------------
# Controller MQTT callback
# ------------------------
def on_controller_message(client, userdata, msg):
    payload = msg.payload.decode()
    parts = payload.split(":")

    if len(parts) != 2:
        return

    action, key = parts
    print(f"Controller -> {action}:{key}")

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
                InfraLib.IRBlast(int(TANK_ID), "LASER")
            case "esc":
                print("Exit requested from controller")
                shutdown_event.set()

    elif action == "release":
        if key in ("up", "down", "left", "right"):
            motorStop()

# ------------------------
# Game MQTT callback
# ------------------------
TEAM_COLOR = ""
QR_CODE = ""
HAS_FLAG = False

def on_game_message(client, userdata, msg):
    payload = msg.payload.decode()
    topic = msg.topic

    global TEAM_COLOR
    global QR_CODE
    global HAS_FLAG

    print(f"Game server -> {topic}: {payload}")

    global TEAM_COLOR, QR_CODE

    if payload.startswith("TEAM"):
        _, TEAM_COLOR = payload.split()
        print(f"Assigned team: {TEAM_COLOR}")

    elif payload.startswith("QR_CODE"):
        _, QR_CODE = payload.split()
        print(f"Assigned QR code: {QR_CODE}")

    elif payload == "START_CATCHING":
        print("Started catching the flag")

    elif payload == "ABORT_CATCHING_EXIT":
        print("Flag catching aborted (exit area)")

    elif payload == "ABORT_CATCHING_SHOT":
        print("Flag catching aborted (shot)")

    elif payload == "FLAG_CATCHED":
        HAS_FLAG = True

    elif payload == "FLAG_LOST":
        HAS_FLAG = False

    elif payload == "FLAG_DEPOSITED":
        print("Flag successfully deposited!")

    elif payload.startswith("WIN"):
        print(f"Game won: {payload}")

    elif payload == "SHOT":
        print("You got shot!")

    elif payload == "FRIENDLY_FIRE":
        print("Friendly fire!")

# ------------------------
# Main Program
# ------------------------
def main():
    global game_client, controller_client, led

    sensor_setup()
    ir_setup()
    led = LED()

    # ------------------------
    # Threads
    # ------------------------
    line_thread = threading.Thread(
        target=line_sensor_loop,
        args=(shutdown_event,),
        daemon=True
    )
    line_thread.start()

    ir_thread = threading.Thread(
        target=ir_loop,
        args=(shutdown_event,),
        daemon=True
    )

    # ------------------------
    # Controller MQTT
    # ------------------------
    controller_client = mqtt.Client(
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2
    )
    controller_client.on_message = on_controller_message

    def on_controller_connect(client, userdata, flags, reasonCode, properties):
        if reasonCode == 0:
            print("Controller MQTT connected")
            client.subscribe(CONTROLLER_TOPIC)

    controller_client.on_connect = on_controller_connect
    controller_client.connect(CONTROLLER_BROKER, 1883)
    controller_client.loop_start()

    # ------------------------
    # Game MQTT
    # ------------------------
    game_client = mqtt.Client(
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2
    )
    game_client.on_message = on_game_message

    def on_game_connect(client, userdata, flags, reasonCode, properties):
        if reasonCode == 0:
            print("Game server MQTT connected")
            client.subscribe(f"{GAME_TOPIC_PREFIX}/{TANK_ID}/#")
            client.publish("init", f"INIT {TANK_ID}")

    game_client.on_connect = on_game_connect
    game_client.connect(GAME_BROKER, 1883)
    game_client.loop_start()

    ir_thread.start()

    move_setup()
    print("Tank ready.")

    try:
        while not shutdown_event.is_set():
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\nCtrl+C detected")
        shutdown_event.set()

    finally:
        print("Shutting down...")

        shutdown_event.set()

        controller_client.loop_stop()
        controller_client.disconnect()

        game_client.loop_stop()
        game_client.disconnect()

        ir_thread.join(timeout=1)
        line_thread.join(timeout=1)

        motorStop()
        GPIO.cleanup()

        print("Clean exit complete.")

# ------------------------
if __name__ == "__main__":
    main()

