# click_step.py
#
# Dataclass definitions for configuring a ClickSequenceState.
#
# Each step in a sequence is one of:
#   ClickStep       -- resolve a target position, optionally confirm text, then left-click
#   RightClickStep  -- right-click a target, then find and left-click a context menu item
#
# Target resolution is controlled by TargetStrategy:
#   COORDINATE_ONLY  -- use the fixed `position` field directly (no template search)
#   TEMPLATE_ONLY    -- search for `template` on screen (original behaviour)
#   COORDINATE_FIRST -- try `position` first; fall back to `template` if confirm fails
#   TEMPLATE_FIRST   -- search for `template` first; fall back to `position` if not found
#
# Text confirmation (confirm_text):
#   If set, the resolved position is first verified via OCR before the click is sent.
#   The OCR region is determined by `confirm_region`:
#     - If confirm_region is provided, OCR is run on that static screen region.
#       Use this for labels that always appear at a fixed location (status bars, etc.)
#     - If confirm_region is None, OCR is run around the resolved click position.
#       Use this for hover labels that appear near the cursor when mousing over a tile.

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional, Tuple


# Screen region dict compatible with mss: {left, top, width, height}
Region = dict


class TargetStrategy(Enum):
    """Controls how a ClickStep resolves its target position."""
    COORDINATE_ONLY  = auto()   # Fixed position only -- fastest, no vision search
    TEMPLATE_ONLY    = auto()   # Template match only -- original behaviour
    COORDINATE_FIRST = auto()   # Coordinate preferred; template as fallback
    TEMPLATE_FIRST   = auto()   # Template preferred; coordinate as fallback


@dataclass
class RetryConfig:
    """Polling retry parameters used by find_with_retry() and WaitState."""
    max_retries: int   = 5
    min_delay:   float = 0.5
    max_delay:   float = 1.5


@dataclass
class ClickStep:
    """
    Resolve a target position and left-click it, with optional text confirmation.

    Target resolution (controlled by `strategy`):
        COORDINATE_ONLY  -- `position` must be set; `template` is ignored.
        TEMPLATE_ONLY    -- `template` must be set; `position` is ignored.
        COORDINATE_FIRST -- move to `position`, verify confirm_text if set,
                           fall back to template search if verification fails.
        TEMPLATE_FIRST   -- search for `template`, fall back to `position` if
                           the template is not found.

    Text confirmation (optional):
        If `confirm_text` is set, the vision service runs an OCR check before
        the click is committed. The source of the OCR region is:
          - `confirm_region` (if provided): a fixed {left, top, width, height}
            dict describing a static screen area -- use for labels in a fixed
            location (e.g. a status bar or info panel).
          - The resolved click position (if confirm_region is None): OCR is run
            in a small area around that position -- use for hover labels that
            appear near the cursor when the mouse moves over a tile or element.

    Attributes:
        position:             Fixed (x, y) coordinate to click.
        template:             Path to a template image to search for.
        strategy:             How to resolve the target (see TargetStrategy).
        confirm_text:         Text that must be present via OCR before clicking.
        confirm_region:       Static screen region to OCR for confirm_text.
                              If None, OCRs around the resolved click position.
        confirm_region_size:  Half-size of the dynamic OCR region (pixels).
        retry:                Retry config for template searches.
        post_wait_min:        Minimum seconds to wait after clicking.
        post_wait_max:        Maximum seconds to wait after clicking.
        label:                Human-readable name for logs.
    """
    position:             Optional[Tuple[int, int]] = None
    template:             Optional[str]             = None
    strategy:             TargetStrategy            = TargetStrategy.COORDINATE_ONLY
    confirm_text:         Optional[str]             = None
    confirm_region:       Optional[Region]          = None
    confirm_region_size:  int                       = 80
    retry:                RetryConfig               = field(default_factory=RetryConfig)
    post_wait_min:        float                     = 0.4
    post_wait_max:        float                     = 0.8
    label:                Optional[str]             = None

    def __post_init__(self):
        if self.label is None:
            if self.template:
                self.label = self.template
            elif self.position:
                self.label = str(self.position)
            else:
                self.label = "(unset)"
        self._validate()

    def _validate(self):
        if self.strategy == TargetStrategy.COORDINATE_ONLY and self.position is None:
            raise ValueError(
                f"ClickStep '{self.label}': strategy is COORDINATE_ONLY but no position set."
            )
        if self.strategy == TargetStrategy.TEMPLATE_ONLY and self.template is None:
            raise ValueError(
                f"ClickStep '{self.label}': strategy is TEMPLATE_ONLY but no template set."
            )
        if self.strategy in (TargetStrategy.COORDINATE_FIRST, TargetStrategy.TEMPLATE_FIRST):
            if self.position is None or self.template is None:
                raise ValueError(
                    f"ClickStep '{self.label}': strategy {self.strategy.name} "
                    f"requires both position and template to be set."
                )


@dataclass
class RightClickStep:
    """
    Right-click a target, then find and left-click a context menu item.

    The primary target is resolved by template search (TEMPLATE_ONLY).
    Both the primary template and the menu item use the same RetryConfig,
    since the menu may take a moment to appear after the right-click.

    Attributes:
        template:       Path to the template to right-click.
        menu_template:  Path to the context menu item template to click.
        retry:          Retry config for both template lookups.
        post_wait_min:  Minimum seconds to wait after the final click.
        post_wait_max:  Maximum seconds to wait after the final click.
        label:          Human-readable name for logs.
    """
    template:      str
    menu_template: str
    retry:         RetryConfig   = field(default_factory=RetryConfig)
    post_wait_min: float         = 0.4
    post_wait_max: float         = 0.8
    label:         Optional[str] = None

    def __post_init__(self):
        if self.label is None:
            self.label = self.template