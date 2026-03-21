# context.py

import threading
import time
import logging
import json
from datetime import datetime
from pathlib import Path

import pyautogui


# ---------------------------------------------------------------------------
# Structured logger — writes both to console and a JSONL file
# ---------------------------------------------------------------------------

class ContextLogger:
    """
    Writes structured log entries as newline-delimited JSON (JSONL).
    Each entry has: timestamp, level, event_type, state, and event-specific fields.

    Log file location defaults to logs/session_<timestamp>.jsonl
    """

    def __init__(self, log_dir: str = "logs"):
        Path(log_dir).mkdir(exist_ok=True)
        session_ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_path = Path(log_dir) / f"session_{session_ts}.jsonl"

        # Human-readable console handler
        console = logging.StreamHandler()
        console.setLevel(logging.DEBUG)
        console.setFormatter(logging.Formatter("[%(asctime)s] %(levelname)-8s %(message)s", "%H:%M:%S"))

        self._logger = logging.getLogger(f"state_machine.{session_ts}")
        self._logger.setLevel(logging.DEBUG)
        self._logger.addHandler(console)
        self._logger.propagate = False

        self._file = open(self.log_path, "a", buffering=1)  # line-buffered

    def _write(self, entry: dict):
        entry["timestamp"] = datetime.now().isoformat()
        self._file.write(json.dumps(entry) + "\n")

    # -- Public log methods called by Context and StateMachine --

    def log_data_change(self, state_name: str, key: str, old_value, new_value):
        self._logger.debug(f"[data] {state_name} | {key}: {old_value!r} → {new_value!r}")
        self._write({
            "level": "DEBUG",
            "event": "data_change",
            "state": state_name,
            "key": key,
            "old": _serializable(old_value),
            "new": _serializable(new_value),
        })

    def log_transition(self, from_state: str, to_state: str):
        self._logger.info(f"[transition] {from_state} → {to_state}")
        self._write({
            "level": "INFO",
            "event": "transition",
            "from": from_state,
            "to": to_state,
        })

    def log_vision(self, state_name: str, template: str, found: bool, position=None):
        status = f"found at {position}" if found else "not found"
        self._logger.debug(f"[vision] {state_name} | {template} — {status}")
        self._write({
            "level": "DEBUG",
            "event": "vision_check",
            "state": state_name,
            "template": template,
            "found": found,
            "position": position,
        })

    def log_interrupt(self, interrupted: bool):
        action = "paused (user interrupt)" if interrupted else "resumed"
        self._logger.info(f"[interrupt] FSM {action}")
        self._write({
            "level": "INFO",
            "event": "interrupt",
            "interrupted": interrupted,
        })

    def log_error(self, state_name: str, message: str, exc: Exception = None):
        self._logger.error(f"[error] {state_name} | {message}" + (f": {exc}" if exc else ""))
        self._write({
            "level": "ERROR",
            "event": "error",
            "state": state_name,
            "message": message,
            "exception": str(exc) if exc else None,
        })

    def close(self):
        self._file.close()


def _serializable(value):
    """Convert a value to something JSON-safe."""
    try:
        json.dumps(value)
        return value
    except (TypeError, ValueError):
        return repr(value)


# ---------------------------------------------------------------------------
# Context — carries shared state across all FSM states
# ---------------------------------------------------------------------------

class Context:
    def __init__(self, vision_service, input_service, log_dir: str = "logs",
                 interrupt_threshold: int = 15, interrupt_resume_after: float = 2.0):
        self.vision = vision_service
        self.input = input_service
        self.running = True
        self.interrupted = False
        self.logger = ContextLogger(log_dir=log_dir)

        # Internal data store — use get()/set() rather than .data[] directly
        self._data: dict = {}

        # Track the current state name so log entries are always annotated
        self._current_state_name: str = "none"

        # Mouse interrupt watcher
        self._interrupt_threshold = interrupt_threshold
        self._interrupt_resume_after = interrupt_resume_after
        self._last_mouse_pos = pyautogui.position()
        self._last_human_activity: float = 0.0
        self._interrupt_thread = threading.Thread(target=self._watch_mouse, daemon=True)
        self._interrupt_thread.start()

    # -- Data accessors ------------------------------------------------------

    def get(self, key: str, default=None):
        """Retrieve a value from the shared data store."""
        return self._data.get(key, default)

    def set(self, key: str, value) -> None:
        """Store a value and log the change."""
        old = self._data.get(key)
        self._data[key] = value
        if old != value:
            self.logger.log_data_change(self._current_state_name, key, old, value)

    def delete(self, key: str) -> None:
        """Remove a key from the store."""
        if key in self._data:
            old = self._data.pop(key)
            self.logger.log_data_change(self._current_state_name, key, old, None)

    def snapshot(self) -> dict:
        """Return a shallow copy of the entire data store (useful for debugging)."""
        return dict(self._data)

    # -- State name tracking (set by StateMachine) ---------------------------

    def _set_current_state(self, name: str):
        self._current_state_name = name

    # -- Mouse interrupt watcher ---------------------------------------------

    def _watch_mouse(self):
        while self.running:
            pos = pyautogui.position()
            dx = abs(pos[0] - self._last_mouse_pos[0])
            dy = abs(pos[1] - self._last_mouse_pos[1])

            if dx > self._interrupt_threshold or dy > self._interrupt_threshold:
                if not self.interrupted:
                    self.interrupted = True
                    self.logger.log_interrupt(interrupted=True)
                self._last_human_activity = time.time()

            elif self.interrupted:
                if time.time() - self._last_human_activity > self._interrupt_resume_after:
                    self.interrupted = False
                    self.logger.log_interrupt(interrupted=False)

            self._last_mouse_pos = pos
            time.sleep(0.1)

    # -- Cleanup -------------------------------------------------------------

    def stop(self):
        """Gracefully stop the FSM and flush logs."""
        self.running = False
        self.logger.close()
