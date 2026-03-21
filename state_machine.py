# state_machine.py

import time
from abc import ABC, abstractmethod
from typing import Optional

from context import Context


class State(ABC):
    def __init__(self, name: str):
        self.name = name

    def on_enter(self, context: Context) -> Optional[str]:
        """
        Called once when transitioning INTO this state.
        Return a state name to immediately redirect, or None to proceed normally.
        Useful for visual validation or precondition checks on entry.
        """
        return None

    @abstractmethod
    def execute(self, context: Context) -> Optional[str]:
        """
        Perform this state's logic.
        Return the next state name, or None to stay in this state.
        """
        pass


class StateMachine:
    def __init__(self, context: Context):
        self.states: dict[str, State] = {}
        self.current_state: Optional[State] = None
        self.context = context

    def add_state(self, state: State):
        self.states[state.name] = state

    def set_start(self, state_name: str):
        if state_name not in self.states:
            raise ValueError(f"Unknown start state: '{state_name}'. Did you forget to add_state()?")
        self.current_state = self.states[state_name]

    def _transition_to(self, state_name: str):
        """Perform a logged transition to a named state."""
        if state_name not in self.states:
            self.context.logger.log_error(
                self.current_state.name if self.current_state else "none",
                f"Transition to unknown state '{state_name}'"
            )
            raise ValueError(f"Unknown state: '{state_name}'")

        from_name = self.current_state.name if self.current_state else "none"
        self.current_state = self.states[state_name]
        self.context._set_current_state(state_name)
        self.context.logger.log_transition(from_name, state_name)

    def run(self):
        if not self.current_state:
            raise RuntimeError("No start state set. Call set_start() before run().")

        # Announce the initial state
        self.context._set_current_state(self.current_state.name)
        self.context.logger.log_transition("(start)", self.current_state.name)

        while self.context.running:
            # Yield while user has control
            if self.context.interrupted:
                time.sleep(0.1)
                continue

            try:
                # on_enter hook — allows visual validation / early redirect
                redirect = self.current_state.on_enter(self.context)
                if redirect:
                    self._transition_to(redirect)
                    continue

                next_state = self.current_state.execute(self.context)

                if next_state:
                    self._transition_to(next_state)

            except Exception as exc:
                self.context.logger.log_error(
                    self.current_state.name,
                    "Unhandled exception in state execution",
                    exc
                )
                raise

        self.context.logger.close()
