# click_step.py
#
# Dataclass definitions for configuring a ClickSequenceState.
# Each step in a sequence is one of:
#   - ClickStep       : find a template, left-click it
#   - RightClickStep  : find a template, right-click it, then find and
#                       left-click a second template (the context menu item)
#
# Retry behaviour is controlled per-step via RetryConfig.

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class RetryConfig:
    """Polling retry parameters used by find_with_retry()."""
    max_retries: int = 5
    min_delay: float = 0.5
    max_delay: float = 1.5


@dataclass
class ClickStep:
    """
    Locate `template` on screen and left-click it.

    Attributes:
        template:       Path to the template image.
        retry:          Retry/polling config for finding the template.
        post_wait_min:  Minimum seconds to wait after clicking.
        post_wait_max:  Maximum seconds to wait after clicking.
        label:          Human-readable name shown in logs (defaults to template path).
    """
    template: str
    retry: RetryConfig = field(default_factory=RetryConfig)
    post_wait_min: float = 0.4
    post_wait_max: float = 0.8
    label: Optional[str] = None

    def __post_init__(self):
        if self.label is None:
            self.label = self.template


@dataclass
class RightClickStep:
    """
    Locate `template` on screen, right-click it, then locate
    `menu_template` (the context menu item that appears) and left-click it.

    Both the initial template and the menu item use the same RetryConfig,
    since the menu item may take a moment to appear after the right-click.

    Attributes:
        template:       Path to the template to right-click.
        menu_template:  Path to the context menu item template to click after.
        retry:          Retry/polling config for both template lookups.
        post_wait_min:  Minimum seconds to wait after the final click.
        post_wait_max:  Maximum seconds to wait after the final click.
        label:          Human-readable name shown in logs.
    """
    template: str
    menu_template: str
    retry: RetryConfig = field(default_factory=RetryConfig)
    post_wait_min: float = 0.4
    post_wait_max: float = 0.8
    label: Optional[str] = None

    def __post_init__(self):
        if self.label is None:
            self.label = self.template