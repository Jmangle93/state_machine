# app_launcher.py

import subprocess
import time

import pygetwindow as gw


class AppLauncher:
    def ensure_focused(
        self,
        window_title: str,
        launch_cmd: str = None,
        timeout: float = 10.0,
    ) -> bool:
        """
        Find a window whose title contains `window_title` and bring it to focus.
        If no matching window is found and `launch_cmd` is provided, launch the
        app and wait up to `timeout` seconds for the window to appear.

        Returns True if the window is focused, False if it could not be found.
        """
        window = self._find_window(window_title)

        if window is None and launch_cmd:
            subprocess.Popen(launch_cmd, shell=True)
            deadline = time.time() + timeout
            while time.time() < deadline:
                window = self._find_window(window_title)
                if window:
                    break
                time.sleep(0.5)

        if window:
            try:
                window.restore()
                window.activate()
                time.sleep(0.3)   # Brief settle before vision checks
                return True
            except Exception:
                return False

        return False

    def _find_window(self, title_substring: str):
        matches = gw.getWindowsWithTitle(title_substring)
        return matches[0] if matches else None