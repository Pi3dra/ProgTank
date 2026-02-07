import random
import paho.mqtt.client as mqtt
import time
import threading
import os

# QR codes and weapons
qr_codes = {"RED": "RED_BASE", "BLUE": "BLUE_BASE"}
weapons = {"0xf1": "Laser Gun"}

# ------------------------
# Team assignment helpers
# ------------------------
def assignToTeam(tank_id):
    if sum(x['color'] == "RED" for x in participants.values()) < sum(x['color'] == "BLUE" for x in participants.values()):
        addToRedTeam(tank_id)
    elif sum(x['color'] == "RED" for x in participants.values()) > sum(x['color'] == "BLUE" for x in participants.values()):
        addToBlueTeam(tank_id)
    else:
        if random.choice(["RED", "BLUE"]) == "RED":
            addToRedTeam(tank_id)
        else:
            addToBlueTeam(tank_id)
    client.publish(f"tanks/{tank_id}/init", "END")


def addToBlueTeam(tank_id):
    participants[tank_id] = {"color": "BLUE", "flag": False, "catching": False}
    client.publish(f"tanks/{tank_id}/init", "TEAM BLUE")
    client.publish(f"tanks/{tank_id}/init", "QR_CODE " + qr_codes["BLUE"])
    print(f"Rasptank {tank_id} is BLUE")


def addToRedTeam(tank_id):
    participants[tank_id] = {"color": "RED", "flag": False, "catching": False}
    client.publish(f"tanks/{tank_id}/init", "TEAM RED")
    client.publish(f"tanks/{tank_id}/init", "QR_CODE " + qr_codes["RED"])
    print(f"Rasptank {tank_id} is RED")


# ------------------------
# Flag handling
# ------------------------
def giveFlag(tank_id, topic):
    for _ in range(5):
        time.sleep(1)
        if not participants[tank_id]["catching"]:
            return
    participants[tank_id]["flag"] = True
    participants[tank_id]["catching"] = False
    client.publish(topic, "FLAG_CATCHED")
    print(f"{tank_id} captured the flag")


# ------------------------
# MQTT message processing
# ------------------------
def processData(client, userdata, message):
    querry = str(message.payload.decode("utf-8")).split(" ")

    # ------------------------
    # Initialization topic
    # ------------------------
    if message.topic == "init":
        if querry[0] == "INIT":
            if initPhase:
                assignToTeam(querry[1])
            else:
                client.publish(f"tanks/{querry[1]}/init", "GAME_ALREADY_STARTED")
        return

    # ------------------------
    # Split topic for participants
    # ------------------------
    topic_parts = message.topic.split('/')
    participant_id = topic_parts[1]
    subtopic = topic_parts[2] if len(topic_parts) > 2 else ''

    if participant_id not in participants:
        return

    # ------------------------
    # Flag topic
    # ------------------------
    if subtopic == "flag":
        if querry[0] == "ENTER_FLAG_AREA":
            if not any(p["flag"] for p in participants.values()):
                client.publish(message.topic, "START_CATCHING")
                participants[participant_id]["catching"] = True
                print(f"{participant_id} start catching the flag")
                threading.Thread(target=giveFlag, args=[participant_id, message.topic]).start()
            elif participants[participant_id]["flag"]:
                client.publish(message.topic, "ALREADY_GOT")
                print(f"{participant_id} has already the flag")
            else:
                client.publish(message.topic, "NOT_ONBASE")
                print(f"Hey {participant_id}, there is no flag here anymore")
        elif querry[0] == "EXIT_FLAG_AREA":
            if participants[participant_id]["catching"]:
                client.publish(message.topic, "ABORT_CATCHING_EXIT")
                participants[participant_id]["catching"] = False
                print(f"{participant_id} abort catching the flag, you exited the flag area")

    # ------------------------
    # Shots topic
    # ------------------------
    elif subtopic == "shots":
        if querry[0] == "SHOT_BY":
            shot = querry[1][:4]
            shooter_hex = "0x" + querry[1][4:]
            shooter = str(int(shooter_hex, 16))
            if shooter not in participants:
                print(f"{shooter} not in participants weird...")
                print(participants)
                return

            # ------------------------
            # Self-shot case
            # ------------------------
            if participant_id == shooter:
                client.publish(f"{message.topic}/in", "SHOT")
                print(f"{participant_id} shot itself with {weapons.get(shot, 'Unknown weapon')}")

                # Abort flag capture if necessary
                if participants[participant_id]["catching"]:
                    client.publish(f"tanks/{participant_id}/flag", "ABORT_CATCHING_SHOT")
                    participants[participant_id]["catching"] = False

                # Drop flag if carrying
                if participants[participant_id]["flag"]:
                    client.publish(f"tanks/{participant_id}/flag", "FLAG_LOST")
                    participants[participant_id]["flag"] = False
                return

            # ------------------------
            # Enemy shot
            # ------------------------
            if participants[participant_id]["color"] != participants[shooter]["color"]:
                client.publish(f"{message.topic}/in", "SHOT")
                client.publish(f"tanks/{shooter}/shots/out", "SHOT")
                print(f"{participant_id} shot by {shooter} with {weapons.get(shot, 'Unknown weapon')}")

                if participants[participant_id]["catching"]:
                    client.publish(f"tanks/{participant_id}/flag", "ABORT_CATCHING_SHOT")
                    participants[participant_id]["catching"] = False

                if participants[participant_id]["flag"]:
                    client.publish(f"tanks/{participant_id}/flag", "FLAG_LOST")
                    participants[participant_id]["flag"] = False

            # ------------------------
            # Friendly fire (not self)
            # ------------------------
            else:
                client.publish(f"tanks/{shooter}/shots/out", "FRIENDLY_FIRE")
                print(f"Careful {shooter}, friendly fire")

    # ------------------------
    # QR code topic
    # ------------------------
    elif subtopic == "qr_code":
        if querry[0] == "QR_CODE":
            qr = querry[1]
            if qr == qr_codes.get(participants[participant_id]["color"]):
                client.publish(message.topic, "SCAN_SUCCESSFUL")
                if participants[participant_id]["flag"]:
                    client.publish(f"tanks/{participant_id}/flag", "FLAG_DEPOSITED")
                    participants[participant_id]["flag"] = False
                    scores[participants[participant_id]["color"]] += 1
                    print(f"RED : {scores['RED']} // BLUE : {scores['BLUE']}")
                    if scores[participants[participant_id]["color"]] == 1:
                        for tid in participants.keys():
                            client.publish(f"tanks/{tid}/flag", f"WIN {participants[participant_id]['color']}")
                else:
                    client.publish(f"tanks/{participant_id}/flag", "NO_FLAG")
                    print(f"{participant_id}, there is no flag to deposit")
            else:
                client.publish(message.topic, "SCAN_FAILED")


# ------------------------
# Game startup
# ------------------------
def start_game():
    print("Welcome to World of Rasptank")
    input("Initialisation phase, press Enter to continue...\n")
    global initPhase
    initPhase = False
    print("Initialisation phase finished")


# ------------------------
# Main
# ------------------------
if __name__ == "__main__":
    initPhase = True
    participants = {}
    scores = {"RED": 0, "BLUE": 0}

    client = mqtt.Client()
    client.connect("192.168.1.76")

    client.subscribe("init")
    client.subscribe("tanks/+/flag")
    client.subscribe("tanks/+/shots")
    client.subscribe("tanks/+/qr_code")
    client.loop_start()
    client.on_message = processData

    start_game()

    try:
        while True:
            time.sleep(0.01)
    except KeyboardInterrupt:
        client.loop_stop()
        print("Server shutting down...")

