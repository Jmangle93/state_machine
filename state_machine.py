from abc import ABC, abstractmethod
from typing import Dict, Optional
from context import Context


class State(ABC):
    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    def execute(self, context: Context) -> Optional[str]:
        """
        Perform logic.
        Return next state name, or None to stay in same state.
        """
        pass


class StateMachine:
    def __init__(self, context):
        self.states = {}
        self.current_state: Optional[State] = None
        self.context = context

    def add_state(self, state: State):
        self.states[state.name] = state

    def set_start(self, state_name: str):
        self.current_state = self.states[state_name]

    def run(self):
        while self.context.running:
            next_state = self.current_state.execute(self.context)

            if next_state:
                self.current_state = self.states[next_state]
