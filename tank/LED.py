#!/usr/bin/python3
# File name   : LED.py
# Description : WS_2812
# Website     : based on the code from https://github.com/rpi-ws281x/rpi-ws281x-python/blob/master/examples/strandtest.py
# Author      : original code by Tony DiCola (tony@tonydicola.com)
# Date        : 2019/02/23
import time
from rpi_ws281x import *
import argparse


class LED:
    def __init__(self):
        self.LED_COUNT = 16  # Number of LED pixels.
        self.LED_PIN = 12  # GPIO pin connected to the pixels (18 uses PWM!).
        self.LED_FREQ_HZ = 800000  
        self.LED_DMA = 10  
        self.LED_BRIGHTNESS = 255  
        self.LED_INVERT = (
            False  # True to invert the signal (when using NPN transistor level shift)
        )
        self.LED_CHANNEL = 0  # set to '1' for GPIOs 13, 19, 41, 45 or 53
        parser = argparse.ArgumentParser()
        parser.add_argument(
            "-c", "--clear", action="store_true", help="clear the display on exit"
        )
        args = parser.parse_args()

        # Create NeoPixel object with appropriate configuration.
        self.strip = Adafruit_NeoPixel(
            self.LED_COUNT,
            self.LED_PIN,
            self.LED_FREQ_HZ,
            self.LED_DMA,
            self.LED_INVERT,
            self.LED_BRIGHTNESS,
            self.LED_CHANNEL,
        )
        # Intialize the library (must be called once before other functions).
        self.strip.begin()

    def colorWipe(self, R, G, B):
        color = Color(R, G, B)
        for i in range(self.strip.numPixels()):
            self.strip.setPixelColor(i, color)
        self.strip.show()


def setcolor(led, color):
    rgb = (0, 0, 0)
    match color:
        case "RED":
            rgb = (255, 0, 0)
        case "BLUE":
            rgb = (0, 0, 255)
    r,g,b = rgb
    led.colorWipe(r,g,b)

def blink(led, color):
    rgb = (0, 0, 0)
    match color:
        case "RED":
            rgb = (255, 0, 0)
        case "BLUE":
            rgb = (0, 0, 255)

    r, g, b = rgb

    for _ in range (3):
        led.colorWipe(r, g, b)
        time.sleep(0.5)
        led.colorWipe(int(r/2),int(g/2),int(b/2))
        time.sleep(0.5)
    led.colorWipe(r,g,b)

    led.colorWipe(0,0,0)


