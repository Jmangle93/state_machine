# vision_service.py
#
# Pluggable vision service with two complementary approaches:
#
#   Template matching (OpenCV)
#   --------------------------
#   find_template()        — locate a template image anywhere on screen
#   verify_template_at()   — confirm a template is still present near a position
#
#   Text search (Tesseract OCR via pytesseract)
#   -------------------------------------------
#   find_text()            — locate a text string anywhere on screen;
#                            returns the (x, y) centre of its bounding box
#   read_region()          — OCR a specific screen region; returns the raw string
#   verify_text_at()       — confirm expected text exists near a known position;
#                            useful for validating a template match before acting
#
# Dependencies:
#   pip install opencv-python mss pytesseract numpy
#   + Tesseract binary: https://github.com/tesseract-ocr/tesseract
#     Windows: set TESSERACT_CMD below to the .exe path
#     macOS:   brew install tesseract
#     Linux:   apt install tesseract-ocr

import cv2
import numpy as np
import mss
import pytesseract
from typing import Optional, Tuple

# Uncomment and set this on Windows if tesseract is not on your PATH:
# pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"


class VisionService:
    def __init__(self, threshold: float = 0.85):
        self.threshold = threshold
        self._sct = mss.mss()   # Shared mss context — kept open for the session

    # ------------------------------------------------------------------
    # Template matching
    # ------------------------------------------------------------------

    def find_template(
        self,
        template_path: str,
        context=None,
    ) -> Optional[Tuple[int, int]]:
        """
        Search the full screen for template_path using normalised cross-correlation.
        Returns the (x, y) centre of the best match if it meets the threshold,
        or None. Pass context to enable automatic vision logging.
        """
        screenshot_gray = self._grab_screen_gray()
        template = cv2.imread(template_path, cv2.IMREAD_GRAYSCALE)
        result = cv2.matchTemplate(screenshot_gray, template, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(result)

        if max_val >= self.threshold:
            h, w = template.shape
            position = (max_loc[0] + w // 2, max_loc[1] + h // 2)
        else:
            position = None

        if context is not None:
            context.logger.log_vision(
                context._current_state_name, template_path,
                found=position is not None, position=position,
            )
        return position

    def verify_template_at(
        self,
        template_path: str,
        position: Tuple[int, int],
        region_size: int = 60,
        context=None,
    ) -> bool:
        """
        Confirm that template_path still appears near a known position by
        checking a small region around it. Faster and more accurate than a
        full-screen search when you already know roughly where to look.
        """
        region = self._region_around(position, region_size)
        screenshot_gray = cv2.cvtColor(
            np.array(self._sct.grab(region)), cv2.COLOR_BGR2GRAY
        )
        template = cv2.imread(template_path, cv2.IMREAD_GRAYSCALE)
        result = cv2.matchTemplate(screenshot_gray, template, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, _ = cv2.minMaxLoc(result)
        found = max_val >= self.threshold

        if context is not None:
            context.logger.log_vision(
                context._current_state_name, template_path,
                found=found, position=position if found else None,
            )
        return found

    # ------------------------------------------------------------------
    # Text search (OCR)
    # ------------------------------------------------------------------

    def find_text(
        self,
        text: str,
        context=None,
        case_sensitive: bool = False,
    ) -> Optional[Tuple[int, int]]:
        """
        Search the full screen for `text` using Tesseract OCR.
        Returns the (x, y) centre of the first matching word bounding box,
        or None if not found.

        Best used for locating UI labels whose position is unknown at authoring
        time. For known positions, verify_text_at() is faster and more accurate.
        """
        screenshot = np.array(self._sct.grab(self._sct.monitors[1]))
        screenshot_rgb = cv2.cvtColor(screenshot, cv2.COLOR_BGR2RGB)

        data = pytesseract.image_to_data(
            screenshot_rgb,
            output_type=pytesseract.Output.DICT,
        )

        needle = text if case_sensitive else text.lower()
        position = None

        for i, word in enumerate(data["text"]):
            haystack = word if case_sensitive else word.lower()
            if needle in haystack and int(data["conf"][i]) > 0:
                x = data["left"][i] + data["width"][i] // 2
                y = data["top"][i] + data["height"][i] // 2
                position = (x, y)
                break

        if context is not None:
            context.logger.log_vision(
                context._current_state_name,
                f"[text] '{text}'",
                found=position is not None,
                position=position,
            )
        return position

    def read_region(
        self,
        region: dict,
        context=None,
    ) -> str:
        """
        OCR a specific screen region and return the extracted text as a string.
        Use this to read dynamic values (counters, labels, status text) that
        change at runtime and cannot be pre-templated.

        Args:
            region:  mss-style dict with keys: left, top, width, height.
            context: FSM context for logging (optional).

        Example:
            text = context.vision.read_region(
                {"left": 100, "top": 200, "width": 150, "height": 30},
                context=context,
            )
        """
        screenshot = np.array(self._sct.grab(region))
        screenshot_rgb = cv2.cvtColor(screenshot, cv2.COLOR_BGR2RGB)
        result = pytesseract.image_to_string(screenshot_rgb).strip()

        if context is not None:
            context.logger._logger.debug(
                f"[vision] read_region {region} -> '{result}'"
            )
        return result

    def verify_text_at(
        self,
        text: str,
        position: Tuple[int, int],
        region_size: int = 80,
        context=None,
        case_sensitive: bool = False,
    ) -> bool:
        """
        Confirm that `text` appears in a small region around a known position.

        The recommended pattern is to combine this with find_template():
            pos = context.vision.find_template("templates/ok_btn.png", context)
            if pos and context.vision.verify_text_at("OK", pos, context=context):
                context.input.click(pos)

        This catches cases where a template matches the right shape but the
        wrong content (e.g. two visually similar buttons with different labels).
        """
        region = self._region_around(position, region_size)
        screenshot = np.array(self._sct.grab(region))
        screenshot_rgb = cv2.cvtColor(screenshot, cv2.COLOR_BGR2RGB)
        ocr_result = pytesseract.image_to_string(screenshot_rgb)

        needle = text if case_sensitive else text.lower()
        found = needle in (ocr_result if case_sensitive else ocr_result.lower())

        if context is not None:
            context.logger.log_vision(
                context._current_state_name,
                f"[text@pos] '{text}'",
                found=found,
                position=position if found else None,
            )
        return found

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _grab_screen_gray(self) -> np.ndarray:
        screenshot = np.array(self._sct.grab(self._sct.monitors[1]))
        return cv2.cvtColor(screenshot, cv2.COLOR_BGR2GRAY)

    def _region_around(self, position: Tuple[int, int], size: int) -> dict:
        x, y = position
        return {
            "left": int(x - size),
            "top": int(y - size),
            "width": size * 2,
            "height": size * 2,
        }

    def __del__(self):
        self._sct.close()