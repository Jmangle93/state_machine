# input_service.py

import pyautogui
import random
import time


class InputService:
    def mouse_to(self, position):
        x, y = position
        pyautogui.moveTo(
            x + random.randint(-2, 2),
            y + random.randint(-2, 2),
            duration=random.uniform(0.05, 0.15)
        )

    def click(self, position):
        self.mouse_to(position)
        pyautogui.click()

    def right_click(self, position):
        self.mouse_to(position)
        pyautogui.rightClick()

    def wait(self, min_time=0.3, max_time=0.6):
        time.sleep(random.uniform(min_time, max_time))
