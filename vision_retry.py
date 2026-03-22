# vision_retry.py
#
# Reusable helper for polling a vision template with randomized delays
# between attempts. Import and use this in any state that needs retry logic.

import time
import random
from typing import Optional, Tuple

from context import Context


def find_with_retry(
    template_path: str,
    context: Context,
    max_retries: int = 5,
    min_delay: float = 0.5,
    max_delay: float = 1.5,
) -> Optional[Tuple[int, int]]:
    """
    Attempt to find a template on screen, retrying up to `max_retries` times.
    Waits a random duration between `min_delay` and `max_delay` seconds between
    each attempt.

    Returns the (x, y) center position on success, or None if all attempts fail.
    Logs every attempt (via vision_service logging) and a final failure summary.

    Args:
        template_path: Path to the template image file.
        context:       The shared FSM context (used for vision + logging).
        max_retries:   Maximum number of attempts before giving up.
        min_delay:     Minimum seconds to wait between retries.
        max_delay:     Maximum seconds to wait between retries.
    """
    for attempt in range(1, max_retries + 1):
        pos = context.vision.find_template(template_path, context=context)

        if pos is not None:
            if attempt > 1:
                context.logger._logger.info(
                    f"[vision_retry] '{template_path}' found on attempt {attempt}/{max_retries}"
                )
            return pos

        if attempt < max_retries:
            delay = random.uniform(min_delay, max_delay)
            context.logger._logger.debug(
                f"[vision_retry] '{template_path}' not found "
                f"(attempt {attempt}/{max_retries}), retrying in {delay:.2f}s"
            )
            time.sleep(delay)

    # All attempts exhausted
    context.logger.log_error(
        context._current_state_name,
        f"'{template_path}' not found after {max_retries} attempt(s) "
        f"(delays {min_delay}–{max_delay}s)"
    )
    return None