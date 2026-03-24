# states/click_sequence_state.py
#
# Reusable base class for any state that clicks through a fixed sequence of
# UI elements, with optional per-step text confirmation and coordinate support.
#
# Subclass and define these class-level attributes:
#
#   class MyState(ClickSequenceState):
#       name         = "MyState"
#       window_title = "My App"
#       launch_cmd   = None
#       next_state   = "NextState"
#       steps = [
#           ClickStep(position=(640, 480), confirm_text="Start", label="Start tile"),
#           RightClickStep(template="templates/item.png",
#                          menu_template="templates/use.png"),
#       ]

from typing import List, Optional, Tuple, Union

from app_launcher import AppLauncher
from click_step import ClickStep, RightClickStep, TargetStrategy
from context import Context
from state_machine import State
from vision_retry import find_with_retry

Step = Union[ClickStep, RightClickStep]


class ClickSequenceState(State):
    """
    Base class for states that execute a fixed sequence of click steps.

    Subclasses must define:
        name         (str)         Unique FSM state name.
        window_title (str)         Substring of the target window title.
        next_state   (str)         State to transition to on full success.
        steps        (list[Step])  Ordered ClickStep / RightClickStep list.

    Subclasses may optionally define:
        launch_cmd   (str|None)    Shell command to launch the app if not running.
    """

    window_title: str          = "My App"
    launch_cmd:   Optional[str] = None
    next_state:   str          = ""
    steps:        List[Step]   = []

    def __init__(self):
        cls = self.__class__
        name = cls.__dict__.get("name", cls.__name__)
        super().__init__(name)
        self._launcher = AppLauncher()

    # ------------------------------------------------------------------
    # on_enter -- verify the app is open and focused
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
                f"'{self.__class__.window_title}'. Stopping.",
            )
            context.stop()
            return None

        context.logger._logger.info(
            f"[{self.name}] on_enter: '{self.__class__.window_title}' is focused"
        )
        return None

    # ------------------------------------------------------------------
    # execute -- run each step in order
    # ------------------------------------------------------------------

    def execute(self, context: Context) -> Optional[str]:
        steps = self.__class__.steps
        for i, step in enumerate(steps, start=1):
            tag = f"[{self.name}] step {i}/{len(steps)} ({step.label})"

            if isinstance(step, ClickStep):
                success = self._run_click(step, tag, context)
            elif isinstance(step, RightClickStep):
                success = self._run_right_click(step, tag, context)
            else:
                context.logger.log_error(self.name, f"Unknown step type: {type(step)}")
                context.stop()
                return None

            if not success:
                context.stop()
                return None

        context.logger._logger.info(
            f"[{self.name}] All {len(steps)} steps complete, "
            f"transitioning to {self.__class__.next_state}"
        )
        return self.__class__.next_state

    # ------------------------------------------------------------------
    # Step runners
    # ------------------------------------------------------------------

    def _run_click(self, step: ClickStep, tag: str, context: Context) -> bool:
        """Resolve the target position, confirm text if required, then click."""
        pos = self._resolve_position(step, tag, context)
        if pos is None:
            return False

        if step.confirm_text is not None:
            if not self._confirm_text(step, pos, tag, context):
                return False

        context.logger._logger.info(f"{tag} -- clicking at {pos}")
        context.input.click(pos)
        context.input.wait(min_time=step.post_wait_min, max_time=step.post_wait_max)
        return True

    def _run_right_click(
        self, step: RightClickStep, tag: str, context: Context
    ) -> bool:
        """Right-click the primary template, then click the menu item."""
        context.logger._logger.info(
            f"{tag} -- right-click search, up to {step.retry.max_retries} attempts "
            f"({step.retry.min_delay}-{step.retry.max_delay}s delay)"
        )
        pos = find_with_retry(
            step.template, context,
            max_retries=step.retry.max_retries,
            min_delay=step.retry.min_delay,
            max_delay=step.retry.max_delay,
        )
        if pos is None:
            return False

        context.logger._logger.info(f"{tag} -- right-clicking at {pos}")
        context.input.right_click(pos)
        context.input.wait(min_time=step.post_wait_min, max_time=step.post_wait_max)

        context.logger._logger.info(
            f"{tag} -- seeking menu item, up to {step.retry.max_retries} attempts"
        )
        menu_pos = find_with_retry(
            step.menu_template, context,
            max_retries=step.retry.max_retries,
            min_delay=step.retry.min_delay,
            max_delay=step.retry.max_delay,
        )
        if menu_pos is None:
            return False

        context.logger._logger.info(f"{tag} -- clicking menu item at {menu_pos}")
        context.input.click(menu_pos)
        context.input.wait(min_time=step.post_wait_min, max_time=step.post_wait_max)
        return True

    # ------------------------------------------------------------------
    # Target resolution
    # ------------------------------------------------------------------

    def _resolve_position(
        self, step: ClickStep, tag: str, context: Context
    ) -> Optional[Tuple[int, int]]:
        """
        Return the (x, y) position to click based on the step's TargetStrategy.

        COORDINATE_ONLY  -- return step.position directly.
        TEMPLATE_ONLY    -- search for step.template; return match or None.
        COORDINATE_FIRST -- move to step.position first; if confirm_text is set
                            and fails, fall back to template search.
        TEMPLATE_FIRST   -- search for step.template first; if not found, fall
                            back to step.position.
        """
        strategy = step.strategy

        if strategy == TargetStrategy.COORDINATE_ONLY:
            context.logger._logger.info(
                f"{tag} -- using fixed coordinate {step.position}"
            )
            return step.position

        if strategy == TargetStrategy.TEMPLATE_ONLY:
            context.logger._logger.info(
                f"{tag} -- template search, up to {step.retry.max_retries} attempts "
                f"({step.retry.min_delay}-{step.retry.max_delay}s delay)"
            )
            return find_with_retry(
                step.template, context,
                max_retries=step.retry.max_retries,
                min_delay=step.retry.min_delay,
                max_delay=step.retry.max_delay,
            )

        if strategy == TargetStrategy.COORDINATE_FIRST:
            context.logger._logger.info(
                f"{tag} -- coordinate-first: trying {step.position}"
            )
            # Move to coordinate so hover labels appear, then check confirm_text
            context.input.mouse_to(step.position)
            context.input.wait(min_time=0.15, max_time=0.25)
            if step.confirm_text and not self._confirm_text(step, step.position, tag, context):
                context.logger._logger.info(
                    f"{tag} -- coordinate confirm failed, falling back to template"
                )
                return find_with_retry(
                    step.template, context,
                    max_retries=step.retry.max_retries,
                    min_delay=step.retry.min_delay,
                    max_delay=step.retry.max_delay,
                )
            return step.position

        if strategy == TargetStrategy.TEMPLATE_FIRST:
            context.logger._logger.info(
                f"{tag} -- template-first search, up to {step.retry.max_retries} attempts"
            )
            pos = find_with_retry(
                step.template, context,
                max_retries=step.retry.max_retries,
                min_delay=step.retry.min_delay,
                max_delay=step.retry.max_delay,
            )
            if pos is None:
                context.logger._logger.info(
                    f"{tag} -- template not found, falling back to coordinate {step.position}"
                )
                return step.position
            return pos

        context.logger.log_error(self.name, f"Unknown TargetStrategy: {strategy}")
        return None

    # ------------------------------------------------------------------
    # Text confirmation
    # ------------------------------------------------------------------

    def _confirm_text(
        self,
        step: ClickStep,
        pos: Tuple[int, int],
        tag: str,
        context: Context,
    ) -> bool:
        """
        Verify step.confirm_text is visible before committing a click.

        If step.confirm_region is set, OCR that static region.
        Otherwise, OCR a region around `pos` (covers hover labels).
        Logs the result and returns True on success, False on failure.
        """
        if step.confirm_region is not None:
            context.logger._logger.info(
                f"{tag} -- confirming text '{step.confirm_text}' "
                f"in static region {step.confirm_region}"
            )
            found = self._ocr_region_contains(
                step.confirm_text, step.confirm_region, context
            )
        else:
            context.logger._logger.info(
                f"{tag} -- confirming text '{step.confirm_text}' "
                f"near position {pos} (hover label)"
            )
            # Move to position so the hover label appears, then OCR around it
            context.input.mouse_to(pos)
            context.input.wait(min_time=0.15, max_time=0.25)
            found = context.vision.verify_text_at(
                step.confirm_text, pos,
                region_size=step.confirm_region_size,
                context=context,
            )

        if not found:
            context.logger.log_error(
                self.name,
                f"{tag} -- confirm_text '{step.confirm_text}' not found. Stopping.",
            )
        return found

    def _ocr_region_contains(
        self, text: str, region: dict, context: Context
    ) -> bool:
        """OCR a static region and check whether it contains `text`."""
        result = context.vision.read_region(region, context=context)
        return text.lower() in result.lower()