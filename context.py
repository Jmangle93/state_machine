# context.py
from app_launcher import AppLauncher
import pyautogui
import threading
import time

class Context:
    def __init__(self, vision_service, input_service):
        self.vision = vision_service
        self.input = input_service
        self.data = {}
        self.running = True
        self.launcher = AppLauncher()
        self.interrupted = False
        self._last_mouse_pos = pyautogui.position()
        self._interrupt_thread = threading.Thread(target=self._watch_mouse, daemon=True)
        self._interrupt_thread.start()

    def _watch_mouse(self, threshold=15, resume_after=2.0):
        while self.running:
            pos = pyautogui.position()
            dx = abs(pos[0] - self._last_mouse_pos[0])
            dy = abs(pos[1] - self._last_mouse_pos[1])
            if dx > threshold or dy > threshold:
                self.interrupted = True
                self._last_mouse_pos = pos
                self._last_human_activity = time.time()
            elif self.interrupted:
                if time.time() - self._last_human_activity > resume_after:
                    self.interrupted = False
            self._last_mouse_pos = pos
            time.sleep(0.1)
