#!/usr/bin/env python3

import time
import threading
import Adafruit_PCA9685

# =======================
# Hardware abstraction
# =======================
class PCA9685Controller:
    def __init__(self, address=0x40, busnum=1, freq=50):
        self.pwm = Adafruit_PCA9685.PCA9685(address=address, busnum=busnum)
        self.pwm.set_pwm_freq(freq)

    def set_servo(self, channel, value):
        self.pwm.set_pwm(channel, 0, value)

    def stop_all(self, channels=16):
        for i in range(channels):
            self.set_servo(i, 0)

# =======================
# Servo Controller Thread
# =======================
class ServoController(threading.Thread):
    def __init__(self, hw: PCA9685Controller, channels=16):
        super().__init__()
        self.hw = hw
        self.channels = channels
        self._stop_event = threading.Event()
        self._pause_event = threading.Event()
        self._pause_event.clear()

        # Servo state
        self.init_pos = [300] * channels
        self.goal_pos = [300] * channels
        self.now_pos = [300] * channels
        self.last_pos = [300] * channels
        self.speed = [0] * channels
        self.direction = [1] * channels
        self.max_pos = [520] * channels
        self.min_pos = [100] * channels
        self.current_angle = [0] * channels  # **logical angles in degrees**

        # Movement config
        self.mode = "init"  # 'init', 'auto', 'certain', 'wiggle'
        self.steps = 30
        self.delay = 0.037

    # =======================
    # Thread control
    # =======================
    def stop(self):
        self._stop_event.set()
        self._pause_event.set()  # wake up if paused

    def pause(self):
        self._pause_event.clear()

    def resume(self):
        self._pause_event.set()

    def run(self):
        while not self._stop_event.is_set():
            self._pause_event.wait()  # block if paused
            if self.mode == "init":
                self._move_init()
            elif self.mode == "auto":
                self._move_auto()
            elif self.mode == "certain":
                self._move_certain()
            elif self.mode == "wiggle":
                self._move_wiggle()
            time.sleep(self.delay)

    # =======================
    # Movement modes
    # =======================
    def _move_init(self):
        for i in range(self.channels):
            self.now_pos[i] = self.init_pos[i]
            self.last_pos[i] = self.init_pos[i]
            self.hw.set_servo(i, self.now_pos[i])
        self.pause()

    def _move_auto(self):
        for step in range(self.steps):
            for i in range(self.channels):
                delta = (self.goal_pos[i] - self.last_pos[i]) / self.steps
                self.now_pos[i] = int(round(self.last_pos[i] + delta * (step + 1)))
                self.hw.set_servo(i, self.now_pos[i])
            time.sleep(self.delay)
        self.last_pos = self.now_pos.copy()
        self.pause()

    def _move_certain(self):
        moving = True
        while moving:
            moving = False
            for i in range(self.channels):
                if self.now_pos[i] < self.goal_pos[i]:
                    self.now_pos[i] += self.speed[i]
                    if self.now_pos[i] > self.goal_pos[i]:
                        self.now_pos[i] = self.goal_pos[i]
                    moving = True
                elif self.now_pos[i] > self.goal_pos[i]:
                    self.now_pos[i] -= self.speed[i]
                    if self.now_pos[i] < self.goal_pos[i]:
                        self.now_pos[i] = self.goal_pos[i]
                    moving = True
                self.hw.set_servo(i, self.now_pos[i])
            time.sleep(self.delay)
        self.pause()

    def _move_wiggle(self):
        i = 0
        direction = self.direction[i]
        self.now_pos[i] += direction * self.speed[i]
        if self.now_pos[i] > self.max_pos[i] or self.now_pos[i] < self.min_pos[i]:
            self.direction[i] *= -1
        self.hw.set_servo(i, self.now_pos[i])
        time.sleep(self.delay)

    # =======================
    # Public control
    # =======================
    def set_goal(self, channel_indices, goal_values, speed=None):
        for idx, val in zip(channel_indices, goal_values):
            self.goal_pos[idx] = min(max(val, self.min_pos[idx]), self.max_pos[idx])
            if speed:
                self.speed[idx] = speed[idx]
        self.resume()

    def set_mode(self, mode):
        self.mode = mode
        self.resume()

    def move_angle(self, channel, angle):
        angle = min(max(angle, 0),360)
    
        pwm_value = int(self.min_pos[channel] + (self.max_pos[channel] - self.min_pos[channel]) * (angle/360))
        self.now_pos[channel] = pwm_value
        self.current_angle[channel] = angle
        self.hw.set_servo(channel, pwm_value)
        
# =======================
# Standalone test
# =======================
if __name__ == "__main__":
    hw = PCA9685Controller()
    sc = ServoController(hw)
    sc.start()
    sc.pause()  # Pause thread for manual control

    try:
        for i in range(9, 16):
            print(f"Moving servo {i} to 90°")
            sc.move_angle(i, 90)
            time.sleep(2)

    except KeyboardInterrupt:
        print("Stopping all servos...")
        sc.stop()
        sc.join()
        hw.stop_all()
        print("Clean exit.")

