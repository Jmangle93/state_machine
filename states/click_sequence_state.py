# states/click_sequence_state.py
#
# Reusable base class for any state that needs to:
#   1. Confirm a target app is open and focused (on_enter)
#   2. Execute a sequence of left-clicks and/or right-click+menu steps
#
# Usage — subclass and define the class-level attributes:
#
#   from click_step import ClickStep, RightClickStep, RetryConfig
#   from states.click_sequence_state import ClickSequenceState
#
#   class OpenInventoryState(ClickSequenceState):
#       name         = "OpenInventoryState"
#       window_title = "My Game"
#       launch_cmd   = None
#       next_state   = "InventoryReadyState"
#       steps = [
#           ClickStep("templates/menu_button.png", label="Menu button"),
#           RightClickStep(
#               template="templates/item_icon.png",
#               menu_template="templates/use_item.png",
#               retry=RetryConfig(max_retries=8, min_delay=1.0, max_delay=3.0),
#               label="Use item",
#           ),
#       ]

from typing import Optional, List, Union

from app_launcher import AppLauncher
from click_step import ClickStep, RightClickStep
from context import Context
from state_machine import State
from vision_retry import find_with_retry


# Type alias for a sequence step
Step = Union[ClickStep, RightClickStep]


class ClickSequenceState(State):
    """
    Base class for states that click through a fixed sequence of UI elements.

    Subclasses must define:
        name         (str)         Unique state name registered with the FSM.
        window_title (str)         Substring of the target window's title.
        next_state   (str)         State to transition to on success.
        steps        (list[Step])  Ordered list of ClickStep / RightClickStep.

    Subclasses may optionally define:
        launch_cmd   (str | None)  Shell command to launch the app if not running.
    """

    # -- Subclasses override these --
    window_title: str = "My App"
    launch_cmd: Optional[str] = None
    next_state: str = ""
    steps: List[Step] = []

    def __init__(self):
        super().__init__(self.__class__.name if isinstance(self.__class__.name, str)
                         else self.__class__.__name__)
        self._launcher = AppLauncher()

    # ------------------------------------------------------------------
    # on_enter — verify the app is open and focused
    # ------------------------------------------------------------------

    def on_enter(self, context: Context) -> Optional[str]:
        context.logger._logger.info(f"[{self.name}] on_enter: checking app focus")

        focused = self._launcher.ensure_focused(
            window_title=self.__class__.window_title,
            launch_cmd=self.__class__.launch_cmd,
            timeout=10.0,
        )

        if not focused:
            context.logger.log_error(
                self.name,
                f"Could not find or open window matching "
                f"'{self.__class__.window_title}'. Stopping."
            )
            context.stop()
            return None

        context.logger._logger.info(
            f"[{self.name}] on_enter: '{self.__class__.window_title}' is focused"
        )
        return None

    # ------------------------------------------------------------------
    # execute — run through each step in order
    # ------------------------------------------------------------------

    def execute(self, context: Context) -> Optional[str]:
        for i, step in enumerate(self.__class__.steps, start=1):
            step_tag = f"[{self.name}] step {i}/{len(self.__class__.steps)} ({step.label})"

            if isinstance(step, ClickStep):
                success = self._run_click(step, step_tag, context)
            elif isinstance(step, RightClickStep):
                success = self._run_right_click(step, step_tag, context)
            else:
                context.logger.log_error(self.name, f"Unknown step type: {type(step)}")
                context.stop()
                return None

            if not success:
                context.stop()
                return None

        context.logger._logger.info(
            f"[{self.name}] All {len(self.__class__.steps)} steps complete, "
            f"transitioning to {self.__class__.next_state}"
        )
        return self.__class__.next_state

    # ------------------------------------------------------------------
    # Private step runners
    # ------------------------------------------------------------------

    def _run_click(self, step: ClickStep, tag: str, context: Context) -> bool:
        """Find the template and left-click it. Returns False on failure."""
        context.logger._logger.info(
            f"{tag} — left-click, up to {step.retry.max_retries} attempts "
            f"({step.retry.min_delay}–{step.retry.max_delay}s delay)"
        )

        pos = find_with_retry(
            step.template, context,
            max_retries=step.retry.max_retries,
            min_delay=step.retry.min_delay,
            max_delay=step.retry.max_delay,
        )

        if pos is None:
            return False

        context.logger._logger.info(f"{tag} — clicking at {pos}")
        context.input.click(pos)
        context.input.wait(min_time=step.post_wait_min, max_time=step.post_wait_max)
        return True

    def _run_right_click(self, step: RightClickStep, tag: str, context: Context) -> bool:
        """Right-click the primary template, then find and click the menu item."""

        # 1. Find and right-click the primary target
        context.logger._logger.info(
            f"{tag} — right-click, up to {step.retry.max_retries} attempts "
            f"({step.retry.min_delay}–{step.retry.max_delay}s delay)"
        )

        pos = find_with_retry(
            step.template, context,
            max_retries=step.retry.max_retries,
            min_delay=step.retry.min_delay,
            max_delay=step.retry.max_delay,
        )

        if pos is None:
            return False

        context.logger._logger.info(f"{tag} — right-clicking at {pos}")
        context.input.right_click(pos)
        context.input.wait(min_time=step.post_wait_min, max_time=step.post_wait_max)

        # 2. Find and left-click the context menu item (same retry config)
        context.logger._logger.info(
            f"{tag} — seeking menu item, up to {step.retry.max_retries} attempts"
        )

        menu_pos = find_with_retry(
            step.menu_template, context,
            max_retries=step.retry.max_retries,
            min_delay=step.retry.min_delay,
            max_delay=step.retry.max_delay,
        )

        if menu_pos is None:
            return False

        context.logger._logger.info(f"{tag} — clicking menu item at {menu_pos}")
        context.input.click(menu_pos)
        context.input.wait(min_time=step.post_wait_min, max_time=step.post_wait_max)
        return True