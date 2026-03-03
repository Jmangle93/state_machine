# vision_service.py

import cv2
import numpy as np
import mss


class VisionService:
    def __init__(self, threshold=0.85):
        self.threshold = threshold

    def find_template(self, template_path):
        with mss.mss() as sct:
            monitor = sct.monitors[1]
            screenshot = np.array(sct.grab(monitor))
            screenshot_gray = cv2.cvtColor(screenshot, cv2.COLOR_BGR2GRAY)

        template = cv2.imread(template_path, 0)
        result = cv2.matchTemplate(
            screenshot_gray, template, cv2.TM_CCOEFF_NORMED
        )

        _, max_val, _, max_loc = cv2.minMaxLoc(result)

        if max_val >= self.threshold:
            h, w = template.shape
            center_x = max_loc[0] + w // 2
            center_y = max_loc[1] + h // 2
            return (center_x, center_y)

        return None
