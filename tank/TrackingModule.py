import time
import RPi.GPIO as GPIO

line_pin_middle = 16

def setup():
    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(line_pin_middle, GPIO.IN)


def run():
    status_middle = GPIO.input(line_pin_middle)
    print("Capteur: %d\n" % (status_middle))
    return status_middle


if __name__ == "__main__":
    try:
        setup()
        while True:
            run()
    except KeyboardInterrupt:
        pass
