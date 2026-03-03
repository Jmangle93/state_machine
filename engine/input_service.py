# input_service.py

import pyautogui
import random
import time


class InputService:
    def click(self, position):
        x, y = position
        pyautogui.moveTo(
            x + random.randint(-2, 2),
            y + random.randint(-2, 2),
            duration=random.uniform(0.05, 0.15)
        )
        pyautogui.click()

    def wait(self, min_time=0.3, max_time=0.6):
        time.sleep(random.uniform(min_time, max_time))
