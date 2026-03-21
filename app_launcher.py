# app_launcher.py
import subprocess
import time
import pygetwindow as gw

# Usage:
# context.launcher.ensure_focused("My App", launch_cmd="myapp.exe")

class AppLauncher:
    def ensure_focused(self, window_title_substring: str, launch_cmd: str = None, timeout: float = 10.0) -> bool:
        """Find and focus a window, optionally launching it first. Returns True if successful."""
        windows = gw.getWindowsWithTitle(window_title_substring)
        if not windows and launch_cmd:
            subprocess.Popen(launch_cmd, shell=True)
            deadline = time.time() + timeout
            while time.time() < deadline:
                windows = gw.getWindowsWithTitle(window_title_substring)
                if windows:
                    break
                time.sleep(0.5)

        if windows:
            w = windows[0]
            w.restore()
            w.activate()
            return True
        return False
