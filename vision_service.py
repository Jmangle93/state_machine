# vision_service.py

import cv2
import numpy as np
import mss


class VisionService:
    def __init__(self, threshold=0.85):
        self.threshold = threshold
        self._sct = mss.mss()   # Keep one mss context open for the session

    def find_template(self, template_path, context=None):
        """
        Search the full screen for template_path.
        Pass context to get automatic vision logging.
        Returns (center_x, center_y) on match, or None.
        """
        monitor = self._sct.monitors[1]
        screenshot = np.array(self._sct.grab(monitor))
        screenshot_gray = cv2.cvtColor(screenshot, cv2.COLOR_BGR2GRAY)

        template = cv2.imread(template_path, 0)
        result = cv2.matchTemplate(screenshot_gray, template, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(result)

        if max_val >= self.threshold:
            h, w = template.shape
            position = (max_loc[0] + w // 2, max_loc[1] + h // 2)
        else:
            position = None

        if context is not None:
            context.logger.log_vision(
                context._current_state_name,
                template_path,
                found=position is not None,
                position=position
            )

        return position

    def verify_template_at(self, template_path, position, region_size=60, context=None):
        """
        Check whether template_path appears near a known position.
        Pass context to get automatic vision logging.
        Returns True/False.
        """
        x, y = position
        region = {
            "left": int(x - region_size),
            "top": int(y - region_size),
            "width": region_size * 2,
            "height": region_size * 2,
        }

        screenshot = np.array(self._sct.grab(region))
        screenshot_gray = cv2.cvtColor(screenshot, cv2.COLOR_BGR2GRAY)

        template = cv2.imread(template_path, 0)
        result = cv2.matchTemplate(screenshot_gray, template, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, _ = cv2.minMaxLoc(result)

        found = max_val >= self.threshold

        if context is not None:
            context.logger.log_vision(
                context._current_state_name,
                template_path,
                found=found,
                position=position if found else None
            )

        return found

    def __del__(self):
        self._sct.close()