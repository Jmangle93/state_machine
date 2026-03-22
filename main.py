# main.py

from vision_service import VisionService
from input_service import InputService
from context import Context
from state_machine import StateMachine
from states.test_click_sequence import TestClickSequenceState

vision = VisionService(threshold=0.80)
input_service = InputService()
context = Context(vision, input_service)

state_machine = StateMachine(context)

state_machine.add_state(TestClickSequenceState())
# state_machine.add_state(NextState("NextState"))   # add your follow-on state here

state_machine.set_start("TestClickSequenceState")
state_machine.run()