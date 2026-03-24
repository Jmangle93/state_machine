# states/wait_state.py
#
# A reusable polling state that waits for a condition to become true before
# transitioning. Useful as a buffer between action states when an app needs
# time to load, animate, or respond.
#
# Supports three wait modes (set by configuring the class attributes):
#   Template   -- set `template`; waits until the image appears on screen.
#   Text       -- set `wait_text`; waits until the string appears via OCR.
#   Either     -- set both; transitions as soon as either condition is met.
#
# Usage:
#
#   class InventoryLoadedState(WaitState):
#       name         = "InventoryLoadedState"
#       next_state   = "ReadInventoryState"
#       template     = "templates/inventory_panel.png"
#       # -- or wait for text --
#       wait_text    = "Inventory"
#       # -- or wait for either --
#       template     = "templates/inventory_panel.png"
#       wait_text    = "Inventory"
#       retry        = RetryConfig(max_retries=20, min_delay=0.5, max_delay=1.5)

import time
import random
from typing import Optional

from click_step import RetryConfig
from context import Context
from state_machine import State


class WaitState(State):
    """
    Polls for a template, a text string, or either, then transitions.

    Subclasses must define:
        name        (str)            Unique FSM state name.
        next_state  (str)            State to transition to when condition is met.

    Subclasses must define at least one of:
        template    (str|None)       Template image path to wait for.
        wait_text   (str|None)       Text string to wait for via full-screen OCR.

    Subclasses may optionally define:
        retry       (RetryConfig)    Polling config (attempts, delays).
        fail_state  (str|None)       State to transition to on timeout.
                                     If None, the machine stops on timeout.
    """

    template:   Optional[str]        = None
    wait_text:  Optional[str]        = None
    retry:      RetryConfig          = RetryConfig(max_retries=20, min_delay=0.5, max_delay=1.5)
    fail_state: Optional[str]        = None

    def __init__(self):
        cls = self.__class__
        name = cls.__dict__.get("name", cls.__name__)
        super().__init__(name)
        self._validate()

    def _validate(self):
        if not self.__class__.template and not self.__class__.wait_text:
            raise ValueError(
                f"WaitState '{self.name}': at least one of `template` or "
                f"`wait_text` must be set."
            )

    # on_enter is intentionally omitted -- WaitState does not require an app
    # focus check. Add one in a subclass if needed.

    def execute(self, context: Context) -> Optional[str]:
        cls      = self.__class__
        retry    = cls.retry
        template = cls.template
        text     = cls.wait_text

        mode = (
            "template or text" if (template and text)
            else "template"    if template
            else "text"
        )
        context.logger._logger.info(
            f"[{self.name}] Waiting for {mode} "
            f"(up to {retry.max_retries} attempts, "
            f"{retry.min_delay}-{retry.max_delay}s delay)"
        )

        for attempt in range(1, retry.max_retries + 1):
            found, what = self._check(template, text, context)

            if found:
                context.logger._logger.info(
                    f"[{self.name}] Condition met ({what}) "
                    f"on attempt {attempt}/{retry.max_retries}, "
                    f"transitioning to {cls.next_state}"
                )
                return cls.next_state

            if attempt < retry.max_retries:
                delay = random.uniform(retry.min_delay, retry.max_delay)
                context.logger._logger.debug(
                    f"[{self.name}] Not yet (attempt {attempt}/{retry.max_retries}), "
                    f"retrying in {delay:.2f}s"
                )
                time.sleep(delay)

        # Timeout
        context.logger.log_error(
            self.name,
            f"Condition not met after {retry.max_retries} attempts "
            f"(template={template!r}, wait_text={text!r})",
        )

        if cls.fail_state:
            context.logger._logger.info(
                f"[{self.name}] Transitioning to fail_state '{cls.fail_state}'"
            )
            return cls.fail_state

        context.stop()
        return None

    def _check(
        self,
        template: Optional[str],
        text: Optional[str],
        context: Context,
    ):
        """
        Check whether either wait condition is satisfied.
        Returns (True, description) on success, (False, None) otherwise.
        """
        if template:
            pos = context.vision.find_template(template, context=context)
            if pos is not None:
                return True, f"template '{template}' at {pos}"

        if text:
            pos = context.vision.find_text(text, context=context)
            if pos is not None:
                return True, f"text '{text}' at {pos}"

        return False, None